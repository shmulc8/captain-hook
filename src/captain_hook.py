#!/usr/bin/env python3
"""captain-hook CLI & Universal Lifecycle Hook Dispatcher for AI Coding Agents.

Supports Claude Code, Cursor, Windsurf, Aider, Antigravity, Continue CLI, Roo Code, and more.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

VERSION = "1.0.0"

# --- Built-in Security & Safety Guards ---

SECRET_PATTERNS = [
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS Access Key"),
    (re.compile(r"(?i)ghp_[0-9a-zA-Z]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"(?i)gho_[0-9a-zA-Z]{36}"), "GitHub OAuth Access Token"),
    (re.compile(r"(?i)glpat-[0-9a-zA-Z\-]{20}"), "GitLab Personal Access Token"),
    (re.compile(r"-----BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY-----"), "Private Key"),
    (re.compile(r"(?i)sk-[a-zA-Z0-9]{48}"), "OpenAI API Key"),
    (re.compile(r"(?i)sk-ant-[a-zA-Z0-9\-]{40,}"), "Anthropic API Key"),
]

BLOCKED_COMMANDS = [
    re.compile(r"\brm\s+-[rRf]{1,2}\s+[/~*]"),
    re.compile(r"\b(mkfs|dd\s+if=)\b"),
    re.compile(r"\bgit\s+push\s+.*--force\b"),
    re.compile(r"\bchmod\s+-R\s+777\b"),
    re.compile(r"\bchown\s+-R\s+root\b"),
]

def guard_secrets(text: str) -> str | None:
    for pattern, name in SECRET_PATTERNS:
        if pattern.search(text):
            return f"Blocked: Secret key pattern detected ({name})"
    return None

def guard_commands(cmd: str) -> str | None:
    for pattern in BLOCKED_COMMANDS:
        if pattern.search(cmd):
            return f"Blocked: Dangerous shell command pattern matched ({pattern.pattern})"
    return None

def guard_symlinks(path: str) -> str | None:
    if os.path.exists(path) and os.path.islink(path):
        return f"Blocked: Target file '{path}' is a symlink pointing outside repository boundaries"
    return None

# --- Core Dispatcher Logic ---

def dispatch_event(event_name: str, stdin_data: str) -> int:
    payload = {}
    if stdin_data.strip():
        try:
            payload = json.loads(stdin_data)
        except json.JSONDecodeError:
            payload = {"raw": stdin_data}

    # Extract common fields across agent payloads
    prompt = payload.get("prompt") or payload.get("raw") or ""
    path = payload.get("path") or payload.get("filepath") or payload.get("file") or ""
    command = payload.get("command") or payload.get("cmd") or ""

    # 1. PrePrompt Check
    if event_name in ("PrePrompt", "beforeSubmitPrompt", "pre_user_prompt", "UserPromptSubmit"):
        err = guard_secrets(prompt)
        if err:
            sys.stderr.write(f"captain-hook: {err}\n")
            return 2

    # 2. PreCommand Check
    if event_name in ("PreCommand", "beforeShellExecution", "pre_run_command", "PreToolUse"):
        err = guard_commands(command) or guard_secrets(command)
        if err:
            sys.stderr.write(f"captain-hook: {err}\n")
            return 2

    # 3. PreWrite Check
    if event_name in ("PreWrite", "beforeReadFile", "pre_write_code"):
        if path:
            err = guard_symlinks(path)
            if err:
                sys.stderr.write(f"captain-hook: {err}\n")
                return 2

    # 4. PostWrite Hook (Auto-formatter)
    if event_name in ("PostWrite", "afterFileEdit", "post_write_code", "PostToolUse"):
        if path and os.path.exists(path):
            if path.endswith((".js", ".ts", ".jsx", ".tsx", ".json")) and shutil.which("npx"):
                subprocess.run(["npx", "prettier", "--write", path], capture_output=True)
            elif path.endswith(".py") and shutil.which("ruff"):
                subprocess.run(["ruff", "format", path], capture_output=True)

    return 0

# --- Generator / Init Logic ---

def init_agent_configs(target_agent: str, root_dir: str):
    print(f"captain-hook v{VERSION}: Initializing agent hook configurations in {root_dir}")

    # Cursor
    if target_agent in ("cursor", "all"):
        cursor_dir = os.path.join(root_dir, ".cursor")
        os.makedirs(cursor_dir, exist_ok=True)
        cfg = {
            "version": 1,
            "hooks": {
                "beforeSubmitPrompt": [{"command": "captain-hook dispatch PrePrompt"}],
                "beforeShellExecution": [{"command": "captain-hook dispatch PreCommand"}],
                "beforeMCPExecution": [{"command": "captain-hook dispatch PreMCP"}],
                "beforeReadFile": [{"command": "captain-hook dispatch PreWrite"}],
                "afterFileEdit": [{"command": "captain-hook dispatch PostWrite"}],
                "stop": [{"command": "captain-hook dispatch SessionEnd"}]
            }
        }
        with open(os.path.join(cursor_dir, "hooks.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print("  ✓ Created .cursor/hooks.json (Cursor AI)")

    # Windsurf
    if target_agent in ("windsurf", "all"):
        windsurf_dir = os.path.join(root_dir, ".windsurf")
        os.makedirs(windsurf_dir, exist_ok=True)
        cfg = {
            "hooks": {
                "pre_user_prompt": [{"command": "captain-hook dispatch PrePrompt", "show_output": False}],
                "pre_write_code": [{"command": "captain-hook dispatch PreWrite"}],
                "post_write_code": [{"command": "captain-hook dispatch PostWrite"}],
                "pre_run_command": [{"command": "captain-hook dispatch PreCommand"}],
                "post_run_command": [{"command": "captain-hook dispatch PostCommand"}],
                "pre_mcp_tool_use": [{"command": "captain-hook dispatch PreMCP"}],
                "post_mcp_tool_use": [{"command": "captain-hook dispatch PostMCP"}]
            }
        }
        with open(os.path.join(windsurf_dir, "hooks.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print("  ✓ Created .windsurf/hooks.json (Windsurf Cascade)")

    # Claude Code
    if target_agent in ("claude", "all"):
        claude_dir = os.path.join(root_dir, ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        cfg = {
            "hooks": {
                "UserPromptSubmit": [{"command": "captain-hook dispatch PrePrompt"}],
                "PreToolUse": [{"command": "captain-hook dispatch PreToolUse"}],
                "PostToolUse": [{"command": "captain-hook dispatch PostToolUse"}],
                "Stop": [{"command": "captain-hook dispatch SessionEnd"}]
            }
        }
        with open(os.path.join(claude_dir, "settings.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print("  ✓ Created .claude/settings.json (Claude Code)")

    # Aider
    if target_agent in ("aider", "all"):
        cfg_path = os.path.join(root_dir, ".aider.conf.yml")
        content = """# .aider.conf.yml generated by captain-hook
auto-lint: true
lint-cmd: "captain-hook dispatch PostWrite"
auto-test: true
test-cmd: "python3 -m unittest discover tests"
"""
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  ✓ Created .aider.conf.yml (Aider AI)")

    # Antigravity (AGY)
    if target_agent in ("antigravity", "all"):
        hooks_dir = os.path.join(root_dir, "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        prevent_script = """#!/usr/bin/env python3
import sys
from captain_hook import dispatch_event
sys.exit(dispatch_event("PreWrite", ""))
"""
        p_path = os.path.join(hooks_dir, "prevent.py")
        with open(p_path, "w", encoding="utf-8") as f:
            f.write(prevent_script)
        os.chmod(p_path, 0o755)
        print("  ✓ Created hooks/prevent.py (Antigravity AGY)")

    print("\nInitialization complete! Captain Hook is ready to protect your project.")

# --- CLI Main ---

def main():
    parser = argparse.ArgumentParser(
        description="captain-hook: Universal lifecycle hooks dispatcher for AI coding agents."
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize agent hook configurations.")
    init_parser.add_argument(
        "--agent",
        choices=["all", "cursor", "windsurf", "claude", "aider", "antigravity"],
        default="all",
        help="Target coding agent to generate hooks for (default: all)"
    )

    # dispatch
    dispatch_parser = subparsers.add_parser("dispatch", help="Dispatch a hook event.")
    dispatch_parser.add_argument("event", help="Canonical or agent event name")

    args = parser.parse_args()

    if args.subcommand == "init":
        init_agent_configs(args.agent, os.getcwd())
        sys.exit(0)
    elif args.subcommand == "dispatch":
        stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
        code = dispatch_event(args.event, stdin_data)
        sys.exit(code)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
