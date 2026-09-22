# GitHub Deprecation Radar

[![Daily dependency deprecation scan](https://github.com/marco13-moo/github-deprecation-radar/actions/workflows/deprecation-dashboard.yml/badge.svg)](https://github.com/marco13-moo/github-deprecation-radar/actions/workflows/deprecation-dashboard.yml)

An evidence-based, daily dashboard of deprecated or withdrawn libraries across an account's public GitHub repositories. The workflow inventories repositories, requests each repository's GitHub dependency-graph SBOM, checks package versions against their authoritative registry, and commits this README plus a machine-readable JSON report when the result changes.

<!-- deprecation-dashboard:start -->
_Last refreshed: **2026-09-22T17:07:03.062410Z** · Scope: public repositories owned by **marco13-moo**_

| Repositories | Packages checked | Deprecated | Repos affected | Incomplete coverage |
|---:|---:|---:|---:|---:|
| 20 | 0 | 0 | 0 | 20 |

## Action queue

No registry-confirmed deprecated dependencies were detected in the completed checks.

## Coverage gaps

- [marco13-moo/atlas-platform-fabric](https://github.com/marco13-moo/atlas-platform-fabric): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/cloudspend-guardian](https://github.com/marco13-moo/cloudspend-guardian): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/cron-actions](https://github.com/marco13-moo/cron-actions): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/daily-activity-bot](https://github.com/marco13-moo/daily-activity-bot): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/daily-activity-commits](https://github.com/marco13-moo/daily-activity-commits): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/daily-code-review](https://github.com/marco13-moo/daily-code-review): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/daily-dose-of-devops](https://github.com/marco13-moo/daily-dose-of-devops): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/devsecops-vulnerability-automation](https://github.com/marco13-moo/devsecops-vulnerability-automation): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/finops-carbon-runtime](https://github.com/marco13-moo/finops-carbon-runtime): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/github-achievements-reference](https://github.com/marco13-moo/github-achievements-reference): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/github-dashboard](https://github.com/marco13-moo/github-dashboard): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/github-metrics](https://github.com/marco13-moo/github-metrics): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/ludotheca-share-mesh](https://github.com/marco13-moo/ludotheca-share-mesh): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/marco13-moo](https://github.com/marco13-moo/marco13-moo): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/marco13-moo.github.io](https://github.com/marco13-moo/marco13-moo.github.io): unsupported ecosystems: `github`, `githubactions`
- [marco13-moo/my-setup](https://github.com/marco13-moo/my-setup): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/personal-cron](https://github.com/marco13-moo/personal-cron): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/predictive-reliability-platform](https://github.com/marco13-moo/predictive-reliability-platform): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/self-service-cicd-demo](https://github.com/marco13-moo/self-service-cicd-demo): Dependency graph SBOM unavailable or not enabled
- [marco13-moo/self-service-cicd-platform](https://github.com/marco13-moo/self-service-cicd-platform): Dependency graph SBOM unavailable or not enabled

> A repository is only considered checked where GitHub supplied an SBOM and the package ecosystem has a supported registry signal. A coverage gap is not a clean bill of health.
<!-- deprecation-dashboard:end -->

## What it detects

| Ecosystem | Registry signal | Interpretation |
|---|---|---|
| npm | Version-level `deprecated` message | Publisher explicitly deprecated the installed version |
| PyPI | Yanked release files | Maintainer withdrew the installed release |
| NuGet | Registration `deprecation` metadata | Publisher deprecated the package/version |
| Composer | Packagist `abandoned` metadata | Package is unmaintained, optionally with a replacement |

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
          ▼
Dependency Graph SBOM ── unavailable ──► Coverage gaps
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
