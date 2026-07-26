# Agent Hook Specifications Reference (`references/specs.md`)

This document provides exact, authoritative specifications for all supported AI coding agents.

---

## 1. Cursor AI

- **Config Path**: `.cursor/hooks.json` (Workspace) or `~/.cursor/hooks.json` (User Global)
- **JSON Schema**:
  ```json
  {
    "version": 1,
    "hooks": {
      "beforeSubmitPrompt": [ { "command": "..." } ],
      "beforeShellExecution": [ { "command": "..." } ],
      "beforeMCPExecution": [ { "command": "..." } ],
      "beforeReadFile": [ { "command": "..." } ],
      "afterFileEdit": [ { "command": "..." } ],
      "stop": [ { "command": "..." } ]
    }
  }
  ```
- **Payload (`stdin`) Field Names**:
  - `filepath`: Path to target file
  - `prompt`: User prompt string
  - `command`: Shell command string
  - `server`: MCP server name
  - `tool`: MCP tool name
  - `args`: MCP arguments dictionary

---

## 2. Windsurf (Cascade)

- **Config Path**: `.windsurf/hooks.json` (Workspace); `~/.codeium/windsurf/hooks.json` (User, Devin Desktop) or `~/.codeium/hooks.json` (User, JetBrains); `/etc/windsurf/hooks.json`, `/Library/Application Support/Windsurf/hooks.json`, or `C:\ProgramData\Windsurf\hooks.json` (System)
- **JSON Schema** — all 12 events:
  ```json
  {
    "hooks": {
      "pre_read_code": [ { "command": "..." } ],
      "post_read_code": [ { "command": "..." } ],
      "pre_write_code": [ { "command": "..." } ],
      "post_write_code": [ { "command": "..." } ],
      "pre_run_command": [ { "command": "..." } ],
      "post_run_command": [ { "command": "..." } ],
      "pre_mcp_tool_use": [ { "command": "..." } ],
      "post_mcp_tool_use": [ { "command": "..." } ],
      "pre_user_prompt": [ { "command": "...", "show_output": false } ],
      "post_cascade_response": [ { "command": "..." } ],
      "post_cascade_response_with_transcript": [ { "command": "..." } ],
      "post_setup_worktree": [ { "command": "..." } ]
    }
  }
  ```
  Per-hook fields are `command` (required), `powershell`, `show_output`, and `working_directory`. There is no `timeout` field.
- **Payload (`stdin`) Field Names** — a common envelope (`agent_action_name`, `trajectory_id`, `execution_id`, `timestamp`, `model_name`) wrapping a `tool_info` object; the per-event data is **inside `tool_info`**:
  - `tool_info.user_prompt`: User prompt string
  - `tool_info.file_path`: Path to file
  - `tool_info.edits[]`: `{ "old_string": "...", "new_string": "..." }` entries
  - `tool_info.command_line`: Terminal command string
  - `tool_info.cwd`: Command working directory
  - `tool_info.mcp_server_name` / `tool_info.mcp_tool_name` / `tool_info.mcp_tool_arguments` / `tool_info.mcp_result`
- **Blocking Contract**: Exit Code **2** cancels the action, but only on the five `pre_*` hooks. Any other non-zero code is non-blocking and the action proceeds.

---

## 3. Claude Code

- **Config Path**: `.claude/settings.json` (Workspace) or `~/.claude/settings.json` (Global)
- **JSON Schema**:
  ```json
  {
    "hooks": {
      "UserPromptSubmit": [
        { "hooks": [ { "type": "command", "command": "..." } ] }
      ],
      "PreToolUse": [
        { "matcher": "Bash|Edit|Write", "hooks": [ { "type": "command", "command": "..." } ] }
      ],
      "PostToolUse": [
        { "matcher": "Edit|Write", "hooks": [ { "type": "command", "command": "..." } ] }
      ],
      "SessionStart": [
        { "hooks": [ { "type": "command", "command": "..." } ] }
      ],
      "SessionEnd": [
        { "hooks": [ { "type": "command", "command": "..." } ] }
      ],
      "Stop": [
        { "hooks": [ { "type": "command", "command": "..." } ] }
      ]
    }
  }
  ```
- **Payload (`stdin`) Field Names**:
  - `tool_name`: Name of tool (`Edit`, `Write`, `Bash`, `Glob`, etc.)
  - `tool_input`: Object containing `file_path` or `command`
  - `prompt`: User prompt string
- **Schema note**: every event maps to an array of matcher groups; each group holds a nested `hooks` array whose entries set `type` to `command` alongside the `command` string. `matcher` is a regex over the tool name and only applies to `PreToolUse`/`PostToolUse`. An event array whose entries carry `command` directly, with no nested `hooks` array, is invalid.

---

## 4. Aider AI

- **Config Path**: `.aider.conf.yml` (Workspace) or `~/.aider.conf.yml` (Global)
- **YAML Schema**:
  ```yaml
  auto-lint: true
  lint-cmd: "<CAPTAIN_HOOK> dispatch PostWrite"
  auto-test: true
  test-cmd: "python3 -m unittest discover tests"
  auto-commit: true
  ```

---

## 5. Antigravity (AGY)

- **Config Path**: `.agents/hooks.json` (Workspace) or `~/.gemini/config/hooks.json` (User)
- **Supported Events**: `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`. `matcher` (a regex over tool names) applies to the two tool events.
- **Payload (`stdin`) Field Names**: camelCase, with `conversationId`, `workspacePaths`, `transcriptPath`, and `artifactDirectoryPath` on every event.
- **Blocking Contract**: **no exit-code contract**. Hooks print a JSON object on `stdout`; `PreToolUse` must carry `decision` (`"allow"` / `"deny"` / `"ask"` / `"force_ask"`), and `Stop` uses `{"decision": "continue"}` to prevent termination.

---

## 6. Continue CLI (`cn`)

- **Config Path**: `~/.continue/settings.json`
- **Supported Events**: 17 CLI events including `PreToolUse`, `UserPromptSubmit`, `TaskCompleted`.
- **Blocking Contract**: Exit Code **2** blocks execution.
