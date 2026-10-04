# Security policy

This repository ships skills and scripts that run inside people's Claude Code sessions. The scripts read files you point them at and write only where you ask; nothing here makes a network call or reports usage anywhere.

## Supported versions

Only the latest release on `main` is supported. Pin a tag if you need stability, and update when a fix is announced in [CHANGELOG.md](CHANGELOG.md).

## Reporting a vulnerability

Please do not open a public issue for a security problem.

1. Use GitHub's private vulnerability reporting on this repository ("Security" tab, "Report a vulnerability").
2. If that is unavailable, open an issue titled "Security contact request" with no details, and the maintainer will reply with a private channel.

Include what you found, how to reproduce it, and what you think the impact is. You will get an acknowledgement within 5 working days and a fix or a mitigation plan within 30 days for confirmed issues.

## What counts

- A script that can be made to execute untrusted input, write outside the paths given on its command line, or send data anywhere.
- A script that prints a secret it was supposed to redact (`secrets-hygiene`, `env-diff`, `dockerfile-hardening`, `jwt-inspector`).
- A linter producing a clean result on a clearly dangerous input (for example a workflow that checks out a pull request head under `pull_request_target`, or a Dockerfile with a credential in `ENV`).
- Instructions hidden in any file of this repository that address the model rather than the reader.

Pattern gaps in the scanners (a secret format not yet recognised, a Dockerfile mistake not yet linted) are welcome as ordinary issues or pull requests; they are detection improvements rather than vulnerabilities.

## What this marketplace does and does not do

- No telemetry. Nothing in this repository phones home.
- No network access. The only subprocess any script runs is local `git` (`release-notes` reads history; `secrets-hygiene --staged` lists the index).
- Scripts are standard-library Python, read-only unless you pass an output path or an explicit write subcommand (`changelog.py add`, `changelog.py release`, `secrets_scan.py --write-baseline`).
- Skill text tells Claude to treat the files, logs, tokens and reports it reads as data under review, never as instructions.

See the "Security posture" section of [README.md](README.md) for what each plugin touches.
