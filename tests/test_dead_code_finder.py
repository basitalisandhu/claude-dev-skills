from conftest import load_script, run_json, run_main

mod = load_script("code-quality", "dead-code-finder", "dead_code_finder.py")


def test_reports_unused_python_function_and_keeps_used_ones(write, tmp_path):
    write("pkg/util.py", "def used():\n    return 1\n\ndef unused_helper():\n    return 2\n\nclass Orphan:\n    pass\n\nclass Used:\n    def method_called(self):\n        return self\n")
    write("pkg/main.py", "from pkg.util import used, Used\nprint(used(), Used().method_called())\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    names = {f["qualname"] for f in rep["findings"]}
    assert names == {"unused_helper", "Orphan"}
    assert rep["files_scanned"] == 2


def test_skips_private_dunder_decorated_and_all_exports(write, tmp_path):
    write("app.py", "__all__ = ['exported']\n\ndef exported():\n    pass\n\ndef _private():\n    pass\n\nclass A:\n    def __repr__(self):\n        return 'A'\n\n@app.route('/')\ndef handler():\n    pass\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    assert rep["findings"] == []
    rc, rep = run_json(mod, [str(tmp_path), "--json", "--include-private"])
    assert {f["name"] for f in rep["findings"]} == {"_private"}


def test_javascript_exports_without_importers_are_reported(write, tmp_path):
    write("src/a.ts", "export function usedFn() {}\nexport const unusedConst = 1;\nexport class UnusedClass {}\nexport { usedFn as alias, other };\nconst other = 2;\n")
    write("src/b.ts", "import { usedFn, alias } from './a';\nusedFn(); alias();\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    names = {f["name"] for f in rep["findings"]}
    assert names == {"unusedConst", "UnusedClass", "other"}


def test_fail_on_findings_and_missing_path(write, tmp_path):
    write("x.py", "def lonely():\n    pass\n")
    rc, out, _ = run_main(mod, [str(tmp_path), "--fail-on-findings"])
    assert rc == 1 and "lonely" in out
    rc, _, err = run_main(mod, [str(tmp_path / "nope")])
    assert rc == 2 and "not found" in err


def test_syntax_errors_are_reported_not_fatal(write, tmp_path):
    write("bad.py", "def broken(:\n")
    write("good.py", "def fine():\n    pass\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    assert len(rep["parse_errors"]) == 1 and "bad.py" in rep["parse_errors"][0]
    assert [f["name"] for f in rep["findings"]] == ["fine"]
