# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

### Added

- `changelog-keeper show --format github` produces release-body categories, bullets and an optional compare link without changing default or JSON output.

## [0.2.1] - 2026-10-05

### Changed

- Every skill description now carries a double-quoted phrase a user would type. Added one to the 28 descriptions without it (adr-writer, api-contract-review, api-docs-from-code, changelog-keeper, complexity-report, cors-review, cron-doctor, csv-profiler, dead-code-finder, dependency-audit-reader, dockerfile-hardening, github-actions-author, json-schema-author, jwt-inspector, k8s-manifest-review, memory-leak-checklist, onboarding-doc, perf-profile-reader, postmortem-writer, readme-author, regex-builder, release-notes, schema-migration-plan, sql-query-review, stack-trace-explainer, terraform-review, test-gap-finder, type-coverage), and postmortem-writer now has a "Use when" sentence.
- Reworded cron-doctor, dead-code-finder, dockerfile-hardening and regex-builder around how people ask for them (goal first, user wording such as "review my Dockerfile"); recall on the labelled trigger prompts rose from 0.40, 0.60, 0.40 and 0.40 to 1.00, 1.00, 1.00 and 0.80, with precision unchanged at 1.00.
- `scripts/validate_plugins.py` now fails on a description without a double-quoted trigger phrase of 2 to 8 words, with tests.

## [0.2.0] - 2026-10-05

### Added

- csv-profiler: the dialect report now says whether quoted fields escape quotes by doubling them, and detects CRLF, BOM and mixed line endings (contributed by echomehran in #14, closes #8).

- `terraform-apply-gate` (devops, script): checks a saved Terraform plan (`terraform show -json`) against a small YAML policy (forbidden destroys by resource type, required tags, a replacement and delete ceiling, protected names, allowed providers) and prints an allow, ask or block verdict with a reason per resource; exit 0 allow, 1 ask or block, 2 bad input.
- `diff-security-review` (security-basics, script): scans the added lines of a saved `git diff` or `gh pr diff` for new network calls, shell and process execution, unsafe deserialisation, SQL built from strings, credential-shaped literals (redacted), disabled TLS checks and new permissions in workflows and manifests, with file and line, for a reader to judge in context.

### Changed

- `terraform-review` and `review-checklist` now point to the new skills for plan gating and the security pass on a diff.

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
