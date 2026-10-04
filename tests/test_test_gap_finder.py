from conftest import load_script, run_json, run_main

mod = load_script("code-quality", "test-gap-finder", "test_gap_finder.py")


def test_python_naming_and_import_conventions(write, tmp_path):
    write("pkg/alpha.py", "x = 1\n")
    write("pkg/beta.py", "y = 2\n")
    write("pkg/gamma.py", "z = 3\n")
    write("tests/test_alpha.py", "from pkg.alpha import x\n")
    write("tests/test_other.py", "from pkg import gamma\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    assert rep["uncovered"] == ["pkg/beta.py"]
    assert rep["covered"] == 2 and rep["test_files"] == 2


def test_javascript_spec_and_tests_dir(write, tmp_path):
    write("src/a.ts", "export const a = 1;\n")
    write("src/a.test.ts", "import { a } from './a';\n")
    write("src/b.ts", "export const b = 1;\n")
    write("src/__tests__/b.ts", "import { b } from '../b';\n")
    write("src/c.ts", "export const c = 1;\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rep["uncovered"] == ["src/c.ts"]


def test_go_and_rust_conventions(write, tmp_path):
    write("svc/handler.go", "package svc\n")
    write("svc/handler_test.go", "package svc\n")
    write("svc/store.go", "package svc\n")
    write("lib/parse.rs", "#[cfg(test)]\nmod tests {}\n")
    write("lib/emit.rs", "fn emit() {}\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert sorted(rep["uncovered"]) == ["lib/emit.rs", "svc/store.go"]


def test_min_and_errors(write, tmp_path):
    write("a.py", "pass\n")
    rc, out, _ = run_main(mod, [str(tmp_path), "--min", "10"])
    assert rc == 1 and "no test: a.py" in out
    rc, _, err = run_main(mod, [str(tmp_path / "missing")])
    assert rc == 2
