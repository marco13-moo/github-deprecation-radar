"""Concurrent orchestration for repository and registry inspection."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from .github import GitHubClient
from .http import HttpError
from .models import Finding, RepositoryResult
from .registries import RegistryInspector, safe_inspect


@dataclass(slots=True)
class Scanner:
    github: GitHubClient
    registries: RegistryInspector
    concurrency: int = 8

    def scan(self, repositories: list[dict[str, Any]]) -> list[RepositoryResult]:
        """Scan repositories concurrently while returning stable, sorted output."""

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = {executor.submit(self._scan_repository, repository): repository for repository in repositories}
            results = [future.result() for future in as_completed(futures)]
        return sorted(results, key=lambda result: result.name.casefold())

    def _scan_repository(self, repository: dict[str, Any]) -> RepositoryResult:
        full_name = repository["full_name"]
        result = RepositoryResult(name=full_name, url=repository["html_url"])
        try:
            packages = self.github.dependency_packages(full_name)
        except HttpError as exc:
            if exc.status in {403, 404}:
                result.error = "Dependency graph SBOM unavailable or not enabled"
            else:
                result.error = str(exc)
            return result

        for package in packages:
            if package.ecosystem not in self.registries.supported_ecosystems:
                result.unsupported_ecosystems.add(package.ecosystem)
                continue
            verdict = safe_inspect(self.registries, package)
            if verdict.severity == "unknown":
                result.lookup_errors.append(f"{package.name}@{package.version}: {verdict.reason}")
                continue
            result.packages_scanned += 1
            if verdict.deprecated:
                result.findings.append(
                    Finding(
                        repository=full_name,
                        package=package,
                        severity=verdict.severity,
                        reason=verdict.reason,
                        remediation=verdict.remediation,
                        evidence_url=verdict.evidence_url,
                    )
                )
        result.findings.sort(key=lambda finding: (finding.package.ecosystem, finding.package.name.casefold()))
        return result
