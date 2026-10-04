from conftest import assemble, load_script, run_json, run_main

mod = load_script("devops", "dockerfile-hardening", "dockerfile_lint.py")

# assembled at run time so the full token never sits in the repository (see conftest.assemble)
FAKE_STRIPE_KEY = assemble("sk_live_", "abcdefghijklmnop123456")

BAD = f"""FROM python:latest
MAINTAINER someone
ENV API_KEY={FAKE_STRIPE_KEY}
ARG DB_PASSWORD
RUN apt-get update && apt-get install -y curl && apt-get upgrade -y
RUN curl -sSL https://example.com/install.sh | bash
RUN pip install flask && chmod -R 777 /app
RUN sudo make install
ADD https://example.com/tool.tgz /tmp/
ADD src/ /app/src/
COPY .env /app/.env
COPY . /app
EXPOSE 22 8080
CMD python app.py
"""

GOOD = """FROM python:3.12-slim@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
RUN adduser --system --group app \\
    && apt-get update \\
    && apt-get install -y --no-install-recommends tini \\
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --chown=app:app src/ /app/src/
USER app
HEALTHCHECK CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
ENTRYPOINT ["tini", "--", "python", "/app/src/main.py"]
"""


def test_bad_dockerfile_findings(write, tmp_path):
    f = write("Dockerfile", BAD)
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 1
    ids = {x["id"] for x in rep["findings"]}
    for expected in ["DF-001", "DF-002", "DF-003", "DF-004", "DF-005", "DF-006", "DF-007", "DF-008", "DF-009", "DF-010", "DF-011", "DF-012", "DF-013", "DF-014", "DF-016", "DF-017"]:
        assert expected in ids, expected
    sev = {x["id"]: x["severity"] for x in rep["findings"]}
    assert sev["DF-004"] == "critical" and sev["DF-005"] == "high"
    # the secret value is masked
    key_finding = [x for x in rep["findings"] if x["id"] == "DF-004" and "API_KEY" in x["title"]][0]
    assert FAKE_STRIPE_KEY not in key_finding["evidence"]
    assert rep["counts"]["critical"] == 1


def test_good_dockerfile_is_clean_at_high(write, tmp_path):
    f = write("Dockerfile", GOOD)
    write(".dockerignore", ".git\n")
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 0
    ids = {x["id"] for x in rep["findings"]}
    assert "DF-002" not in ids and "DF-001" not in ids and "DF-006" not in ids
    assert ids <= {"DF-015"}


def test_user_inherited_from_named_stage_and_root_user(write, tmp_path):
    f = write("Dockerfile", "FROM alpine:3.20 AS base\nRUN adduser -D app\nUSER app\nFROM base\nCMD [\"sh\"]\n")
    rc, rep = run_json(mod, [str(f), "--json", "--fail-on", "critical"])
    assert "DF-002" not in {x["id"] for x in rep["findings"]}
    f2 = write("Dockerfile.root", "FROM alpine:3.20\nUSER app\nUSER root\nCMD [\"sh\"]\n")
    rc, rep = run_json(mod, [str(f2), "--json"])
    assert "DF-002" in {x["id"] for x in rep["findings"]}


def test_fail_on_and_bad_path(write, tmp_path):
    f = write("Dockerfile", "FROM alpine:3.20\nUSER nobody\nHEALTHCHECK NONE\nCMD [\"sh\"]\n")
    rc, out, _ = run_main(mod, [str(f)])
    assert rc == 0 and "findings" in out
    rc, out, _ = run_main(mod, [str(f), "--fail-on", "info"])
    assert rc == 1  # DF-015 digest note
    rc, _, err = run_main(mod, [str(tmp_path / "missing")])
    assert rc == 2


def test_parser_handles_continuations_and_heredocs():
    ins = mod.parse_dockerfile("FROM a:1\nRUN echo one \\\n    && echo two\n# comment\nRUN <<EOT\necho hi\nEOT\nCMD [\"x\"]\n")
    assert [i["instruction"] for i in ins] == ["FROM", "RUN", "RUN", "CMD"]
    assert "echo two" in ins[1]["args"] and ins[1]["line"] == 2
    assert "echo hi" in ins[2]["args"]
