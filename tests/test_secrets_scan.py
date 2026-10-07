import json

from conftest import assemble, load_script, run_json, run_main

mod = load_script("security-basics", "secrets-hygiene", "secrets_scan.py")

# Fixture credentials. AWS's documented example key id may be spelled out; the others are assembled at run time so
# the complete token never appears in the repository (see conftest.assemble).
AWS_EXAMPLE_KEY = "AKIAIOSFODNN7EXAMPLE"
FAKE_GITHUB_TOKEN = assemble("ghp_", "abcdefghijklmnopqrstuvwxyz0123456789")
HIGH_ENTROPY = assemble("ab3Fz9QmLp2X", "cV7nRt4YwK8s")
FAKE_DB_PASSWORD = assemble("S3cret", "Passw0rd")
FAKE_SLACK_TOKEN = assemble("xoxb-", "123456789012-", "abcdefghijklmnop")
PRIVATE_KEY_HEADER = assemble("-----BEGIN RSA ", "PRIVATE KEY-----")


def test_finds_and_redacts(write, tmp_path):
    write("config.py", (
        f"AWS_KEY = '{AWS_EXAMPLE_KEY}'\n"
        f"GITHUB = '{FAKE_GITHUB_TOKEN}'\n"
        f"API_KEY = '{HIGH_ENTROPY}'\n"
        "SAFE = 'changeme-placeholder'\n"
        "TOKEN = 'sk-live-whatever'  # secrets-hygiene: ignore\n"
        f"DB = 'postgres://app:{FAKE_DB_PASSWORD}@db.internal/app'\n"
    ))
    write("key.pem", f"{PRIVATE_KEY_HEADER}\nMIIE...\n")
    write("logo.png", "\x00binary")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 1
    rules = {f["rule"] for f in rep["findings"]}
    assert {"aws-access-key-id", "github-token", "generic-secret-assignment", "private-key", "url-with-password"} <= rules
    out = json.dumps(rep)
    assert AWS_EXAMPLE_KEY not in out and FAKE_DB_PASSWORD not in out and HIGH_ENTROPY not in out
    assert not any(f["line"] == 5 for f in rep["findings"] if f["file"] == "config.py")
    assert not any(f["line"] == 4 for f in rep["findings"] if f["file"] == "config.py")
    assert rep["counts"]["critical"] >= 3


def test_env_file_not_ignored_and_example_ok(write, tmp_path):
    write(".env", "SECRET=hello\n")
    write(".env.example", "SECRET=\n")
    write("app.py", "x = 1\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert any(f["rule"] == "env-file-not-ignored" and f["file"] == ".env" for f in rep["findings"])
    # the fingerprint depends on the path inside the tree, not on where the tree is checked out, so a baseline is portable
    other = tmp_path / "elsewhere"
    (other / "sub").mkdir(parents=True)
    (other / "sub" / ".env").write_text("SECRET=hello\n", encoding="utf-8")
    rc, rep2 = run_json(mod, [str(other), "--json"])
    fp = lambda rep: {f["fingerprint"] for f in rep["findings"] if f["rule"] == "env-file-not-ignored"}
    assert fp(rep) and fp(rep) != fp(rep2)
    (other / "sub" / ".env").unlink(); (other / ".env").write_text("SECRET=hello\n", encoding="utf-8")
    rc, rep3 = run_json(mod, [str(other), "--json"])
    assert fp(rep3) == fp(rep)
    write(".gitignore", ".env\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert not any(f["rule"] == "env-file-not-ignored" for f in rep["findings"])


def test_baseline_roundtrip(write, tmp_path):
    write("a.py", f"token = '{FAKE_SLACK_TOKEN}'\n")
    base = tmp_path / "baseline.json"
    rc, out, _ = run_main(mod, [str(tmp_path), "--write-baseline", str(base)])
    assert rc == 0 and base.is_file()
    data = json.loads(base.read_text(encoding="utf-8"))
    assert len(data["fingerprints"]) == 1 and "xoxb" not in base.read_text(encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--json", "--baseline", str(base)])
    assert rc == 0 and rep["findings"] == [] and rep["suppressed_by_baseline"] == 1
    rc, _, err = run_main(mod, [str(tmp_path), "--baseline", str(tmp_path / "nope.json")])
    assert rc == 2


def test_clean_tree_fail_on_and_missing_path(write, tmp_path):
    write("ok.py", "greeting = 'hello world'\nurl = 'https://example.com/path'\n")
    write("node_modules/x/index.js", f"const k = '{AWS_EXAMPLE_KEY}';\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0 and rep["findings"] == []
    rc, _, _ = run_main(mod, [str(tmp_path / "nope")])
    assert rc == 2


def test_entropy_and_redact():
    assert mod.entropy("aaaa") == 0.0 and mod.entropy(HIGH_ENTROPY) > 3.5
    assert mod.redact("abcdefghijklmnop") == "abcd************"
