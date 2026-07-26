#!/usr/bin/env python3
"""captain-hook standalone dispatcher and policy script."""

from __future__ import annotations

import argparse
import functools
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
    # Two shapes in one pattern: a prefixed project/service key, whose body may
    # contain hyphens, or a legacy key, which is an unbroken alphanumeric run.
    # The hyphen has to be allowed for `sk-proj-` (real keys carry them) but
    # only after a known prefix — allowing it everywhere matches any kebab-case
    # identifier that happens to start with `sk-`.
    (re.compile(r"(?i)\bsk-(?:(?:proj|svcacct|admin)-[a-zA-Z0-9_\-]{40,}|(?!ant-)[a-zA-Z0-9]{32,})"), "OpenAI API Key"),
    (re.compile(r"(?i)sk-ant-[a-zA-Z0-9\-]{40,}"), "Anthropic API Key"),
]

# A regex denylist over a command string — NOT a sandbox. It does not parse
# shell syntax, so variable expansion, command substitution, and relative
# targets get through by design. It stops the accident, not an adversary; the
# upgrade path is a container or restricted shell, not more regexes. Read the
# "Known limits" table in references/guards.md before adding a pattern here.
BLOCKED_COMMANDS = [
    # rm carrying -r, -R, or -f in any flag arrangement, targeting a root-ish
    # path. One destructive flag is enough: `rm -f ~/.ssh/id_rsa` and
    # `rm -r /` each destroy something irreplaceable without the pair.
    # The flag group accepts long flags and the `--` end-of-options separator:
    # `\w` excludes `-`, so `rm -rf -- /` and `rm --recursive --force /` used to
    # terminate the match before the target was ever examined. A flag token is
    # `--?[\w][\w-]*`, not `--?[\w-]+`: letting the body match a leading `-`
    # makes the dash count ambiguous, and 40 such tokens then backtrack
    # exponentially — a hang in a guard that runs on every command.
    (re.compile(r"\brm\s+(?:--?[\w][\w-]*\s+|--\s+)*-{1,2}\w*[rRf]\w*\s+(?:--?[\w][\w-]*\s+|--\s+)*['\"]?[/~*]"),
     "recursive or forced delete of a root path"),
    # `dd if=` cannot carry a trailing \b: the alternative ends in `=` and a
    # real target starts with `/`, both non-word, so no boundary exists there.
    # With one, this fired on `dd if=foo` and never on `dd if=/dev/sda`.
    (re.compile(r"\bmkfs\b|\bdd\s+if="), "raw disk write or filesystem format"),
    # --force-with-lease is the safe form; blocking it pushes people to --force.
    # `-f` is the spelling models emit most often and was uncovered.
    (re.compile(r"\bgit\s+push\s+(?:.*\s)?(?:--force(?!-with-lease)|-f)\b"), "force push"),
    # Order-insensitive: `chmod 777 -R /` is the same command as `chmod -R 777`.
    # Symbolic modes granting write to others count too — `a+rwx` and `o+w` are
    # 777 by another name.
    (re.compile(r"\bchmod\s+(?:-R\s+(?:777|[ugoa]*\+\w*w\w*)|(?:777|[ugoa]*\+\w*w\w*)\s+-R)\b"),
     "recursive world-writable permissions"),
    (re.compile(r"\bchown\s+-R\s+root\b"), "recursive ownership change to root"),
]


def _as_str(value) -> str:
    """Coerce a payload field to text the guards can actually match.

    A non-string where a string was expected used to reach `re.search` and
    raise; an unhandled exception exits 1, which blocks nowhere, so the guard
    failed open on exactly the malformed payload it should distrust. An
    argv-shaped list is joined rather than discarded — `["git", "push",
    "--force"]` is a command line, and the denylist should see it as one.
    """
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(_as_str(item) for item in value)
    return json.dumps(value, default=str)


def _first_str(value) -> str:
    """First element of a list-shaped field, or the value if it is already a str.

    Antigravity's `workspacePaths` is plural (specs/antigravity.md section 5).
    A repository root is singular, so the first entry is the only defensible
    reading — and a wrong root is worse than no root, which is why an
    unexpected shape returns "" and lets _repo_root() fall back.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], str):
        return value[0]
    return ""


def extract_fields(payload: dict) -> tuple[str, str, str, str, str, dict, str]:
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    # Windsurf/Cascade nests every per-event field under tool_info.
    tool_info = payload.get("tool_info") if isinstance(payload.get("tool_info"), dict) else {}
    # Antigravity sends camelCase and nests tool fields under toolCall
    # (specs/antigravity.md section 5). Documentation-derived: nothing here has
    # been run against a live Antigravity session, so these are APPENDED to the
    # chains below and never replace a verified spelling.
    tool_call = payload.get("toolCall") if isinstance(payload.get("toolCall"), dict) else {}

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
        or tool_call.get("filePath")
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
        or tool_call.get("command")
        or ""
    )
    tool = (
        payload.get("tool")
        or payload.get("tool_name")
        or tool_info.get("mcp_tool_name")
        or payload.get("agent_action_name")
        or tool_call.get("toolName")
        or ""
    )
    server = (
        payload.get("server")
        or payload.get("mcp_server_name")
        or tool_info.get("mcp_server_name")
        or ""
    )
    args = payload.get("args") or payload.get("arguments") or tool_input or tool_info or tool_call or {}
    # The host's working directory is not reliably the repository (see
    # README-INSTALL.md), so prefer the one the payload carries.
    cwd = (
        payload.get("cwd")
        or payload.get("workspace_root")
        # OpenHands (specs/openhands_devin.md section 4).
        or payload.get("working_dir")
        or tool_info.get("cwd")
        or _first_str(payload.get("workspacePaths"))
        or ""
    )

    return (
        _as_str(prompt),
        _as_str(path),
        _as_str(command),
        _as_str(tool),
        _as_str(server),
        args,  # any JSON type; only ever json.dumps'd, never pattern-matched raw
        _as_str(cwd),
    )


def _repo_root(start: str | None = None) -> str:
    """Nearest ancestor directory containing a .git entry, else the cwd.

    Walks up rather than shelling out to git: this runs on every hook
    invocation and must not spawn a subprocess.
    """
    # realpath, not abspath: every path the guards compare against this one is
    # resolved, and on macOS a temp dir alone is enough to make the two spell
    # the same directory differently (/var vs /private/var).
    current = os.path.realpath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.realpath(start or os.getcwd())
        current = parent


def escapes_repo(path: str, root: str | None = None, base: str | None = None) -> tuple[bool, str]:
    """Does `path` resolve outside the repository root?

    Resolves symlinks in every path component, including parent directories
    and including paths that do not exist yet, so a write to a new file
    through a symlinked directory is caught.

    `base` is the directory a RELATIVE path is measured from. It must be the
    working directory the payload carried, not the hook process's own: the
    host is not guaranteed to launch the hook from the agent's directory
    (README-INSTALL.md), and resolving the two halves of this check from
    different origins lets `../x` read as in-repo while the agent writes it
    outside — or blocks an ordinary in-repo write when the hook runs from
    elsewhere.

    Returns (escapes, resolved_path).
    """
    root = os.path.realpath(root or _repo_root())
    if not os.path.isabs(path):
        path = os.path.join(base or root, path)
    resolved = os.path.realpath(path)
    if resolved == root:
        return False, resolved
    # os.path.join, not root + os.sep: a root of "/" would otherwise build the
    # prefix "//", which no path starts with, and every read and write in the
    # repository would be reported as escaping it.
    return not resolved.startswith(os.path.join(root, "")), resolved


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
    # OpenHands — the config file spells these snake_case (specs/openhands_devin.md
    # section 3). Without them an unrecognised `post_tool_use` took the blocking
    # branch and could print "Blocked:" on an event that cannot block.
    "post_tool_use", "session_start", "session_end",
})

# The subset the auto-formatter keys off. Must stay a subset of POST_EVENTS.
POST_WRITE_EVENTS = frozenset({
    "PostWrite", "afterFileEdit", "post_write_code", "PostToolUse",
})

# Post events where exit 2 is the only channel that reaches the model. Claude
# Code shows a hook's stderr to Claude on exit 2 and swallows it on exit 0
# (specs/claude_code.md section 5), so reporting a secret with 0 tells nobody.
# Nothing is blocked either way — the write already landed.
POST_EVENTS_STDERR_TO_MODEL = frozenset({"PostToolUse"})

# Events that CAN still prevent the action. Kept as documentation of what was
# verified upstream; the runtime check below is the complement of POST_EVENTS
# so that an unrecognized event gets guards rather than silently skipping them.
BLOCKING_EVENTS = frozenset({
    "PrePrompt", "PreRead", "PreWrite", "PreCommand", "PreMCP",
    "beforeSubmitPrompt", "beforeShellExecution", "beforeMCPExecution", "beforeReadFile",
    "pre_user_prompt", "pre_read_code", "pre_write_code", "pre_run_command", "pre_mcp_tool_use",
    "UserPromptSubmit", "PreToolUse", "Stop", "SubagentStop", "PreCompact",
    "PreInvocation",
    # OpenHands snake_case config keys (specs/openhands_devin.md section 3).
    "pre_tool_use", "user_prompt_submit",
    # git's own contract: any non-zero exit from a pre-commit hook aborts the
    # commit. This is the fallback gate for the five agents that cannot block.
    "PreCommit",
})


def _is_blocking(event_name: str) -> bool:
    """Unknown events are treated as blocking — fail safe, not silent."""
    return event_name not in POST_EVENTS


# The reason for the most recent block, so `--decision-json` can repeat it to
# an agent that reads stdout instead of exit codes.
_LAST_BLOCK_REASON = ""


def _block(reason: str) -> int:
    global _LAST_BLOCK_REASON
    _LAST_BLOCK_REASON = reason
    sys.stderr.write(f"captain-hook: Blocked: {reason}\n")
    return 2


def _decision_json(event_name: str, exit_code: int) -> str:
    """Antigravity's allow/deny contract is stdout JSON, not an exit code.

    See specs/antigravity.md section 6: a `PreToolUse` hook's output must carry
    a `decision`, and a non-zero exit status blocks nothing there. Post events
    take `{}`.
    """
    if event_name in POST_EVENTS:
        return "{}"
    if exit_code == 2:
        return json.dumps({"decision": "deny", "reason": _LAST_BLOCK_REASON})
    return json.dumps({"decision": "allow"})


CONFIG_FILENAME = ".captain-hook.json"

# Config shape (every key optional):
# {
#   "ignore_paths":    ["glob", ...],   # skip all guards for matching paths
#   "allow_secrets_in":["glob", ...],   # skip only the secret scan for these
#   "allow_commands":  ["regex", ...]   # commands exempt from the denylist
# }
# Loosening only, and every suppression announces itself on stderr — an
# override that nobody can see is the thing this design exists to avoid.


CONFIG_LIST_KEYS = ("ignore_paths", "allow_secrets_in", "allow_commands")


def _config_list(data: dict, key: str) -> list[str]:
    """Read one override key, rejecting anything that is not a list of strings.

    Type-checking the top-level object alone is not enough: a string value
    (`"ignore_paths": "vendor/**"`, the common hand-edit slip) is iterable, so
    every guard would then be tested against its individual *characters* —
    including `*`, which matches everything. A wrong type must be as inert as a
    missing key, and must say so.
    """
    value = data.get(key, [])
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    sys.stderr.write(
        f"captain-hook: Warning: {CONFIG_FILENAME} key '{key}' must be a list of strings, "
        f"got {type(value).__name__} — ignored, guards stay on\n"
    )
    return []


def load_config(root: str | None = None) -> dict:
    """Load .captain-hook.json from the repository root.

    A missing file means no overrides. A malformed file is reported and
    treated as empty — an unreadable config must never silently disable the
    guards. Returns every known key normalized to a list of strings.
    """
    root = root or _repo_root()
    path = os.path.join(root, CONFIG_FILENAME)
    empty = {key: [] for key in CONFIG_LIST_KEYS}
    if not os.path.isfile(path):
        return empty
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(
            f"captain-hook: Warning: could not read {CONFIG_FILENAME} ({exc}) "
            f"— continuing with all guards enabled\n"
        )
        return empty
    if not isinstance(data, dict):
        sys.stderr.write(
            f"captain-hook: Warning: {CONFIG_FILENAME} must be a JSON object, got "
            f"{type(data).__name__} — continuing with all guards enabled\n"
        )
        return empty
    return {key: _config_list(data, key) for key in CONFIG_LIST_KEYS}


@functools.lru_cache(maxsize=None)
def _glob_re(pattern: str) -> re.Pattern:
    """Compile a glob in which `*` does NOT cross a path separator.

    `fnmatch`'s `*` matches `/` too, so `tests/fixtures/*.json` would also
    exempt `tests/fixtures/deep/prod.json` — an override that reads as one
    directory silently covering a whole subtree. `**` still crosses, as in
    .gitignore, so a deliberate subtree exemption is still one character away.
    """
    out = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "*":
            if pattern[i + 1:i + 2] == "*":
                i += 2
                if pattern[i:i + 1] == "/":
                    i += 1
                    # `(?:.*/)?`, not `.*`: `**/` must match whole directory
                    # components, so `**/node_modules` covers `src/node_modules`
                    # and the top-level `node_modules` — but NOT
                    # `src/my_node_modules`, which is a different directory
                    # whose name merely ends the same way. Dropping the
                    # separator here reintroduced exactly the silent widening
                    # the `*` branch below exists to prevent.
                    out.append("(?:.*/)?")
                else:
                    out.append(".*")
                continue
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(char))
        i += 1
    return re.compile("".join(out) + r"\Z")


def _matches_any(path: str, patterns: list, root: str | None = None, base: str | None = None) -> bool:
    """Match a path against glob patterns, relative to the repo root.

    Relative paths measure from `base` — the payload's working directory — for
    the same reason escapes_repo does: an override written against the repo
    layout must not silently stop matching because the host launched the hook
    from a different directory.
    """
    if not path or not patterns:
        return False
    root = root or _repo_root()
    if not os.path.isabs(path):
        path = os.path.join(base or root, path)
    abs_path = os.path.realpath(path)
    try:
        rel = os.path.relpath(abs_path, root)
    except ValueError:
        rel = abs_path
    return any(
        _glob_re(p).match(rel) or _glob_re(p).match(abs_path)
        for p in patterns
        if isinstance(p, str)
    )


def _command_allowed(command: str, patterns: list, span: tuple[int, int]) -> str | None:
    """Return the allow_commands pattern covering `span`, if any.

    Containment, not a bare search anywhere in the line: an entry allowing a
    release script's force push must not also exempt the `rm -rf ~/` chained
    after it. The exemption applies to the text the denylist actually matched.
    """
    start, end = span
    for raw in patterns:
        if not isinstance(raw, str):
            continue
        try:
            if any(m.start() <= start and m.end() >= end for m in re.finditer(raw, command)):
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


def _local_node_bin(name: str, root: str, start: str) -> str | None:
    """Find a project-local node_modules/.bin entry, never leaving the repo.

    The walk stops at the repository root on purpose. Continuing to `/` would
    execute whatever `node_modules/.bin/prettier` happens to sit in an ancestor
    directory — a stray `npm install` in $HOME is enough — which is the
    arbitrary-code-execution-in-a-hook problem that `npx` was dropped to avoid.
    """
    root = os.path.realpath(root)
    current = os.path.realpath(os.path.abspath(start))
    if not current.startswith(os.path.join(root, "")) and current != root:
        current = root
    while True:
        candidate = os.path.join(current, "node_modules", ".bin", name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        if current == root:
            return None
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


# A commit hook gets no stdin and no arguments from git, so the fields every
# other event carries are empty. Reading the staged diff is the only way this
# gate can inspect anything — and it is the one place a subprocess is
# acceptable: a commit is not the per-tool-call hot path _repo_root() is
# written for, and it happens orders of magnitude less often.
GIT_TIMEOUT_SECONDS = 10


def _staged(root: str) -> tuple[str, list[str]]:
    """(added lines of the staged diff, staged file paths). Empty on failure.

    Failure here must not block: a hook that aborts every commit because git
    was unavailable gets deleted, and a deleted hook protects nothing.
    """
    def run(args: list[str]) -> str:
        try:
            result = subprocess.run(
                ["git", *args], cwd=root, capture_output=True, text=True,
                timeout=GIT_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            sys.stderr.write(f"captain-hook: Warning: git {args[0]} failed ({exc}) — commit not inspected\n")
            return ""
        if result.returncode != 0:
            sys.stderr.write(f"captain-hook: Warning: git {args[0]} exited {result.returncode} — commit not inspected\n")
            return ""
        return result.stdout

    diff = run(["diff", "--cached", "--unified=0", "--no-color"])
    # Only ADDED lines. A diff's context and removed lines carry the secret
    # being deleted, and blocking a commit that removes a key is backwards.
    added = "\n".join(
        line[1:] for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    names = [n for n in run(["diff", "--cached", "--name-only"]).splitlines() if n]
    return added, names


def dispatch_event(event_name: str, stdin_data: str, argv_paths: list[str] | None = None) -> int:
    payload = {}
    if stdin_data.strip():
        try:
            payload = json.loads(stdin_data)
        except json.JSONDecodeError:
            payload = {"raw": stdin_data}
    if not isinstance(payload, dict):
        payload = {"raw": stdin_data}

    prompt, path, command, tool, server, args, cwd = extract_fields(payload)
    # aider's lint-cmd passes the edited files as arguments and sends no JSON
    # on stdin, so argv is the only place the path appears (specs/aider.md).
    if not path and argv_paths:
        path = argv_paths[0]

    # Every guard measures against one repository root, taken from the payload
    # when the host provides it: hooks do not reliably run with the repository
    # as their working directory (README-INSTALL.md), and deriving the root
    # from the wrong cwd both blocks in-repo paths and loses the overrides.
    root = _repo_root(cwd or None)
    # Relative paths in the payload are the agent's, measured from ITS working
    # directory — not this process's, which the host chooses freely.
    base = os.path.realpath(cwd) if cwd else root

    # Overrides are loaded once, above the blocking/post split, so the advisory
    # post-event scan honors them too — otherwise an allowlisted fixture still
    # warns on every save, which is the noise this exists to remove.
    config = load_config(root)

    if event_name == "PreCommit" and not (prompt or command or path):
        staged_text, staged_paths = _staged(root)
        # The added lines become the scanned text; the file list drives the
        # path guard. Both go through the same guards every other event uses,
        # so allow_secrets_in and ignore_paths keep working. Only the first
        # staged path reaches the path guard — see specs/copilot.md.
        prompt = staged_text
        if staged_paths:
            path = staged_paths[0]

    if _matches_any(path, config["ignore_paths"], root, base):
        sys.stderr.write(
            f"captain-hook: Note: all guards skipped for '{path}' by "
            f"{CONFIG_FILENAME} (ignore_paths)\n"
        )
        return 0

    scan_secrets = not _matches_any(path, config["allow_secrets_in"], root, base)
    allowed_commands = config["allow_commands"]
    post_exit = 0

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
                    return _block(f"Secret key pattern detected ({label})")

        # 2. Dangerous Command Denylist
        if command:
            for pattern, label in BLOCKED_COMMANDS:
                hit = pattern.search(command)
                if hit:
                    allowed_by = _command_allowed(command, allowed_commands, hit.span())
                    if allowed_by:
                        sys.stderr.write(
                            f"captain-hook: Note: {label} allowed by "
                            f"{CONFIG_FILENAME} (allow_commands: {allowed_by})\n"
                        )
                        # continue, not break: an allowlist entry exempts the
                        # pattern it matched, not the rest of the denylist.
                        # `git push --force && rm -rf ~/` must still be blocked
                        # by a rule allowing only the force push.
                        continue
                    return _block(label)

        # 3. Symlink / Path-Escape Guard
        if path:
            escapes, resolved = escapes_repo(path, root, base)
            if escapes:
                return _block(
                    f"'{path}' resolves to '{resolved}', outside the repository root"
                )
    elif scan_secrets:
        # Post events cannot block; report and continue so the formatter runs.
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(stdin_data):
                sys.stderr.write(
                    f"captain-hook: Warning: {label} pattern present in "
                    f"'{path or 'payload'}' — this event cannot be blocked\n"
                )
                if event_name in POST_EVENTS_STDERR_TO_MODEL:
                    post_exit = 2
                break

    # 4. Post-Write Auto Formatting — locally installed tools only.
    # Known uncovered: no test formats a real file. Doing so would require
    # prettier or ruff on the machine, and the suite is deliberately
    # dependency-free. What IS covered: the timeout, the missing-binary path,
    # and the node_modules walk's containment clamp — see verify_hooks.sh.
    # The formatter rewrites the file it is pointed at, so it gets the same
    # containment as a write: a post event naming a path outside the repository
    # is not something this hook should be running a tool against.
    if (
        event_name in POST_WRITE_EVENTS
        and path
        and os.path.exists(path)
        and not escapes_repo(path, root, base)[0]
    ):
        start = os.path.dirname(os.path.abspath(path))
        if path.endswith((".js", ".ts", ".jsx", ".tsx", ".json")):
            # Resolve the prettier binary itself. Deliberately not launched via
            # the npm auto-install runner, which fetches an unpinned package
            # from the registry when prettier is absent — a network call and
            # arbitrary code execution inside a security hook. See
            # references/guards.md section 4.
            prettier = shutil.which("prettier") or _local_node_bin("prettier", root, start)
            if prettier:
                _run_formatter([prettier, "--write", path], path)
        elif path.endswith(".py"):
            ruff = shutil.which("ruff")
            if ruff:
                _run_formatter([ruff, "format", path], path)

    return post_exit


def main():
    parser = argparse.ArgumentParser(description="captain-hook standalone dispatcher.")
    subparsers = parser.add_subparsers(dest="subcommand")

    dispatch_parser = subparsers.add_parser("dispatch", help="Dispatch a hook event.")
    dispatch_parser.add_argument("event", help="Canonical or agent event name")
    # aider appends the edited filenames to lint-cmd (specs/aider.md). Rejecting
    # them made argparse exit 2 before any guard ran, which aider reports back to
    # the model as a lint failure on a file that is fine.
    dispatch_parser.add_argument(
        "paths", nargs="*", help="Optional file paths appended by the host (aider lint-cmd)"
    )
    dispatch_parser.add_argument(
        "--decision-json",
        action="store_true",
        help="Also print an allow/deny decision object on stdout (Antigravity).",
    )

    args = parser.parse_args()

    if args.subcommand == "dispatch":
        stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
        code = dispatch_event(args.event, stdin_data, args.paths)
        if args.decision_json:
            sys.stdout.write(_decision_json(args.event, code) + "\n")
        sys.exit(code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
