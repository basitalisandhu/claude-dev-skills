import json

from conftest import load_script, run_json, run_main

mod = load_script("security-basics", "http-security-headers", "headers_check.py")

BAD = """HTTP/1.1 200 OK
Server: nginx/1.18.0
X-Powered-By: PHP/7.4
Content-Type: text/html
Set-Cookie: session=abc; Path=/
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
X-XSS-Protection: 1; mode=block
Content-Security-Policy-Report-Only: default-src 'self'

<html></html>
"""

GOOD = """HTTP/2 200
content-type: text/html; charset=utf-8
strict-transport-security: max-age=63072000; includeSubDomains; preload
content-security-policy: default-src 'self'; script-src 'self' 'nonce-abc'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'
x-content-type-options: nosniff
referrer-policy: strict-origin-when-cross-origin
permissions-policy: camera=(), microphone=()
cross-origin-opener-policy: same-origin
cross-origin-resource-policy: same-origin
set-cookie: __Host-session=abc; Path=/; Secure; HttpOnly; SameSite=Lax
cache-control: no-store
"""


def test_bad_response(write, tmp_path):
    f = write("resp.txt", BAD)
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 1 and rep["grade"] == "F" and rep["status"] == "HTTP/1.1 200 OK"
    ids = {x["id"] for x in rep["findings"]}
    for expected in ["HDR-001", "HDR-002", "HDR-003", "HDR-004", "HDR-005", "HDR-006", "HDR-007", "HDR-008", "HDR-009", "HDR-010", "HDR-011", "HDR-012", "HDR-013"]:
        assert expected in ids, expected
    assert rep["counts"]["critical"] == 1
    cookie = [x for x in rep["findings"] if x["id"] == "HDR-007"]
    assert {x["severity"] for x in cookie} == {"high", "medium"}


def test_good_response(write, tmp_path):
    f = write("resp.txt", GOOD)
    rc, rep = run_json(mod, [str(f), "--json", "--fail-on", "info"])
    assert rc == 0, rep["findings"]
    assert rep["grade"] == "A" and rep["findings"] == []


def test_json_input_http_mode_and_redirect_blocks(write, tmp_path):
    f = write("h.json", json.dumps({"Content-Type": "text/plain", "Set-Cookie": ["a=1; HttpOnly; SameSite=Lax"]}))
    rc, rep = run_json(mod, [str(f), "--json", "--http"])
    assert "HDR-001" not in {x["id"] for x in rep["findings"]}
    assert not any(x["id"] == "HDR-007" and "Secure" in x["title"] for x in rep["findings"])
    two = "HTTP/1.1 301 Moved\nLocation: /x\n\nHTTP/1.1 200 OK\nX-Content-Type-Options: nosniff\n\n"
    f2 = write("two.txt", two)
    rc, rep = run_json(mod, [str(f2), "--json"])
    assert rep["status"] == "HTTP/1.1 200 OK" and "HDR-003" not in {x["id"] for x in rep["findings"]}


def test_csp_details_and_errors(write, tmp_path):
    f = write("c.txt", "HTTP/1.1 200 OK\nContent-Security-Policy: default-src *; script-src 'unsafe-inline' 'unsafe-eval' https:\nStrict-Transport-Security: max-age=300\n")
    rc, rep = run_json(mod, [str(f), "--json"])
    titles = " | ".join(x["title"] for x in rep["findings"])
    assert "'unsafe-inline'" in titles and "'unsafe-eval'" in titles and "Wildcard" in titles and "max-age below one year" in titles
    rc, _, err = run_main(mod, [str(tmp_path / "nope")])
    assert rc == 2
    e = write("empty.txt", "just text without headers\n")
    rc, _, err = run_main(mod, [str(e)])
    assert rc == 2 and "no headers" in err
    rc, out, _ = run_main(mod, [str(f)])
    assert rc == 1 and "grade" in out
def test_har_input(write, tmp_path):
    har = {
        "log": {
            "entries": [
                {
                    "request": {"url": "https://example.com/api"},
                    "response": {
                        "status": 200,
                        "statusText": "OK",
                        "httpVersion": "HTTP/1.1",
                        "content": {"mimeType": "application/json"},
                        "headers": [
                            {"name": "Content-Type", "value": "application/json"},
                            {"name": "Set-Cookie", "value": "a=1; Path=/"},
                            {"name": "Set-Cookie", "value": "b=2; Path=/"}
                        ]
                    }
                },
                {
                    "request": {"url": "https://example.com/"},
                    "response": {
                        "status": 200,
                        "statusText": "OK",
                        "httpVersion": "HTTP/2",
                        "content": {"mimeType": "text/html"},
                        "headers": [
                            {"name": "Content-Type", "value": "text/html"}
                        ]
                    }
                }
            ]
        }
    }
    f = write("test.har", json.dumps(har))
    
    # Default picks the HTML one (the second entry here)
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rep["status"] == "HTTP/2 200 OK"
    assert "content-type" in rep["headers_present"]
    
    # --url picks the first one
    rc, rep = run_json(mod, [str(f), "--json", "--url", "https://example.com/api"])
    assert rep["status"] == "HTTP/1.1 200 OK"
    
    # an entry list with duplicate set-cookie headers produces two cookie findings
    # for the API entry, it has a=1 and b=2 without Secure/HttpOnly
    cookies = [x for x in rep["findings"] if x["id"] == "HDR-007"]
    assert len(cookies) >= 2
    cookie_titles = [x["title"] for x in cookies]
    assert any("Cookie a without" in t for t in cookie_titles)
    assert any("Cookie b without" in t for t in cookie_titles)

