import shutil
import subprocess

import pytest

from conftest import load_script, run_json, run_main

mod = load_script("devops", "release-notes", "release_notes.py")

LOG = (
    "aaaa111\x1fAda\x1f2026-02-01\x1ffeat(api): add pagination\x1fCloses #12\x1e"
    "bbbb222\x1fBob\x1f2026-02-02\x1ffix: handle empty body (#34)\x1f\x1e"
    "cccc333\x1fAda\x1f2026-02-03\x1frefactor!: drop legacy client\x1fBREAKING CHANGE: v1 client removed\x1e"
    "dddd444\x1fCy\x1f2026-02-04\x1fBump dependency foo to 2.0\x1f\x1e"
    "eeee555\x1fCy\x1f2026-02-05\x1fUpdate README\x1f\x1e"
    "ffff666\x1fDi\x1f2026-02-06\x1fSomething unusual happened\x1fRefs PROJ-77\x1e"
)


def test_markdown_from_captured_log(write, tmp_path):
    f = write("log.txt", LOG)
    rc, out, _ = run_main(mod, ["--input", str(f), "--version", "1.2.0", "--date", "2026-02-07", "--repo-url", "https://github.com/o/r"])
    assert rc == 0
    assert out.startswith("## 1.2.0 (2026-02-07)")
    assert "### Breaking changes" in out and "- Drop legacy client: v1 client removed (" in out
    # the migration note belongs to the breaking section only; the refactor section keeps the plain subject
    assert out.count("v1 client removed") == 1
    assert "- **api:** Add pagination ([#12](https://github.com/o/r/issues/12)) ([aaaa111](https://github.com/o/r/commit/aaaa111))" in out
    assert "### Bug fixes" in out and "Handle empty body (#34)" in out
    assert "### Build and dependencies" in out and "### Documentation" in out and "### Other changes" in out
    assert "PROJ-77" in out


def test_json_classification(write, tmp_path):
    f = write("log.txt", LOG)
    rc, notes = run_json(mod, ["--input", str(f), "--json", "--authors"])
    assert notes["commits"] == 6 and notes["contributors"] == ["Ada", "Bob", "Cy", "Di"]
    keys = [s["key"] for s in notes["sections"]]
    assert keys == ["breaking", "feat", "fix", "refactor", "docs", "build", "other"]
    breaking = notes["sections"][0]["entries"][0]
    assert breaking["breaking"] is True and breaking["sha"] == "cccc333" and breaking["breaking_note"] == "v1 client removed"


def test_empty_input_and_missing_file(write, tmp_path):
    f = write("empty.txt", "")
    rc, out, _ = run_main(mod, ["--input", str(f)])
    assert rc == 0 and "No changes in this range." in out
    rc, _, err = run_main(mod, ["--input", str(tmp_path / "nope")])
    assert rc == 2


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_runs_git_log_locally(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {"GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@example.com", "HOME": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    def git(*a):
        subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, env=env)
    git("init", "-q")
    (repo / "a.txt").write_text("a")
    git("add", "a.txt")
    git("commit", "-q", "-m", "feat: first feature")
    (repo / "a.txt").write_text("b")
    git("commit", "-q", "-am", "fix: a bug")
    rc, notes = run_json(mod, ["--repo", str(repo), "--json"])
    assert rc == 0 and notes["commits"] == 2
    assert [s["key"] for s in notes["sections"]] == ["feat", "fix"]
    rc, _, err = run_main(mod, ["--repo", str(tmp_path / "not-a-repo")])
    assert rc == 2
