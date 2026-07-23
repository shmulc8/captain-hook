"""Modular Claude Code Agent Adapter."""

from __future__ import annotations

from .base import BaseAgentAdapter


class ClaudeAdapter(BaseAgentAdapter):
    name = "claude"
    config_relpath = ".claude/settings.json"

    def generate_config_content(self) -> dict:
        return {
            "hooks": {
                "UserPromptSubmit": [{"command": "captain-hook dispatch PrePrompt"}],
                "PreToolUse": [{"command": "captain-hook dispatch PreToolUse"}],
                "PostToolUse": [{"command": "captain-hook dispatch PostToolUse"}],
                "Stop": [{"command": "captain-hook dispatch SessionEnd"}],
            }
        }
