"""Tests for the strict-YAML frontmatter check in scripts/validate_plugins.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("validate_plugins", ROOT / "scripts" / "validate_plugins.py")
vp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vp)


def check(frontmatter_lines: str) -> list[str]:
    return vp.check_frontmatter_scalars(Path("x/SKILL.md"), f"---\n{frontmatter_lines}\n---\nbody\n")


def test_plain_scalar_with_colon_space_fails():
    problems = check("name: a\ndescription: Do this. Use when: asked.")
    assert len(problems) == 1 and "x/SKILL.md:3" in problems[0]


def test_plain_scalar_with_space_hash_fails():
    assert check("description: Use it # not a comment")


def test_plain_scalar_without_indicators_passes():
    assert check("name: a\ndescription: Use when a url like http://x.test/a#b appears. Not for 10:30 times.") == []


def test_quoted_scalar_with_colon_passes():
    assert check('description: "Use when: asked, with a \\"quote\\" inside"') == []
    assert check("description: 'it''s: fine'") == []


def test_unclosed_quote_fails():
    assert check('description: "never closed: here')
    assert check('description: "ends with escaped quote\\"')
    assert check("description: 'open")


def test_nested_metadata_value_is_checked():
    assert check("metadata:\n  author: Name: Other")
    assert check("metadata:\n  author: Muhammad Basit Ali") == []


def test_repository_skills_all_pass():
    for p in sorted((ROOT / "plugins").glob("*/skills/*/SKILL.md")):
        assert vp.check_frontmatter_scalars(p, p.read_text(encoding="utf-8")) == [], p
