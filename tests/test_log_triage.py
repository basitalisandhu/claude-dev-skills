from conftest import load_script, run_json, run_main

mod = load_script("debugging", "log-triage", "log_triage.py")

LOG = """2026-01-02T10:00:00Z INFO request id=7f3a9c0e-1234-4abc-9def-0123456789ab path=/api/users/42 took 12ms
2026-01-02T10:00:01Z INFO request id=0a1b2c3d-5678-4abc-9def-0123456789ab path=/api/users/43 took 9ms
2026-01-02T10:00:02Z ERROR db connection refused host=10.0.0.5:5432 attempt=1
Traceback (most recent call last):
  File "/app/db.py", line 10, in connect
    raise ConnectionError("refused")
2026-01-02T10:00:03Z ERROR db connection refused host=10.0.0.6:5432 attempt=2
2026-01-02T10:00:04Z WARN cache miss key="user:42"
2026-01-02T10:00:05Z DEBUG tick
"""


def test_clusters_and_ranking(write, tmp_path):
    f = write("app.log", LOG)
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 0
    assert rep["lines"] == 9
    templates = {c["template"]: c for c in rep["clusters"]}
    req = [c for c in rep["clusters"] if "request" in c["template"]][0]
    assert req["count"] == 2 and "<uuid>" in req["template"] and "<ts>" in req["template"]
    err = rep["clusters"][0]
    assert err["level"] == "error" and err["count"] == 2 and "<ip>" in err["template"]
    assert err["continuation_lines"] == 3
    assert len(templates) == 4


def test_level_and_grep_filters(write, tmp_path):
    f = write("app.log", LOG)
    rc, rep = run_json(mod, [str(f), "--json", "--level", "warn"])
    assert {c["level"] for c in rep["clusters"]} == {"error", "warn"}
    rc, rep = run_json(mod, [str(f), "--json", "--grep", "cache"])
    assert len(rep["clusters"]) == 1 and rep["clusters"][0]["level"] == "warn"


def test_fail_on_level_and_text_output(write, tmp_path):
    f = write("app.log", LOG)
    rc, out, _ = run_main(mod, [str(f), "--fail-on-level", "error"])
    assert rc == 1 and "distinct templates" in out and "by level:" in out
    rc, out, _ = run_main(mod, [str(f), "--fail-on-level", "fatal"])
    assert rc == 0


def test_bad_inputs():
    rc, _, err = run_main(mod, ["/nonexistent/file.log"])
    assert rc == 2
    rc, _, err = run_main(mod, ["--grep", "(", "/dev/null"])
    assert rc == 2 and "bad --grep" in err


def test_normalise_examples():
    n = mod.normalise
    assert n("user 42 logged in from 192.168.1.1 at 2026-01-02 10:00:00") == "user <n> logged in from <ip> at <ts>"
    assert n('key "abc" path /var/log/app.log hex 0xdeadbeef') == "key <str> path <path> hex <hex>"
    assert n("sent mail to a.b@example.com via https://smtp.example.com/x") == "sent mail to <email> via <url>"
