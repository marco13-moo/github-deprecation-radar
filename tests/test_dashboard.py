from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from deprecation_dashboard.config import load_config
from deprecation_dashboard.github import eligible_repositories, parse_purl
from deprecation_dashboard.models import Finding, Package, RepositoryResult
from deprecation_dashboard.manifests import (
    parse_cargo_lock,
    parse_gemfile_lock,
    parse_github_actions,
    parse_go_sum,
    parse_package_lock,
    parse_requirements,
)
from deprecation_dashboard.registries import _go_retractions, _version_between
from deprecation_dashboard.report import END_MARKER, START_MARKER, build_payload, render_dashboard, update_readme


class ConfigurationTests(unittest.TestCase):
    def test_loads_supported_yaml_subset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "dashboard.yml")
            path.write_text('owner: "octocat"\ninclude_forks: true\nexclude_repositories:\n  - archive\n', encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.owner, "octocat")
        self.assertTrue(config.include_forks)
        self.assertEqual(config.exclude_repositories, ["archive"])


class GitHubNormalizationTests(unittest.TestCase):
    def test_parses_scoped_npm_purl(self) -> None:
        package = parse_purl("pkg:npm/%40scope/tool@2.1.0")
        self.assertIsNotNone(package)
        assert package is not None
        self.assertEqual((package.ecosystem, package.name, package.version), ("npm", "@scope/tool", "2.1.0"))

    def test_filters_non_actionable_repositories(self) -> None:
        repositories = [
            {"name": "live", "private": False, "fork": False, "archived": False},
            {"name": "fork", "private": False, "fork": True, "archived": False},
            {"name": "old", "private": False, "fork": False, "archived": True},
            {"name": "secret", "private": True, "fork": False, "archived": False},
        ]
        actual = list(eligible_repositories(repositories, include_forks=False, include_archived=False, excluded=set()))
        self.assertEqual([repository["name"] for repository in actual], ["live"])


class ManifestParsingTests(unittest.TestCase):
    def test_extracts_npm_v3_lock_packages(self) -> None:
        packages = parse_package_lock('{"packages":{"":{"name":"app","version":"1.0.0"},"node_modules/left-pad":{"version":"1.3.0"}}}')
        self.assertEqual([(item.name, item.version) for item in packages], [("left-pad", "1.3.0")])

    def test_extracts_python_pins(self) -> None:
        packages = parse_requirements("requests==2.32.5\nunpinned>=1\nrich[pretty]==14.1.0; python_version > '3.10'\n")
        self.assertEqual([(item.name, item.version) for item in packages], [("requests", "2.32.5"), ("rich", "14.1.0")])

    def test_extracts_cargo_go_gem_and_actions(self) -> None:
        cargo = parse_cargo_lock('[[package]]\nname = "serde"\nversion = "1.0.0"\n')
        go = parse_go_sum("golang.org/x/text v0.3.0 h1:abc\ngolang.org/x/text v0.3.0/go.mod h1:def\n")
        gems = parse_gemfile_lock("GEM\n  specs:\n    rake (13.2.1)\n\nPLATFORMS\n")
        actions = parse_github_actions("steps:\n  - uses: actions/checkout@v5\n")
        self.assertEqual(cargo[0].ecosystem, "cargo")
        self.assertEqual(go[0].purl, "pkg:golang/golang.org/x/text@v0.3.0")
        self.assertEqual(gems[0].name, "rake")
        self.assertEqual(actions[0].name, "actions/checkout")

    def test_parses_go_retraction_ranges(self) -> None:
        values = _go_retractions("retract (\n v1.0.0 // broken\n [v1.2.0, v1.2.4] // regression\n)\n")
        self.assertEqual(values[0], ("v1.0.0", "v1.0.0", "broken"))
        self.assertTrue(_version_between("v1.2.3", values[1][0], values[1][1]))
        self.assertFalse(_version_between("v1.3.0", values[1][0], values[1][1]))


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        package = Package("npm", "legacy-lib", "1.0.0", "pkg:npm/legacy-lib@1.0.0")
        finding = Finding(
            "octocat/example",
            package,
            "warning",
            "Use maintained-lib instead",
            "Replace the package and test the lockfile.",
            "https://www.npmjs.com/package/legacy-lib/v/1.0.0",
        )
        self.result = RepositoryResult(
            "octocat/example",
            "https://github.com/octocat/example",
            findings=[finding],
            packages_scanned=3,
            unsupported_ecosystems={"cargo"},
        )

    def test_payload_and_markdown_are_deterministic(self) -> None:
        instant = datetime(2026, 9, 18, 6, 17, tzinfo=timezone.utc)
        payload = build_payload("octocat", [self.result], instant)
        dashboard = render_dashboard(payload)
        self.assertEqual(payload["summary"]["deprecated_dependencies"], 1)
        self.assertIn("legacy-lib@1.0.0", dashboard)
        self.assertIn("unsupported ecosystems: `cargo`", dashboard)

    def test_updates_only_marker_region(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "README.md")
            path.write_text(f"before\n{START_MARKER}\nold\n{END_MARKER}\nafter\n", encoding="utf-8")
            update_readme(path, f"{START_MARKER}\nnew\n{END_MARKER}")
            self.assertEqual(path.read_text(encoding="utf-8"), f"before\n{START_MARKER}\nnew\n{END_MARKER}\nafter\n")

    def test_payload_is_json_serializable(self) -> None:
        json.dumps(build_payload("octocat", [self.result]))


if __name__ == "__main__":
    unittest.main()
