#!/usr/bin/env python3
"""captain-hook standalone dispatcher and policy script."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

VERSION = "1.0.0"

# --- Security Guards & Patterns ---

SECRET_PATTERNS = [
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS Access Key"),
    (re.compile(r"(?i)ghp_[0-9a-zA-Z]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"(?i)gho_[0-9a-zA-Z]{36}"), "GitHub OAuth Access Token"),
    (re.compile(r"(?i)glpat-[0-9a-zA-Z\-]{20}"), "GitLab Personal Access Token"),
    (re.compile(r"-----BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY-----"), "Private Key"),
    (re.compile(r"(?i)\bsk-(?!ant-)(proj-|svcacct-|admin-)?[a-zA-Z0-9_]{20,}[a-zA-Z0-9_\-]{12,}"), "OpenAI API Key"),
    (re.compile(r"(?i)sk-ant-[a-zA-Z0-9\-]{40,}"), "Anthropic API Key"),
]

BLOCKED_COMMANDS = [
    re.compile(r"\brm\s+-[rRf]{1,2}\s+[/~*]"),
    re.compile(r"\b(mkfs|dd\s+if=)\b"),
    re.compile(r"\bgit\s+push\s+.*--force\b"),
    re.compile(r"\bchmod\s+-R\s+777\b"),
    re.compile(r"\bchown\s+-R\s+root\b"),
]


def extract_fields(payload: dict) -> tuple[str, str, str, str, str, dict]:
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    # Windsurf/Cascade nests every per-event field under tool_info.
    tool_info = payload.get("tool_info") if isinstance(payload.get("tool_info"), dict) else {}

    prompt = (
        payload.get("prompt")
        or payload.get("user_prompt")
        or tool_info.get("user_prompt")
        or payload.get("raw")
        or ""
    )
    path = (
        payload.get("path")
        or payload.get("filepath")
        or payload.get("file_path")
        or payload.get("file")
        or tool_input.get("file_path")
        or tool_input.get("path")
        or tool_info.get("file_path")
        or ""
    )
    command = (
        payload.get("command")
        # Flat spelling from third-party templates. Not documented by any spec
        # verified so far, but five specs are still unverified (Plan 009), so
        # this stays as a defensive fallback rather than being deleted.
        or payload.get("command_string")
        or payload.get("cmd")
        or tool_input.get("command")
        or tool_info.get("command_line")
        or ""
    )
    tool = (
        payload.get("tool")
        or payload.get("tool_name")
        or tool_info.get("mcp_tool_name")
        or payload.get("agent_action_name")
        or ""
    )
    server = (
        payload.get("server")
        or payload.get("mcp_server_name")
        or tool_info.get("mcp_server_name")
        or ""
    )
    args = payload.get("args") or payload.get("arguments") or tool_input or tool_info or {}

    return prompt, path, command, tool, server, args


def _repo_root(start: str | None = None) -> str:
    """Nearest ancestor directory containing a .git entry, else the cwd.

    Walks up rather than shelling out to git: this runs on every hook
    invocation and must not spawn a subprocess.
    """
    current = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.abspath(start or os.getcwd())
        current = parent


def escapes_repo(path: str, root: str | None = None) -> tuple[bool, str]:
    """Does `path` resolve outside the repository root?

    Resolves symlinks in every path component, including parent directories
    and including paths that do not exist yet, so a write to a new file
    through a symlinked directory is caught.

    Returns (escapes, resolved_path).
    """
    root = os.path.realpath(root or _repo_root())
    resolved = os.path.realpath(os.path.abspath(path))
    if resolved == root:
        return False, resolved
    return not resolved.startswith(root + os.sep), resolved


def dispatch_event(event_name: str, stdin_data: str) -> int:
    payload = {}
    if stdin_data.strip():
        try:
            payload = json.loads(stdin_data)
        except json.JSONDecodeError:
            payload = {"raw": stdin_data}

    prompt, path, command, tool, server, args = extract_fields(payload)

    # 1. Secret Scanning
    for target in [prompt, command, stdin_data]:
        if not target:
            continue
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(target):
                sys.stderr.write(f"captain-hook: Blocked: Secret key pattern detected ({label})\n")
                return 2

    # 2. Command Sandboxing
    if command:
        for pattern in BLOCKED_COMMANDS:
            if pattern.search(command):
                sys.stderr.write(f"captain-hook: Blocked: Dangerous shell command pattern matched ({pattern.pattern})\n")
                return 2

    # 3. Symlink / Path-Escape Guard
    if path:
        escapes, resolved = escapes_repo(path)
        if escapes:
            sys.stderr.write(
                f"captain-hook: Blocked: '{path}' resolves to '{resolved}', "
                f"outside the repository root\n"
            )
            return 2

    # 4. Post-Write Auto Formatting
    if event_name in ("PostWrite", "afterFileEdit", "post_write_code", "PostToolUse") and path and os.path.exists(path):
        if path.endswith((".js", ".ts", ".jsx", ".tsx", ".json")) and shutil.which("npx"):
            subprocess.run(["npx", "prettier", "--write", path], capture_output=True)
        elif path.endswith(".py") and shutil.which("ruff"):
            subprocess.run(["ruff", "format", path], capture_output=True)

    return 0


def main():
    parser = argparse.ArgumentParser(description="captain-hook standalone dispatcher.")
    subparsers = parser.add_subparsers(dest="subcommand")

    dispatch_parser = subparsers.add_parser("dispatch", help="Dispatch a hook event.")
    dispatch_parser.add_argument("event", help="Canonical or agent event name")

    args = parser.parse_args()

    if args.subcommand == "dispatch":
        stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
        sys.exit(dispatch_event(args.event, stdin_data))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
