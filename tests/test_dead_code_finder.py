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


def test_commonjs_exports_report_only_unrequired_names(write, tmp_path):
    write(
        "lib/util.cjs",
        "function usedHelper() {}\nfunction unusedHelper() {}\nmodule.exports = { usedHelper, unusedHelper };\n",
    )
    write("app/main.js", "const { usedHelper } = require('../lib/util');\nusedHelper();\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    names = {f["name"] for f in rep["findings"]}
    assert names == {"unusedHelper"}


def test_multiline_module_exports_report_each_key_line(write, tmp_path):
    write(
        "lib/util.cjs",
        "function first() {}\nfunction second() {}\nmodule.exports = {\n  first,\n  second,\n};\n",
    )
    write("app/main.js", "const { first } = require('../lib/util');\nfirst();\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    lines = {f["name"]: f["line"] for f in rep["findings"]}
    # Each key is on its own line, not all on the opening brace.
    assert lines == {"second": 5}


def test_module_exports_dot_and_exports_dot(write, tmp_path):
    write("a.cjs", "function a() {}\nmodule.exports.a = a;\n")
    write("b.cjs", "function b() {}\nexports.b = b;\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    assert {f["name"] for f in rep["findings"]} == {"a", "b"}


def test_module_exports_object_with_inline_function_values(write, tmp_path):
    # A `}` inside a value must not end the object scan, or later keys vanish.
    write(
        "lib/util.cjs",
        "module.exports = {\n  a: function () { return 1; },\n  b,\n  c: x,\n};\n",
    )
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    lines = {f["name"]: f["line"] for f in rep["findings"]}
    assert lines == {"a": 2, "b": 3, "c": 4}


def test_module_exports_object_skips_spread_and_computed_keys(write, tmp_path):
    write(
        "lib/util.cjs",
        "module.exports = {\n  helper() { return 2; },\n  nested: { deep: 1 },\n  ...rest,\n  [k]: 1,\n  plain,\n};\n",
    )
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    names = {f["name"] for f in rep["findings"]}
    assert names == {"helper", "nested", "plain"}


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
