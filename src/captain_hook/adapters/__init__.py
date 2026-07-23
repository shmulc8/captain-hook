"""Agent Adapter Exports for captain-hook."""

from .aider import AiderAdapter
from .antigravity import AntigravityAdapter
from .base import BaseAgentAdapter
from .claude import ClaudeAdapter
from .cursor import CursorAdapter
from .windsurf import WindsurfAdapter

BUILTIN_ADAPTERS = [
    CursorAdapter(),
    WindsurfAdapter(),
    ClaudeAdapter(),
    AiderAdapter(),
    AntigravityAdapter(),
]

__all__ = [
    "BaseAgentAdapter",
    "CursorAdapter",
    "WindsurfAdapter",
    "ClaudeAdapter",
    "AiderAdapter",
    "AntigravityAdapter",
    "BUILTIN_ADAPTERS",
]
