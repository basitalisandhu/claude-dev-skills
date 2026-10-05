# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

## [0.1.2] - 2026-10-05

### Changed

- Rewrote five skill descriptions around a phrase a user would type and tightened four more; every description is now double-quoted, under 600 characters and has a "Use when" and a "Not for" sentence. Added a `## Limits` section to the 30 skills without one, boundary lines for skills that overlap with sibling packs, and search phrases to every README.
- Scripts are safer on Windows: UTF-8 stdin, stdout and git output, report paths with forward slashes, LF checkouts via `.gitattributes`, and a `windows-latest` leg in the CI test matrix.
- `scripts/validate_plugins.py` now fails on a description that is unquoted, over 600 characters or missing "Use" or "Not for", and on a skill without `## Limits` before `## Related`, with tests for each rule.

## [0.1.1] - 2026-10-04

### Changed

- Removed the umbrella branding; this project stands alone and links its sibling repositories directly.

### Fixed

- Quoted twelve SKILL.md descriptions that contained a colon so the frontmatter parses under strict YAML readers such as the skills CLI; the validator now fails on unquoted scalars with ': ' or ' #'.

## [0.1.0] - 2026-10-04

### Added

- Plugin marketplace `claude-dev-skills` with six plugins: `code-quality`, `debugging`, `devops`, `data`, `docs`, `security-basics`.
- Forty skills, each with a procedure, an output format and either a tested standard-library script or a reference document.
- `code-quality`: `review-checklist`, `refactor-plan`, `dead-code-finder` (script), `complexity-report` (script), `naming-audit`, `error-handling-review`, `type-coverage` (script), `test-gap-finder` (script).
- `debugging`: `bug-repro-minimiser`, `log-triage` (script), `flaky-test-hunter` (script), `stack-trace-explainer`, `perf-profile-reader` (script), `memory-leak-checklist`.
- `devops`: `dockerfile-hardening` (script), `github-actions-author` (script), `k8s-manifest-review` (script), `terraform-review`, `cron-doctor` (script), `env-diff` (script), `release-notes` (script), `semver-advisor`.
- `data`: `sql-query-review`, `schema-migration-plan`, `csv-profiler` (script), `json-schema-author` (script), `regex-builder` (script), `api-contract-review` (script).
- `docs`: `readme-author`, `adr-writer`, `changelog-keeper` (script), `onboarding-doc`, `api-docs-from-code` (script), `postmortem-writer`.
- `security-basics`: `secrets-hygiene` (script), `dependency-audit-reader` (script), `http-security-headers` (script), `jwt-inspector` (script), `cors-review`, `auth-flow-review`.
- A bundled minimal YAML reader (`_miniyaml.py`) so the GitHub Actions, Kubernetes and OpenAPI linters need no third-party package.
- Repository validator `scripts/validate_plugins.py`, a pytest suite for every script, and a CI workflow that validates the structure, runs the tests on Linux and macOS, and runs `claude plugin validate --strict`.
