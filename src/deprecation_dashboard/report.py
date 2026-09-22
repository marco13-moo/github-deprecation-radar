"""Deterministic JSON and Markdown dashboard rendering."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import RepositoryResult

START_MARKER = "<!-- deprecation-dashboard:start -->"
END_MARKER = "<!-- deprecation-dashboard:end -->"


def build_payload(owner: str, results: list[RepositoryResult], generated_at: datetime | None = None) -> dict[str, object]:
    instant = generated_at or datetime.now(timezone.utc)
    findings = sum(len(result.findings) for result in results)
    incomplete = sum(bool(result.error or result.lookup_errors or result.unsupported_ecosystems) for result in results)
    return {
        "schema_version": 1,
        "generated_at": instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "owner": owner,
        "summary": {
            "repositories_scanned": len(results),
            "packages_checked": sum(result.packages_scanned for result in results),
            "deprecated_dependencies": findings,
            "repositories_with_findings": sum(bool(result.findings) for result in results),
            "repositories_with_incomplete_coverage": incomplete,
        },
        "repositories": [result.as_dict() for result in results],
    }


def render_dashboard(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    assert isinstance(summary, dict)
    repositories = payload["repositories"]
    assert isinstance(repositories, list)
    lines = [
        START_MARKER,
        f"_Last refreshed: **{payload['generated_at']}** · Scope: public repositories owned by **{payload['owner']}**_",
        "",
        "| Repositories | Packages checked | Deprecated | Repos affected | Incomplete coverage |",
        "|---:|---:|---:|---:|---:|",
        f"| {summary['repositories_scanned']} | {summary['packages_checked']} | {summary['deprecated_dependencies']} | {summary['repositories_with_findings']} | {summary['repositories_with_incomplete_coverage']} |",
        "",
        "## Action queue",
        "",
    ]
    findings = [finding for repository in repositories for finding in repository["findings"]]
    if findings:
        lines.extend([
            "| Repository | Ecosystem | Dependency | Signal | Daily remediation step |",
            "|---|---|---|---|---|",
        ])
        for finding in findings:
            package = finding["package"]
            reason = _cell(finding["reason"])
            remediation = _cell(finding["remediation"])
            repo_url = next(repository["url"] for repository in repositories if repository["name"] == finding["repository"])
            lines.append(
                f"| [{finding['repository']}]({repo_url}) | `{package['ecosystem']}` | "
                f"[`{package['name']}@{package['version']}`]({finding['evidence_url']}) | {reason} | {remediation} |"
            )
    else:
        lines.append("No registry-confirmed deprecated dependencies were detected in the completed checks.")

    lines.extend(["", "## Coverage gaps", ""])
    gaps = []
    for repository in repositories:
        reasons = []
        if repository["error"]:
            reasons.append(repository["error"])
        if repository["unsupported_ecosystems"]:
            reasons.append("unsupported ecosystems: " + ", ".join(f"`{item}`" for item in repository["unsupported_ecosystems"]))
        if repository["lookup_errors"]:
            reasons.append(f"{len(repository['lookup_errors'])} registry lookup error(s)")
        if reasons:
            gaps.append(f"- [{repository['name']}]({repository['url']}): " + "; ".join(reasons))
    lines.extend(gaps or ["No coverage gaps were observed during this run."])
    lines.extend(["", "## Discovery coverage", ""])
    lines.extend([
        f"- [{repository['name']}]({repository['url']}): "
        f"{repository['packages_scanned']} supported package(s) checked via "
        f"{', '.join(repository['discovery_sources']) or 'no successful source'}"
        for repository in repositories
    ] or ["No repositories were in scope."])
    lines.extend([
        "",
        "> A repository is only considered checked where GitHub supplied an SBOM and the package ecosystem has a supported registry signal. A coverage gap is not a clean bill of health.",
        END_MARKER,
    ])
    return "\n".join(lines)


def update_readme(path: Path, dashboard: str) -> None:
    content = path.read_text(encoding="utf-8")
    if START_MARKER not in content or END_MARKER not in content:
        raise ValueError("README dashboard markers are missing")
    prefix, remainder = content.split(START_MARKER, 1)
    _, suffix = remainder.split(END_MARKER, 1)
    path.write_text(prefix + dashboard + suffix, encoding="utf-8")


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _cell(value: str) -> str:
    return " ".join(value.replace("|", "\\|").split())
