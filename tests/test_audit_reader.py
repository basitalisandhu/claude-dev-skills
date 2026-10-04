import json

from conftest import load_script, run_json, run_main

mod = load_script("security-basics", "dependency-audit-reader", "audit_reader.py")

NPM7 = {"vulnerabilities": {
    "lodash": {"name": "lodash", "severity": "high", "isDirect": True, "via": [{"source": 1523, "title": "Prototype Pollution", "url": "https://x/1523", "severity": "high"}], "effects": [], "range": "<4.17.21", "fixAvailable": {"name": "lodash", "version": "4.17.21", "isSemVerMajor": False}},
    "minimist": {"name": "minimist", "severity": "critical", "isDirect": False, "via": [{"source": 1179, "title": "Prototype Pollution", "url": "https://x/1179"}], "effects": ["mkdirp"], "range": "<0.2.4", "fixAvailable": False},
    "mkdirp": {"name": "mkdirp", "severity": "critical", "isDirect": False, "via": ["minimist"], "effects": [], "range": "0.4.1 - 0.5.1", "fixAvailable": True},
}}
PIP = [{"name": "requests", "version": "2.25.0", "vulns": [{"id": "PYSEC-2023-74", "fix_versions": ["2.31.0"], "aliases": ["CVE-2023-32681"], "description": "Leaks Proxy-Authorization"}]},
       {"name": "safe", "version": "1.0", "vulns": []}]
CARGO = {"vulnerabilities": {"list": [{"advisory": {"id": "RUSTSEC-2023-0001", "title": "Bad thing", "cvss_severity": "medium"}, "package": {"name": "foo", "version": "1.0.0"}, "versions": {"patched": [">=1.0.1"]}}]}, "warnings": {"unmaintained": [{"kind": "unmaintained", "package": {"name": "old", "version": "0.1"}, "advisory": {"id": "RUSTSEC-2020-0002", "title": "unmaintained"}}]}}
NPM6 = {"advisories": {"1": {"module_name": "ws", "severity": "moderate", "title": "DoS", "url": "https://x/1", "findings": [{"version": "5.0.0", "paths": ["ws"]}], "patched_versions": ">=5.2.3"}}}
YARN = "\n".join([json.dumps({"type": "auditAdvisory", "data": {"resolution": {"path": "a>b"}, "advisory": {"module_name": "b", "severity": "low", "title": "x", "id": 7, "findings": [{"version": "1.0"}], "patched_versions": "<0.0.0"}}}),
                  json.dumps({"type": "auditSummary", "data": {"vulnerabilities": {"low": 1}}})])


def test_npm7(write, tmp_path):
    f = write("npm.json", json.dumps(NPM7))
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 1 and rep["format"] == "npm" and rep["vulnerable_packages"] == 3
    assert rep["counts"] == {"critical": 2, "high": 1, "moderate": 0, "low": 0, "info": 0}
    assert rep["items"][0]["severity"] == "critical"
    by = {i["package"]: i for i in rep["items"]}
    assert by["lodash"]["direct"] is True and by["lodash"]["fix"] == "lodash@4.17.21"
    assert by["minimist"]["fixable"] is False and by["minimist"]["dependents"] == ["mkdirp"]
    assert rep["fixable"] == 2 and rep["unfixable"] == 1


def test_pip_and_cargo(write, tmp_path):
    f = write("pip.json", json.dumps(PIP))
    rc, rep = run_json(mod, [str(f), "--json", "--fail-on", "info"])
    assert rc == 1 and rep["format"] == "pip-audit" and rep["vulnerable_packages"] == 1
    assert rep["items"][0]["fix"] == "2.31.0" and "CVE-2023-32681" in rep["items"][0]["ids"]
    f2 = write("cargo.json", json.dumps(CARGO))
    rc, rep = run_json(mod, [str(f2), "--json"])
    assert rc == 0 and rep["format"] == "cargo" and rep["vulnerable_packages"] == 2
    assert rep["items"][0]["severity"] == "moderate" and rep["items"][1]["severity"] == "low"


def test_npm6_and_yarn(write, tmp_path):
    f = write("npm6.json", json.dumps(NPM6))
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rep["format"] == "npm6" and rep["items"][0]["package"] == "ws" and rep["items"][0]["direct"] is True
    f2 = write("yarn.ndjson", YARN)
    rc, rep = run_json(mod, [str(f2), "--json"])
    assert rep["format"] == "yarn" and rep["items"][0]["package"] == "b" and rep["items"][0]["direct"] is False and rep["items"][0]["fixable"] is False


def test_ignore_text_and_errors(write, tmp_path):
    f = write("npm.json", json.dumps(NPM7))
    rc, rep = run_json(mod, [str(f), "--json", "--ignore", "1523", "--ignore", "1179"])
    assert {i["package"] for i in rep["items"]} == {"mkdirp"}
    rc, out, _ = run_main(mod, [str(f)])
    assert rc == 1 and "upgrade first:" in out
    rc, _, err = run_main(mod, [str(tmp_path / "nope.json")])
    assert rc == 2
    f3 = write("odd.json", json.dumps({"hello": "world"}))
    rc, _, err = run_main(mod, [str(f3)])
    assert rc == 2 and "unrecognised" in err
