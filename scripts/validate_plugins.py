#!/usr/bin/env python3
"""Validate this marketplace repository without the Claude Code CLI.

Checks:
  * every JSON file parses; marketplace.json has name, owner.name and plugins[]; every plugin source directory
    exists and its plugin.json name equals the entry name
  * every plugins/<plugin>/skills/<name>/SKILL.md has YAML frontmatter with name (equal to the directory name,
    lowercase with hyphens, at most 64 chars) and description (non-empty, at most 1024 chars); relative links in
    the body resolve; the body is under 500 lines and says that what the skill reads is untrusted data, not
    instructions
  * frontmatter scalars stay valid under strict YAML readers: a plain (unquoted) value must not contain ": " or
    " #", and a quoted value must be closed
  * every script referenced as ${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<file> exists and is executable;
    every scripts/*.py (apart from private helpers) is executable, has a shebang, offers --json, and has a test
    file tests/test_<stem>.py
  * the root README and each plugin README list every skill; the root README has the install commands
  * house style: no em-dashes, no model identifiers in Markdown, Python or JSON

Exit 1 on any error. Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
warnings: list[str] = []
MODEL_ID_RE = re.compile(r"\b(opus|sonnet|haiku|gpt-?\d|claude-\d|o\d-mini)\b", re.I)
SCRIPT_REF_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/([a-z0-9-]+)/scripts/([A-Za-z0-9_.-]+)")


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def frontmatter(path: Path) -> dict[str, str] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fm: dict[str, str] = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_-]+)\s*:\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def check_json_files() -> dict[Path, object]:
    parsed: dict[Path, object] = {}
    for p in sorted(ROOT.rglob("*.json")):
        if any(part in {"node_modules", ".git", ".pytest_cache"} for part in p.parts):
            continue
        try:
            parsed[p] = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            err(f"{rel(p)}: invalid JSON: {exc}")
    return parsed


def check_marketplace(parsed: dict[Path, object]) -> list[tuple[str, Path]]:
    mp = ROOT / ".claude-plugin" / "marketplace.json"
    data = parsed.get(mp)
    if not isinstance(data, dict):
        err("missing or invalid .claude-plugin/marketplace.json")
        return []
    for key in ("name", "owner", "plugins"):
        if key not in data:
            err(f"marketplace.json: missing {key}")
    if not isinstance(data.get("owner"), dict) or not data["owner"].get("name"):
        err("marketplace.json: owner.name is required")
    name = data.get("name", "")
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", name) or ".." in name:
        err(f"marketplace.json: invalid name {name!r}")
    if not data.get("description"):
        warn("marketplace.json: no description")
    plugins: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for i, entry in enumerate(data.get("plugins") or []):
        if not isinstance(entry, dict) or "name" not in entry or "source" not in entry:
            err(f"marketplace.json: plugins[{i}] needs name and source")
            continue
        if entry["name"] in seen:
            err(f"marketplace.json: duplicate plugin name {entry['name']}")
        seen.add(entry["name"])
        src = entry["source"]
        if not isinstance(src, str) or not src.startswith("./") or ".." in src:
            err(f"marketplace.json: plugins[{i}].source must be a ./relative path without ..: {src}")
            continue
        root = ROOT / src[2:]
        if not root.is_dir():
            err(f"marketplace.json: plugins[{i}] source directory does not exist: {src}")
            continue
        manifest = root / ".claude-plugin" / "plugin.json"
        if not manifest.exists():
            err(f"{src}: missing .claude-plugin/plugin.json")
        else:
            m = parsed.get(manifest)
            if not isinstance(m, dict) or m.get("name") != entry["name"]:
                err(f"{rel(manifest)}: name differs from marketplace entry {entry['name']!r}")
            else:
                for key in ("version", "description", "author"):
                    if key not in m:
                        warn(f"{rel(manifest)}: no {key}")
                if m.get("version") != entry.get("version"):
                    warn(f"{rel(manifest)}: version {m.get('version')} differs from the marketplace entry {entry.get('version')}")
        plugins.append((entry["name"], root))
    return plugins


def check_frontmatter_scalars(path: Path, text: str) -> list[str]:
    """Return problems that make a SKILL.md frontmatter unparseable by strict YAML readers."""
    problems: list[str] = []
    if not text.startswith("---\n"):
        return problems
    end = text.find("\n---", 4)
    if end < 0:
        return problems
    for n, line in enumerate(text[4:end].splitlines(), start=2):
        m = re.match(r"^\s*[A-Za-z_-]+:[ \t]+(.*)$", line)
        if not m:
            continue
        value = m.group(1).strip()
        if not value or value[0] in "|>":
            continue
        where = f"{rel(path) if path.is_relative_to(ROOT) else path}:{n}"
        if value[0] in "\"'":
            quote = value[0]
            i, closed = 1, False
            while i < len(value):
                if quote == '"' and value[i] == "\\":
                    i += 2
                    continue
                if value[i] == quote:
                    if quote == "'" and value[i + 1 : i + 2] == "'":
                        i += 2
                        continue
                    closed = True
                    break
                i += 1
            if not closed:
                problems.append(f"{where}: quoted frontmatter value is not closed")
            elif value[i + 1 :].strip() and not value[i + 1 :].lstrip().startswith("#"):
                problems.append(f"{where}: unexpected text after the closing quote")
        elif ": " in value or " #" in value:
            problems.append(f"{where}: unquoted frontmatter value contains ': ' or ' #'; wrap it in double quotes")
    return problems


def check_skill(plugin_root: Path, skill_dir: Path) -> str | None:
    skill = skill_dir / "SKILL.md"
    if not skill.exists():
        err(f"{rel(skill_dir)}: no SKILL.md")
        return None
    fm = frontmatter(skill)
    if fm is None:
        err(f"{rel(skill)}: no YAML frontmatter")
        return None
    for problem in check_frontmatter_scalars(skill, skill.read_text(encoding="utf-8")):
        err(problem)
    name = fm.get("name", "")
    desc = fm.get("description", "")
    if not name:
        err(f"{rel(skill)}: frontmatter has no name")
    elif name != skill_dir.name:
        err(f"{rel(skill)}: name {name!r} must equal directory name {skill_dir.name!r}")
    if name and (not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name) or len(name) > 64):
        err(f"{rel(skill)}: name must be lowercase letters, digits and single hyphens, at most 64 chars")
    if not desc:
        err(f"{rel(skill)}: frontmatter has no description")
    elif len(desc) > 1024:
        err(f"{rel(skill)}: description is {len(desc)} chars (max 1024)")
    elif not re.search(r"\bUse (when|after|before)\b", desc) or not re.search(r"\bNot\b", desc):
        warn(f"{rel(skill)}: description should say when to use it and when not to")
    if "compatibility" in fm and len(fm["compatibility"]) > 500:
        err(f"{rel(skill)}: compatibility over 500 chars")
    body = skill.read_text(encoding="utf-8")
    if body.count("\n") > 500:
        err(f"{rel(skill)}: over 500 lines; move detail into references/")
    if not re.search(r"\buntrusted\b", body) or not re.search(r"not instructions|never follow|do not act on instructions", body):
        err(f"{rel(skill)}: must say that what it reads is untrusted data, not instructions (see CONTRIBUTING.md)")
    for link in re.findall(r"\]\(([^)#]+)\)", body):
        if link.startswith(("http://", "https://", "mailto:")) or "${" in link:
            continue
        if not (skill_dir / link).exists():
            err(f"{rel(skill)}: link target does not exist: {link}")
    for ref_skill, ref_file in SCRIPT_REF_RE.findall(body):
        target = plugin_root / "skills" / ref_skill / "scripts" / ref_file
        if not target.exists():
            err(f"{rel(skill)}: referenced script does not exist: skills/{ref_skill}/scripts/{ref_file}")
        elif not os.access(target, os.X_OK):
            err(f"{rel(target)}: referenced script is not executable (chmod +x)")
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.is_dir():
        for script in sorted(scripts_dir.glob("*.py")):
            if script.name.startswith("_"):
                continue
            text = script.read_text(encoding="utf-8")
            if not text.startswith("#!/usr/bin/env python3"):
                err(f"{rel(script)}: missing python3 shebang")
            if not os.access(script, os.X_OK):
                err(f"{rel(script)}: not executable (chmod +x)")
            if '"--json"' not in text:
                err(f"{rel(script)}: no --json option")
            if 'if __name__ == "__main__"' not in text:
                err(f"{rel(script)}: no __main__ guard")
            test = ROOT / "tests" / f"test_{script.stem}.py"
            if not test.exists():
                err(f"{rel(script)}: no test file tests/test_{script.stem}.py")
            if f"scripts/{script.name}" not in body:
                err(f"{rel(skill)}: does not mention its script {script.name}")
    return name or None


def check_readme(path: Path, skills: list[str], install: list[str]) -> None:
    if not path.exists():
        err(f"{rel(path)} missing")
        return
    text = path.read_text(encoding="utf-8")
    for s in skills:
        if f"`{s}`" not in text:
            err(f"{rel(path)} does not mention skill `{s}`")
    for needle in install:
        if needle not in text:
            err(f"{rel(path)} is missing the install command {needle!r}")


def check_style() -> None:
    em_dash = chr(0x2014)
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p.suffix not in {".md", ".py", ".json", ".yml", ".yaml", ".toml"}:
            continue
        if any(part in {"node_modules", ".git", ".pytest_cache", "__pycache__"} for part in p.parts):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if em_dash in text:
            line = text[: text.index(em_dash)].count("\n") + 1
            err(f"{rel(p)}:{line}: em-dash found (house style forbids it)")
        if p.suffix in {".md", ".py", ".json"}:
            m = MODEL_ID_RE.search(text)
            if m and not (p.name == "validate_plugins.py"):
                line = text[: m.start()].count("\n") + 1
                err(f"{rel(p)}:{line}: model identifier {m.group(0)!r} (skills must not name a model)")


def main() -> int:
    parsed = check_json_files()
    plugins = check_marketplace(parsed)
    all_skills: list[str] = []
    for name, root in plugins:
        skills_dir = root / "skills"
        if not skills_dir.is_dir():
            err(f"{rel(root)}: no skills/ directory")
            continue
        names: list[str] = []
        for d in sorted(skills_dir.iterdir()):
            if d.is_dir():
                n = check_skill(root, d)
                if n:
                    names.append(n)
        check_readme(root / "README.md", names, [f"/plugin install {name}@claude-dev-skills"])
        all_skills += names
        scripts = [p for p in skills_dir.glob("*/scripts/*.py") if not p.name.startswith("_")]
        print(f"{rel(root)}: {len(names)} skills, {len(scripts)} scripts")
    check_readme(ROOT / "README.md", all_skills, ["/plugin marketplace add basitalisandhu/claude-dev-skills", "/plugin install code-quality@claude-dev-skills"])
    for required in ("LICENSE", "SECURITY.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "CHANGELOG.md", "docs/good-first-issues.md", ".github/workflows/ci.yml"):
        if not (ROOT / required).exists():
            err(f"missing {required}")
    check_style()
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"{len(all_skills)} skills, {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
