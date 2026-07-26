#!/usr/bin/env python3
"""Documentation and template consistency checks for the captain-hook skill.

This repository's product is documentation, so the checks here cover the failure
modes the behavioral suite cannot see: config templates that do not parse, docs
that teach an invalid schema, and references to symbols or projects that do not
exist. Every check is a permanent gate introduced by one of the repair plans.

Stdlib only, by design — a hook-adjacent script must run with no install step.
"""

from __future__ import annotations

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
    r"^> Source: .*https?://\S+.* — (?:verified|checked) \d{4}-\d{2}-\d{2}", re.M
)


def check_spec_provenance() -> list[str]:
    """Every agent spec cites a source URL and the date it was checked.

    Turns the provenance convention into a gate. Without it these files drift
    invisibly — Windsurf's docs already moved hosts once.
    """
    failures = []
    for path in sorted((SKILL_DIR / "references" / "specs").glob("*.md")):
        if not PROVENANCE_RE.search(read(path)):
            failures.append(f"{rel(path)}: missing '> Source: <url> — verified <YYYY-MM-DD>' line")
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
