from conftest import load_script, run_json, run_main

mod = load_script("code-quality", "type-coverage", "type_coverage.py")


def test_python_slots_and_percent(write, tmp_path):
    write("a.py", "def typed(a: int, b: str = '') -> bool:\n    return True\n\ndef untyped(a, b):\n    return a\n\nclass C:\n    def __init__(self, x: int):\n        self.x = x\n    def m(self, y) -> None:\n        pass\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    f = rep["files"][0]
    # typed: a, b, return = 3/3; untyped: a, b, return = 0/3; __init__: x, return(implicit) = 2/2; m: y, return = 1/2
    assert f["slots"] == 10 and f["covered"] == 6
    assert rep["summary"]["percent"] == 60.0
    assert {u["name"] for u in f["untyped"]} == {"untyped", "m"}


def test_typescript_params_and_any(write, tmp_path):
    write("a.ts", "export function f(a: number, b): string { return ''; }\nconst g = (x: any, y: string) => x;\nclass K {\n  method(p, q: number) { return p as any; }\n}\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    f = rep["files"][0]
    assert f["language"] == "typescript"
    assert f["slots"] == 6 and f["covered"] == 4
    assert f["any"] == 2  # x: any and `as any`
    assert {u["name"] for u in f["untyped"]} == {"f", "method"}


def test_min_threshold_exit_code(write, tmp_path):
    write("a.py", "def u(a, b):\n    pass\n")
    rc, out, _ = run_main(mod, [str(tmp_path), "--min", "50"])
    assert rc == 1
    rc, out, _ = run_main(mod, [str(tmp_path)])
    assert rc == 0 and "0.0%" in out


def test_syntax_error_and_missing_path(write, tmp_path):
    write("bad.py", "def (:\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0 and "error" in rep["files"][0]
    rc, _, _ = run_main(mod, [str(tmp_path / "nope")])
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
    f = write("a.py", "def f(x: int) -> int:\n    return x\n")
    rc, _, err = run_main(mod, [str(f), "--min", "150"])
    assert rc == 2 and "between 0 and 100" in err  # used to exit 1 as if coverage were too low
    rc, _, err = run_main(mod, [str(f), "--top", "-1"])
    assert rc == 2 and "1 or more" in err
