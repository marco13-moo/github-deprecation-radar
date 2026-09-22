"""Minimal configuration loader with no external YAML dependency."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Config:
    owner: str = ""
    include_forks: bool = False
    include_archived: bool = False
    exclude_repositories: list[str] = field(default_factory=list)
    max_repositories: int = 100
    request_timeout_seconds: int = 20
    concurrency: int = 8


def load_config(path: Path) -> Config:
    """Load the intentionally-flat YAML subset used by dashboard.yml.

    JSON is also accepted because it is a strict YAML subset. Keeping the parser
    small eliminates a bootstrap dependency from the very tool auditing dependencies.
    """

    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("{"):
        return Config(**json.loads(text))

    values: dict[str, object] = {}
    list_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("-") and list_key:
            item = line.split("-", 1)[1].strip().strip('"\'')
            cast_list = values.setdefault(list_key, [])
            assert isinstance(cast_list, list)
            cast_list.append(item)
            continue
        key, raw_value = (part.strip() for part in line.split(":", 1))
        list_key = key if not raw_value or raw_value == "[]" else None
        if not raw_value or raw_value == "[]":
            values[key] = []
        elif raw_value.lower() in {"true", "false"}:
            values[key] = raw_value.lower() == "true"
        elif raw_value.isdigit():
            values[key] = int(raw_value)
        else:
            values[key] = raw_value.strip('"\'')
    return Config(**values)
