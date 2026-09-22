"""Registry-native deprecation probes with thread-safe memoization."""

from __future__ import annotations

import re
import threading
import urllib.parse
from dataclasses import dataclass
from typing import Callable

from .http import HttpClient, HttpError
from .models import Package


@dataclass(frozen=True, slots=True)
class RegistryVerdict:
    deprecated: bool
    reason: str = ""
    remediation: str = ""
    evidence_url: str = ""
    severity: str = "warning"


class RegistryInspector:
    """Resolve authoritative deprecation metadata for supported ecosystems."""

    def __init__(self, http: HttpClient) -> None:
        self.http = http
        self._cache: dict[str, RegistryVerdict] = {}
        self._lock = threading.Lock()
        self._probes: dict[str, Callable[[Package], RegistryVerdict]] = {
            "npm": self._npm,
            "pypi": self._pypi,
            "nuget": self._nuget,
            "composer": self._composer,
            "cargo": self._cargo,
            "golang": self._golang,
            "gem": self._gem,
            "github": self._github,
            "githubactions": self._github,
        }

    @property
    def supported_ecosystems(self) -> frozenset[str]:
        return frozenset(self._probes)

    def inspect(self, package: Package) -> RegistryVerdict:
        with self._lock:
            cached = self._cache.get(package.purl)
        if cached is not None:
            return cached
        probe = self._probes.get(package.ecosystem)
        verdict = probe(package) if probe else RegistryVerdict(False)
        with self._lock:
            self._cache[package.purl] = verdict
        return verdict

    def _npm(self, package: Package) -> RegistryVerdict:
        encoded_name = urllib.parse.quote(package.name, safe="@")
        encoded_version = urllib.parse.quote(package.version, safe="")
        api_url = f"https://registry.npmjs.org/{encoded_name}/{encoded_version}"
        metadata = self.http.get_json(api_url)
        reason = metadata.get("deprecated")
        if not reason:
            return RegistryVerdict(False)
        homepage = f"https://www.npmjs.com/package/{encoded_name}/v/{encoded_version}"
        return RegistryVerdict(
            True,
            str(reason),
            "Replace the package as directed by its npm deprecation notice, then regenerate and test the lockfile.",
            homepage,
            "critical" if "security" in str(reason).lower() else "warning",
        )

    def _pypi(self, package: Package) -> RegistryVerdict:
        name = urllib.parse.quote(package.name, safe="")
        version = urllib.parse.quote(package.version, safe="")
        api_url = f"https://pypi.org/pypi/{name}/{version}/json"
        metadata = self.http.get_json(api_url)
        files = metadata.get("urls", [])
        yanked = [artifact for artifact in files if artifact.get("yanked")]
        if not yanked:
            return RegistryVerdict(False)
        reasons = sorted({str(item.get("yanked_reason") or "Release withdrawn by its maintainer") for item in yanked})
        return RegistryVerdict(
            True,
            "; ".join(reasons),
            "Upgrade to the newest compatible, non-yanked release and re-lock dependencies before running the test suite.",
            f"https://pypi.org/project/{name}/{version}/",
            "warning",
        )

    def _nuget(self, package: Package) -> RegistryVerdict:
        package_id = urllib.parse.quote(package.name.lower(), safe="")
        version = urllib.parse.quote(package.version.lower(), safe="")
        api_url = f"https://api.nuget.org/v3/registration5-gz-semver2/{package_id}/{version}.json"
        metadata = self.http.get_json(api_url)
        deprecation = metadata.get("catalogEntry", metadata).get("deprecation")
        if not deprecation:
            return RegistryVerdict(False)
        reasons = ", ".join(deprecation.get("reasons", [])) or "Package deprecated by its publisher"
        alternates = deprecation.get("alternatePackage", {})
        alternative = alternates.get("id")
        remediation = (
            f"Migrate to {alternative} and validate the resulting transitive dependency graph."
            if alternative
            else "Upgrade or replace the package according to the NuGet deprecation advisory."
        )
        return RegistryVerdict(True, reasons, remediation, f"https://www.nuget.org/packages/{package.name}/{package.version}")

    def _composer(self, package: Package) -> RegistryVerdict:
        encoded = urllib.parse.quote(package.name, safe="/")
        api_url = f"https://repo.packagist.org/p2/{encoded}.json"
        metadata = self.http.get_json(api_url)
        versions = metadata.get("packages", {}).get(package.name, [])
        record = next((item for item in versions if item.get("version_normalized", "").rstrip(".0") == package.version.rstrip(".0")), None)
        abandoned = (record or {}).get("abandoned")
        if not abandoned:
            return RegistryVerdict(False)
        replacement = abandoned if isinstance(abandoned, str) else None
        remediation = (
            f"Replace this package with {replacement}, update composer.lock, and execute application tests."
            if replacement
            else "Select a maintained replacement, update composer.lock, and execute application tests."
        )
        return RegistryVerdict(
            True,
            "Package is marked abandoned on Packagist.",
            remediation,
            f"https://packagist.org/packages/{package.name}",
        )

    def _cargo(self, package: Package) -> RegistryVerdict:
        name = urllib.parse.quote(package.name, safe="")
        version = urllib.parse.quote(package.version, safe="")
        metadata = self.http.get_json(f"https://crates.io/api/v1/crates/{name}/{version}")
        record = metadata.get("version", {})
        if not record.get("yanked"):
            return RegistryVerdict(False)
        return RegistryVerdict(
            True,
            "Crate version was yanked by its publisher.",
            "Upgrade to a non-yanked compatible crate version, update Cargo.lock, and run cargo test.",
            f"https://crates.io/crates/{name}/{version}",
        )

    def _gem(self, package: Package) -> RegistryVerdict:
        name = urllib.parse.quote(package.name, safe="")
        version = urllib.parse.quote(package.version, safe="")
        metadata = self.http.get_json(f"https://rubygems.org/api/v2/rubygems/{name}/versions/{version}.json")
        if not metadata.get("yanked"):
            return RegistryVerdict(False)
        return RegistryVerdict(
            True,
            "Gem version was yanked from RubyGems.org.",
            "Upgrade to an available release, update Gemfile.lock, and execute the Ruby test suite.",
            f"https://rubygems.org/gems/{name}/versions/{version}",
        )

    def _github(self, package: Package) -> RegistryVerdict:
        repository = package.name.removeprefix("github.com/")
        if repository.count("/") < 1:
            return RegistryVerdict(False)
        quoted = "/".join(urllib.parse.quote(part, safe="") for part in repository.split("/")[:2])
        metadata = self.http.get_json(f"https://api.github.com/repos/{quoted}")
        if not metadata.get("archived"):
            return RegistryVerdict(False)
        return RegistryVerdict(
            True,
            "Upstream GitHub repository is archived and read-only.",
            "Migrate to a maintained alternative or a supported successor before updating the lock or workflow file.",
            metadata.get("html_url", f"https://github.com/{quoted}"),
        )

    def _golang(self, package: Package) -> RegistryVerdict:
        escaped = _escape_go_module(package.name)
        latest = self.http.get_json(f"https://proxy.golang.org/{escaped}/@latest")
        latest_version = latest.get("Version", "")
        if not latest_version:
            return RegistryVerdict(False)
        encoded_version = urllib.parse.quote(latest_version, safe="+-.!")
        go_mod = self.http.get_text(
            f"https://proxy.golang.org/{escaped}/@v/{encoded_version}.mod",
            {"Accept": "text/plain"},
        )
        retractions = _go_retractions(go_mod)
        matching = next((reason for low, high, reason in retractions if _version_between(package.version, low, high)), None)
        if matching is None:
            return RegistryVerdict(False)
        return RegistryVerdict(
            True,
            matching or "Module version was retracted by its publisher.",
            "Upgrade or downgrade to a non-retracted module version, run go mod tidy, and execute go test ./....",
            f"https://pkg.go.dev/{package.name}@{package.version}",
        )


def safe_inspect(inspector: RegistryInspector, package: Package) -> RegistryVerdict:
    """Treat a registry read failure as unknown, never as evidence of health."""

    try:
        return inspector.inspect(package)
    except (HttpError, KeyError, TypeError, ValueError) as exc:
        return RegistryVerdict(False, reason=f"Registry lookup failed: {exc}", severity="unknown")


def _escape_go_module(name: str) -> str:
    return "".join("!" + character.lower() if character.isupper() else character for character in name)


def _go_retractions(go_mod: str) -> list[tuple[str, str, str]]:
    """Parse exact and interval retract directives from the latest go.mod."""

    found = []
    in_block = False
    for raw_line in go_mod.splitlines():
        line, _, comment = raw_line.partition("//")
        stripped = line.strip()
        if stripped == "retract (":
            in_block = True
            continue
        if in_block and stripped == ")":
            in_block = False
            continue
        value = stripped.removeprefix("retract ").strip() if stripped.startswith("retract ") else stripped if in_block else ""
        if not value:
            continue
        interval = re.fullmatch(r"\[\s*([^,]+),\s*([^]]+)\s*]", value)
        if interval:
            found.append((interval.group(1).strip(), interval.group(2).strip(), comment.strip()))
        elif re.fullmatch(r"v[0-9][^\s]*", value):
            found.append((value, value, comment.strip()))
    return found


def _version_between(version: str, low: str, high: str) -> bool:
    def key(value: str) -> tuple[tuple[int, object], ...]:
        return tuple((0, int(part)) if part.isdigit() else (1, part) for part in re.split(r"[.+-]", value.lstrip("v")))

    return key(low) <= key(version) <= key(high)
