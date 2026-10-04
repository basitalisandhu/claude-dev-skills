from conftest import load_script, run_json, run_main

mod = load_script("docs", "changelog-keeper", "changelog.py")

CHANGELOG = """# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added

- A new thing.

## [1.1.0] - 2026-01-10

### Fixed

- A bug.

## [1.0.0] - 2025-12-01

### Added

- First release.

[Unreleased]: https://github.com/o/r/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/o/r/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/o/r/releases/tag/v1.0.0
"""


def test_check_passes_and_show_latest(write, tmp_path):
    f = write("CHANGELOG.md", CHANGELOG)
    rc, rep = run_json(mod, ["--file", str(f), "--json", "check"])
    assert rc == 0 and rep["ok"] and rep["versions"] == ["Unreleased", "1.1.0", "1.0.0"]
    rc, out, _ = run_main(mod, ["--file", str(f), "show", "1.1.0"])
    assert rc == 0 and out == "## [1.1.0] - 2026-01-10\n\n### Fixed\n\n- A bug.\n"
    rc, out, _ = run_main(mod, ["--file", str(f), "latest"])
    assert rc == 0 and out.strip() == "1.1.0"


def test_global_options_accepted_after_the_subcommand(write, tmp_path):
    f = write("CHANGELOG.md", CHANGELOG)
    rc, rep = run_json(mod, ["check", "--file", str(f), "--json"])
    assert rc == 0 and rep["ok"]
    rc, rep = run_json(mod, ["--json", "check", "--file", str(f)])
    assert rc == 0 and rep["ok"]
    rc, out, _ = run_main(mod, ["add", "Fixed", "A late fix.", "--file", str(f), "--dry-run"])
    assert rc == 0 and "- A late fix." in out and "A late fix." not in f.read_text()


def test_check_reports_problems(write, tmp_path):
    f = write("CHANGELOG.md", "# Changelog\n\n## [1.0.0] - 2025-13-01\n\n### Stuff\n\n- x\n\n### Fixed\n\n## [1.1.0] - 2025-01-01\n\n### Added\n\n- y\n")
    rc, rep = run_json(mod, ["--file", str(f), "--json", "check"])
    assert rc == 1
    msgs = " | ".join(p["message"] for p in rep["problems"])
    assert "missing [Unreleased]" in msgs and "not YYYY-MM-DD" in msgs and "non-standard category" in msgs
    assert "empty category Fixed" in msgs and "descending order" in msgs


def test_add_and_release_rewrites_file(write, tmp_path):
    f = write("CHANGELOG.md", CHANGELOG)
    rc, out, _ = run_main(mod, ["--file", str(f), "add", "fixed", "Crash on empty input."])
    assert rc == 0
    rc, out, _ = run_main(mod, ["--file", str(f), "show"])
    assert "### Added\n\n- A new thing.\n\n### Fixed\n\n- Crash on empty input.\n" in out
    rc, out, _ = run_main(mod, ["--file", str(f), "release", "1.2.0", "--date", "2026-02-01"])
    assert rc == 0
    text = f.read_text()
    assert "## [Unreleased]\n\n## [1.2.0] - 2026-02-01\n\n### Added\n\n- A new thing." in text
    assert "[Unreleased]: https://github.com/o/r/compare/v1.2.0...HEAD" in text
    assert "[1.2.0]: https://github.com/o/r/compare/v1.1.0...v1.2.0" in text
    assert "[1.0.0]: https://github.com/o/r/releases/tag/v1.0.0" in text
    rc, rep = run_json(mod, ["--file", str(f), "--json", "check"])
    assert rc == 0, rep


def test_release_errors_and_dry_run(write, tmp_path):
    f = write("CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2025-01-01\n\n### Added\n\n- x\n")
    rc, _, err = run_main(mod, ["--file", str(f), "release", "1.1.0"])
    assert rc == 1 and "nothing to release" in err
    rc, _, err = run_main(mod, ["--file", str(f), "add", "bogus", "x"])
    assert rc == 2
    rc, out, _ = run_main(mod, ["--file", str(f), "--dry-run", "add", "Added", "y"])
    assert rc == 0 and "- y" in out and "- y" not in f.read_text()
    rc, _, err = run_main(mod, ["--file", str(f), "release", "banana"])
    assert rc == 2
    rc, _, _ = run_main(mod, ["--file", str(tmp_path / "nope.md"), "check"])
    assert rc == 2
