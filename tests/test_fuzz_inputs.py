"""Seeded fuzz tests: every script that reads a file must exit 0, 1 or 2 on mutated input, never with a traceback.

Each case starts from valid sample inputs (most are the constants the script's own tests use), applies seeded
mutations (slices deleted or repeated, junk tokens inserted, lines swapped, the file truncated, invalid UTF-8 bytes,
and for JSON inputs values swapped for other JSON types), writes the result to a temporary file and runs the
script's main(). Exit 2 must come with a message on stderr. A failure names the seed, so it can be replayed with
FUZZ_SEED=<seed>; FUZZ_ROUNDS raises the number of rounds per case. Standard library only.
"""
from __future__ import annotations

import base64
import json
import os
import random

import pytest
from conftest import assemble, load_script, run_main
from test_audit_reader import CARGO, PIP, YARN
from test_changelog import CHANGELOG
from test_complexity_report import JS as COMPLEXITY_JS
from test_complexity_report import PY as COMPLEXITY_PY
from test_cron_doctor import CRONTAB
from test_csv_profiler import CSV
from test_dockerfile_lint import BAD as DOCKER_BAD
from test_dockerfile_lint import GOOD as DOCKER_GOOD
from test_extract_docs import JS as DOCS_JS
from test_extract_docs import PY as DOCS_PY
from test_gha_lint import BAD as GHA_BAD
from test_gha_lint import GOOD as GHA_GOOD
from test_headers_check import BAD as HEADERS_BAD
from test_headers_check import GOOD as HEADERS_GOOD
from test_json_schema_infer import SAMPLES as SCHEMA_SAMPLES
from test_k8s_review import BAD as K8S_BAD
from test_k8s_review import GOOD as K8S_GOOD
from test_log_triage import LOG
from test_openapi_lint import BAD as OPENAPI_BAD
from test_openapi_lint import GOOD as OPENAPI_GOOD
from test_perf_profile_reader import COLLAPSED, CPROFILE, PPROF, PYSPY
from test_release_notes import LOG as GIT_LOG
from test_terraform_apply_gate import POLICY as TF_POLICY

ROUNDS = int(os.environ.get("FUZZ_ROUNDS", "40"))
BASE_SEED = int(os.environ.get("FUZZ_SEED", "20261026"))

JUNK = ["\x00", "�", "{", "}", "[", "]", ":", '"', "'", "<", ">", "&", "\n", "\t", "  ", "-", "#", "*", "=",
        "${{ github.event.issue.title }}", "0" * 300, "é", "\r\n", "\\", "---\n", "- ", "? ", "|", "%", "@",
        "1e999", "-1", "null", "NaN", "‮", "a" * 2000, ";", "/*", "*/", '"""', "<!--", "]]>", "&#0;"]

TF_PLAN = json.dumps({"format_version": "1.2", "terraform_version": "1.9.5", "resource_changes": [
    {"address": "aws_s3_bucket.logs", "type": "aws_s3_bucket", "mode": "managed",
     "provider_name": "registry.terraform.io/hashicorp/aws",
     "change": {"actions": ["create"], "after": {"tags": {"owner": "ops"}}, "after_unknown": {}}},
    {"address": "aws_db_instance.prod", "type": "aws_db_instance", "mode": "managed",
     "provider_name": "registry.terraform.io/hashicorp/aws",
     "change": {"actions": ["delete", "create"], "after": {}, "after_unknown": {}},
     "action_reason": "replace_because_cannot_update"}]})

JUNIT = ('<?xml version="1.0"?><testsuites><testsuite name="s" tests="2">'
         '<testcase classname="pkg.TestX" name="a" time="0.5"/>'
         '<testcase classname="pkg.TestX" name="b" time="0.5"><failure message="timeout">trace</failure></testcase>'
         '</testsuite></testsuites>')

DIFF = """diff --git a/app/views.py b/app/views.py
--- a/app/views.py
+++ b/app/views.py
@@ -1,3 +1,5 @@
 import os
+query = "SELECT * FROM users WHERE id = " + request.args["id"]
+subprocess.call(cmd, shell=True)
 def view():
-    return ok()
+    return eval(request.data)
"""

ENV_TEMPLATE = "# comment\nDATABASE_URL=postgres://localhost/db\nAPI_KEY=\nDEBUG=false\nexport PORT=8080\n"
ENV_REAL = "DATABASE_URL=postgres://db/app\nDEBUG=true\nEXTRA=1\nDEBUG=false\n"
REGEX_CASES = ("# emails\n+ user@example.com\n- not-an-email\n"
               '= bob@example.com => {"user": "bob", "domain": "example.com"}\n')
TS_SOURCE = ("export function f(a: number, b): string { return ''; }\nconst g = (x: any, y: string) => x;\n"
             "class K {\n  method(p, q: number) { return p as any; }\n}\n")
SECRETS_TEXT = f'aws_access_key_id = "{assemble("AKIA", "IOSFODNN7EXAMPLE")}"\npassword = "not-a-real-one"\n'


def b64(obj) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


JWT = f"{b64({'alg': 'HS256', 'typ': 'JWT', 'kid': 'k1'})}.{b64({'sub': 'u', 'exp': 1772370000, 'email': 'a@b.c'})}.c2ln"


def junk_value(rng: random.Random, depth: int = 0) -> object:
    choice = rng.randrange(8 if depth < 2 else 5)
    if choice == 0:
        return None
    if choice == 1:
        return rng.choice([True, False, 0, -1, 2**63, 1.5, 1e308])
    if choice in (2, 3):
        return rng.choice(JUNK[:20] + ["", "x", "create", "delete", "high", "critical"])
    if choice == 4:
        return {}
    if choice == 5:
        return [junk_value(rng, depth + 1) for _ in range(rng.randrange(3))]
    return {rng.choice(["name", "id", "type", "severity", "actions", "x"]): junk_value(rng, depth + 1)}


def mutate_json(rng: random.Random, data: object) -> object:
    def walk(node, prefix=()):
        yield prefix
        if isinstance(node, dict):
            for k, v in node.items():
                yield from walk(v, prefix + (k,))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, prefix + (i,))

    for _ in range(rng.randrange(1, 4)):
        paths = list(walk(data))
        path = rng.choice(paths)
        if not path:
            return junk_value(rng)
        parent = data
        for step in path[:-1]:
            parent = parent[step]
        if isinstance(parent, dict) and rng.random() < 0.3:
            parent.pop(path[-1], None)
        else:
            parent[path[-1]] = junk_value(rng)
    return data


def mutate_text(rng: random.Random, text: str) -> str:
    for _ in range(rng.randrange(1, 5)):
        action = rng.randrange(6)
        n = len(text)
        a = rng.randrange(n + 1)
        b = min(n, a + rng.randrange(1, 40))
        if action == 0:
            text = text[:a] + text[b:]
        elif action == 1:
            text = text[:b] + text[a:b] * rng.randrange(2, 4) + text[b:]
        elif action in (2, 3):
            text = text[:a] + rng.choice(JUNK) + text[a:]
        elif action == 4:
            lines = text.split("\n")
            if len(lines) > 1:
                i, j = rng.randrange(len(lines)), rng.randrange(len(lines))
                lines[i], lines[j] = lines[j], lines[i]
            text = "\n".join(lines)
        else:
            text = text[: rng.randrange(n + 1)]
    return text


def mutate(rng: random.Random, seed: str) -> bytes:
    if rng.random() < 0.25:
        try:
            data = json.loads(seed)
        except ValueError:
            data = None
        if isinstance(data, (dict, list)):
            return json.dumps(mutate_json(rng, data)).encode("utf-8")
    raw = mutate_text(rng, seed).encode("utf-8", "surrogatepass")
    if rng.random() < 0.05:
        cut = rng.randrange(len(raw) + 1)
        raw = raw[:cut] + b"\xff\xfe\xc3" + raw[cut:]
    return raw


def put(folder, name: str, data: bytes):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def repo_with(folder, files: dict[str, bytes]):
    for name, data in files.items():
        put(folder / "repo", name, data)
    return folder / "repo"


# case name: (plugin, skill, script, seeds, argv builder taking (rng, tmp folder, mutated bytes) -> argv)
CASES = {
    "complexity_report": ("code-quality", "complexity-report", "complexity_report.py", [COMPLEXITY_PY, COMPLEXITY_JS],
                          lambda r, d, b: [str(put(d, r.choice(["m.py", "m.js", "m.ts"]), b))]),
    "dead_code_finder": ("code-quality", "dead-code-finder", "dead_code_finder.py", [COMPLEXITY_PY, COMPLEXITY_JS],
                         lambda r, d, b: [str(put(d, "src/" + r.choice(["m.py", "m.js", "index.ts"]), b).parent)]),
    "test_gap_finder": ("code-quality", "test-gap-finder", "test_gap_finder.py", [COMPLEXITY_PY],
                        lambda r, d, b: [str(repo_with(d, {"src/app.py": b, "tests/test_app.py": b}))]),
    "type_coverage": ("code-quality", "type-coverage", "type_coverage.py", [COMPLEXITY_PY, TS_SOURCE],
                      lambda r, d, b: [str(put(d, r.choice(["a.py", "a.ts"]), b))]),
    "extract_docs": ("docs", "api-docs-from-code", "extract_docs.py", [DOCS_PY, DOCS_JS],
                     lambda r, d, b: [str(put(d, r.choice(["m.py", "m.js", "m.ts"]), b))]),
    "openapi_lint": ("data", "api-contract-review", "openapi_lint.py", [OPENAPI_BAD, json.dumps(OPENAPI_GOOD)],
                     lambda r, d, b: [str(put(d, r.choice(["api.yaml", "api.json"]), b))]),
    "csv_profiler": ("data", "csv-profiler", "csv_profiler.py", [CSV],
                     lambda r, d, b: [str(put(d, r.choice(["a.csv", "a.tsv"]), b))]),
    "json_schema_infer": ("data", "json-schema-author", "json_schema_infer.py",
                          [json.dumps(s) for s in SCHEMA_SAMPLES],
                          lambda r, d, b: [str(put(d, "sample.json", b))]),
    "regex_tester": ("data", "regex-builder", "regex_tester.py", [REGEX_CASES],
                     lambda r, d, b: [r.choice([r"^(?P<user>[\w.+-]+)@(?P<domain>[\w-]+\.[\w.]+)$", r"(a+)+$", "[",
                                                "(?P<x>a)(?P=x)"]), "--cases", str(put(d, "cases.txt", b))]),
    "flaky_test_hunter": ("debugging", "flaky-test-hunter", "flaky_test_hunter.py", [JUNIT],
                          lambda r, d, b: [str(put(d, "run1.xml", b))]),
    "log_triage": ("debugging", "log-triage", "log_triage.py", [LOG], lambda r, d, b: [str(put(d, "app.log", b))]),
    "perf_profile_reader": ("debugging", "perf-profile-reader", "perf_profile_reader.py",
                            [COLLAPSED, PPROF, CPROFILE, PYSPY], lambda r, d, b: [str(put(d, "profile.txt", b))]),
    "cron_doctor": ("devops", "cron-doctor", "cron_doctor.py", [CRONTAB],
                    lambda r, d, b: [str(put(d, "crontab", b))]),
    "dockerfile_lint": ("devops", "dockerfile-hardening", "dockerfile_lint.py", [DOCKER_BAD, DOCKER_GOOD],
                        lambda r, d, b: [str(put(d, "Dockerfile", b))]),
    "env_diff": ("devops", "env-diff", "env_diff.py", [ENV_TEMPLATE, ENV_REAL],
                 lambda r, d, b: [str(put(d, ".env.example", b)), str(put(d, ".env", b[::-1]))]),
    "gha_lint": ("devops", "github-actions-author", "gha_lint.py", [GHA_BAD, GHA_GOOD],
                 lambda r, d, b: [str(put(d, "ci.yml", b))]),
    "k8s_review": ("devops", "k8s-manifest-review", "k8s_review.py", [K8S_BAD, K8S_GOOD],
                   lambda r, d, b: [str(put(d, "deploy.yaml", b))]),
    "release_notes": ("devops", "release-notes", "release_notes.py", [GIT_LOG],
                      lambda r, d, b: ["--input", str(put(d, "git.log", b)), "--version", "1.0.0", "--date",
                                       "2026-10-26"]),
    "terraform_apply_gate_plan": ("devops", "terraform-apply-gate", "terraform_apply_gate.py", [TF_PLAN],
                                  lambda r, d, b: [str(put(d, "plan.json", b)), "--policy",
                                                   str(put(d, "policy.yml", TF_POLICY.encode()))]),
    "terraform_apply_gate_policy": ("devops", "terraform-apply-gate", "terraform_apply_gate.py", [TF_POLICY],
                                    lambda r, d, b: [str(put(d, "plan.json", TF_PLAN.encode())), "--policy",
                                                     str(put(d, "policy.yml", b))]),
    "changelog": ("docs", "changelog-keeper", "changelog.py", [CHANGELOG],
                  lambda r, d, b: ["--file", str(put(d, "CHANGELOG.md", b)),
                                   *r.choice([["check"], ["show"], ["show", "1.0.0"], ["--dry-run", "add", "Fixed", "x"],
                                              ["--dry-run", "release", "9.9.9", "--date", "2026-10-26"]])]),
    "audit_reader": ("security-basics", "dependency-audit-reader", "audit_reader.py",
                     [json.dumps(PIP), json.dumps(CARGO), YARN], lambda r, d, b: [str(put(d, "audit.json", b))]),
    "diff_security_scan": ("security-basics", "diff-security-review", "diff_security_scan.py", [DIFF],
                           lambda r, d, b: [str(put(d, "change.diff", b))]),
    "headers_check": ("security-basics", "http-security-headers", "headers_check.py", [HEADERS_BAD, HEADERS_GOOD],
                      lambda r, d, b: [str(put(d, "response.txt", b))]),
    "jwt_inspect": ("security-basics", "jwt-inspector", "jwt_inspect.py", [JWT],
                    lambda r, d, b: [b.decode("utf-8", "replace").replace("\x00", ""), "--now",
                                     "2026-03-01T12:00:00+00:00"]),
    "secrets_scan": ("security-basics", "secrets-hygiene", "secrets_scan.py", [SECRETS_TEXT, DOCKER_BAD],
                     lambda r, d, b: [str(put(d, "repo/config.py", b).parent)]),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_mutated_inputs_never_crash(tmp_path, case):
    plugin, skill, script, seeds, argv = CASES[case]
    module = load_script(plugin, skill, script)
    failures = []
    rounds = max(1, ROUNDS // 4) if case == "regex_tester" else ROUNDS  # each round may time a slow pattern
    for round_number in range(rounds):
        seed = BASE_SEED + round_number
        rng = random.Random(f"{case}-{seed}")
        folder = tmp_path / f"r{round_number}"
        folder.mkdir()
        data = mutate(rng, rng.choice(seeds))
        try:
            rc, _out, err = run_main(module, argv(rng, folder, data))
        except Exception as exc:  # noqa: BLE001 - the point is to catch anything
            failures.append(f"seed {seed}: {type(exc).__name__}: {exc}"[:300])
            continue
        if rc not in (0, 1, 2):
            failures.append(f"seed {seed}: exit {rc}")
        elif rc == 2 and not err.strip():
            failures.append(f"seed {seed}: exit 2 with no message")
    assert not failures, "\n".join(failures[:10])


# Crashes the fuzzer found on 2026-10-26, kept as plain regression tests.
REGRESSIONS = [
    ("data", "api-contract-review", "openapi_lint.py", "api.yaml", "openapi: 3.0.3\ninfo: [a, b]\npaths: {}\n", []),
    ("devops", "k8s-manifest-review", "k8s_review.py", "d.yaml",
     "apiVersion: apps/v1\nkind: Deployment\nmetadata: {name: x}\nspec:\n  template: oops\n", []),
    ("devops", "github-actions-author", "gha_lint.py", "ci.yml", "name: ci\non: push\njobs: [1, 2]\n", []),
    ("devops", "terraform-apply-gate", "terraform_apply_gate.py", "plan.json",
     '{"resource_changes": [{"address": "a.b", "type": "a", "change": {"actions": 1.5}}]}', []),
    ("devops", "dockerfile-hardening", "dockerfile_lint.py", "Dockerfile", "FROM python:3.12 AS build\nFROM\n", []),
    ("security-basics", "dependency-audit-reader", "audit_reader.py", "audit.json",
     '[{"name": "x", "version": "1", "vulns": [{"id": true, "fix_versions": [], "description": {"a": 1}}]}]',
     ["--format", "pip-audit"]),
]


@pytest.mark.parametrize("plugin, skill, script, name, text, extra", REGRESSIONS, ids=[r[2] for r in REGRESSIONS])
def test_fuzz_regressions_exit_cleanly(tmp_path, plugin, skill, script, name, text, extra):
    module = load_script(plugin, skill, script)
    rc, _out, err = run_main(module, [str(put(tmp_path, name, text.encode())), *extra])
    assert rc in (0, 1, 2)
    assert rc != 2 or err.strip()


def test_csv_profiler_treats_overflowing_numbers_as_text(tmp_path):
    module = load_script("data", "csv-profiler", "csv_profiler.py")
    rc, out, err = run_main(module, [str(put(tmp_path, "a.csv", b"n\n1\n1e999\n2\n")), "--json"])
    assert rc == 0, err
    assert json.loads(out)["columns"][0]["type"] == "string"


def test_terraform_gate_rejects_a_plan_that_is_not_utf8(tmp_path):
    module = load_script("devops", "terraform-apply-gate", "terraform_apply_gate.py")
    rc, _out, err = run_main(module, [str(put(tmp_path, "plan.json", b"\xff\xfe{}"))])
    assert rc == 2 and "UTF-8" in err
