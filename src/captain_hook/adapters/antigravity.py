"""Modular Antigravity (AGY) Agent Adapter."""

from __future__ import annotations

from .base import BaseAgentAdapter


class AntigravityAdapter(BaseAgentAdapter):
    name = "antigravity"
    config_relpath = "hooks/prevent.py"

    def generate_config_content(self) -> str:
        return """#!/usr/bin/env python3
import sys
from captain_hook import Engine

if __name__ == "__main__":
    engine = Engine()
    sys.exit(engine.dispatch_from_stdin("PreWrite"))
"""
