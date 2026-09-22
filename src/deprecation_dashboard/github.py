"""GitHub repository inventory and dependency-graph SBOM access."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Any, Iterator

from .http import HttpClient
from .models import Package


@dataclass(slots=True)
class GitHubClient:
    http: HttpClient
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def list_public_repositories(self, owner: str, limit: int) -> list[dict[str, Any]]:
        """Return public repositories for either a user or organization owner."""

        encoded = urllib.parse.quote(owner, safe="")
        endpoint = f"https://api.github.com/users/{encoded}/repos"
        repositories: list[dict[str, Any]] = []
        page = 1
        while len(repositories) < limit:
            url = f"{endpoint}?type=public&sort=full_name&per_page=100&page={page}"
            batch = self.http.get_json(url, self.headers)
            if not isinstance(batch, list):
                raise TypeError("GitHub repository response was not a list")
            repositories.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return repositories[:limit]

    def dependency_packages(self, full_name: str) -> list[Package]:
        """Fetch and normalize the repository's SPDX dependency-graph export."""

        quoted = "/".join(urllib.parse.quote(part, safe="") for part in full_name.split("/", 1))
        url = f"https://api.github.com/repos/{quoted}/dependency-graph/sbom"
        payload = self.http.get_json(url, self.headers)
        packages = payload.get("sbom", {}).get("packages", [])
        normalized: dict[str, Package] = {}
        for entry in packages:
            purl = next(
                (
                    reference.get("referenceLocator", "")
                    for reference in entry.get("externalRefs", [])
                    if reference.get("referenceType") == "purl"
                ),
                "",
            )
            package = parse_purl(purl)
            if package:
                normalized[purl] = package
        return list(normalized.values())


def parse_purl(purl: str) -> Package | None:
    """Parse the Package URL subset emitted by GitHub's SPDX endpoint."""

    if not purl.startswith("pkg:") or "@" not in purl:
        return None
    coordinate = purl[4:].split("?", 1)[0].split("#", 1)[0]
    path, version = coordinate.rsplit("@", 1)
    ecosystem, separator, name = path.partition("/")
    if not separator or not version:
        return None
    return Package(
        ecosystem=ecosystem.lower(),
        name=urllib.parse.unquote(name),
        version=urllib.parse.unquote(version),
        purl=purl,
    )


def eligible_repositories(
    repositories: list[dict[str, Any]],
    *,
    include_forks: bool,
    include_archived: bool,
    excluded: set[str],
) -> Iterator[dict[str, Any]]:
    """Apply actionability filters without silently discarding private state."""

    for repository in repositories:
        if repository.get("private", True):
            continue
        if repository.get("fork") and not include_forks:
            continue
        if repository.get("archived") and not include_archived:
            continue
        if repository.get("name") in excluded:
            continue
        yield repository

