"""Modular Cursor AI Agent Adapter."""

from __future__ import annotations

from .base import BaseAgentAdapter


class CursorAdapter(BaseAgentAdapter):
    name = "cursor"
    config_relpath = ".cursor/hooks.json"

    def generate_config_content(self) -> dict:
        return {
            "version": 1,
            "hooks": {
                "beforeSubmitPrompt": [{"command": "captain-hook dispatch PrePrompt"}],
                "beforeShellExecution": [{"command": "captain-hook dispatch PreCommand"}],
                "beforeMCPExecution": [{"command": "captain-hook dispatch PreMCP"}],
                "beforeReadFile": [{"command": "captain-hook dispatch PreWrite"}],
                "afterFileEdit": [{"command": "captain-hook dispatch PostWrite"}],
                "stop": [{"command": "captain-hook dispatch SessionEnd"}],
            },
        }
