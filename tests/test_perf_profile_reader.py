from conftest import load_script, run_json, run_main

mod = load_script("debugging", "perf-profile-reader", "perf_profile_reader.py")

COLLAPSED = """main;handle_request;parse_json 30
main;handle_request;query_db;socket.recv 50
main;handle_request;render 15
main;idle 5
"""

PPROF = """File: app
Type: cpu
Showing nodes accounting for 1.80s, 90% of 2.00s total
      flat  flat%   sum%        cum   cum%
     1.20s 60.00% 60.00%      1.50s 75.00%  main.compute
     0.40s 20.00% 80.00%      0.40s 20.00%  runtime.mallocgc
     0.20s 10.00% 90.00%      2.00s   100%  main.main
"""

CPROFILE = """         1234 function calls in 3.500 seconds

   Ordered by: internal time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      100    2.000    0.020    2.500    0.025 app.py:10(slow)
     1000    0.900    0.001    0.900    0.001 {built-in method time.sleep}
        1    0.100    0.100    3.500    3.500 app.py:1(main)
"""

PYSPY = """Process 123: python app.py
Python v3.11.0

Thread 0x7F1 (active): "MainThread"
    recv (socket.py:10)
    query (db.py:20)
    main (app.py:5)
Thread 0x7F2 (idle): "worker"
    wait (threading.py:300)
    run (worker.py:9)
"""


def test_collapsed_stacks(write, tmp_path):
    f = write("p.txt", COLLAPSED)
    rc, s = run_json(mod, [str(f), "--json"])
    assert rc == 0 and s["format"] == "collapsed" and s["total"] == 100
    assert s["top_self"][0]["name"] == "socket.recv" and s["top_self"][0]["percent"] == 50.0
    assert s["top_cumulative"][0]["name"] == "main" and s["top_cumulative"][0]["percent"] == 100.0
    assert s["top_stacks"][0]["samples"] == 50
    assert any("one frame holds" in c for c in s["checks"]) and any("waiting" in c for c in s["checks"])


def test_pprof_text(write, tmp_path):
    f = write("p.txt", PPROF)
    rc, s = run_json(mod, [str(f), "--json"])
    assert s["format"] == "pprof" and s["unit"] == "s" and s["total"] == 2.0
    assert s["top_self"][0]["name"] == "main.compute" and s["top_self"][0]["percent"] == 60.0
    assert s["top_cumulative"][0]["name"] == "main.main"


def test_cprofile_text(write, tmp_path):
    f = write("p.txt", CPROFILE)
    rc, s = run_json(mod, [str(f), "--json"])
    assert s["format"] == "cprofile" and s["total"] == 3.5
    assert s["top_self"][0]["name"] == "app.py:10(slow)" and s["top_self"][0]["calls"] == "100"
    assert s["top_cumulative"][0]["name"] == "app.py:1(main)"


def test_pyspy_dump_and_text_output(write, tmp_path):
    f = write("d.txt", PYSPY)
    rc, s = run_json(mod, [str(f), "--json"])
    assert s["format"] == "pyspy-dump" and s["total"] == 2
    assert {r["name"] for r in s["top_self"]} == {"recv (socket.py:10)", "wait (threading.py:300)"}
    rc, out, _ = run_main(mod, [str(f)])
    assert rc == 0 and "top by self" in out


def test_unrecognised_and_missing(write, tmp_path):
    f = write("x.txt", "hello world\nthis is not a profile\n")
    rc, _, err = run_main(mod, [str(f)])
    assert rc == 2 and "could not recognise" in err
    rc, _, _ = run_main(mod, [str(tmp_path / "nope")])
    assert rc == 2
    rc, _, err = run_main(mod, [str(f), "--format", "pprof"])
    assert rc == 2 and "no rows" in err
