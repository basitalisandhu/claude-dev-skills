#!/usr/bin/env python3
"""Refresh the sample output blocks in each skill's README.md by running the command each block names.

A sample block in a skill README looks like this (paths are relative to the repository root):

    <!-- sample: plugins/devops/skills/env-diff/scripts/env_diff.py tests/fixtures/env-diff/template.env.example ... -->
    ```text
    ...output...
    ```

The command runs with the current Python. `--lines=N` before the script path keeps the first N lines and adds "...".
With --check nothing is written and the exit code is 1 when a README is out of date (tests/test_skill_readmes.py runs
this), so the samples cannot drift from the scripts. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCK = re.compile(r"(<!-- sample: (?P<cmd>[^\n]+?) -->\n```text\n)(?P<body>.*?)^```$", re.DOTALL | re.MULTILINE)


def run(command: str) -> str:
    args = shlex.split(command)
    lines = None
    if args and args[0].startswith("--lines="):
        lines = int(args.pop(0).split("=", 1)[1])
    proc = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
    if proc.returncode not in (0, 1):
        raise SystemExit(f"render_samples.py: {command!r} exited {proc.returncode}: {proc.stderr.strip()}")
    out = proc.stdout.rstrip("\n").split("\n")
    if lines is not None and len(out) > lines:
        out = [*out[:lines], "..."]
    return "\n".join(line.rstrip() for line in out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="render_samples.py", description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if a README sample is out of date")
    args = parser.parse_args(argv)
    stale = []
    for readme in sorted(ROOT.glob("plugins/*/skills/*/README.md")):
        old = readme.read_text(encoding="utf-8")
        new = BLOCK.sub(lambda m: m.group(1) + run(m.group("cmd")) + "\n```", old)
        if old != new:
            stale.append(readme.relative_to(ROOT).as_posix())
            if not args.check:
                readme.write_text(new, encoding="utf-8", newline="\n")
    for name in stale:
        print(("out of date: " if args.check else "updated: ") + name)
    return 1 if stale and args.check else 0


if __name__ == "__main__":
    sys.exit(main())
