from conftest import assemble, load_script, run_json, run_main

mod = load_script("devops", "env-diff", "env_diff.py")


def test_missing_extra_empty_and_values_hidden(write, tmp_path):
    t = write(".env.example", "# comment\nDATABASE_URL=postgres://localhost/db\nAPI_KEY=\nDEBUG=false\nexport PORT=8080\n")
    e = write(".env", "DATABASE_URL=postgres://user:realpassword@db/prod\nAPI_KEY=\nEXTRA=1\nPORT=9000\nPORT=9001\nnot a line\n")
    rc, rep = run_json(mod, [str(t), str(e), "--json"])
    assert rc == 1
    f = rep["files"][0]
    assert f["missing"] == ["DEBUG"] and f["extra"] == ["EXTRA"] and f["empty"] == ["API_KEY"]
    assert f["set"] == ["DATABASE_URL", "PORT"]
    assert f["duplicates"] == ["PORT (line 5)"] and f["malformed"] == ["line 6"]
    rc, out, _ = run_main(mod, [str(t), str(e)])
    assert "realpassword" not in out and "9001" not in out


def test_ok_and_allow_extra_and_ignore(write, tmp_path):
    t = write("t", "A=1\nB=2\n")
    e = write("e", "A=x\nB=y\nC=z\n")
    rc, _, _ = run_main(mod, [str(t), str(e)])
    assert rc == 1
    rc, _, _ = run_main(mod, [str(t), str(e), "--allow-extra"])
    assert rc == 0
    rc, _, _ = run_main(mod, [str(t), str(e), "--ignore", "C"])
    assert rc == 0
    e2 = write("e2", "A=x\n")
    rc, _, _ = run_main(mod, [str(t), str(e2), "--ignore", "B"])
    assert rc == 0


def test_template_values_that_look_real(write, tmp_path):
    stripe_key = assemble("sk_live_", "4eC39HqLyjWDarjtT1zdp7dc")  # assembled so the full token never sits in the repo
    t = write("t", f"STRIPE_KEY={stripe_key}\nPLACEHOLDER=changeme\nURL=http://localhost:3000\nSHORT=abc\n")
    e = write("e", "STRIPE_KEY=\nPLACEHOLDER=\nURL=\nSHORT=\n")
    rc, rep = run_json(mod, [str(t), str(e), "--json"])
    assert rep["template"]["values_that_look_real"] == ["STRIPE_KEY"]


def test_missing_files(write, tmp_path):
    t = write("t", "A=1\n")
    rc, _, err = run_main(mod, [str(tmp_path / "nope"), str(t)])
    assert rc == 2
    rc, _, err = run_main(mod, [str(t), str(tmp_path / "nope")])
    assert rc == 2


def test_quoted_values_and_inline_comments():
    values, malformed, dups = mod.parse_env('A="hello # not comment"\nB=plain # comment\nC=\'x\'\n')
    assert values == {"A": "hello # not comment", "B": "plain", "C": "x"} and not malformed and not dups
