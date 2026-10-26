"""Tests for the bundled minimal YAML reader (one copy per skill that needs it; the copies must stay identical)."""
import importlib.util
import math

import pytest
from conftest import PLUGINS

COPIES = [
    PLUGINS / "devops/skills/github-actions-author/scripts/_miniyaml.py",
    PLUGINS / "devops/skills/k8s-manifest-review/scripts/_miniyaml.py",
    PLUGINS / "devops/skills/terraform-apply-gate/scripts/_miniyaml.py",
    PLUGINS / "data/skills/api-contract-review/scripts/_miniyaml.py",
]


def _load():
    spec = importlib.util.spec_from_file_location("miniyaml_under_test", COPIES[0])
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


yaml = _load()


def test_copies_are_identical():
    texts = {p.read_text(encoding="utf-8") for p in COPIES}
    assert len(texts) == 1


def test_workflow_shapes():
    doc = yaml.load("""
name: ci
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - name: Run
        run: |
          echo "a: b" # kept
          pytest
        env:
          FOO: "bar # kept"
""")
    assert doc["on"]["push"]["branches"] == ["main"]
    assert doc["on"]["pull_request"] is None
    assert doc["permissions"] == {"contents": "read"}
    steps = doc["jobs"]["test"]["steps"]
    assert steps[0] == {"uses": "actions/checkout@v4"}
    assert steps[1]["run"] == 'echo "a: b" # kept\npytest\n'
    assert steps[1]["env"]["FOO"] == "bar # kept"


def test_scalars_flow_anchors_and_multi_doc():
    docs = yaml.load_all("""
base: &b {a: 1, b: two}
derived:
  <<: *b
  b: three
nums: [1, 2.5, -3, 0x10, 1_000]
bools: [true, False, yes, on]
nulls: [~, null, ]
strs: ['it''s', "tab\\there", plain text]
folded: >-
  one
  two
literal: |+
  keep

---
second: doc
...
""")
    assert len(docs) == 2
    d = docs[0]
    assert d["derived"] == {"a": 1, "b": "three"}
    assert d["nums"] == [1, 2.5, -3, 16, 1000]
    assert d["bools"] == [True, False, "yes", "on"]
    assert d["nulls"] == [None, None]
    assert d["strs"] == ["it's", "tab\there", "plain text"]
    assert d["folded"] == "one two"
    assert d["literal"] == "keep\n\n"
    assert docs[1] == {"second": "doc"}


def test_sequence_at_parent_indent_and_nested_sequences():
    d = yaml.load("items:\n- a\n- b: 1\n  c: 2\n- - x\n  - y\nkey: v\n")
    assert d["items"] == ["a", {"b": 1, "c": 2}, ["x", "y"]]
    assert d["key"] == "v"


def test_errors_have_line_numbers():
    with pytest.raises(yaml.YAMLError) as exc:
        yaml.load("a:\n\tb: 1\n")
    assert "line 2" in str(exc.value)
    with pytest.raises(yaml.YAMLError):
        yaml.load("a: *missing\n")
    assert yaml.load("") is None
    assert yaml.load("# only a comment\n") is None


def test_special_floats():
    assert math.isinf(yaml.load("x: .inf")["x"])
    assert math.isnan(yaml.load("x: .nan")["x"])


@pytest.mark.skipif(importlib.util.find_spec("yaml") is None, reason="PyYAML not installed; cross-check skipped")
def test_matches_pyyaml_on_kubernetes_sample():
    import yaml as pyyaml
    text = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  labels: {app: web}
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: web
        image: "nginx:1.25"
        args: ["--port", "8080"]
        securityContext:
          runAsNonRoot: true
        resources:
          limits: {cpu: "500m", memory: 128Mi}
"""
    assert yaml.load(text) == pyyaml.safe_load(text)


# Inputs that made the reader loop for ever ("- - -:" and friends) or raise something other than YAMLError. Each
# runs in a child process under a timeout, so a regression fails the test instead of hanging the suite.
HANG_OR_CRASH = ["- - -:", "- - - -:", "-  - -:", "a:\n  - - -:", "- - ----: --->#[1", "-  - - }'b: ", "[[a]: 1]",
                 "[{1}:- ", "--- &x", "---  !t "]

_FUZZ_CHILD = r"""
import importlib.util, random, sys
spec = importlib.util.spec_from_file_location("m", sys.argv[1]); m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
cases = sys.argv[3:]
tokens = ["-", " ", "- ", ":", ": ", "a", "b: ", "\n", "  ", "[", "]", "{", "}", ",", "&x", "*x", "|", ">", "#", "'",
          '"', "? ", "---", "...", "!t ", "-:", "1"]
rng = random.Random(20261026)
cases += ["".join(rng.choice(tokens) for _ in range(rng.randrange(1, 14))) for _ in range(int(sys.argv[2]))]
for text in cases:
    try:
        m.load(text)
    except m.YAMLError:
        pass
print("ok", len(cases))
"""


@pytest.mark.parametrize("copy", COPIES, ids=lambda p: p.parts[-3])
def test_malformed_sequences_terminate_with_yaml_error(copy):
    import subprocess
    import sys

    proc = subprocess.run([sys.executable, "-c", _FUZZ_CHILD, str(copy), "3000", *HANG_OR_CRASH], capture_output=True,
                          text=True, encoding="utf-8", timeout=60)
    assert proc.returncode == 0 and proc.stdout.startswith("ok"), proc.stderr[-2000:]


def test_dash_dash_dash_colon_is_a_yaml_error():
    with pytest.raises(yaml.YAMLError, match="cannot parse this sequence item"):
        yaml.load("- - -:")
    assert yaml.load("--- &x") is None
