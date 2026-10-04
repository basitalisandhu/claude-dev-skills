from conftest import load_script, run_json, run_main

mod = load_script("data", "regex-builder", "regex_tester.py")


def test_cases_file_with_groups(write, tmp_path):
    f = write("cases.txt", "# emails\n+ user@example.com\n+ a.b+c@sub.example.org\n- not-an-email\n- user@localhost\n= bob@example.com => {\"user\": \"bob\", \"domain\": \"example.com\"}\n")
    pat = r"^(?P<user>[\w.+-]+)@(?P<domain>[\w-]+(?:\.[\w-]+)+)$"
    rc, rep = run_json(mod, [pat, "--cases", str(f), "--json"])
    assert rc == 0, rep
    assert rep["passed"] == 5 and rep["failed"] == 0 and rep["named_groups"] == ["user", "domain"]
    assert rep["cases"][4]["named"] == {"user": "bob", "domain": "example.com"}


def test_failing_cases_and_inline_args():
    rc, rep = run_json(mod, [r"\d{3}-\d{4}", "--match", "555-1234", "--match", "no digits", "--no-match", "555-1234", "--json"])
    assert rc == 1 and rep["passed"] == 1 and rep["failed"] == 2
    rc, out, _ = run_main(mod, [r"\d{3}-\d{4}", "--match", "555-1234"])
    assert rc == 0 and "ok" in out


def test_fullmatch_flags_and_ascii():
    rc, rep = run_json(mod, ["abc", "--match", "ABC", "--flags", "i", "--fullmatch", "--json"])
    assert rc == 0
    rc, rep = run_json(mod, ["abc", "--match", "xabcx", "--fullmatch", "--json"])
    assert rc == 1
    rc, rep = run_json(mod, [r"^\w+$", "--match", "héllo", "--json"])
    assert rc == 0
    rc, rep = run_json(mod, [r"^\w+$", "--match", "héllo", "--ascii", "--json"])
    assert rc == 1


def test_backtracking_warnings():
    rc, rep = run_json(mod, r"(a+)+$ --match aaa --json".split())
    assert rc == 1 and any("nested quantifier" in w for w in rep["warnings"])
    rc, rep = run_json(mod, [r"^(\w|\d)*x$", "--match", "ax", "--json"])
    assert rc == 1 and any("overlapping" in w for w in rep["warnings"])


def test_bad_pattern_cases_and_flags(write, tmp_path):
    rc, _, err = run_main(mod, ["(", "--match", "x"])
    assert rc == 2 and "invalid pattern" in err
    rc, _, err = run_main(mod, ["x", "--flags", "q"])
    assert rc == 2
    f = write("bad.txt", "? what\n")
    rc, _, err = run_main(mod, ["x", "--cases", str(f)])
    assert rc == 2 and "line 1" in err
    rc, _, err = run_main(mod, ["x", "--cases", str(tmp_path / "nope")])
    assert rc == 2
