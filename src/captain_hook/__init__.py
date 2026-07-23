"""captain-hook: Universal AI Agent Hooks Dispatcher & Policy Engine."""

from .engine import Engine
from .models import CanonicalEvent, HookPayload, PolicyResult

__version__ = "1.0.0"
__all__ = ["Engine", "CanonicalEvent", "HookPayload", "PolicyResult"]
