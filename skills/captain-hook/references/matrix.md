# Canonical Event & Agent Capability Matrix (`references/matrix.md`)

This reference maps `captain-hook` canonical lifecycle events to vendor-native event names, JSON payload keys, and blocking capabilities across all 10 supported AI coding agents.

---

## 1. Complete Event Mapping Table

| Canonical Event | Cursor AI | Windsurf (Cascade) | Claude Code | Antigravity (AGY) | Continue CLI (`cn`) | Aider AI | Roo Code / Cline | OpenHands | GitHub Copilot | Amazon Q |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`PrePrompt`** | `beforeSubmitPrompt` | `pre_user_prompt` | `UserPromptSubmit` | Prompt Interceptor | `UserPromptSubmit` | Pre-Chat | System Prompt Guard | Action Interceptor | `copilot-instructions` | `.amazonq/rules` |
| **`PreWrite`** | `beforeReadFile` (guard) | `pre_write_code` | `PreToolUse` (`Edit`/`Write`) | `hooks/prevent.py` | `PreToolUse` | `auto-lint` pre-pass | Tool Interceptor | Pre-Action Hook | Git Pre-commit | Pre-check Guard |
| **`PostWrite`** | `afterFileEdit` | `post_write_code` | `PostToolUse` (`Edit`/`Write`) | `--fix` post-pass | `PostToolUse` | `lint-cmd` | Post-tool Hook | Observation Hook | Post-edit Hook | Post-check |
| **`PreCommand`** | `beforeShellExecution` | `pre_run_command` | `PreToolUse` (`Bash`) | `run_command` guard | `PreToolUse` | CLI guard | Terminal Guard | Command Interceptor | Shell hook | Command Guard |
| **`PostCommand`** | N/A | `post_run_command` | `PostToolUse` (`Bash`) | Command Listener | `PostToolUse` | CLI Listener | Terminal Hook | Command Result | Shell Listener | Post-command |
| **`PreMCP`** | `beforeMCPExecution` | `pre_mcp_tool_use` | `PreToolUse` (MCP) | MCP Proxy | `PreToolUse` | MCP Proxy | MCP Interceptor | Tool Interceptor | Extension Hook | MCP Guard |
| **`PostMCP`** | N/A | `post_mcp_tool_use` | `PostToolUse` (MCP) | MCP Proxy | `PostToolUse` | MCP Proxy | MCP Hook | Observation Hook | Extension Listener | Post-MCP |
| **`SessionEnd`** | `stop` | `post_user_prompt` | `Stop` / `SessionEnd` | Turn Listener | `TaskCompleted` | `auto-test` | Mode End | Turn Complete | Commit Gate | Session End |

---

## 2. Stdin Payload Field Resolution

Agents send structured JSON payloads on standard input (`stdin`). `captain-hook` normalizes field names automatically using the resolution order below:

### Target File Path Resolution
1. `path`
2. `filepath` (Cursor)
3. `file_path` (Windsurf / Claude)
4. `file`
5. `tool_input.file_path` (Claude Code `Edit` / `Write` tool)
6. `tool_input.path`

### User Prompt Text Resolution
1. `prompt` (Cursor / Claude Code)
2. `user_prompt` (Windsurf)
3. `raw`

### Terminal Command Resolution
1. `command` (Cursor / Claude Code `Bash` tool)
2. `command_string` (Windsurf)
3. `cmd`
4. `tool_input.command`

### MCP Server & Tool Resolution
1. `server` / `mcp_server_name`
2. `tool` / `tool_name`
3. `args` / `arguments` / `tool_input`

---

## 3. Exit Code Semantics

| Exit Code | Semantics | Host Agent Behavior |
| :---: | :--- | :--- |
| **`0`** | **ALLOW / PROCEED** | Agent continues tool or action execution. Standard output may be logged or passed to AI. |
| **`1`** | **HOOK SCRIPT ERROR** | Script crashed or threw an unhandled exception. Logged to agent debug console. |
| **`2`** | **BLOCK / REJECT** | Policy violation. The action is **BLOCKED**. The agent cancels execution and passes `stderr` text to the AI model or user UI. |
