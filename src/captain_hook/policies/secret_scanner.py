"""Modular Secret Scanner Policy."""

from __future__ import annotations

import re
from typing import List, Tuple

from ..models import CanonicalEvent, HookPayload, PolicyResult
from .base import BasePolicy

SECRET_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS Access Key"),
    (re.compile(r"(?i)ghp_[0-9a-zA-Z]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"(?i)gho_[0-9a-zA-Z]{36}"), "GitHub OAuth Access Token"),
    (re.compile(r"(?i)glpat-[0-9a-zA-Z\-]{20}"), "GitLab Personal Access Token"),
    (re.compile(r"-----BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY-----"), "Private Key"),
    (re.compile(r"(?i)sk-[a-zA-Z0-9]{48}"), "OpenAI API Key"),
    (re.compile(r"(?i)sk-ant-[a-zA-Z0-9\-]{40,}"), "Anthropic API Key"),
]


class SecretScannerPolicy(BasePolicy):
    name = "secret_scanner"
    events_handled = [
        CanonicalEvent.PRE_PROMPT,
        CanonicalEvent.PRE_COMMAND,
        CanonicalEvent.PRE_WRITE,
        CanonicalEvent.PRE_MCP,
    ]

    def evaluate(self, event: str, payload: HookPayload) -> PolicyResult:
        targets = [payload.prompt, payload.command, payload.raw]
        for t in targets:
            if not t:
                continue
            for pattern, label in SECRET_PATTERNS:
                if pattern.search(t):
                    return PolicyResult(
                        allowed=False,
                        exit_code=2,
                        message=f"Blocked: Secret key pattern detected ({label})",
                    )
        return PolicyResult(allowed=True, exit_code=0)
