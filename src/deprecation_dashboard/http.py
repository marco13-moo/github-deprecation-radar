"""Small retrying HTTP client built solely on the Python standard library."""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class HttpError(RuntimeError):
    """An HTTP request failed after bounded retry processing."""

    def __init__(self, status: int, url: str, message: str) -> None:
        super().__init__(f"HTTP {status} for {url}: {message}")
        self.status = status
        self.url = url


@dataclass(slots=True)
class HttpClient:
    """JSON client with deterministic headers and transient-failure retries."""

    timeout: int = 20
    attempts: int = 3
    user_agent: str = "github-deprecation-radar/1.0"

    def get_json(self, url: str, headers: dict[str, str] | None = None) -> Any:
        return json.loads(self.get_text(url, headers))

    def get_text(self, url: str, headers: dict[str, str] | None = None) -> str:
        """Return decoded response text with the same retry semantics as JSON."""

        merged = {"Accept": "application/json", "User-Agent": self.user_agent}
        merged.update(headers or {})
        for attempt in range(self.attempts):
            request = urllib.request.Request(url, headers=merged)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return response.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                body = exc.read(512).decode("utf-8", errors="replace")
                if exc.code not in {429, 500, 502, 503, 504} or attempt + 1 == self.attempts:
                    raise HttpError(exc.code, url, body) from exc
                retry_after = exc.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt + 1 == self.attempts:
                    raise HttpError(0, url, str(exc)) from exc
                delay = 2**attempt
            time.sleep(delay + random.uniform(0, 0.25))
        raise AssertionError("retry loop exhausted without returning or raising")
