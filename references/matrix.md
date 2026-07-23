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

## 2. Universal Exit Code Semantics

| Exit Code | Meaning | Host Agent Behavior |
| :---: | :--- | :--- |
| **`0`** | **ALLOW / SUCCESS** | Action proceeds. `stdout` is logged or passed to AI agent context. |
| **`1`** | **HOOK SCRIPT ERROR** | Script execution crashed. Logged to agent debug console. |
| **`2`** | **BLOCK / REJECT** | Policy violation. The action is **BLOCKED**. Execution cancels and `stderr` is passed to agent/user. |
