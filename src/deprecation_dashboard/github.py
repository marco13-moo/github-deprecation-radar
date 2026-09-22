"""GitHub repository inventory and dependency-graph SBOM access."""

from __future__ import annotations

import base64
import urllib.parse
from dataclasses import dataclass
from typing import Any, Iterator

from .http import HttpClient
from .models import Package
from .manifests import parser_for


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

    def manifest_packages(self, repository: dict[str, Any]) -> tuple[list[Package], list[str]]:
        """Discover and parse dependency locks directly from a public Git tree."""

        full_name = repository["full_name"]
        quoted = "/".join(urllib.parse.quote(part, safe="") for part in full_name.split("/", 1))
        branch = urllib.parse.quote(repository.get("default_branch") or "main", safe="")
        tree_url = f"https://api.github.com/repos/{quoted}/git/trees/{branch}?recursive=1"
        tree = self.http.get_json(tree_url, self.headers)
        if tree.get("truncated"):
            raise RuntimeError("Git tree was truncated; manifest coverage would be incomplete")

        packages: dict[str, Package] = {}
        errors: list[str] = []
        candidates = [
            item for item in tree.get("tree", [])
            if item.get("type") == "blob"
            and item.get("size", 0) <= 2_000_000
            and parser_for(item.get("path", ""))
        ]
        for item in candidates:
            path = item["path"]
            parser = parser_for(path)
            assert parser is not None
            try:
                blob = self.http.get_json(item["url"], self.headers)
                text = base64.b64decode(blob["content"]).decode("utf-8")
                for package in parser(text):
                    packages[package.purl] = package
            except (ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
                errors.append(f"{path}: unable to parse lockfile ({exc})")
        return list(packages.values()), errors


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
