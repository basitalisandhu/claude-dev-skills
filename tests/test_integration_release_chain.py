"""End-to-end chain across two skills: release-notes feeds changelog-keeper, the way a release is cut.

1. release_notes.py reads a captured git log and groups the commits by Conventional Commits type (--json);
2. each grouped entry is added to CHANGELOG.md under its Keep a Changelog category with changelog.py add;
3. changelog.py release turns [Unreleased] into the new version, and check, latest and show must then agree with
   what the release notes said.

The scripts run as separate processes on files in a temporary folder, as a user or CI job would run them. The git
log and the starting changelog are the samples the two scripts' own tests use.
"""
from __future__ import annotations

import json
import subprocess
import sys

from conftest import script_path
from test_changelog import CHANGELOG
from test_release_notes import LOG

RELEASE_NOTES = script_path("devops", "release-notes", "release_notes.py")
CHANGELOG_PY = script_path("docs", "changelog-keeper", "changelog.py")
CATEGORY = {"breaking": "Changed", "feat": "Added", "fix": "Fixed", "perf": "Changed"}


def run(script, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, encoding="utf-8",
                          timeout=60)
    return proc.returncode, proc.stdout, proc.stderr


def test_release_notes_feed_the_changelog(tmp_path):
    log = tmp_path / "git.log"
    log.write_text(LOG, encoding="utf-8", newline="\n")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8", newline="\n")

    rc, out, err = run(RELEASE_NOTES, "--input", str(log), "--version", "1.2.0", "--date", "2026-10-26", "--json")
    assert rc == 0, err
    notes = json.loads(out)
    added = []
    for section in notes["sections"]:
        category = CATEGORY.get(section["key"])
        if category is None:
            continue
        for entry in section["entries"]:
            text = ("BREAKING: " if section["key"] == "breaking" else "") + entry["text"]
            rc, _out, err = run(CHANGELOG_PY, "--file", str(changelog), "add", category, text)
            assert rc == 0, err
            added.append((category, text))
    assert ("Added", "Add pagination") in added and any(t.startswith("BREAKING: ") for _c, t in added)

    rc, _out, err = run(CHANGELOG_PY, "--file", str(changelog), "release", "1.2.0", "--date", "2026-10-26")
    assert rc == 0, err
    rc, out, err = run(CHANGELOG_PY, "--file", str(changelog), "check")
    assert rc == 0, out + err
    rc, out, _err = run(CHANGELOG_PY, "--file", str(changelog), "latest")
    assert out.strip() == "1.2.0"

    rc, out, _err = run(CHANGELOG_PY, "--file", str(changelog), "show", "1.2.0")
    assert rc == 0
    for category, text in added:
        assert f"### {category}" in out and f"- {text}" in out
    assert "- A new thing." in out  # the entry that was already under [Unreleased] ships in the same release
    rc, out, _err = run(CHANGELOG_PY, "--file", str(changelog), "show")
    assert "A new thing." not in out and "Add pagination" not in out  # [Unreleased] starts empty again
