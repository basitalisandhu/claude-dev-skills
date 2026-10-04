import json

from conftest import load_script, run_json, run_main

mod = load_script("data", "api-contract-review", "openapi_lint.py")

BAD = """openapi: 3.0.3
info:
  title: Pets
servers:
  - url: http://api.example.com/{version}
paths:
  /pet_store/{id}/:
    get:
      responses:
        '200':
          description: ok
    post:
      operationId: createPet
      summary: Create
      parameters:
        - name: petId
          in: path
          schema: {type: string}
      responses:
        '201':
          description: created
          content:
            application/json: {}
  /petOwners:
    get:
      operationId: createPet
      tags: [owners]
      responses:
        '404': {description: nope}
components:
  schemas:
    Unused:
      type: object
    Ref:
      $ref: '#/components/schemas/Missing'
"""

GOOD = {
    "openapi": "3.1.0",
    "info": {"title": "Pets", "version": "1.0.0"},
    "servers": [{"url": "https://api.example.com"}],
    "tags": [{"name": "pets"}],
    "security": [{"bearer": []}],
    "paths": {
        "/pets/{id}": {
            "parameters": [{"name": "id", "in": "path", "required": True, "description": "Pet id", "schema": {"type": "string"}}],
            "get": {"operationId": "getPet", "summary": "Get a pet", "tags": ["pets"],
                    "responses": {"200": {"description": "ok", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Pet"}, "example": {"id": "1"}}}},
                                  "404": {"description": "missing", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}}},
            "delete": {"operationId": "deletePet", "summary": "Delete", "tags": ["pets"],
                       "responses": {"204": {"description": "gone"}, "default": {"description": "error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}, "example": {"message": "x"}}}}}},
        }
    },
    "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}},
                   "schemas": {"Pet": {"type": "object", "properties": {"id": {"type": "string"}}}, "Error": {"type": "object", "properties": {"message": {"type": "string"}}}}},
}


def test_bad_spec(write, tmp_path):
    f = write("bad.yaml", BAD)
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 1 and rep["operations"] == 3
    ids = {x["id"] for x in rep["findings"]}
    for expected in ["OAS-000", "OAS-001", "OAS-002", "OAS-003", "OAS-004", "OAS-005", "OAS-006", "OAS-007", "OAS-008", "OAS-009", "OAS-010", "OAS-011", "OAS-012", "OAS-013", "OAS-014", "OAS-015"]:
        assert expected in ids, expected
    titles = [x["title"] for x in rep["findings"]]
    assert any("Duplicate operationId createPet" in t for t in titles)
    assert any("{id} in the template is not declared" in t for t in titles)
    assert any("petId declared but not in the template" in t for t in titles)
    assert any("missing component" in t for t in titles)
    assert any("Mixed path naming styles" in t for t in titles)


def test_good_spec_json(write, tmp_path):
    f = write("good.json", json.dumps(GOOD))
    rc, rep = run_json(mod, [str(f), "--json", "--fail-on", "info"])
    assert rc == 0, rep["findings"]
    assert rep["findings"] == []


def test_fail_on_levels_and_text(write, tmp_path):
    spec = dict(GOOD)
    spec = json.loads(json.dumps(GOOD))
    del spec["paths"]["/pets/{id}"]["get"]["summary"]
    f = write("warn.json", json.dumps(spec))
    rc, out, _ = run_main(mod, [str(f)])
    assert rc == 0 and "OAS-006" in out
    rc, _, _ = run_main(mod, [str(f), "--fail-on", "warn"])
    assert rc == 1


def test_errors(write, tmp_path):
    f = write("bad.json", "{oops")
    rc, _, err = run_main(mod, [str(f)])
    assert rc == 2 and "cannot parse" in err
    rc, _, _ = run_main(mod, [str(tmp_path / "nope.yaml")])
    assert rc == 2
    f2 = write("swagger.yaml", "swagger: '2.0'\ninfo: {title: x, version: '1'}\npaths: {}\n")
    rc, rep = run_json(mod, [str(f2), "--json"])
    assert rc == 1 and any("Not an OpenAPI 3.x" in x["title"] for x in rep["findings"])
