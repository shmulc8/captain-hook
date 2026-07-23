#!/usr/bin/env python3
"""Example Antigravity (AGY) write-time prevention hook integrated with captain-hook."""
from __future__ import annotations

import sys
from captain_hook import dispatch_event

if __name__ == "__main__":
    # Relay to captain-hook dispatcher
    sys.exit(dispatch_event("PreWrite", ""))
