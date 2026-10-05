import json

from conftest import load_script, run_json, run_main

mod = load_script("devops", "terraform-apply-gate", "terraform_apply_gate.py")

AWS = "registry.terraform.io/hashicorp/aws"


def rc(address, rtype, actions, after=None, after_unknown=None, provider=AWS, reason=None):
    entry = {
        "address": address,
        "type": rtype,
        "mode": "managed",
        "provider_name": provider,
        "change": {"actions": actions, "after": after, "after_unknown": after_unknown or {}},
    }
    if reason:
        entry["action_reason"] = reason
    return entry


def plan_file(write, changes, **extra):
    data = {"format_version": "1.2", "terraform_version": "1.9.5", "resource_changes": changes, **extra}
    return write("plan.json", json.dumps(data))


POLICY = """\
forbid_destroy: [aws_db_instance, "aws_dynamodb_*"]
protected_names: ["*prod*"]
allowed_providers: [hashicorp/aws]
required_tags: [owner, environment]
max_replace: 1
"""


def test_clean_plan_is_allowed(write):
    p = plan_file(
        write,
        [
            rc("aws_s3_bucket.logs", "aws_s3_bucket", ["create"], {"tags": {"owner": "ops", "environment": "dev"}}),
            rc("aws_iam_role.app", "aws_iam_role", ["no-op"], {}),
        ],
    )
    pol = write("policy.yml", POLICY)
    code, rep = run_json(mod, [str(p), "--policy", str(pol), "--json"])
    assert code == 0 and rep["verdict"] == "allow" and rep["findings"] == []
    assert rep["summary"]["create"] == 1 and rep["summary"]["no-op"] == 1


def test_forbidden_type_and_protected_name_block(write):
    p = plan_file(
        write,
        [
            rc(
                "aws_db_instance.main",
                "aws_db_instance",
                ["delete", "create"],
                {},
                reason="replace_because_cannot_update",
            ),
            rc("aws_sqs_queue.prod_jobs", "aws_sqs_queue", ["delete"], None),
            rc("aws_dynamodb_table.t", "aws_dynamodb_table", ["delete"], None),
        ],
    )
    pol = write("policy.yml", POLICY)
    code, rep = run_json(mod, [str(p), "--policy", str(pol), "--json"])
    assert code == 1 and rep["verdict"] == "block"
    rules = {(f["rule"], f["address"]) for f in rep["findings"]}
    assert ("forbidden-destroy", "aws_db_instance.main") in rules
    assert ("protected-name", "aws_sqs_queue.prod_jobs") in rules
    assert ("forbidden-destroy", "aws_dynamodb_table.t") in rules
    assert any("replace_because_cannot_update" in f["reason"] for f in rep["findings"])


def test_other_destroy_asks_and_can_be_switched_off(write):
    p = plan_file(write, [rc("aws_sqs_queue.jobs", "aws_sqs_queue", ["delete"], None)])
    code, rep = run_json(mod, [str(p), "--json"])
    assert code == 1 and rep["verdict"] == "ask" and rep["findings"][0]["rule"] == "destroy"
    pol = write("p.yml", "ask_on_destroy: false\n")
    code, rep = run_json(mod, [str(p), "--policy", str(pol), "--json"])
    assert code == 0 and rep["verdict"] == "allow"


def test_tags_missing_unknown_and_tag_types(write):
    p = plan_file(
        write,
        [
            rc("aws_s3_bucket.a", "aws_s3_bucket", ["create"], {"tags": {"owner": "x"}}),
            rc("aws_s3_bucket.b", "aws_s3_bucket", ["create"], {"tags_all": {"owner": "x", "environment": "p"}}),
            rc("aws_s3_bucket.c", "aws_s3_bucket", ["update"], {}, {"tags": True}),
            rc(
                "random_id.x",
                "random_id",
                ["create"],
                {"byte_length": 4},
                provider="registry.terraform.io/hashicorp/random",
            ),
        ],
    )
    pol = write("p.yml", "required_tags: [owner, environment]\n")
    code, rep = run_json(mod, [str(p), "--policy", str(pol), "--json"])
    found = {(f["rule"], f["address"]) for f in rep["findings"]}
    assert found == {("missing-tags", "aws_s3_bucket.a"), ("unknown-tags", "aws_s3_bucket.c")}
    assert code == 1 and rep["verdict"] == "ask"
    pol = write("p2.yml", "required_tags: [owner]\ntag_types: [random_*]\n")
    code, rep = run_json(mod, [str(p), "--policy", str(pol), "--json"])
    assert [(f["rule"], f["address"]) for f in rep["findings"]] == [("missing-tags", "random_id.x")]


def test_provider_and_limits_block(write):
    p = plan_file(
        write,
        [
            rc(
                "google_storage_bucket.g",
                "google_storage_bucket",
                ["create"],
                {},
                provider="registry.terraform.io/hashicorp/google",
            ),
            rc("aws_instance.a", "aws_instance", ["create", "delete"], {}),
            rc("aws_instance.b", "aws_instance", ["delete", "create"], {}),
        ],
    )
    pol = write("p.yml", "allowed_providers: [hashicorp/aws]\nmax_replace: 1\nmax_destroy: 1\nask_on_destroy: false\n")
    code, rep = run_json(mod, [str(p), "--policy", str(pol), "--json"])
    rules = sorted(f["rule"] for f in rep["findings"])
    assert rules == ["max-destroy", "max-replace", "provider-not-allowed"]
    assert code == 1 and rep["verdict"] == "block" and rep["summary"]["replace"] == 2


def test_errored_plan_blocks_and_data_sources_ignored(write):
    data_read = {
        "address": "data.aws_ami.x",
        "type": "aws_ami",
        "mode": "data",
        "provider_name": AWS,
        "change": {"actions": ["read"]},
    }
    p = plan_file(write, [data_read], errored=True)
    code, rep = run_json(mod, [str(p), "--json"])
    assert code == 1 and rep["verdict"] == "block" and rep["findings"][0]["rule"] == "plan-errored"


def test_bad_input_exit_2(write, tmp_path):
    code, _, err = run_main(mod, [str(tmp_path / "missing.json")])
    assert code == 2 and "not found" in err
    bad = write("bad.json", "{not json")
    assert run_main(mod, [str(bad)])[0] == 2
    state = write("state.json", json.dumps({"format_version": "1.0", "values": {}}))
    code, _, err = run_main(mod, [str(state)])
    assert code == 2 and "not a saved plan" in err
    good = plan_file(write, [])
    typo = write("typo.yml", "forbid_destory: [aws_db_instance]\n")
    code, _, err = run_main(mod, [str(good), "--policy", str(typo)])
    assert code == 2 and "forbid_destory" in err
    wrong = write("wrong.yml", "max_replace: lots\n")
    assert run_main(mod, [str(good), "--policy", str(wrong)])[0] == 2


def test_text_output_and_out_file(write, tmp_path):
    p = plan_file(write, [rc("aws_sqs_queue.jobs", "aws_sqs_queue", ["delete"], None)])
    code, out, _ = run_main(mod, [str(p)])
    assert code == 1 and "verdict ASK" in out and "aws_sqs_queue.jobs" in out
    target = tmp_path / "gate.json"
    code, out, _ = run_main(mod, [str(p), "--json", "--out", str(target)])
    assert out == "" and json.loads(target.read_text(encoding="utf-8"))["verdict"] == "ask"
