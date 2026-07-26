#!/usr/bin/env python3
"""captain-hook standalone dispatcher and policy script."""

from __future__ import annotations

import argparse
import fnmatch
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

# A regex denylist over a command string — NOT a sandbox. It does not parse
# shell syntax, so variable expansion, command substitution, and relative
# targets get through by design. It stops the accident, not an adversary; the
# upgrade path is a container or restricted shell, not more regexes. Read the
# "Known limits" table in references/guards.md before adding a pattern here.
BLOCKED_COMMANDS = [
    # rm with recursive+force in any flag arrangement, targeting a root-ish path.
    (re.compile(r"\brm\s+(-\w+\s+)*-\w*[rR]\w*\s+(-\w+\s+)*-\w*f\w*\s+['\"]?[/~*]"),
     "recursive force delete of a root path"),
    (re.compile(r"\brm\s+(-\w+\s+)*-\w*[rRf]{2}\w*\s+['\"]?[/~*]"),
     "recursive force delete of a root path"),
    (re.compile(r"\b(mkfs|dd\s+if=)\b"), "raw disk write or filesystem format"),
    # --force-with-lease is the safe form; blocking it pushes people to --force.
    (re.compile(r"\bgit\s+push\s+.*--force(?!-with-lease)\b"), "force push"),
    (re.compile(r"\bchmod\s+-R\s+777\b"), "recursive world-writable permissions"),
    (re.compile(r"\bchown\s+-R\s+root\b"), "recursive ownership change to root"),
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


# Every event that fires AFTER the action it describes. Returning 2 at any of
# these produces a "Blocked" message for something that was not blocked.
POST_EVENTS = frozenset({
    # canonical
    "PostWrite", "PostCommand", "PostMCP", "SessionEnd",
    # Cursor
    "afterFileEdit", "stop",
    # Windsurf
    "post_read_code", "post_write_code", "post_run_command", "post_mcp_tool_use",
    "post_cascade_response", "post_cascade_response_with_transcript", "post_setup_worktree",
    # Claude Code — verified: exit 2 does not block on any of these
    "PostToolUse", "SessionStart", "Notification",
    # Antigravity
    "PostInvocation",
})

# The subset the auto-formatter keys off. Must stay a subset of POST_EVENTS.
POST_WRITE_EVENTS = frozenset({
    "PostWrite", "afterFileEdit", "post_write_code", "PostToolUse",
})

# Events that CAN still prevent the action. Kept as documentation of what was
# verified upstream; the runtime check below is the complement of POST_EVENTS
# so that an unrecognized event gets guards rather than silently skipping them.
BLOCKING_EVENTS = frozenset({
    "PrePrompt", "PreWrite", "PreCommand", "PreMCP",
    "beforeSubmitPrompt", "beforeShellExecution", "beforeMCPExecution", "beforeReadFile",
    "pre_user_prompt", "pre_read_code", "pre_write_code", "pre_run_command", "pre_mcp_tool_use",
    "UserPromptSubmit", "PreToolUse", "Stop", "SubagentStop", "PreCompact",
    "PreInvocation",
})


def _is_blocking(event_name: str) -> bool:
    """Unknown events are treated as blocking — fail safe, not silent."""
    return event_name not in POST_EVENTS


CONFIG_FILENAME = ".captain-hook.json"

# Config shape (every key optional):
# {
#   "ignore_paths":    ["glob", ...],   # skip all guards for matching paths
#   "allow_secrets_in":["glob", ...],   # skip only the secret scan for these
#   "allow_commands":  ["regex", ...]   # commands exempt from the denylist
# }
# Loosening only, and every suppression announces itself on stderr — an
# override that nobody can see is the thing this design exists to avoid.


def load_config(root: str | None = None) -> dict:
    """Load .captain-hook.json from the repository root.

    A missing file means no overrides. A malformed file is reported and
    treated as empty — an unreadable config must never silently disable the
    guards.
    """
    root = root or _repo_root()
    path = os.path.join(root, CONFIG_FILENAME)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(
            f"captain-hook: Warning: could not read {CONFIG_FILENAME} ({exc}) "
            f"— continuing with all guards enabled\n"
        )
        return {}
    return data if isinstance(data, dict) else {}


def _matches_any(path: str, patterns: list) -> bool:
    """Match a path against glob patterns, relative to the repo root."""
    if not path or not patterns:
        return False
    root = _repo_root()
    abs_path = os.path.realpath(os.path.abspath(path))
    try:
        rel = os.path.relpath(abs_path, root)
    except ValueError:
        rel = abs_path
    return any(
        fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(abs_path, p)
        for p in patterns
        if isinstance(p, str)
    )


def _command_allowed(command: str, patterns: list) -> str | None:
    """Return the allow_commands pattern exempting `command`, if any."""
    for raw in patterns:
        if not isinstance(raw, str):
            continue
        try:
            if re.search(raw, command):
                return raw
        except re.error as exc:
            sys.stderr.write(
                f"captain-hook: Warning: invalid allow_commands regex {raw!r} "
                f"in {CONFIG_FILENAME} ({exc}) — ignored\n"
            )
    return None


# The formatter runs inside a hook on every file write. It must never reach the
# network and must never outlive the host's own hook timeout (30s Antigravity,
# 60s Claude Code, unspecified on Windsurf) — so it gets its own, shorter one.
FORMAT_TIMEOUT_SECONDS = 10


def _local_node_bin(name: str) -> str | None:
    """Find a project-local node_modules/.bin entry by walking up from cwd."""
    current = os.path.abspath(os.getcwd())
    while True:
        candidate = os.path.join(current, "node_modules", ".bin", name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _run_formatter(argv: list[str], path: str) -> None:
    """Best-effort format. Never raises, never blocks the caller's decision."""
    try:
        subprocess.run(argv, capture_output=True, timeout=FORMAT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        sys.stderr.write(
            f"captain-hook: Warning: formatter timed out after "
            f"{FORMAT_TIMEOUT_SECONDS}s on '{path}' — file left unformatted\n"
        )
    except OSError as exc:
        sys.stderr.write(f"captain-hook: Warning: formatter failed on '{path}': {exc}\n")


def dispatch_event(event_name: str, stdin_data: str) -> int:
    payload = {}
    if stdin_data.strip():
        try:
            payload = json.loads(stdin_data)
        except json.JSONDecodeError:
            payload = {"raw": stdin_data}

    prompt, path, command, tool, server, args = extract_fields(payload)

    # Overrides are loaded once, above the blocking/post split, so the advisory
    # post-event scan honors them too — otherwise an allowlisted fixture still
    # warns on every save, which is the noise this exists to remove.
    config = load_config()

    if _matches_any(path, config.get("ignore_paths", [])):
        sys.stderr.write(
            f"captain-hook: Note: all guards skipped for '{path}' by "
            f"{CONFIG_FILENAME} (ignore_paths)\n"
        )
        return 0

    scan_secrets = not _matches_any(path, config.get("allow_secrets_in", []))
    allowed_commands = config.get("allow_commands", []) or []

    if _is_blocking(event_name):
        # 1. Secret Scanning — scan the fields a user controls, not the whole
        # envelope. Scanning raw stdin swept in file contents and diffs, which
        # made a post-write save of any key-shaped string look like an attack.
        for target in (prompt, command, json.dumps(args, default=str) if args else ""):
            if not target:
                continue
            for pattern, label in SECRET_PATTERNS:
                if pattern.search(target):
                    if not scan_secrets:
                        sys.stderr.write(
                            f"captain-hook: Note: {label} in '{path}' allowed by "
                            f"{CONFIG_FILENAME} (allow_secrets_in)\n"
                        )
                        break
                    sys.stderr.write(f"captain-hook: Blocked: Secret key pattern detected ({label})\n")
                    return 2

        # 2. Dangerous Command Denylist
        if command:
            for pattern, label in BLOCKED_COMMANDS:
                if pattern.search(command):
                    allowed_by = _command_allowed(command, allowed_commands)
                    if allowed_by:
                        sys.stderr.write(
                            f"captain-hook: Note: {label} allowed by "
                            f"{CONFIG_FILENAME} (allow_commands: {allowed_by})\n"
                        )
                        break
                    sys.stderr.write(f"captain-hook: Blocked: {label}\n")
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
    elif scan_secrets:
        # Post events cannot block; report and continue so the formatter runs.
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(stdin_data):
                sys.stderr.write(
                    f"captain-hook: Warning: {label} pattern present in "
                    f"'{path or 'payload'}' — this event cannot be blocked\n"
                )
                break

    # 4. Post-Write Auto Formatting — locally installed tools only.
    # Known uncovered: no test actually formats a file. Doing so would require
    # prettier or ruff on the machine, and the suite is deliberately
    # dependency-free. The timeout and the missing-binary path are tested.
    if event_name in POST_WRITE_EVENTS and path and os.path.exists(path):
        if path.endswith((".js", ".ts", ".jsx", ".tsx", ".json")):
            # Resolve the prettier binary itself. Deliberately not launched via
            # the npm auto-install runner, which fetches an unpinned package
            # from the registry when prettier is absent — a network call and
            # arbitrary code execution inside a security hook. See
            # references/guards.md section 4.
            prettier = shutil.which("prettier") or _local_node_bin("prettier")
            if prettier:
                _run_formatter([prettier, "--write", path], path)
        elif path.endswith(".py"):
            ruff = shutil.which("ruff")
            if ruff:
                _run_formatter([ruff, "format", path], path)

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
