"""Modular Windsurf Cascade Agent Adapter."""

from __future__ import annotations

from .base import BaseAgentAdapter


class WindsurfAdapter(BaseAgentAdapter):
    name = "windsurf"
    config_relpath = ".windsurf/hooks.json"

    def generate_config_content(self) -> dict:
        return {
            "hooks": {
                "pre_user_prompt": [{"command": "captain-hook dispatch PrePrompt", "show_output": False}],
                "pre_write_code": [{"command": "captain-hook dispatch PreWrite"}],
                "post_write_code": [{"command": "captain-hook dispatch PostWrite"}],
                "pre_run_command": [{"command": "captain-hook dispatch PreCommand"}],
                "post_run_command": [{"command": "captain-hook dispatch PostCommand"}],
                "pre_mcp_tool_use": [{"command": "captain-hook dispatch PreMCP"}],
                "post_mcp_tool_use": [{"command": "captain-hook dispatch PostMCP"}],
            }
        }
