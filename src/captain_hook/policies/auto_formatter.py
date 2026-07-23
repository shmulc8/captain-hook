"""Modular Auto-Formatter Policy."""

from __future__ import annotations

import os
import shutil
import subprocess

from ..models import CanonicalEvent, HookPayload, PolicyResult
from .base import BasePolicy


class AutoFormatterPolicy(BasePolicy):
    name = "auto_formatter"
    events_handled = [CanonicalEvent.POST_WRITE]

    def evaluate(self, event: str, payload: HookPayload) -> PolicyResult:
        path = payload.path
        if path and os.path.exists(path):
            if path.endswith((".js", ".ts", ".jsx", ".tsx", ".json")) and shutil.which("npx"):
                subprocess.run(["npx", "prettier", "--write", path], capture_output=True)
            elif path.endswith(".py") and shutil.which("ruff"):
                subprocess.run(["ruff", "format", path], capture_output=True)
        return PolicyResult(allowed=True, exit_code=0)
