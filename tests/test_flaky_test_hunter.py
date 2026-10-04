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
    return '<?xml version="1.0"?><testsuites><testsuite name="s" tests="%d">%s</testsuite></testsuites>' % (len(cases), "".join(rows))


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
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0 and "error" in rep["runs"][0]
    rc, _, err = run_main(mod, [str(tmp_path / "nope")])
    assert rc == 2
    (tmp_path / "empty").mkdir()
    rc, _, err = run_main(mod, [str(tmp_path / "empty")])
    assert rc == 2 and "no XML" in err
