"""Every skill has a README.md; for a skill with a script, its sample is the real, current output on a committed fixture.

scripts/render_samples.py reruns each `<!-- sample: ... -->` command; run it without --check to refresh the READMEs
after changing a script's output. The samples are rendered on Linux and macOS, so the comparison is skipped on
Windows, where the scripts print paths with backslashes.
"""
from __future__ import annotations

import subprocess
import sys

import pytest
from conftest import PLUGINS, ROOT


def skills():
    return sorted(p.parent for p in PLUGINS.glob("*/skills/*/SKILL.md"))


def test_every_skill_has_a_readme():
    for skill in skills():
        readme = skill / "README.md"
        assert readme.is_file(), f"{skill.name} has no README.md"
        text = readme.read_text(encoding="utf-8")
        assert text.startswith(f"# {skill.name}\n") and "(SKILL.md)" in text, readme
        has_script = (skill / "scripts").is_dir()
        assert ("<!-- sample: " in text) == has_script, f"{readme}: a sample block exactly when the skill has a script"


@pytest.mark.skipif(sys.platform == "win32", reason="samples are rendered with POSIX paths")
def test_readme_samples_match_the_scripts():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "render_samples.py"), "--check"],
                          capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr + "\nrun python3 scripts/render_samples.py to refresh"
