"""Domain objects kept deliberately independent from transport concerns."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Package:
    """A concrete package version extracted from a GitHub dependency SBOM."""

    ecosystem: str
    name: str
    version: str
    purl: str


@dataclass(frozen=True, slots=True)
class Finding:
    """A registry-backed deprecation or withdrawal finding."""

    repository: str
    package: Package
    severity: str
    reason: str
    remediation: str
    evidence_url: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RepositoryResult:
    """Findings and coverage state for one repository."""

    name: str
    url: str
    findings: list[Finding] = field(default_factory=list)
    packages_scanned: int = 0
    unsupported_ecosystems: set[str] = field(default_factory=set)
    lookup_errors: list[str] = field(default_factory=list)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "findings": [finding.as_dict() for finding in self.findings],
            "packages_scanned": self.packages_scanned,
            "unsupported_ecosystems": sorted(self.unsupported_ecosystems),
            "lookup_errors": self.lookup_errors,
            "error": self.error,
        }
