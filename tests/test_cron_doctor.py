from conftest import load_script, run_json, run_main

mod = load_script("devops", "cron-doctor", "cron_doctor.py")

CRONTAB = """MAILTO=ops@example.com
PATH=/usr/local/bin:/usr/bin:/bin
# nightly backup
30 2 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1
*/5 * * * * /usr/local/bin/poll.sh
0 9 1 * 1 /usr/local/bin/report.sh > /dev/null 2>&1
0 9 * * * /usr/local/bin/a.sh >/dev/null 2>&1
0 9 * * * /usr/local/bin/b.sh >/dev/null 2>&1
* * * * * date +%Y > /tmp/x
@daily /usr/local/bin/rotate.sh >/dev/null 2>&1
@daily /usr/local/bin/rotate.sh >/dev/null 2>&1
61 * * * * /bin/true
"""


def test_schedules_descriptions_and_findings(write, tmp_path):
    f = write("crontab", CRONTAB)
    rc, rep = run_json(mod, [str(f), "--json", "--now", "2026-03-10T12:00"])
    assert rc == 1  # CRON-001 for the 61 and CRON-004 for %
    jobs = {j["line"]: j for j in rep["jobs"]}
    assert jobs[4]["description"] == "at 02:30 every day"
    assert jobs[4]["next"][0] == "2026-03-11T02:30"
    assert jobs[5]["description"] == "every 5 minutes every day"
    assert jobs[5]["next"][0] == "2026-03-10T12:05"
    assert "OR" in jobs[6]["description"]
    assert jobs[10]["schedule"] == "@daily"
    assert jobs[12]["valid"] is False
    ids = {x["id"] for x in rep["findings"]}
    for expected in ["CRON-001", "CRON-002", "CRON-003", "CRON-004", "CRON-006", "CRON-008", "CRON-009", "CRON-011", "CRON-012"]:
        assert expected in ids, expected
    assert "CRON-007" not in ids and "CRON-005" not in ids


def test_system_crontab_user_field_and_missing_newline(write, tmp_path):
    f = write("sys", "0 3 * * * root /usr/bin/updatedb >/dev/null 2>&1")
    rc, rep = run_json(mod, [str(f), "--json", "--system", "--now", "2026-01-01T00:00"])
    j = rep["jobs"][0]
    assert j["user"] == "root" and j["command"].startswith("/usr/bin/updatedb")
    assert "CRON-010" in {x["id"] for x in rep["findings"]}
    rc, rep = run_json(mod, [str(f), "--json", "--now", "2026-01-01T00:00"])  # auto-detect
    assert rep["jobs"][0]["user"] == "root"


def test_field_parsing_and_names():
    pf = mod.parse_field
    assert pf("*/15", "minute", 0, 59, {}) == {0, 15, 30, 45}
    assert pf("1-5", "day-of-week", 0, 7, mod.CRON_DAYS) == {1, 2, 3, 4, 5}
    assert pf("mon,wed,7", "day-of-week", 0, 7, mod.CRON_DAYS) == {1, 3, 0}
    assert pf("jan-mar", "month", 1, 12, mod.MONTHS) == {1, 2, 3}
    import pytest
    with pytest.raises(mod.CronError):
        pf("5-1", "hour", 0, 23, {})
    with pytest.raises(mod.CronError):
        pf("*/0", "hour", 0, 23, {})


def test_next_runs_respect_dow_and_month(write, tmp_path):
    f = write("c", "0 8 * 2 mon /x >/dev/null 2>&1\n")
    rc, rep = run_json(mod, [str(f), "--json", "--now", "2026-01-15T00:00", "--next", "2"])
    assert rep["jobs"][0]["next"] == ["2026-02-02T08:00", "2026-02-09T08:00"]


def test_text_output_and_bad_inputs(write, tmp_path):
    f = write("c", "0 8 * * * /x >/dev/null 2>&1\n")
    rc, out, _ = run_main(mod, [str(f), "--now", "2026-01-01T00:00"])
    assert rc == 0 and "at 08:00 every day" in out and "next:" in out
    rc, _, err = run_main(mod, [str(tmp_path / "nope")])
    assert rc == 2
    rc, _, err = run_main(mod, [str(f), "--now", "not-a-date"])
    assert rc == 2
