"""Modular Command Sandbox Policy."""

from __future__ import annotations

import re
from typing import List

from ..models import CanonicalEvent, HookPayload, PolicyResult
from .base import BasePolicy

BLOCKED_COMMANDS: List[re.Pattern] = [
    re.compile(r"\brm\s+-[rRf]{1,2}\s+[/~*]"),
    re.compile(r"\b(mkfs|dd\s+if=)\b"),
    re.compile(r"\bgit\s+push\s+.*--force\b"),
    re.compile(r"\bchmod\s+-R\s+777\b"),
    re.compile(r"\bchown\s+-R\s+root\b"),
]


class CommandSandboxPolicy(BasePolicy):
    name = "command_sandbox"
    events_handled = [CanonicalEvent.PRE_COMMAND]

    def evaluate(self, event: str, payload: HookPayload) -> PolicyResult:
        cmd = payload.command
        if not cmd:
            return PolicyResult(allowed=True, exit_code=0)

        for pattern in BLOCKED_COMMANDS:
            if pattern.search(cmd):
                return PolicyResult(
                    allowed=False,
                    exit_code=2,
                    message=f"Blocked: Dangerous shell command pattern matched ({pattern.pattern})",
                )
        return PolicyResult(allowed=True, exit_code=0)
