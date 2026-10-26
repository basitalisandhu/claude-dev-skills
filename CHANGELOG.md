# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

## [0.4.1] - 2026-10-26

### Fixed

- The bundled YAML reader (`_miniyaml.py` in `api-contract-review`, `github-actions-author`, `k8s-manifest-review` and `terraform-apply-gate`) looped for ever on a malformed sequence such as `- - -:`, so `openapi_lint.py`, `gha_lint.py`, `k8s_review.py` and `terraform_apply_gate.py --policy` hung instead of exiting 2. A sequence item that consumes no input now raises a YAML error ("cannot parse this sequence item"). The same reader raised `TypeError` on a flow collection used as a mapping key (`[[a]: 1]`) and `IndexError` on a document start followed only by an anchor or tag (`--- &x`); the first is now a YAML error and the second an empty document. The sequence and flow-key fixes are equivalent to the ones in m365-governance-skills 0.6.0.
- `tests/test_miniyaml.py` runs the inputs above and 3,000 seeded random YAML fragments against every copy in a child process under a 60-second timeout, so a new hang fails the test instead of stalling CI. 200,000 fragments run clean locally.

## [0.4.0] - 2026-10-26

### Added

- `log-triage`: `--since` and `--until` keep a time window (#6). The first timestamp in each line decides, in ISO 8601, Apache access-log or syslog format (syslog has no year and is read as the current year); a line without a timestamp follows the line before it, so stack traces stay with their message. A date alone covers the whole day, no offset means UTC, and `--until` before `--since` exits 2. The JSON report gains a `window` object with the lines left outside.
- A README in every skill folder (42). For the 25 skills with a script it shows the command and a real sample on a committed fixture in `tests/fixtures/<skill>/`; `scripts/render_samples.py` refreshes them and `tests/test_skill_readmes.py` fails when a sample no longer matches the script.
- `tests/test_fuzz_inputs.py`: seeded fuzzing of every script that reads a file (26 cases: slices deleted or repeated, junk tokens, swapped lines, truncation, invalid UTF-8, and JSON values swapped for other types), plus regression tests for each crash it found. Replay a failure with `FUZZ_SEED`; run longer with `FUZZ_ROUNDS`.
- `tests/test_integration_release_chain.py`: release notes from a captured git log are added to a CHANGELOG with `changelog.py add`, released with `changelog.py release`, and `check`, `latest` and `show` must agree with the notes.
- `tests/test_performance.py`: large JavaScript and TypeScript inputs must finish well under the old quadratic times.

### Fixed

- Crashes found by the fuzzer now exit 2 with the file and the reason, instead of a traceback: `api-contract-review` (an `info` or `servers` of the wrong type), `k8s-manifest-review` (a `template`, `securityContext` or container that is not a mapping), `github-actions-author` and `k8s-manifest-review` (parse errors are now also printed to stderr, where an exit 2 had no message), `terraform-apply-gate` (a plan or policy that is not UTF-8, actions or attributes of the wrong type), `dependency-audit-reader` (ids, names or fix versions of the wrong type) and `dockerfile-hardening` (a final `FROM` with no image).
- `csv-profiler`: a value such as `1e999` that overflows to infinity made the statistics crash; non-finite numbers now count as text.
- `secrets-hygiene`: the fingerprint of an unignored `.env` finding was built from the OS path, so a baseline written on Linux or macOS did not match on Windows; it now uses the forward-slash path, as the other findings already did.
- `perf-profile-reader`: functions with the same time were listed in a different order on each run (they were collected through a set); the order is now stable.
- Line numbers in the JavaScript and TypeScript paths of `api-docs-from-code`, `complexity-report`, `type-coverage` and `dead-code-finder` were found by counting newlines from the start of the file for every match, which made large files quadratic. A binary search over the newline positions gives the same output: on a file of 9,000 copies of the test sample, `extract_docs.py` went from 34.0s to 0.21s, `complexity_report.py` from 11.0s to 0.56s and `type_coverage.py` from 3.52s to 0.21s; `dead_code_finder.py` on 3,000 copies of an exports file went from 1.12s to 0.31s.

### Changed

- 26 skill descriptions reworded around how people ask, after a cross-mode lexical trigger check over all 42 skills (5 should-trigger and 5 should-not-trigger prompts each, every skill's should-trigger prompts also counted against the others): precision 0.92 to 0.98, recall 0.68 to 0.91. Each still has "Use when", "Not for" and a `## Limits` section.
- Versions 0.4.0 in every `plugin.json` and the marketplace.

## [0.3.1] - 2026-10-18

### Fixed

- `http-security-headers`: `headers_check.py` exits 2 with a clear error, instead of a traceback, when a HAR `response` is not an object or `response.headers` is not a list.
- `dependency-audit-reader`: an empty file no longer reads as a clean pip-audit report (exit 0); empty, binary and non-JSON input, and a `--format` that does not fit the document, exit 2 with the reason instead of a traceback.
- `dependency-audit-reader`: `--ignore GHSA-...` now works for npm 7 and later reports, whose advisories are keyed by a numeric source (the GHSA id is read from the advisory link), and a pip-audit alias such as a CVE id ignores the same advisory; a package stays listed while any advisory on it is not ignored. Transitive npm entries show the package they come through (`via minimist`), and the summary counts ignored packages.
- `flaky-test-hunter`: XML that is not a JUnit report (a `pom.xml` in the same folder) is skipped instead of counting as a run, which had marked every test as present in only some runs; when no file is a readable report the script exits 2 instead of reporting "0 flaky" with exit 0, and a single usable run gets a warning.
- `test-gap-finder`: a folder with no source modules (only entry points such as `app.py`, or nothing at all) exits 2 instead of reporting 100% and passing any `--min`; the summary counts the entry-point and config files it skipped, and a private module such as `_parser.py` matches `test_parser.py`.
- `changelog-keeper`: a binary file exits 2 instead of a traceback.
- `api-contract-review`, `github-actions-author`, `k8s-manifest-review`, `dockerfile-hardening`: empty, binary, plain-text or JSON-array input exits 2 with a readable reason; before, it exited 1 with a finding that showed a Python type name such as NoneType, or exited 0 with "0 findings".
- `complexity-report`, `type-coverage`, `api-docs-from-code`: a non-source file or a folder with no source files exits 2 instead of a clean-looking "0 functions" report.
- `regex-builder`: an empty or binary cases file exits 2 instead of "0 passed, 0 failed"; a pattern with no cases says only the backtracking check ran. `csv-profiler`, `cron-doctor`, `env-diff` and `log-triage` reject binary input, `env-diff` rejects a template with no keys, `log-triage` rejects empty input, and `release-notes` rejects `--input` text that has no records in the expected format.
- Numeric options are range-checked (`--top`, `--max-complexity`, `--max-length`, `--min`, `--min-coverage`, `--min-runs`, `--next`, `--sample`, `--enum-max`, `--enum-min-samples`): a negative count or a percentage over 100 now exits 2 with a usage error instead of being accepted or read as a failed threshold.

### Added

- `http-security-headers`: `headers_check.py` reads a browser HAR export; it picks the first HTML response, or the entry given with `--url`, and exits 2 with a specific error for an empty or unmatched HAR. Thanks @Cid-oe (#11).

### Changed

- `regex-builder` and `log-triage` descriptions reworded around how people ask ("extract the id and amount from lines like", "cluster the messages and tell me what to look at"); recall on the labelled trigger prompts rose from 0.80 to 1.00 for both, precision unchanged at 1.00.
- The README has one "Exit codes" section for every script (0 clean, 1 findings at the threshold, 2 bad input or usage), and the code-quality, debugging and security-basics plugin READMEs show real output from `test_gap_finder.py`, `flaky_test_hunter.py` and `audit_reader.py`.
- Tests rose from 154 to 202; every script now has at least six. `ruff check .` runs clean under a `[tool.ruff]` configuration in `pyproject.toml`.

## [0.3.0] - 2026-10-09

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
