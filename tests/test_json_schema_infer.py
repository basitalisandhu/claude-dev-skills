import json

from conftest import load_script, run_json, run_main

mod = load_script("data", "json-schema-author", "json_schema_infer.py")

SAMPLES = [
    {"id": 1, "name": "a", "email": "a@x.io", "status": "active", "tags": ["x"], "score": 1.5, "meta": {"k": 1}, "created": "2024-01-01T00:00:00Z"},
    {"id": 2, "name": "b", "email": "b@x.io", "status": "inactive", "tags": [], "score": 2, "meta": {"k": 2, "extra": True}, "created": "2024-01-02T00:00:00Z", "nick": None},
    {"id": 3, "name": "c", "email": "c@x.io", "status": "active", "tags": ["y", "z"], "score": 3.25, "meta": {"k": 3}, "created": "2024-01-03T00:00:00Z", "nick": "cc"},
    {"id": 4, "name": "d", "email": "d@x.io", "status": "active", "tags": ["x"], "score": 0, "meta": {"k": 4}, "created": "2024-01-04T00:00:00Z"},
    {"id": 5, "name": "e", "email": "e@x.io", "status": "banned", "tags": ["x"], "score": 9.5, "meta": {"k": 5}, "created": "2024-01-05T00:00:00Z"},
]


def test_infer_from_array(write, tmp_path):
    f = write("s.json", json.dumps(SAMPLES))
    rc, schema = run_json(mod, [str(f), "--title", "User"])
    assert rc == 0
    assert schema["$schema"].endswith("2020-12/schema") and schema["title"] == "User"
    props = schema["properties"]
    assert schema["required"] == ["created", "email", "id", "meta", "name", "score", "status", "tags"]
    assert props["id"]["type"] == "integer" and props["id"]["minimum"] == 1 and props["id"]["maximum"] == 5
    assert props["score"]["type"] == "number"
    assert props["email"]["format"] == "email" and props["created"]["format"] == "date-time"
    assert props["status"]["enum"] == ["active", "banned", "inactive"]
    assert props["nick"]["type"] == ["null", "string"]
    assert props["tags"]["items"]["type"] == "string"
    assert props["meta"]["required"] == ["k"] and props["meta"]["additionalProperties"] is False
    assert schema["x-inferred-from"]["samples"] == 5


def test_ndjson_and_options(write, tmp_path):
    f = write("s.ndjson", "\n".join(json.dumps(s) for s in SAMPLES) + "\n")
    rc, schema = run_json(mod, [str(f), "--no-examples", "--no-bounds", "--enum-max", "2"])
    props = schema["properties"]
    assert "examples" not in props["name"] and "minimum" not in props["id"] and "enum" not in props["status"]
    assert "minLength" not in props["name"]


def test_merges_multiple_files_and_examples(write, tmp_path):
    a = write("a.json", json.dumps({"x": 1}))
    b = write("b.json", json.dumps({"x": "two", "y": [1, 2]}))
    rc, schema = run_json(mod, [str(a), str(b)])
    assert schema["properties"]["x"]["type"] == ["integer", "string"]
    assert schema["required"] == ["x"]
    assert schema["properties"]["x"]["examples"] == [1, "two"]
    assert schema["properties"]["y"]["items"]["type"] == "integer"


def test_errors(write, tmp_path):
    f = write("bad.json", "{not json\n")
    rc, _, err = run_main(mod, [str(f)])
    assert rc == 2 and "not JSON" in err
    rc, _, _ = run_main(mod, [str(tmp_path / "nope.json")])
    assert rc == 2
    e = write("empty.json", "  ")
    rc, _, err = run_main(mod, [str(e)])
    assert rc == 2
