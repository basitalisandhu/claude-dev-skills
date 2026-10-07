"""Shared helpers for the script tests.

Every skill script lives at plugins/<plugin>/skills/<skill>/scripts/<name>.py and is a standalone program, not a
package. Tests load one by path with load_script() and call its main(argv) function, capturing stdout.
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"


def script_path(plugin: str, skill: str, name: str) -> Path:
    return PLUGINS / plugin / "skills" / skill / "scripts" / name


def load_script(plugin: str, skill: str, name: str):
    """Import a skill script by path under a unique module name."""
    path = script_path(plugin, skill, name)
    module_name = f"skill_{plugin}_{skill}_{path.stem}".replace("-", "_")
    if module_name in sys.modules:
        return sys.modules[module_name]
    scripts_dir = str(path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_main(module, argv: list[str]) -> tuple[int, str, str]:
    """Run module.main(argv) and return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            rc = module.main(argv)
        except SystemExit as exc:  # argparse errors
            rc = int(exc.code or 0)
    return rc, out.getvalue(), err.getvalue()


def run_json(module, argv: list[str]) -> tuple[int, dict | list]:
    rc, out, err = run_main(module, argv)
    try:
        return rc, json.loads(out)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"not JSON (rc={rc}): {out!r} stderr={err!r}") from exc


def assemble(*parts: str) -> str:
    """Join the pieces of a fake credential at run time.

    Fixtures need values shaped like real tokens (Stripe, Slack, GitHub, npm, ...) so the scanners have something to
    find, but the complete value must never sit in a committed file: GitHub push protection and secret scanners
    reject it, fake or not. Joining at run time (rather than `"sk_live_" + "..."`, which the compiler folds into one
    constant in the .pyc) keeps the whole value out of both the sources and the bytecode cache.
    """
    return "".join(parts)


@pytest.fixture
def write(tmp_path: Path):
    def _write(rel: str, content: str) -> Path:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")  # identical bytes on every OS (no CRLF on Windows)
        return p
    return _write
