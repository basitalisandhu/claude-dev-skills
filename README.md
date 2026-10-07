# claude-dev-skills

**Claude Code skills for everyday development: code review, refactoring, debugging, CI and containers, data and APIs, documentation, and security basics. Forty-two skills in six plugins, each with a procedure, an output format and, where it helps, a tested standard-library script.**

claude-dev-skills is a Claude Code plugin marketplace for the work developers do every day: reviewing a pull request, finding why a test is flaky, hardening a Dockerfile, planning a schema migration, writing release notes, checking a token. Each skill is a fixed procedure with a concrete output, so two people (or two sessions) reach the same result and the evidence is a file, a line or a command output. Twenty-five skills bundle a Python script (standard library only, `--json` output, tested) that does the mechanical part; the rest bundle checklists and templates.

No network access, no telemetry: scripts read the files you point them at and write only where you ask.

Find this when you search for: code review checklist, tech debt, code smells, flaky tests, CI fails randomly, race condition, Docker image too big, zero-downtime migration, ReDoS, release notes, incident report, OWASP Top 10, npm audit fix, terraform plan policy, prevent terraform destroy, security review of a pull request.

## When to use this

- Review this PR against a fixed checklist before merging: `review-checklist`
- Which tests are flaky, and why: `flaky-test-hunter`
- Is this Dockerfile, workflow or Kubernetes manifest safe to ship: `dockerfile-hardening`, `github-actions-author`, `k8s-manifest-review`
- Can we apply this Terraform plan under our rules: `terraform-apply-gate`
- What does this pull request add to the attack surface: `diff-security-review`
- Change a column on a live table without downtime: `schema-migration-plan`
- Turn a commit range into release notes and keep the changelog consistent: `release-notes`, `changelog-keeper`, `semver-advisor`
- Did a secret get committed, what is in this JWT, are the headers right: `secrets-hygiene`, `jwt-inspector`, `http-security-headers`

## Install

In a Claude Code session:

```text
/plugin marketplace add basitalisandhu/claude-dev-skills
/plugin install code-quality@claude-dev-skills
```

Install any of the six plugins the same way: `/plugin install debugging@claude-dev-skills`, `/plugin install devops@claude-dev-skills`, `/plugin install data@claude-dev-skills`, `/plugin install docs@claude-dev-skills`, `/plugin install security-basics@claude-dev-skills`.

From a shell (scripts and CI machines):

```bash
claude plugin marketplace add basitalisandhu/claude-dev-skills
claude plugin install devops@claude-dev-skills --scope user
```

To try a plugin without installing, clone the repository and start Claude Code with `claude --plugin-dir ./plugins/devops`.

Requirements: Python 3.11 or newer on `PATH` as `python3` for the scripts (standard library only). `git` is used by `release-notes` and by `secrets-hygiene --staged`. Nothing else.

After installing, skills appear as `/<plugin>:<skill>`, for example `/devops:dockerfile-hardening`, and Claude invokes them on its own when a request matches a skill's description.

This pack is also part of [claude-skills](https://github.com/basitalisandhu/claude-skills), which holds every skill I maintain as one marketplace: `/plugin marketplace add basitalisandhu/claude-skills`.

## What is inside

```text
plugins/<plugin>/
├── .claude-plugin/plugin.json      plugin manifest
├── README.md                       the plugin's skill table
└── skills/<name>/
    ├── SKILL.md                    frontmatter (name, description with when and when not), procedure, output format
    ├── scripts/<name>.py           optional: argparse, --json, exit codes 0/1/2, standard library only
    └── references/*.md             optional: checklists, templates, per-tool notes
tests/test_<script>.py              pytest for every script (25 scripts, 143 tests)
scripts/validate_plugins.py         structure, frontmatter, scripts, READMEs and house style
```

## Skills

### code-quality

| Skill | Triggers on | What it produces |
|---|---|---|
| `review-checklist` | "review this PR", "look at my diff", a pre-merge gate | findings with severity and file:line across correctness, tests, errors, security, performance, readability, compatibility; a verdict |
| `refactor-plan` | "refactor", "split this file", "untangle imports" | an ordered list of behaviour-preserving moves, each one commit with its tests and rollback; before and after measurements |
| `dead-code-finder` | "what can we delete?", cleanup before a refactor | `dead_code_finder.py` candidates (Python and JS/TS) confirmed against dynamic use, in deletion order |
| `complexity-report` | "most complex code", CI complexity threshold, refactor evidence | `complexity_report.py` ranking by cyclomatic complexity, length and depth, with the simplification per function |
| `naming-audit` | "are these names clear?", conventions for a new codebase | renames grouped by cost (private, repository-wide, public with deprecation) and convention proposals |
| `error-handling-review` | "review error handling", "it failed silently" | findings against a checklist plus one error policy per layer with code examples |
| `type-coverage` | "how typed is this?", enabling strict mode | `type_coverage.py` annotated-slot percentages, explicit `any` counts, least-typed files, a ratchet plan |
| `test-gap-finder` | "what is untested?", "did the PR add tests?" | `test_gap_finder.py` modules with no test by name or import, prioritised by risk |

### debugging

| Skill | Triggers on | What it produces |
|---|---|---|
| `bug-repro-minimiser` | "sometimes", "on my machine", before any fix | the smallest deterministic reproduction, environment pins, what was ruled out, a regression test |
| `log-triage` | a log dump, a failing CI log, "logs full of errors" | `log_triage.py` message templates with counts, levels and attached traces; the three things to investigate |
| `flaky-test-hunter` | CI fails intermittently, "is this test flaky?" | `flaky_test_hunter.py` tests that both passed and failed across JUnit reports, with cause and fix |
| `stack-trace-explainer` | a pasted trace, "what does this mean?" | root cause in the chain, first project frame, error class, hypothesis and the one check that confirms it |
| `perf-profile-reader` | a py-spy, pprof or cProfile capture, "where does the time go?" | `perf_profile_reader.py` top frames by self and cumulative time, busy versus waiting, the fan-out point, candidates with ceilings |
| `memory-leak-checklist` | memory grows until restart, OOM kills | confirm, measure the heap, retaining path, suspect, fix, verify, with per-runtime tool commands |

### devops

| Skill | Triggers on | What it produces |
|---|---|---|
| `dockerfile-hardening` | "review this Dockerfile", "make the image smaller" | `dockerfile_lint.py` findings (17 rules) and a pinned, non-root, multi-stage Dockerfile |
| `github-actions-author` | "add CI", "review our workflows", unpinned actions | `gha_lint.py` findings (permissions, pull_request_target, injection, pinning) and workflows from templates |
| `k8s-manifest-review` | "review these manifests", "harden this pod spec" | `k8s_review.py` findings (16 rules) and manifests on the restricted baseline |
| `terraform-review` | "review this Terraform", a module before it ships | checklist findings, plan reading (destroys and replacements), rules to automate |
| `terraform-apply-gate` | "can we apply this plan?", a pre-apply CI step or hook | `terraform_apply_gate.py` allow, ask or block verdict against a YAML policy (forbidden destroys, tags, replacement ceiling, protected names, providers) |
| `cron-doctor` | "my cron job did not run", "ran twice" | `cron_doctor.py` schedule explanations, next runs, findings (12 rules), fixes and when to leave cron |
| `env-diff` | "works locally, fails in staging", onboarding | `env_diff.py` missing, extra, empty and duplicate keys between a template and real env files, values never shown |
| `release-notes` | "write the release notes", GitHub release body | `release_notes.py` grouped Markdown from a commit range, edited for readers with a migration section |
| `semver-advisor` | "is this breaking?", "major or minor?" | a version decision with a classified change list and the alternatives to a major |

### data

| Skill | Triggers on | What it produces |
|---|---|---|
| `sql-query-review` | "why is this query slow?", "review this SQL" | correctness and performance findings with the plan as evidence and the exact index or rewrite |
| `schema-migration-plan` | add, rename, drop or change a column on a live table | expand, migrate, contract steps with lock and duration per step, backfill shape and rollback |
| `csv-profiler` | "what is in this file?", "load this CSV" | `csv_profiler.py` column types, nulls, distinct, ranges, keys and warnings; cleaning steps and a schema |
| `json-schema-author` | "validate this JSON", "schema from examples" | `json_schema_infer.py` draft from samples, then a hand-finished schema with fixtures |
| `regex-builder` | "write a regex", "why does it not match?" | `regex_tester.py` results per labelled case, groups, backtracking warnings; a verbose pattern with tests |
| `api-contract-review` | "review the OpenAPI spec", client generator fails | `openapi_lint.py` findings (16 rules) and a review of resources, errors, versioning and security |

### docs

| Skill | Triggers on | What it produces |
|---|---|---|
| `readme-author` | no README, stale README, about to publish | a README in a fixed order with verified commands and no unbacked claims |
| `adr-writer` | choosing a technology or pattern, "why did we do it this way?" | a numbered decision record with context, options, decision, consequences and status |
| `changelog-keeper` | a changelog line, cutting a release, format drift | `changelog.py` check, add, release and show for Keep a Changelog files |
| `onboarding-doc` | a new team member, a service changing hands | `docs/ONBOARDING.md` verified on a clean machine: setup, code map, working loop, operations, people, first tasks |
| `api-docs-from-code` | "document this package", stale reference | `extract_docs.py` Markdown reference from docstrings and JSDoc, undocumented symbols, a coverage gate |
| `postmortem-writer` | after an outage or a near-miss | a blameless postmortem with quantified impact, timeline, conditions and amplifiers, checkable actions |

### security-basics

| Skill | Triggers on | What it produces |
|---|---|---|
| `secrets-hygiene` | "check for secrets", pre-commit, after a leak | `secrets_scan.py` redacted findings, baseline, rotation and history cleanup steps |
| `dependency-audit-reader` | npm audit, pip-audit or cargo audit fails CI | `audit_reader.py` ranked vulnerable packages, fixable versus not, upgrade and override plan |
| `http-security-headers` | "are our headers secure?", a scanner finding | `headers_check.py` grade and findings (13 rules); the header set for the server in use |
| `jwt-inspector` | "what is in this token?", "is our JWT setup safe?" | `jwt_inspect.py` decoded claims (never verified) with findings; a review of issuer and verifier |
| `cors-review` | a CORS error, "allow the frontend", a permissive policy | checklist findings and an allowlist configuration for the framework or gateway |
| `auth-flow-review` | designing login, reviewing auth, an account takeover | per-flow findings with severity, corrected flows, attack tests for staging |
| `diff-security-review` | "is this PR safe security-wise?", a pre-merge security pass | `diff_security_scan.py` findings on added lines only (network, shell, deserialisation, SQL strings, secrets, TLS off, permissions) with file and line, read in context |

Deeper security work for LLM agents (threat modelling, agent configuration audits, prompt injection review, MCP server review) lives in the sibling marketplace [agent-security-skills](https://github.com/basitalisandhu/agent-security-skills).

## Security posture

What each component can touch, so you can decide before you install:

- **Skills** are Markdown instructions. They tell Claude to treat what it reads in your repository (code, logs, tokens, comments, reports) as data under review, never as instructions.
- **Scripts** are standard-library Python. They read the paths given on the command line and write only where you pass an output path or run an explicit write subcommand (`changelog.py add` and `release`, `secrets_scan.py --write-baseline`). The only subprocess any script runs is local `git` (`release_notes.py` reads history, `secrets_scan.py --staged` lists the index). No sockets are opened anywhere; CI runs the bundled secrets scanner (with `.secrets-baseline.json` covering the fake credentials in the test fixtures) and the workflow linter on this repository itself.
- **Redaction** is the default: `secrets_scan.py`, `env_diff.py`, `dockerfile_lint.py` and `gha_lint.py` never print a secret value, and `jwt_inspect.py` states in every output that it did not verify the signature.
- **No telemetry.** Nothing here reports usage anywhere.
- The repository validates its own structure with `scripts/validate_plugins.py` and `claude plugin validate --strict`.

Report security problems privately: see [SECURITY.md](SECURITY.md).

## Compatibility with agentskills.io

Every `SKILL.md` follows the Agent Skills format: frontmatter with `name` (equal to the directory name) and `description` (double-quoted, at most 600 characters here against the format's 1024, with a "Use when" and a "Not for" sentence), optional `license`, `compatibility` and `metadata`, supporting files in `references/` and `scripts/`, and a body under 500 lines. Skill bodies reference `${CLAUDE_PLUGIN_ROOT}` for script paths; other hosts should substitute the skill's own directory.

## Development

```bash
python3 -m pytest -q                       # 143 tests across 25 scripts, the bundled YAML reader and the validator
python3 scripts/validate_plugins.py        # structure, frontmatter, scripts, READMEs, house style
claude plugin validate --strict . && for p in plugins/*/; do claude plugin validate --strict "$p"; done
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the ground rules and [docs/good-first-issues.md](docs/good-first-issues.md) for a place to start.

## Related projects

More tools by the same author: https://github.com/basitalisandhu

| Project | What it is |
|---|---|
| [agent-security-skills](https://github.com/basitalisandhu/agent-security-skills) | Claude Code plugin for securing LLM agents: threat modelling, config audits, prompt injection review, MCP server review, incident lookup |
| [Install every Claude Code skill at once](https://github.com/basitalisandhu/claude-skills) | All packs in one repository; the catalog is at https://basitalisandhu.github.io/claude-skills/ |

## Licence

MIT. See [LICENSE](LICENSE).
