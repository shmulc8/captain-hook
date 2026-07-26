#!/usr/bin/env python3
"""Documentation and template consistency checks for the captain-hook skill.

This repository's product is documentation, so the checks here cover the failure
modes the behavioral suite cannot see: config templates that do not parse, docs
that teach an invalid schema, and references to symbols or projects that do not
exist. Every check is a permanent gate introduced by one of the repair plans.

Stdlib only, by design — a hook-adjacent script must run with no install step.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES_DIR = SKILL_DIR / "examples"
REPO_ROOT = SKILL_DIR.parent.parent
# Directories at the repository root that are not shipped documentation. The
# first entry is load-bearing: plans/ is gitignored working material that
# quotes the forbidden strings on purpose (it holds the plans that removed
# them), so scanning it would make four gates permanently red.
# .claude/ is the same kind of thing: a developer's own gitignored machine
# settings, not something this repository ships.
EXCLUDED_DIRS = {"plans", ".git", "node_modules", ".remember", "assets", ".github", ".claude"}

# Blocks using these placeholders are illustrative fragments, not whole documents.
PLACEHOLDER = "..."
PY_FRAGMENT_MARKER = "# ..."

JSON_BLOCK_RE = re.compile(r"```json\n(.*?)```", re.S)
PYTHON_BLOCK_RE = re.compile(r"```python\n(.*?)```", re.S)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

FLAT_HOOK_RE = re.compile(
    r'"(PreToolUse|PostToolUse|UserPromptSubmit|Stop|SessionStart|SessionEnd)"'
    r'\s*:\s*\[\s*\{\s*"command"'
)
PHANTOM_SYMBOLS = ("BasePolicy", "PolicyResult", "CanonicalEvent", "BaseAgentAdapter", "HookPayload")
CONTAMINATION = ("captain-obvious", "co_py", "co_ts")
EXIT_CODE_FICTION = "or non-zero"
# Amazon Q project rules are Markdown context files; this YAML schema was invented.
INVENTED_AMAZON_Q_SCHEMA = ('before_command', 'action: "block"')


SCANNED_SUFFIXES = {".md", ".json", ".yml", ".yaml", ".py", ".sh"}


def _excluded(path: pathlib.Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.relative_to(REPO_ROOT).parts[:-1])


def _scan(suffixes: set[str]) -> list[pathlib.Path]:
    return sorted(
        {
            p
            for p in REPO_ROOT.rglob("*")
            if p.is_file() and p.suffix in suffixes and not _excluded(p)
        }
    )


def markdown_files() -> list[pathlib.Path]:
    return _scan({".md"})


def text_files() -> list[pathlib.Path]:
    """Every file a substring gate should scan: docs, templates, and scripts."""
    return _scan(SCANNED_SUFFIXES)


def rel(path: pathlib.Path) -> str:
    return str(path.relative_to(SKILL_DIR.parent.parent))


def read(path: pathlib.Path) -> str:
    """Read a shipped file as UTF-8 regardless of the caller's locale.

    `read_text()` decodes with the preferred encoding, so under `LC_ALL=C` —
    the default in plenty of CI containers — every check here died on the first
    em dash with a UnicodeDecodeError instead of reporting a result.
    """
    return path.read_text(encoding="utf-8")


def check_json_blocks() -> list[str]:
    """1. Every fenced json block in the shipped docs parses."""
    failures = []
    for path in markdown_files():
        for i, block in enumerate(JSON_BLOCK_RE.findall(read(path))):
            if PLACEHOLDER in block:
                continue
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                failures.append(f"{rel(path)} json block {i}: {exc}")
    return failures


def check_example_json() -> list[str]:
    """2. Every shipped config template parses."""
    failures = []
    for path in sorted(EXAMPLES_DIR.rglob("*.json")):
        try:
            json.loads(read(path))
        except json.JSONDecodeError as exc:
            failures.append(f"{rel(path)}: {exc}")
    return failures


def check_flat_claude_schema() -> list[str]:
    """3. No invalid flat Claude Code hook form survives (Plan 001).

    Scans each file whole rather than line by line: FLAT_HOOK_RE's `\\s*` groups
    span newlines, which is how pretty-printed JSON actually spells the invalid
    form, so a per-line scan can only ever catch the minified one-liner.
    """
    failures = []
    for path in text_files():
        if path.name == pathlib.Path(__file__).name:
            continue  # this file spells out the forbidden form on purpose
        text = read(path)
        for match in FLAT_HOOK_RE.finditer(text):
            lineno = text.count("\n", 0, match.start()) + 1
            failures.append(f"{rel(path)}:{lineno}: flat hook form, needs a nested matcher group")
    return failures


def check_phantom_symbols() -> list[str]:
    """4. No references to the plugin API that was removed (Plan 006)."""
    return _substring_gate(PHANTOM_SYMBOLS, "symbol does not exist in captain_hook.py")


def check_exit_code_fiction() -> list[str]:
    """5. No "exit 2 or non-zero blocks" claim (Plan 003)."""
    return _substring_gate((EXIT_CODE_FICTION,), "non-2 exit codes do not block anywhere")


def check_contamination() -> list[str]:
    """6. No references to a different project (Plan 005)."""
    return _substring_gate(CONTAMINATION, "belongs to another project")


def check_amazon_q_schema() -> list[str]:
    """Amazon Q has no event/action model (Plan 008)."""
    return _substring_gate(INVENTED_AMAZON_Q_SCHEMA, "Amazon Q rules have no event or action fields")


def _substring_gate(needles: tuple[str, ...], why: str) -> list[str]:
    failures = []
    for path in text_files():
        if path.name == pathlib.Path(__file__).name:
            continue  # this file names the forbidden strings on purpose
        for lineno, line in enumerate(read(path).splitlines(), 1):
            for needle in needles:
                if needle in line:
                    failures.append(f"{rel(path)}:{lineno}: '{needle}' — {why}")
    return failures


# `$PATH` is the shell's search path, never a filename; four shipped examples
# passed it to prettier as the file to format. `npx` in a hook fetches an
# unpinned package from the registry on every miss — a network call and
# arbitrary code execution inside a hook, which is why the dispatcher resolves
# binaries directly (references/guards.md section 4).
HOOK_COMMAND_ANTIPATTERNS = (
    ('"$PATH"', "$PATH is the shell's search path, not the edited file"),
    ("npx ", "npx fetches an unpinned package from the network inside a hook"),
)


def check_hook_command_antipatterns() -> list[str]:
    """No shipped example wires a hook command that cannot work or fetches code."""
    failures = []
    for path in text_files():
        if path.name == pathlib.Path(__file__).name:
            continue  # this file names the forbidden strings on purpose
        for lineno, line in enumerate(read(path).splitlines(), 1):
            if '"command"' not in line and "command:" not in line:
                continue
            for needle, why in HOOK_COMMAND_ANTIPATTERNS:
                if needle in line:
                    failures.append(f"{rel(path)}:{lineno}: {needle!r} — {why}")
    return failures


PROVENANCE_RE = re.compile(
    r"^> Source: .*https?://\S+.* — (?:verified|checked) (\d{4}-\d{2}-\d{2})", re.M
)
# A vendor hook API drifting for six months without anyone re-reading it is the
# failure this gate exists for; a year is when the file should be assumed wrong.
PROVENANCE_WARN_DAYS = 180
PROVENANCE_FAIL_DAYS = 365
# A spec that deliberately claims nothing has nothing to go stale.
PROVENANCE_EXEMPT = {"continue.md"}


def check_spec_provenance() -> list[str]:
    """Every agent spec cites a source URL and a check date that is not ancient.

    Turns the provenance convention into a gate. Without it these files drift
    invisibly — Windsurf's docs already moved hosts once. The date is compared,
    not merely matched: every spec was written on the same day, so an
    existence-only check is satisfied forever and the freshness claim in
    README.md becomes decoration.
    """
    today = datetime.date.today()
    failures = []
    for path in sorted((SKILL_DIR / "references" / "specs").glob("*.md")):
        match = PROVENANCE_RE.search(read(path))
        if not match:
            failures.append(f"{rel(path)}: missing '> Source: <url> — verified <YYYY-MM-DD>' line")
            continue
        if path.name in PROVENANCE_EXEMPT:
            continue
        try:
            checked = datetime.date.fromisoformat(match.group(1))
        except ValueError:
            failures.append(f"{rel(path)}: provenance date {match.group(1)!r} is not a real date")
            continue
        age = (today - checked).days
        if age > PROVENANCE_FAIL_DAYS:
            failures.append(
                f"{rel(path)}: last verified {age} days ago ({checked}) — re-read the upstream "
                f"page and update the date, or mark the spec unverified. Do not bump the date "
                f"without re-reading it."
            )
        elif age > PROVENANCE_WARN_DAYS:
            print(f"      warning: {rel(path)} last verified {age} days ago ({checked})")
    return failures


# The five agents README promotes as able to block an action must each have a
# committed payload in their own shape, plus a case that runs it. Antigravity
# had neither, so nothing noticed that the dispatcher could not read a single
# one of its fields — the suite was green and one of the five advertised agents
# was guarded by nothing. A roster entry without evidence is a claim.
BLOCKING_AGENT_FIXTURES = {
    "claude": "Claude Code",
    "cursor": "Cursor",
    "windsurf": "Windsurf",
    "openhands": "OpenHands",
    "antigravity": "Antigravity",
}
PAYLOADS_DIR = EXAMPLES_DIR / "payloads"


def check_blocking_agent_fixtures() -> list[str]:
    """Every agent in the blocking roster has a fixture and a suite case."""
    names = [p.name for p in PAYLOADS_DIR.glob("*.json")]
    suite = read(SKILL_DIR / "scripts" / "verify_hooks.sh")
    failures = []
    for prefix, agent in sorted(BLOCKING_AGENT_FIXTURES.items()):
        matching = [n for n in names if n.startswith(prefix + "_")]
        if not matching:
            failures.append(
                f"examples/payloads/: no fixture for {agent} — every agent in the "
                f"blocking roster needs one in its own payload shape"
            )
            continue
        if not any(n in suite for n in matching):
            failures.append(
                f"examples/payloads/: {agent} has fixtures ({', '.join(sorted(matching))}) "
                f"but verify_hooks.sh runs none of them"
            )
    return failures


# The roster split — who can block, who is advisory — is the question this
# skill exists to answer, and the frontmatter description is what decides
# whether it activates at all. It named eight of ten agents while the body
# documented all ten, so the two least-guessable agents were also the two the
# skill would not surface for.
ROSTER_AGENTS = (
    "Claude Code", "Cursor", "Windsurf", "OpenHands", "Antigravity",
    "Aider", "Roo Code", "Copilot", "Amazon Q", "Continue",
)
DESCRIPTION_RE = re.compile(r"^description:\s*(.+)$", re.M)
DESCRIPTION_MAX = 1024


def check_skill_description() -> list[str]:
    """SKILL.md's description names every agent with a spec, and fits the cap."""
    text = read(SKILL_DIR / "SKILL.md")
    match = DESCRIPTION_RE.search(text)
    if not match:
        return ["skills/captain-hook/SKILL.md: no description in frontmatter"]
    description = match.group(1)
    failures = [
        f"skills/captain-hook/SKILL.md: description does not name {agent!r}"
        for agent in ROSTER_AGENTS
        if agent not in description
    ]
    if len(description) > DESCRIPTION_MAX:
        failures.append(
            f"skills/captain-hook/SKILL.md: description is {len(description)} chars, "
            f"over the {DESCRIPTION_MAX} cap some hosts enforce"
        )
    spec_count = len(list((SKILL_DIR / "references" / "specs").glob("*.md")))
    if spec_count != len(ROSTER_AGENTS):
        failures.append(
            f"references/specs/ holds {spec_count} specs but ROSTER_AGENTS lists "
            f"{len(ROSTER_AGENTS)} — add the new agent to the description and to this check"
        )
    return failures


# Aider silently ignores an unknown key, so a typo in the shipped template is
# invisible: the config loads, the setting never applies, nothing is logged.
# `auto-commit` for `auto-commits` shipped for exactly that reason. Line-based
# on purpose — this script is stdlib-only and there is no YAML parser.
KNOWN_AIDER_KEYS = {
    "auto-lint", "lint-cmd", "auto-test", "test-cmd", "auto-commits",
    "dirty-commits", "attribute-author", "attribute-committer", "model",
}
AIDER_KEY_RE = re.compile(r"^([a-z][a-z0-9-]*)\s*:", re.M)


def check_aider_template_keys() -> list[str]:
    """Every top-level key in the shipped Aider template is one Aider reads."""
    path = EXAMPLES_DIR / "aider_conf.yml"
    if not path.exists():
        return [f"{rel(path)}: missing"]
    failures = []
    for key in AIDER_KEY_RE.findall(read(path)):
        if key not in KNOWN_AIDER_KEYS:
            failures.append(
                f"{rel(path)}: '{key}' is not a key Aider reads — see "
                f"references/specs/aider.md section 3"
            )
    return failures


def check_ci_guide_matches_workflow() -> list[str]:
    """The CI guide claims to reproduce the workflow exactly; hold it to that."""
    workflow = REPO_ROOT / ".github" / "workflows" / "verify.yml"
    guide = SKILL_DIR / "references" / "ci_cd_integration.md"
    if not workflow.exists():
        return []
    blocks = [b.strip() for b in re.findall(r"```yaml\n(.*?)```", read(guide), re.S)]
    if read(workflow).strip() not in blocks:
        return [f"{rel(guide)}: the YAML block no longer matches {rel(workflow)}"]
    return []


def check_heading_sequence() -> list[str]:
    """SKILL.md's numbered sections are 1..N with no gaps or duplicates.

    A duplicate `## 6` survived several documentation commits and broke
    in-page anchors; four lines of lint stop it recurring.
    """
    text = read(SKILL_DIR / "SKILL.md")
    nums = [int(m) for m in re.findall(r"^## (\d+)\.", text, re.M)]
    if nums != list(range(1, len(nums) + 1)):
        return [f"skills/captain-hook/SKILL.md: heading numbers are {nums}, expected 1..{len(nums)}"]
    return []


def check_relative_links() -> list[str]:
    """7. Every relative markdown link resolves to a file that exists."""
    failures = []
    for path in markdown_files():
        for target in MD_LINK_RE.findall(read(path)):
            target = target.strip()
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            if "://" in target:
                continue
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                failures.append(f"{rel(path)}: broken link -> {target}")
    return failures


def check_python_blocks() -> list[str]:
    """8. Every fenced python block compiles."""
    failures = []
    for path in markdown_files():
        for i, block in enumerate(PYTHON_BLOCK_RE.findall(read(path))):
            if PY_FRAGMENT_MARKER in block or block.split("\n")[0].strip().endswith(PLACEHOLDER):
                continue
            try:
                compile(block, f"{path.name}:block{i}", "exec")
            except SyntaxError as exc:
                failures.append(f"{rel(path)} python block {i}: {exc}")
    return failures


CHECKS = [
    ("Fenced JSON blocks parse", check_json_blocks),
    ("Example configs parse", check_example_json),
    ("Claude Code schema is the nested matcher form", check_flat_claude_schema),
    ("No phantom plugin-API symbols", check_phantom_symbols),
    ("No 'or non-zero blocks' exit-code claim", check_exit_code_fiction),
    ("No cross-project contamination", check_contamination),
    ("No invented Amazon Q blocking schema", check_amazon_q_schema),
    ("Agent specs cite a verified source", check_spec_provenance),
    ("SKILL.md heading numbers are contiguous", check_heading_sequence),
    ("Relative markdown links resolve", check_relative_links),
    ("Fenced Python blocks compile", check_python_blocks),
    ("Hook commands avoid $PATH and npx", check_hook_command_antipatterns),
    ("CI guide reproduces the workflow", check_ci_guide_matches_workflow),
    ("Aider template keys are real", check_aider_template_keys),
    ("SKILL.md description names every agent", check_skill_description),
    ("Every blocking agent has a payload fixture", check_blocking_agent_fixtures),
]


def main() -> int:
    # The ✓/❌ markers below need a UTF-8 stdout; CI containers default to C.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    passed = 0
    failed = 0
    for name, check in CHECKS:
        failures = check()
        if failures:
            failed += 1
            print(f"  Checking [{name}] ... ❌ FAILED ({len(failures)})")
            for failure in failures:
                print(f"      {failure}")
        else:
            passed += 1
            print(f"  Checking [{name}] ... ✓ PASSED")

    print("")
    print(f"Documentation Summary: {passed} Passed, {failed} Failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
