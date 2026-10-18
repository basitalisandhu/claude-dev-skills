from conftest import load_script, run_json, run_main

mod = load_script("debugging", "flaky-test-hunter", "flaky_test_hunter.py")


def junit(cases: dict[str, tuple[str, str]]) -> str:
    rows = []
    for name, (status, msg) in cases.items():
        inner = ""
        if status == "failed":
            inner = f'<failure message="{msg}">trace</failure>'
        elif status == "skipped":
            inner = "<skipped/>"
        elif status == "rerun":
            inner = f'<rerunFailure message="{msg}"/>'
        rows.append(f'<testcase classname="pkg.TestX" name="{name}" time="0.5">{inner}</testcase>')
    return f'<?xml version="1.0"?><testsuites><testsuite name="s" tests="{len(cases)}">{"".join(rows)}</testsuite></testsuites>'


def test_detects_flaky_and_always_failing(write, tmp_path):
    write("runs/run1.xml", junit({"a": ("passed", ""), "b": ("failed", "timeout"), "c": ("failed", "assert")}))
    write("runs/run2.xml", junit({"a": ("passed", ""), "b": ("passed", ""), "c": ("failed", "assert")}))
    write("runs/run3.xml", junit({"a": ("passed", ""), "b": ("failed", "timeout"), "c": ("failed", "assert")}))
    rc, rep = run_json(mod, [str(tmp_path / "runs"), "--json"])
    assert rc == 0
    assert [t["id"] for t in rep["flaky"]] == ["pkg.TestX::b"]
    b = rep["flaky"][0]
    assert b["passed"] == 1 and b["failed"] == 2 and b["top_message"] == "timeout" and b["flake_rate"] == 0.667
    assert [t["id"] for t in rep["always_failing"]] == ["pkg.TestX::c"]
    assert rep["tests"] == 3 and len(rep["runs"]) == 3


def test_rerun_counts_as_flaky_and_partial_presence(write, tmp_path):
    write("r1.xml", junit({"a": ("rerun", "flaky once"), "d": ("passed", "")}))
    write("r2.xml", junit({"a": ("passed", "")}))
    rc, rep = run_json(mod, [str(tmp_path / "r1.xml"), str(tmp_path / "r2.xml"), "--json"])
    assert [t["id"] for t in rep["flaky"]] == ["pkg.TestX::a"]
    assert rep["flaky"][0]["reruns"] == 1
    assert rep["partial_presence"] == [{"id": "pkg.TestX::d", "runs_seen": 1, "runs_total": 2}]


def test_fail_on_flaky_exit_code_and_text(write, tmp_path):
    write("r1.xml", junit({"a": ("failed", "x")}))
    write("r2.xml", junit({"a": ("passed", "")}))
    rc, out, _ = run_main(mod, [str(tmp_path), "--fail-on-flaky"])
    assert rc == 1 and "flaky (passed and failed" in out
    rc, out, _ = run_main(mod, [str(tmp_path)])
    assert rc == 0


def test_bad_xml_and_missing_paths(write, tmp_path):
    write("bad.xml", "<testsuite><testcase name='a'")
    rc, out, err = run_main(mod, [str(tmp_path), "--json"])
    assert rc == 2 and out == "" and "no" in err and "bad.xml" in err  # used to exit 0 with "0 flaky"
    rc, _, err = run_main(mod, [str(tmp_path / "nope")])
    assert rc == 2
    (tmp_path / "empty").mkdir()
    rc, _, err = run_main(mod, [str(tmp_path / "empty")])
    assert rc == 2 and "no XML" in err


def test_non_junit_xml_in_a_directory_is_skipped_not_counted(write, tmp_path):
    write("ci/run1.xml", junit({"a": ("failed", "x"), "b": ("passed", "")}))
    write("ci/run2.xml", junit({"a": ("passed", ""), "b": ("passed", "")}))
    write("ci/pom.xml", "<project><modelVersion>4.0.0</modelVersion></project>")
    rc, rep = run_json(mod, [str(tmp_path / "ci"), "--json", "--fail-on-flaky"])
    assert rc == 1 and rep["usable_runs"] == 2 and len(rep["runs"]) == 3
    assert [t["id"] for t in rep["flaky"]] == ["pkg.TestX::a"]
    assert rep["partial_presence"] == []  # the pom.xml used to count as a run, so every test looked partially present
    rc, out, _ = run_main(mod, [str(tmp_path / "ci")])
    assert "(1 file(s) skipped)" in out and "not a JUnit report" in out


def test_only_non_junit_or_empty_files_exit_2(write, tmp_path):
    write("pom.xml", "<project/>")
    write("empty.xml", "")
    rc, out, err = run_main(mod, [str(tmp_path / "pom.xml"), str(tmp_path / "empty.xml")])
    assert rc == 2 and out == "" and "pom.xml" in err and "empty.xml" in err


def test_single_run_warns_that_flakiness_needs_several_runs(write, tmp_path):
    f = write("only.xml", junit({"a": ("failed", "x")}))
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 0 and rep["usable_runs"] == 1 and rep["flaky"] == []
    assert rep["warnings"] and "only one usable run" in rep["warnings"][0]


def test_surefire_flaky_failure_and_message_from_text(write, tmp_path):
    surefire = ('<testsuite name="s"><testcase classname="com.x.ATest" name="t" time="1.0">'
                '<flakyFailure message="first try timed out"/></testcase>'
                '<testcase classname="com.x.ATest" name="u" time="0.1"><error>NullPointerException at A.java:3\nmore</error></testcase></testsuite>')
    write("s1.xml", surefire)
    write("s2.xml", '<testsuite name="s"><testcase classname="com.x.ATest" name="t" time="0.9"/>'
                    '<testcase classname="com.x.ATest" name="u" time="0.1"><error>NullPointerException at A.java:3</error></testcase></testsuite>')
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert [t["id"] for t in rep["flaky"]] == ["com.x.ATest::t"] and rep["flaky"][0]["reruns"] == 1
    assert rep["always_failing"][0]["top_message"] == "NullPointerException at A.java:3"


def test_min_runs_must_be_positive(write, tmp_path):
    rc, _, err = run_main(mod, [str(write("r1.xml", junit({"a": ("passed", "")}))), "--min-runs", "0"])
    assert rc == 2 and "1 or more" in err
