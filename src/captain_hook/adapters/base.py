"""Base Agent Adapter Interface for captain-hook."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAgentAdapter(ABC):
    """Abstract base class for all AI agent hook configuration generators.
    
    To support a new AI agent:
    1. Subclass BaseAgentAdapter
    2. Define name and config_relpath
    3. Implement generate_config_content()
    """

    name: str = "base"
    config_relpath: str = ""

    @abstractmethod
    def generate_config_content(self) -> dict | str:
        """Return the dictionary (for JSON) or string content (for YAML/script) for the agent config."""
        pass
