"""Modular Symlink Guard Policy."""

from __future__ import annotations

import os

from ..models import CanonicalEvent, HookPayload, PolicyResult
from .base import BasePolicy


class SymlinkGuardPolicy(BasePolicy):
    name = "symlink_guard"
    events_handled = [CanonicalEvent.PRE_WRITE]

    def evaluate(self, event: str, payload: HookPayload) -> PolicyResult:
        path = payload.path
        if path and os.path.exists(path) and os.path.islink(path):
            return PolicyResult(
                allowed=False,
                exit_code=2,
                message=f"Blocked: Target file '{path}' is a symlink pointing outside repository boundaries",
            )
        return PolicyResult(allowed=True, exit_code=0)
