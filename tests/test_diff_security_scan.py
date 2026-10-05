import json

from conftest import assemble, load_script, run_json, run_main

mod = load_script("security-basics", "diff-security-review", "diff_security_scan.py")


def make_diff(path: str, added: list[str], context: list[str] | None = None, start: int = 10) -> str:
    """Build a one-hunk unified diff that adds `added` after `context` lines."""
    context = context or ["def handler(request):"]
    body = [f" {c}" for c in context] + [f"+{a}" for a in added]
    header = f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
    hunk = f"@@ -{start},{len(context)} +{start},{len(context) + len(added)} @@\n"
    return header + hunk + "\n".join(body) + "\n"


def rules_of(rep):
    return [(f["rule"], f["file"], f["line"]) for f in rep["findings"]]


def test_core_rules_with_file_and_line(write):
    diff = make_diff(
        "app/client.py",
        [
            "    resp = requests.get(url, verify=False)",
            "    data = pickle.loads(blob)",
            "    subprocess.run(cmd, shell=True)",
            '    cur.execute(f"SELECT * FROM users WHERE id = {uid}")',
            "    out = subprocess.run(['ls', '-l'])",
            "    r = requests.post(api_url, json=payload)",
        ],
    )
    p = write("change.diff", diff)
    code, rep = run_json(mod, [str(p), "--json"])
    assert code == 1
    assert rules_of(rep) == [
        ("tls-disabled", "app/client.py", 11),
        ("unsafe-deserialise", "app/client.py", 12),
        ("shell-exec", "app/client.py", 13),
        ("sql-from-string", "app/client.py", 14),
        ("process-exec", "app/client.py", 15),
        ("net-call", "app/client.py", 16),
    ]
    assert rep["added_lines_scanned"] == 6 and rep["files"] == 1


def test_only_added_lines_are_scanned(write):
    diff = (
        "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,3 +1,3 @@\n"
        " import os\n-os.system(cmd)\n+run_safely(cmd)\n x = eval_count\n"
    )
    p = write("c.diff", diff)
    code, rep = run_json(mod, [str(p), "--json"])
    assert code == 0 and rep["findings"] == [] and rep["added_lines_scanned"] == 1


def test_secret_literals_are_redacted(write):
    key_id = assemble("AKIA", "IOSFODNN7EXAMPLE")
    header = assemble("-----BEGIN ", "RSA PRIVATE KEY-----")
    diff = make_diff(
        "settings.py",
        [f'AWS_ID = "{key_id}"', 'db_password = "hunter2pw"', f'PEM = """{header}', 'password = "changeme-later"'],
        context=["# settings"],
        start=1,
    )
    p = write("c.diff", diff)
    code, rep = run_json(mod, [str(p), "--json"])
    assert [f["line"] for f in rep["findings"] if f["rule"] == "secret-literal"] == [2, 3, 4]
    text = json.dumps(rep)
    assert key_id not in text and "hunter2pw" not in text
    assert code == 1


def test_workflow_and_manifest_permissions(write):
    wf = make_diff(
        ".github/workflows/ci.yml",
        ["on: pull_request_target", "permissions:", "  contents: write", "  id-token: write"],
        context=["name: ci"],
        start=1,
    )
    pkg = make_diff("package.json", ['    "postinstall": "node setup.js",'], context=['  "scripts": {'], start=5)
    k8s = make_diff("deploy/pod.yaml", ["        privileged: true"], context=["      securityContext:"], start=20)
    iam = make_diff("iam/policy.json", ['      "Action": "*",'], context=["    {"], start=3)
    other = make_diff("docs/notes.yml", ["  contents: write"], context=["x:"], start=1)
    p = write("c.diff", wf + pkg + k8s + iam + other)
    code, rep = run_json(mod, [str(p), "--json"])
    got = rules_of(rep)
    assert ("workflow-permission", ".github/workflows/ci.yml", 2) in got
    assert ("workflow-permission", ".github/workflows/ci.yml", 4) in got
    assert ("workflow-permission", ".github/workflows/ci.yml", 5) in got
    assert ("install-hook", "package.json", 6) in got
    assert ("privileged-runtime", "deploy/pod.yaml", 21) in got
    assert ("wildcard-iam", "iam/policy.json", 4) in got
    assert not any(f == "docs/notes.yml" for _, f, _ in got)
    assert code == 1


def test_ignore_comment_exclude_and_fail_on(write):
    diff = make_diff("tests/test_x.py", ["    requests.get(u)"]) + make_diff(
        "app/x.py", ["    requests.get(u)  # diff-security-review: ignore", "    fetch(url)"]
    )
    p = write("c.diff", diff)
    code, rep = run_json(mod, [str(p), "--json", "--exclude", "tests/*"])
    assert rules_of(rep) == [("net-call", "app/x.py", 12)]
    assert code == 1
    code, _, _ = run_main(mod, [str(p), "--fail-on", "high", "--exclude", "tests/*"])
    assert code == 0


def test_deleted_file_and_multiple_hunks(write):
    diff = (
        "diff --git a/old.py b/old.py\ndeleted file mode 100644\n--- a/old.py\n+++ /dev/null\n@@ -1,1 +0,0 @@\n"
        "-os.system(x)\n"
        "diff --git a/n.go b/n.go\n--- a/n.go\n+++ b/n.go\n@@ -1,1 +1,2 @@\n package main\n"
        '+var _ = exec.Command("ls")\n@@ -40,1 +41,2 @@\n }\n+tls := &tls.Config{InsecureSkipVerify: true}\n'
    )
    p = write("c.diff", diff)
    code, rep = run_json(mod, [str(p), "--json"])
    assert rules_of(rep) == [("tls-disabled", "n.go", 42), ("process-exec", "n.go", 2)]
    assert rep["files"] == 1


def test_bad_input_and_text_output(write, tmp_path):
    assert run_main(mod, [str(tmp_path / "missing.diff")])[0] == 2
    p = write("notes.txt", "just some text\n+ not a diff\n")
    code, _, err = run_main(mod, [str(p)])
    assert code == 2 and "not a unified diff" in err
    good = write("c.diff", make_diff("a.js", ["const r = await fetch(u);"]))
    code, out, _ = run_main(mod, [str(good)])
    assert code == 1 and "a.js:11" in out and "net-call" in out
    target = tmp_path / "f.json"
    code, out, _ = run_main(mod, [str(good), "--json", "--out", str(target)])
    assert out == "" and json.loads(target.read_text(encoding="utf-8"))["findings"][0]["rule"] == "net-call"


def test_safe_variants_not_flagged(write):
    diff = make_diff(
        "a.py",
        [
            "    data = yaml.load(text, Loader=yaml.SafeLoader)",
            "    cur.execute('SELECT * FROM t WHERE id = %s', (uid,))",
            '    token = os.environ["API_TOKEN"]',
            "    result = evaluate(x)",
        ],
    )
    p = write("c.diff", diff)
    code, rep = run_json(mod, [str(p), "--json"])
    assert rep["findings"] == [] and code == 0
