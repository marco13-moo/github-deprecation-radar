# GitHub Deprecation Radar

[![Daily dependency deprecation scan](https://github.com/marco13-moo/github-deprecation-radar/actions/workflows/deprecation-dashboard.yml/badge.svg)](https://github.com/marco13-moo/github-deprecation-radar/actions/workflows/deprecation-dashboard.yml)

An evidence-based, daily dashboard of deprecated or withdrawn libraries across an account's public GitHub repositories. The workflow inventories repositories, combines GitHub dependency-graph SBOMs with direct lockfile discovery, checks exact package versions against authoritative registries, and commits this README plus a machine-readable JSON report when the result changes.

## What changed

The September 2026 coverage upgrade removed the GitHub SBOM endpoint as a single point of failure:

- Added public Git-tree discovery and exact-version parsing for npm, pnpm, Yarn, Python requirements, Poetry, uv, Pipenv, Cargo, Go, RubyGems, Composer, NuGet, and Gradle lockfiles.
- Expanded authoritative deprecation signals from four ecosystems to npm, PyPI, NuGet, Composer, Cargo, Go modules, RubyGems, and GitHub-hosted dependencies such as Actions.
- Added per-repository discovery provenance so the dashboard identifies whether evidence came from an SBOM, repository lockfiles, or both.
- Reduced incomplete repository coverage from 20 repositories to 6 and increased verified package checks from 0 to 112 in the first upgraded run.
- Added offline parser and Go-retraction tests while preserving explicit coverage gaps for unavailable repositories, unsupported metadata, and registry failures.

See [`data/dashboard.json`](data/dashboard.json) for the complete machine-readable result and [the workflow history](https://github.com/marco13-moo/github-deprecation-radar/actions/workflows/deprecation-dashboard.yml) for execution evidence.

<!-- deprecation-dashboard:start -->
_Last refreshed: **2026-09-24T11:40:47.563486Z** · Scope: public repositories owned by **marco13-moo**_

| Repositories | Packages checked | Deprecated | Repos affected | Incomplete coverage |
|---:|---:|---:|---:|---:|
| 20 | 112 | 0 | 0 | 6 |

## Action queue

No registry-confirmed deprecated dependencies were detected in the completed checks.

## Coverage gaps

- [marco13-moo/atlas-platform-fabric](https://github.com/marco13-moo/atlas-platform-fabric): Dependency graph SBOM unavailable or not enabled; no supported lockfile dependencies were discovered; 1 registry lookup error(s)
- [marco13-moo/github-achievements-reference](https://github.com/marco13-moo/github-achievements-reference): Dependency graph SBOM unavailable or not enabled; no supported lockfile dependencies were discovered
- [marco13-moo/ludotheca-share-mesh](https://github.com/marco13-moo/ludotheca-share-mesh): Dependency graph SBOM unavailable or not enabled; no supported lockfile dependencies were discovered
- [marco13-moo/marco13-moo](https://github.com/marco13-moo/marco13-moo): Dependency graph SBOM unavailable or not enabled; no supported lockfile dependencies were discovered
- [marco13-moo/my-setup](https://github.com/marco13-moo/my-setup): Dependency graph SBOM unavailable or not enabled; no supported lockfile dependencies were discovered
- [marco13-moo/self-service-cicd-demo](https://github.com/marco13-moo/self-service-cicd-demo): Dependency graph SBOM unavailable or not enabled; no supported lockfile dependencies were discovered

## Discovery coverage

- [marco13-moo/atlas-platform-fabric](https://github.com/marco13-moo/atlas-platform-fabric): 0 supported package(s) checked via no successful source
- [marco13-moo/cloudspend-guardian](https://github.com/marco13-moo/cloudspend-guardian): 4 supported package(s) checked via repository-lockfiles
- [marco13-moo/cron-actions](https://github.com/marco13-moo/cron-actions): 1 supported package(s) checked via repository-lockfiles
- [marco13-moo/daily-activity-bot](https://github.com/marco13-moo/daily-activity-bot): 1 supported package(s) checked via repository-lockfiles
- [marco13-moo/daily-activity-commits](https://github.com/marco13-moo/daily-activity-commits): 1 supported package(s) checked via repository-lockfiles
- [marco13-moo/daily-code-review](https://github.com/marco13-moo/daily-code-review): 2 supported package(s) checked via repository-lockfiles
- [marco13-moo/daily-dose-of-devops](https://github.com/marco13-moo/daily-dose-of-devops): 8 supported package(s) checked via repository-lockfiles
- [marco13-moo/devsecops-vulnerability-automation](https://github.com/marco13-moo/devsecops-vulnerability-automation): 4 supported package(s) checked via repository-lockfiles
- [marco13-moo/finops-carbon-runtime](https://github.com/marco13-moo/finops-carbon-runtime): 2 supported package(s) checked via repository-lockfiles
- [marco13-moo/github-achievements-reference](https://github.com/marco13-moo/github-achievements-reference): 0 supported package(s) checked via repository-lockfiles
- [marco13-moo/github-dashboard](https://github.com/marco13-moo/github-dashboard): 2 supported package(s) checked via repository-lockfiles
- [marco13-moo/github-metrics](https://github.com/marco13-moo/github-metrics): 1 supported package(s) checked via repository-lockfiles
- [marco13-moo/ludotheca-share-mesh](https://github.com/marco13-moo/ludotheca-share-mesh): 0 supported package(s) checked via repository-lockfiles
- [marco13-moo/marco13-moo](https://github.com/marco13-moo/marco13-moo): 0 supported package(s) checked via repository-lockfiles
- [marco13-moo/marco13-moo.github.io](https://github.com/marco13-moo/marco13-moo.github.io): 3 supported package(s) checked via github-sbom, repository-lockfiles
- [marco13-moo/my-setup](https://github.com/marco13-moo/my-setup): 0 supported package(s) checked via repository-lockfiles
- [marco13-moo/personal-cron](https://github.com/marco13-moo/personal-cron): 1 supported package(s) checked via repository-lockfiles
- [marco13-moo/predictive-reliability-platform](https://github.com/marco13-moo/predictive-reliability-platform): 2 supported package(s) checked via repository-lockfiles
- [marco13-moo/self-service-cicd-demo](https://github.com/marco13-moo/self-service-cicd-demo): 0 supported package(s) checked via repository-lockfiles
- [marco13-moo/self-service-cicd-platform](https://github.com/marco13-moo/self-service-cicd-platform): 80 supported package(s) checked via repository-lockfiles

> A dependency is only considered checked when an exact version came from an SBOM or supported lockfile and its ecosystem has an authoritative registry signal. A coverage gap is not a clean bill of health.
<!-- deprecation-dashboard:end -->

## What it detects

| Ecosystem | Registry signal | Interpretation |
|---|---|---|
| npm | Version-level `deprecated` message | Publisher explicitly deprecated the installed version |
| PyPI | Yanked release files | Maintainer withdrew the installed release |
| NuGet | Registration `deprecation` metadata | Publisher deprecated the package/version |
| Composer | Packagist `abandoned` metadata | Package is unmaintained, optionally with a replacement |
| Cargo | crates.io `yanked` metadata | Publisher withdrew the installed crate version |
| Go modules | `retract` directives in the publisher's latest `go.mod` | Publisher declared the installed module version unsuitable |
| RubyGems | Version-level `yanked` metadata | Publisher removed the installed gem version |
| GitHub Actions / GitHub packages | Repository `archived` state | Upstream source is permanently read-only |

Other ecosystems are shown under **Coverage gaps**. The scanner does not conflate “no supported signal” with “healthy.” Vulnerabilities and ordinary available upgrades are deliberately outside this dashboard's scope; Dependabot or Renovate should complement it.

## Daily remediation loop

1. Open the first item in the **Action queue** and review its registry evidence.
2. Apply the prescribed replacement or upgrade in a short-lived branch.
3. Regenerate the ecosystem lockfile; do not edit resolved versions by hand.
4. Run unit, integration, compatibility, license, and vulnerability checks.
5. Merge only after required checks pass, then confirm the next daily run removes the finding.
6. Triage **Coverage gaps** separately by enabling dependency graphs, retrying registry failures, or adding a registry adapter.

## Installation

1. Fork or copy this repository into the GitHub account you want to scan.
2. Optionally set `owner` and exclusions in [`dashboard.yml`](dashboard.yml). By default, the workflow infers the owner from this repository.
3. Enable **Settings → Actions → General → Workflow permissions → Read and write permissions** so the workflow can commit dashboard changes.
4. Enable the dependency graph on repositories being scanned. For broader or organization-restricted access, create a fine-grained token with read-only **Contents** and **Metadata** access and save it as `DASHBOARD_TOKEN` in this repository. Public repositories ordinarily work with the workflow token.
5. Run **Daily dependency deprecation scan** manually once. It subsequently runs every day.

The workflow excludes itself, forks, archived repositories, and private repositories by default. It never changes scanned repositories or opens pull requests.

## Local execution

```bash
export GH_TOKEN="$(gh auth token)"
PYTHONPATH=src python -m deprecation_dashboard.cli
PYTHONPATH=src python -m unittest discover -s tests -v
```

Python 3.11 or newer is required. Runtime dependencies are intentionally limited to the standard library.

## Architecture

```text
GitHub repository inventory
          │
          ├── Dependency Graph SBOM
          └── Public Git tree ──► exact-version lockfile parsers
          │
          ▼
Package URL normalization
          │
          ├── supported registry ──► deprecation evidence ──► Action queue
          └── unsupported registry ─────────────────────────► Coverage gaps
```

`data/dashboard.json` is the canonical structured artifact. README content between the dashboard markers is a deterministic projection of that data.

## Security and operational properties

- Least-privilege workflow permissions: repository contents are writable only so the generated report can be committed.
- Bounded concurrency, request timeouts, and exponential retry for transient failures.
- No secrets are written to output, logs, generated JSON, or the README.
- Registry or SBOM failures remain visible as incomplete coverage.
- The workflow stages only the generated README and JSON artifact.

## Contributing

Registry adapters should consume an authoritative publisher signal, distinguish “unknown” from “not deprecated,” include an evidence URL, and ship with offline tests. Please do not infer deprecation solely from package age or inactivity.

## License

MIT © Marco
