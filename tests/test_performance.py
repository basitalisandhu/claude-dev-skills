"""Cost must grow with the input, not with its square.

The JavaScript and TypeScript paths of four scripts used to find each match's line number by counting newlines from
the start of the file, which made a large file quadratic (a 9,000-copy sample took 34 seconds in extract_docs.py).
These tests run inputs large enough that the old code took several seconds and the fixed code well under one, with
a generous ceiling so a slow CI machine does not fail them.
"""
from __future__ import annotations

import time

import pytest
from conftest import load_script, run_main
from test_complexity_report import JS as COMPLEXITY_JS
from test_extract_docs import JS as DOCS_JS

TS_SOURCE = ("export function f(a: number, b): string { return ''; }\nconst g = (x: any, y: string) => x;\n"
             "class K {\n  method(p, q: number) { return p as any; }\n}\n")
EXPORTS = "export function a(){}\nexport const b = 1;\nmodule.exports.c = 1;\nexports.d = 2;\n"

CASES = [
    ("docs", "api-docs-from-code", "extract_docs.py", "big.js", DOCS_JS, 6000, False),
    ("code-quality", "complexity-report", "complexity_report.py", "big.js", COMPLEXITY_JS, 6000, False),
    ("code-quality", "type-coverage", "type_coverage.py", "big.ts", TS_SOURCE, 15000, False),
    ("code-quality", "dead-code-finder", "dead_code_finder.py", "lib.js", EXPORTS, 10000, True),
]


@pytest.mark.parametrize("plugin, skill, script, name, sample, copies, folder", CASES, ids=[c[2] for c in CASES])
def test_large_javascript_input_is_not_quadratic(tmp_path, plugin, skill, script, name, sample, copies, folder):
    module = load_script(plugin, skill, script)
    path = tmp_path / name
    path.write_text(sample * copies, encoding="utf-8")
    start = time.perf_counter()
    rc, _out, err = run_main(module, [str(tmp_path if folder else path), "--json"])
    elapsed = time.perf_counter() - start
    assert rc in (0, 1), err
    assert elapsed < 4.0, f"{script} took {elapsed:.1f}s on {copies} copies; line numbers may be counted per match again"
