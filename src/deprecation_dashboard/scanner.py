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
        packages_by_purl = {}
        sbom_error: str | None = None
        try:
            for package in self.github.dependency_packages(full_name):
                packages_by_purl[package.purl] = package
            result.discovery_sources.add("github-sbom")
        except HttpError as exc:
            if exc.status in {403, 404}:
                sbom_error = "Dependency graph SBOM unavailable or not enabled"
            else:
                sbom_error = str(exc)

        try:
            manifest_packages, manifest_errors = self.github.manifest_packages(repository)
            for package in manifest_packages:
                packages_by_purl[package.purl] = package
            result.lookup_errors.extend(manifest_errors)
            result.discovery_sources.add("repository-lockfiles")
        except (HttpError, RuntimeError) as exc:
            result.lookup_errors.append(f"Manifest discovery failed: {exc}")

        packages = list(packages_by_purl.values())
        if not packages and sbom_error:
            result.error = sbom_error + "; no supported lockfile dependencies were discovered"

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
