from conftest import load_script, run_json, run_main

mod = load_script("docs", "api-docs-from-code", "extract_docs.py")

PY = '''"""Module summary line.

More detail.
"""


def documented(a: int, b: str = "x") -> bool:
    """Do a thing.

    Args:
        a: the first number.
        b (str): a label.

    Returns:
        True when it worked.

    Raises:
        ValueError: when a is negative.
    """
    return True


def undocumented(x):
    return x


def _private():
    """Hidden."""


class Widget:
    """A widget.

    :param size: the size.
    :returns: nothing
    """

    def render(self):
        """Render it."""

    def _internal(self):
        pass
'''

JS = '''/**
 * Add two numbers.
 * @param {number} a - first
 * @param {number} b second
 * @returns {number} the sum
 * @throws {RangeError} when overflow
 * @example
 * add(1, 2)
 */
export function add(a, b) { return a + b; }

/** Multiply. @deprecated use mul2 */
export const mul = (a, b) => a * b;

export class Thing {
  /**
   * Run it.
   */
  run(x) {}
}

export function nothingHere() {}
'''


def test_python_extraction(write, tmp_path):
    write("pkg/m.py", PY)
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    m = rep["modules"][0]
    assert m["module_doc"] == "Module summary line."
    syms = {s["name"]: s for s in m["symbols"]}
    assert set(syms) == {"documented", "undocumented", "Widget", "Widget.render"}
    d = syms["documented"]
    assert d["signature"] == "def documented(a: int, b: str = 'x') -> bool"
    assert d["summary"] == "Do a thing." and d["params"] == {"a": "the first number.", "b": "a label."}
    assert d["returns"].startswith("True when") and d["raises"] == ["ValueError"]
    assert syms["Widget"]["params"] == {"size": "the size."} and syms["Widget"]["returns"] == "nothing"
    assert syms["undocumented"]["documented"] is False
    assert rep["summary"] == {"files": 1, "symbols": 4, "documented": 3, "percent": 75.0}


def test_javascript_jsdoc(write, tmp_path):
    write("src/a.js", JS)
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    syms = {s["name"]: s for s in rep["modules"][0]["symbols"]}
    assert syms["add"]["params"] == {"a": "first", "b": "second"}
    assert syms["add"]["returns"] == "the sum" and syms["add"]["raises"] == ["RangeError"]
    assert syms["add"]["examples"] == ["add(1, 2)"]
    assert syms["mul"]["deprecated"] == "use mul2"
    assert syms["run"]["kind"] == "method" and syms["run"]["summary"] == "Run it."
    assert syms["nothingHere"]["documented"] is False


def test_markdown_output_and_min_coverage(write, tmp_path):
    write("m.py", PY)
    rc, out, _ = run_main(mod, [str(tmp_path)])
    assert rc == 0 and "# API reference" in out and "### `def documented(" in out and "## Undocumented public symbols" in out
    assert "| `a` | the first number. |" in out
    rc, _, _ = run_main(mod, [str(tmp_path), "--min-coverage", "90"])
    assert rc == 1
    rc, rep = run_json(mod, [str(tmp_path), "--json", "--include-private"])
    assert "_private" in {s["name"] for s in rep["modules"][0]["symbols"]}


def test_syntax_error_and_missing_path(write, tmp_path):
    write("bad.py", "def (:\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0 and "error" in rep["modules"][0]
    rc, _, _ = run_main(mod, [str(tmp_path / "nope")])
    assert rc == 2
