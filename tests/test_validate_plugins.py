"""Tests for the frontmatter, description and section checks in scripts/validate_plugins.py."""
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


GOOD_DESC = '"Check a thing for problems. Use when asked \\"is this ok?\\". Not for other things."'


def test_good_description_passes():
    assert vp.check_description(GOOD_DESC) == []


def test_unquoted_or_single_quoted_description_fails():
    assert any("double-quoted" in p for p in vp.check_description("Check it. Use when asked. Not for that."))
    assert any("double-quoted" in p for p in vp.check_description("'Check it. Use when asked. Not for that.'"))


def test_description_length_limit_counts_the_parsed_value():
    body = 'Use when asked "is it ok?". Not for that. '
    at_limit = body + "x" * (vp.DESCRIPTION_MAX - len(body))
    assert vp.check_description(f'"{at_limit}"') == []
    problems = vp.check_description(f'"{at_limit}x"')
    assert problems == [f"description is {vp.DESCRIPTION_MAX + 1} chars (max {vp.DESCRIPTION_MAX})"]


def test_description_needs_use_and_not_for():
    assert any("Use when" in p for p in vp.check_description('"Check it. Not for that."'))
    assert any("Not for" in p for p in vp.check_description('"Check it. Use when asked. Not a linter."'))
    assert vp.check_description('"Write it. Use when asked \\"what went wrong?\\". Not for bugs."') == []


def test_description_needs_a_quoted_trigger_phrase_of_two_to_eight_words():
    def phrase_problems(desc: str) -> list[str]:
        return [p for p in vp.check_description(desc) if "trigger phrase" in p]

    assert phrase_problems('"Check it. Use when asked. Not for that."')
    assert phrase_problems('"Check it. Use when asked \\"flaky?\\". Not for that."')
    assert phrase_problems('"Check it. Use when asked \\"one two three four five six seven eight nine\\". Not for that."')
    assert phrase_problems('"Check it. Use when asked \\"is it flaky?\\". Not for that."') == []
    assert phrase_problems('"Check it. Use when asked \\"one two three four five six seven eight\\". Not for that."') == []
    assert vp.trigger_phrases('Use when asked "is it flaky?" or "slow".') == ["is it flaky?"]


def test_empty_description_fails():
    assert vp.check_description("") == ["frontmatter has no description"]
    assert "frontmatter has no description" in vp.check_description('""')


def test_scalar_value_resolves_quotes_and_escapes():
    assert vp.scalar_value('"say \\"hi\\""') == 'say "hi"'
    assert vp.scalar_value("'it''s'") == "it's"
    assert vp.scalar_value("plain") == "plain"


def test_limits_section_required_and_before_related():
    ok = "# T\n\n## Procedure\n\n## Limits\n\n- x\n\n## Related\n\n- y\n"
    assert vp.check_sections(ok) == []
    assert any("no \"## Limits\"" in p for p in vp.check_sections("# T\n\n## Related\n"))
    assert vp.check_sections("# T\n\n## Related\n\n## Limits\n") == ['"## Limits" must come before "## Related"']


def test_limits_heading_inside_a_code_fence_does_not_count():
    body = "# T\n\n```markdown\n## Limits\n```\n\n## Related\n"
    assert vp.check_sections(body)


def test_repository_skills_pass_description_and_section_rules():
    for p in sorted((ROOT / "plugins").glob("*/skills/*/SKILL.md")):
        text = p.read_text(encoding="utf-8")
        fm = vp.frontmatter(p)
        assert vp.check_description(fm["description"]) == [], p
        assert vp.check_sections(text) == [], p
