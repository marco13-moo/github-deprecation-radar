"""Command-line entry point for local and GitHub Actions execution."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .config import load_config
from .github import GitHubClient, eligible_repositories
from .http import HttpClient
from .registries import RegistryInspector
from .report import build_payload, render_dashboard, update_readme, write_json
from .scanner import Scanner


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a cross-repository dependency deprecation dashboard.")
    parser.add_argument("--config", type=Path, default=Path("dashboard.yml"))
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--output", type=Path, default=Path("data/dashboard.json"))
    arguments = parser.parse_args()

    config = load_config(arguments.config)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        parser.error("GH_TOKEN or GITHUB_TOKEN is required")
    owner = config.owner or _repository_owner(os.environ.get("GITHUB_REPOSITORY", ""))
    if not owner:
        parser.error("set owner in dashboard.yml or provide GITHUB_REPOSITORY")

    http = HttpClient(timeout=config.request_timeout_seconds)
    github = GitHubClient(http=http, token=token)
    current_repository = os.environ.get("GITHUB_REPOSITORY", "").partition("/")[2]
    excluded = set(config.exclude_repositories)
    if current_repository:
        excluded.add(current_repository)
    inventory = github.list_public_repositories(owner, config.max_repositories)
    repositories = list(
        eligible_repositories(
            inventory,
            include_forks=config.include_forks,
            include_archived=config.include_archived,
            excluded=excluded,
        )
    )
    results = Scanner(github, RegistryInspector(http), config.concurrency).scan(repositories)
    payload = build_payload(owner, results)
    write_json(arguments.output, payload)
    update_readme(arguments.readme, render_dashboard(payload))
    print(
        f"Scanned {payload['summary']['repositories_scanned']} repositories; "
        f"found {payload['summary']['deprecated_dependencies']} deprecated dependencies."
    )
    return 0


def _repository_owner(repository: str) -> str:
    return repository.partition("/")[0]


if __name__ == "__main__":
    raise SystemExit(main())
