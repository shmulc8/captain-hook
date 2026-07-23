"""Modular Claude Code Agent Adapter."""

from __future__ import annotations

from .base import BaseAgentAdapter


class ClaudeAdapter(BaseAgentAdapter):
    name = "claude"
    config_relpath = ".claude/settings.json"

    def generate_config_content(self) -> dict:
        return {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "hooks": [
                            {"type": "command", "command": "captain-hook dispatch PrePrompt"}
                        ]
                    }
                ],
                "PreToolUse": [
                    {
                        "matcher": "Bash|Edit|Write",
                        "hooks": [
                            {"type": "command", "command": "captain-hook dispatch PreToolUse"}
                        ]
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "Edit|Write",
                        "hooks": [
                            {"type": "command", "command": "captain-hook dispatch PostToolUse"}
                        ]
                    }
                ]
            }
        }
