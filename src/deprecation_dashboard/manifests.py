"""Lockfile discovery and exact-version extraction for common ecosystems."""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Callable
from pathlib import PurePosixPath

from .models import Package

Parser = Callable[[str], list[Package]]


def parser_for(path: str) -> Parser | None:
    """Choose a parser by basename while excluding vendored dependency trees."""

    if any(part in {"node_modules", "vendor", ".venv"} for part in PurePosixPath(path).parts):
        return None
    name = PurePosixPath(path).name
    exact = {
        "package-lock.json": parse_package_lock,
        "npm-shrinkwrap.json": parse_package_lock,
        "Cargo.lock": parse_cargo_lock,
        "poetry.lock": parse_python_lock,
        "uv.lock": parse_python_lock,
        "Pipfile.lock": parse_pipfile_lock,
        "composer.lock": parse_composer_lock,
        "packages.lock.json": parse_nuget_lock,
        "Gemfile.lock": parse_gemfile_lock,
        "go.sum": parse_go_sum,
        "gradle.lockfile": parse_gradle_lock,
        "pnpm-lock.yaml": parse_pnpm_lock,
        "yarn.lock": parse_yarn_lock,
    }
    if name in exact:
        return exact[name]
    if re.fullmatch(r"requirements(?:[-_.][A-Za-z0-9_.-]+)?\.txt", name, re.IGNORECASE):
        return parse_requirements
    if path.startswith(".github/workflows/") and name.endswith((".yml", ".yaml")):
        return parse_github_actions
    return None


def parse_package_lock(text: str) -> list[Package]:
    data = json.loads(text)
    found: list[Package] = []
    for path, entry in data.get("packages", {}).items():
        if not path or not entry.get("version") or entry.get("link"):
            continue
        name = entry.get("name") or _node_modules_name(path)
        if name:
            found.append(_package("npm", name, str(entry["version"])))
    if found:
        return found

    def visit(dependencies: dict[str, object]) -> None:
        for name, value in dependencies.items():
            if not isinstance(value, dict) or not value.get("version"):
                continue
            found.append(_package("npm", name, str(value["version"])))
            visit(value.get("dependencies", {}))

    visit(data.get("dependencies", {}))
    return found


def parse_cargo_lock(text: str) -> list[Package]:
    return [_package("cargo", item["name"], str(item["version"])) for item in tomllib.loads(text).get("package", [])]


def parse_python_lock(text: str) -> list[Package]:
    return [_package("pypi", item["name"], str(item["version"])) for item in tomllib.loads(text).get("package", [])]


def parse_pipfile_lock(text: str) -> list[Package]:
    data = json.loads(text)
    found = []
    for section in ("default", "develop"):
        for name, item in data.get(section, {}).items():
            version = item.get("version", "") if isinstance(item, dict) else ""
            if version.startswith("=="):
                found.append(_package("pypi", name, version[2:]))
    return found


def parse_requirements(text: str) -> list[Package]:
    found = []
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==([^\s;]+)")
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match:
            found.append(_package("pypi", match.group(1), match.group(2)))
    return found


def parse_composer_lock(text: str) -> list[Package]:
    data = json.loads(text)
    return [
        _package("composer", item["name"], str(item["version"]).lstrip("v"))
        for section in ("packages", "packages-dev")
        for item in data.get(section, [])
    ]


def parse_nuget_lock(text: str) -> list[Package]:
    data = json.loads(text)
    found = []
    for dependencies in data.get("dependencies", {}).values():
        for name, item in dependencies.items():
            version = item.get("resolved") if isinstance(item, dict) else None
            if version:
                found.append(_package("nuget", name, str(version)))
    return found


def parse_gemfile_lock(text: str) -> list[Package]:
    found = []
    in_specs = False
    for line in text.splitlines():
        if line == "GEM":
            in_specs = False
        elif line.strip() == "specs:":
            in_specs = True
        elif in_specs and re.match(r"^    \S", line):
            match = re.match(r"^    ([A-Za-z0-9_.-]+) \(([^ )]+)", line)
            if match:
                found.append(_package("gem", match.group(1), match.group(2)))
        elif in_specs and line and not line.startswith(" "):
            in_specs = False
    return found


def parse_go_sum(text: str) -> list[Package]:
    found = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 2 and not fields[1].endswith("/go.mod"):
            found.append(_package("golang", fields[0], fields[1]))
    return found


def parse_gradle_lock(text: str) -> list[Package]:
    found = []
    for line in text.splitlines():
        coordinate = line.partition("=")[0].strip()
        fields = coordinate.split(":")
        if len(fields) == 3:
            found.append(_package("maven", f"{fields[0]}/{fields[1]}", fields[2]))
    return found


def parse_pnpm_lock(text: str) -> list[Package]:
    found = []
    for line in text.splitlines():
        match = re.match(r"^\s{2,}['\"]?/?((?:@[^/]+/)?[^@:'\"]+)@([^:'\"(]+)", line)
        if match:
            found.append(_package("npm", match.group(1), match.group(2)))
    return found


def parse_yarn_lock(text: str) -> list[Package]:
    found = []
    current_names: list[str] = []
    for line in text.splitlines():
        if line and not line.startswith((" ", "#")) and line.rstrip().endswith(":"):
            current_names = []
            for selector in line[:-1].split(","):
                selector = selector.strip().strip('"\'')
                match = re.match(r"((?:@[^/]+/)?[^@]+)@", selector)
                if match:
                    current_names.append(match.group(1))
        elif current_names:
            match = re.match(r"\s+version\s+[\"']([^\"']+)", line)
            if match:
                found.extend(_package("npm", name, match.group(1)) for name in current_names)
                current_names = []
    return found


def parse_github_actions(text: str) -> list[Package]:
    found = []
    for match in re.finditer(r"\buses:\s*['\"]?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([^\s'\"#]+)", text):
        found.append(_package("githubactions", match.group(1), match.group(2)))
    return found


def _node_modules_name(path: str) -> str:
    tail = path.rsplit("node_modules/", 1)[-1]
    parts = tail.split("/")
    return "/".join(parts[:2]) if tail.startswith("@") else parts[0]


def _package(ecosystem: str, name: str, version: str) -> Package:
    return Package(ecosystem, name, version, f"pkg:{ecosystem}/{name}@{version}")
