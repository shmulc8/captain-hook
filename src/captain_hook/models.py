"""Data models for events, payloads, and policy results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


class CanonicalEvent:
    PRE_PROMPT = "PrePrompt"
    PRE_WRITE = "PreWrite"
    POST_WRITE = "PostWrite"
    PRE_COMMAND = "PreCommand"
    POST_COMMAND = "PostCommand"
    PRE_MCP = "PreMCP"
    POST_MCP = "PostMCP"
    SESSION_END = "SessionEnd"


@dataclass
class HookPayload:
    prompt: str = ""
    path: str = ""
    command: str = ""
    tool: str = ""
    server: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""


@dataclass
class PolicyResult:
    allowed: bool = True
    exit_code: int = 0
    message: str = ""
