# Executable Lifecycle Hooks Matrix (`references/matrix.md`)

This document maps canonical lifecycle events to vendor-native **Executable Hook Systems** across AI coding agents. Non-executable prompt files or rules files are explicitly excluded.

---

## 1. Executable Hook Mapping Table

| Canonical Event | Cursor AI | Windsurf (Cascade) | Claude Code | Antigravity (AGY) | Continue CLI (`cn`) | Aider AI | Git Hooks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`PrePrompt`** | `beforeSubmitPrompt` | `pre_user_prompt` | `UserPromptSubmit` | Prompt Interceptor | `UserPromptSubmit` | Pre-Chat Hook | Pre-commit |
| **`PreWrite`** | `beforeReadFile` | `pre_write_code` | `PreToolUse` (`Edit`/`Write`) | `hooks/prevent.py` | `PreToolUse` | `auto-lint` pre-pass | Pre-commit |
| **`PostWrite`** | `afterFileEdit` | `post_write_code` | `PostToolUse` (`Edit`/`Write`) | Post-fix Hook | `PostToolUse` | `lint-cmd` | Post-commit |
| **`PreCommand`** | `beforeShellExecution` | `pre_run_command` | `PreToolUse` (`Bash`) | Command Guard | `PreToolUse` | Pre-exec Hook | Pre-commit |
| **`PostCommand`** | N/A | `post_run_command` | `PostToolUse` (`Bash`) | Command Listener | `PostToolUse` | Post-exec Hook | Post-commit |
| **`PreMCP`** | `beforeMCPExecution` | `pre_mcp_tool_use` | `PreToolUse` (MCP) | MCP Proxy Hook | `PreToolUse` | MCP Proxy Hook | N/A |
| **`PostMCP`** | N/A | `post_mcp_tool_use` | `PostToolUse` (MCP) | MCP Proxy Hook | `PostToolUse` | MCP Proxy Hook | N/A |
| **`SessionEnd`** | `stop` | `post_user_prompt` | `Stop` / `SessionEnd` | Turn End Hook | `TaskCompleted` | `test-cmd` | Post-commit |

---

## 2. Exit Code Semantics by Agent

Exit `0` allows, everywhere. Exit `1` — and every other non-zero code that is
not `2` — is a **non-blocking hook error** on every agent in this table: the
host surfaces the message and **proceeds with the action**. A hook that raises
an unhandled exception exits `1` and therefore fails **open**.

Exit `2` is the block signal, but only where the host is still able to act:

| Agent | Exit 2 blocks? | Fail-open on crash? |
| :--- | :--- | :--- |
| **Claude Code** | Only on gate events — `PreToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `PreCompact` among them. Not on `PostToolUse`, `SessionStart`, `SessionEnd`, or `Notification` | Yes — non-2 codes proceed |
| **Cursor** | Yes, equivalent to `permission: "deny"` | **Yes by default** — set `failClosed: true` per hook to fail closed |
| **Windsurf** | Only on the five `pre_*` hooks | Yes — other codes proceed |
| **Antigravity** | **No** — decide via `{"decision": "deny"}` on stdout | See its spec |
