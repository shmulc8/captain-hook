#!/usr/bin/env python3
"""Example write-time prevention hook that relays to the bundled dispatcher script.

The dispatcher is a standalone script, not an installed package, so this
example loads it by path relative to this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

_DISPATCHER = Path(__file__).resolve().parent.parent / "scripts" / "captain_hook.py"
sys.path.insert(0, str(_DISPATCHER.parent))

from captain_hook import dispatch_event  # noqa: E402

if __name__ == "__main__":
    sys.exit(dispatch_event("PreWrite", sys.stdin.read() if not sys.stdin.isatty() else ""))
