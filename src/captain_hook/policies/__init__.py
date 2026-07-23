"""Built-in Policy Exports for captain-hook."""

from .auto_formatter import AutoFormatterPolicy
from .base import BasePolicy
from .command_sandbox import CommandSandboxPolicy
from .secret_scanner import SecretScannerPolicy
from .symlink_guard import SymlinkGuardPolicy

BUILTIN_POLICIES = [
    SecretScannerPolicy(),
    CommandSandboxPolicy(),
    SymlinkGuardPolicy(),
    AutoFormatterPolicy(),
]

__all__ = [
    "BasePolicy",
    "SecretScannerPolicy",
    "CommandSandboxPolicy",
    "SymlinkGuardPolicy",
    "AutoFormatterPolicy",
    "BUILTIN_POLICIES",
]
