#!/usr/bin/env python3
"""Regenerate the secret-pattern catalog in the docs from captain_hook.py.

`SECRET_PATTERNS` in `captain_hook.py` is the single source of truth. It stays a
plain literal — the dispatcher is a hook script, and adding a runtime file read
or a shared import to its hot path buys nothing and adds a failure mode. Instead
the three documentation copies are *generated* from it, so drift is a check
rather than a discipline.

Run with no arguments to rewrite the docs; run with --check to fail on drift.
Stdlib only.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from captain_hook import SECRET_PATTERNS  # noqa: E402

HTML_MARKERS = ("<!-- BEGIN:SECRET_PATTERNS -->", "<!-- END:SECRET_PATTERNS -->")
PYTHON_MARKERS = ("    # BEGIN:SECRET_PATTERNS", "    # END:SECRET_PATTERNS")


def render_bullets(bullet: str) -> str:
    return "\n".join(f"{bullet} **{label}**: `{pattern.pattern}`" for pattern, label in SECRET_PATTERNS)


def render_python_literal() -> str:
    return "\n".join(
        f'    (re.compile(r"{pattern.pattern}"), "{label}"),' for pattern, label in SECRET_PATTERNS
    )


TARGETS = [
    (SKILL_DIR / "references/guards.md", HTML_MARKERS, lambda: render_bullets("*")),
    (SKILL_DIR / "references/security_rules.md", HTML_MARKERS, lambda: render_bullets("-")),
    (SKILL_DIR / "references/recipes.md", PYTHON_MARKERS, render_python_literal),
]


def splice(text: str, markers: tuple[str, str], body: str, path: pathlib.Path) -> str:
    begin, end = markers
    try:
        head, rest = text.split(begin, 1)
        _, tail = rest.split(end, 1)
    except ValueError:
        raise SystemExit(f"{path}: missing marker pair {begin!r} / {end!r}")
    return f"{head}{begin}\n{body}\n{end}{tail}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift and exit 1 without writing",
    )
    args = parser.parse_args()

    drifted = []
    for path, markers, render in TARGETS:
        current = path.read_text()
        updated = splice(current, markers, render(), path)
        if current == updated:
            continue
        if args.check:
            drifted.append(path)
        else:
            path.write_text(updated)
            print(f"  regenerated {path.relative_to(SKILL_DIR.parent.parent)}")

    if args.check:
        if drifted:
            print(f"  Checking [Secret-pattern catalog in sync] ... ❌ FAILED ({len(drifted)})")
            for path in drifted:
                print(f"      {path.relative_to(SKILL_DIR.parent.parent)} is out of date — run sync_patterns.py")
            return 1
        print("  Checking [Secret-pattern catalog in sync] ... ✓ PASSED")
        return 0

    print(f"  {len(SECRET_PATTERNS)} patterns synced to {len(TARGETS)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
