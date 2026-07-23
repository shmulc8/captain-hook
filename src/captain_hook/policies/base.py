"""Base Policy Interface for captain-hook modular security policies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import HookPayload, PolicyResult


class BasePolicy(ABC):
    """Abstract base class for all captain-hook policies.
    
    To create a custom policy plugin:
    1. Subclass BasePolicy
    2. Define name and list of handled canonical events
    3. Implement evaluate() returning PolicyResult
    """

    name: str = "base-policy"
    events_handled: List[str] = []

    @abstractmethod
    def evaluate(self, event: str, payload: HookPayload) -> PolicyResult:
        """Evaluate event & payload against policy rules."""
        pass
