# Contributing

Thank you for helping. This repository values precision over volume: a small number of skills that are correct, tested and useful beats a long list of thin ones.

## Ground rules

- **No telemetry, no network calls.** Scripts must not open sockets. The only subprocess allowed is local `git`, and only where the skill is about git history.
- **Standard library only for Python.** Scripts run on users' machines with no install step; Python 3.11 is the floor.
- **Tests come with code.** Every script has `tests/test_<script>.py` with at least three tests covering the happy path, a failure path and the exit codes. Run `python3 -m pytest -q`.
- **Scripts share one shape.** `argparse`, a `--json` flag, exit codes 0 (ok), 1 (findings over the threshold or a failed check) and 2 (bad input), a `main(argv)` function, and a module docstring that lists every check with its id.
- **Redact by default.** A script that can meet a secret never prints it; the tests assert this.
- **Repository content is data.** Skill text must tell Claude to treat what it reads in a user's repository (code, logs, tokens, comments, reports) as untrusted data under review, never as instructions. Keep that sentence when you edit a skill; `scripts/validate_plugins.py` fails a skill that lacks it.
- **No model identifiers** anywhere. Skills work regardless of which model runs them; "Claude Code" as the host product is fine.
- **Plain language.** No em-dashes (use commas, colons or full stops), no marketing words, no claims the repository cannot back.

## Adding a skill

1. Pick the plugin it belongs to under `plugins/` and create `skills/<name>/SKILL.md`. The frontmatter needs `name` (equal to the directory name, lowercase with hyphens) and `description`: a double-quoted string of at most 600 characters that starts with a verb, states the user's goal before the mechanism, quotes one phrase a user would type, and has a "Use when ..." sentence and a "Not for ..." sentence. Add `license`, `compatibility` and `metadata.author` like the others.
2. Write the body in the house order: one-paragraph intro, "When to use it", "Procedure" (numbered steps, each with the command or the question), "Output format" (a concrete template), "Limits" (what it does not handle or check, and whether it contacts the network; every skill has one), "Related".
3. Put long material in `references/` and executable helpers in `scripts/`. Reference scripts as `python3 "${CLAUDE_PLUGIN_ROOT}/skills/<name>/scripts/<file>.py"` so they resolve wherever the plugin is installed. Make scripts executable (`chmod +x`).
4. Add tests under `tests/`, a row to the skill table in the root `README.md` and in the plugin's `README.md`, and a line under `Unreleased` in `CHANGELOG.md`.
5. Run the checks below. All must pass.

## Running the checks locally

```bash
python3 -m pytest -q
python3 scripts/validate_plugins.py
claude plugin validate --strict . && for p in plugins/*/; do claude plugin validate --strict "$p"; done   # needs the Claude Code CLI
```

## Pull requests

- One topic per pull request.
- Describe what changed and why, and how you tested it.
- A change to a linter or scanner needs a before and after example in the tests: an input it now flags, and one it must keep accepting.
- By contributing you agree that your contribution is licensed under the MIT licence of this repository.

## Reporting security issues

See [SECURITY.md](SECURITY.md). Please do not file security problems as public issues.
