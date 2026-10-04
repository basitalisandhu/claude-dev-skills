import base64
import json

from conftest import load_script, run_json, run_main

mod = load_script("security-basics", "jwt-inspector", "jwt_inspect.py")
NOW = "2026-03-01T12:00:00+00:00"
NOW_TS = 1772366400


def b64(obj) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


def token(header, payload, sig="c2lnbmF0dXJl"):
    return f"{b64(header)}.{b64(payload)}.{sig}"


def test_sound_token_has_only_notes():
    t = token({"alg": "RS256", "typ": "JWT", "kid": "key-1"}, {"iss": "https://issuer.example", "aud": "api", "sub": "user-1", "iat": NOW_TS - 60, "exp": NOW_TS + 3600, "scope": "read"})
    rc, rep = run_json(mod, [t, "--json", "--now", NOW])
    assert rc == 0 and rep["verified"] is False and rep["findings"] == []
    assert rep["payload"]["sub"] == "user-1"


def test_alg_none_and_empty_signature_and_bearer_prefix():
    t = f"{b64({'alg': 'none'})}.{b64({'sub': 'x', 'exp': NOW_TS + 10})}."
    rc, rep = run_json(mod, ["Bearer " + t, "--json", "--now", NOW])
    assert rc == 1
    ids = [f["id"] for f in rep["findings"]]
    assert ids.count("JWT-001") == 2 and rep["counts"]["critical"] == 2


def test_lifetime_sensitive_claims_and_header_risks():
    t = token({"alg": "HS256", "jku": "https://evil.example/keys", "kid": "../../etc/passwd"},
              {"sub": "u", "iat": NOW_TS, "exp": NOW_TS + 60 * 86400, "password": "hunter2", "email": "a@b.c", "nbf": NOW_TS + 3600})
    rc, rep = run_json(mod, [t, "--json", "--now", NOW])
    ids = {f["id"] for f in rep["findings"]}
    assert {"JWT-002", "JWT-003", "JWT-004", "JWT-005", "JWT-006", "JWT-007", "JWT-010"} <= ids
    life = [f for f in rep["findings"] if f["id"] == "JWT-002"][0]
    assert life["severity"] == "high" and "60 days" in life["title"]
    assert any(f["id"] == "JWT-007" and f["severity"] == "high" for f in rep["findings"])
    assert any(f["id"] == "JWT-007" and f["severity"] == "info" for f in rep["findings"])


def test_expired_text_output_and_jwe():
    t = token({"alg": "ES256", "typ": "JWT"}, {"iss": "i", "aud": "a", "sub": "s", "iat": NOW_TS - 7200, "exp": NOW_TS - 3600})
    rc, out, _ = run_main(mod, [t, "--now", NOW])
    assert rc == 0 and "SIGNATURE NOT VERIFIED" in out and "expired" in out and "1h" in out
    jwe = f"{b64({'alg': 'RSA-OAEP', 'enc': 'A256GCM'})}.a.b.c.d"
    rc, rep = run_json(mod, [jwe, "--json"])
    assert rep["segments"] == 5 and rep["payload"] is None and any(f["id"] == "JWT-009" for f in rep["findings"])


def test_not_a_jwt_and_bad_now():
    rc, _, err = run_main(mod, ["hello.world"])
    assert rc == 2 and "not a JWT" in err
    rc, _, err = run_main(mod, ["x.y.z"])
    assert rc == 2
    t = token({"alg": "RS256"}, {"exp": NOW_TS})
    rc, _, err = run_main(mod, [t, "--now", "yesterday"])
    assert rc == 2
