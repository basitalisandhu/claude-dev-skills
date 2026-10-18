from conftest import load_script, run_json, run_main

mod = load_script("code-quality", "complexity-report", "complexity_report.py")

PY = '''
def simple(a):
    return a

def branchy(a, b):
    if a and b:
        for i in range(3):
            if i == 2:
                return i
    elif b:
        while a:
            a -= 1
    try:
        pass
    except ValueError:
        pass
    return [x for x in range(3) if x]

class K:
    def m(self, x):
        return x if x else None
'''

JS = '''
export function one(a) { return a; }
const two = (a, b) => {
  if (a && b) { return 1; }
  for (const x of a) { if (x) { continue; } }
  return a ? b : null;
};
class C {
  method(x) {
    switch (x) { case 1: return 1; case 2: return 2; }
    try { x(); } catch (e) { return e; }
  }
}
'''


def test_python_complexity_counts():
    import pathlib
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "m.py"
        p.write_text(PY, encoding="utf-8")
        rc, rep = run_json(mod, [str(p), "--json"])
    by = {f["name"]: f for f in rep["functions"]}
    assert by["simple"]["complexity"] == 1
    # if(1) + and(1) + for(1) + inner if(1) + elif(1) + while(1) + except(1) + comprehension(1) + comp-if(1) = 10
    assert by["branchy"]["complexity"] == 10
    assert by["branchy"]["max_depth"] >= 3
    assert by["K.m"]["complexity"] == 2
    assert by["branchy"]["grade"] == "B"


def test_javascript_functions_found_and_counted(write, tmp_path):
    write("a.js", JS)
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    by = {f["name"]: f for f in rep["functions"]}
    assert by["one"]["complexity"] == 1
    assert by["two"]["complexity"] == 1 + 5  # if, &&, for, if, ?:
    assert by["method"]["complexity"] == 1 + 2 + 1  # two cases + catch


def test_thresholds_drive_exit_code(write, tmp_path):
    write("m.py", PY)
    rc, out, _ = run_main(mod, [str(tmp_path), "--max-complexity", "3"])
    assert rc == 1 and "branchy" in out
    rc, out, _ = run_main(mod, [str(tmp_path), "--max-complexity", "50", "--max-length", "500"])
    assert rc == 0


def test_summary_and_bad_path(write, tmp_path):
    write("m.py", PY)
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rep["summary"]["functions"] == 3
    assert rep["summary"]["max_complexity"] == 10
    rc, _, err = run_main(mod, [str(tmp_path / "missing")])
    assert rc == 2


def test_unsupported_file_and_empty_tree_exit_2(write, tmp_path):
    # a non-source file or an empty folder used to report "0 functions" with exit 0, which reads as a clean result
    rc, out, err = run_main(mod, [str(write("notes.txt", "just some text\n"))])
    assert rc == 2 and "not a supported source file" in err and out == ""
    (tmp_path / "empty").mkdir()
    write("empty/README.md", "# nothing to measure\n")
    rc, out, err = run_main(mod, [str(tmp_path / "empty")])
    assert rc == 2 and "no source files found" in err and out == ""


def test_out_of_range_options_exit_2(write, tmp_path):
    f = write("a.py", "def f():\n    return 1\n")
    for opt, val, msg in [("--top", "-3", "1 or more"), ("--max-complexity", "0", "1 or more"), ("--max-length", "ten", "whole number")]:
        rc, out, err = run_main(mod, [str(f), opt, val])
        assert rc == 2 and msg in err and out == "", opt
