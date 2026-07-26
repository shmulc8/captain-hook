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

- **Config Path**: `.windsurf/hooks.json` (Workspace), `~/.codeium/windsurf/hooks.json` (User), `/etc/windsurf/hooks.json` (System)
- **JSON Schema**:
  ```json
  {
    "hooks": {
      "pre_user_prompt": [ { "command": "...", "show_output": false } ],
      "pre_write_code": [ { "command": "..." } ],
      "post_write_code": [ { "command": "..." } ],
      "pre_run_command": [ { "command": "..." } ],
      "post_run_command": [ { "command": "..." } ],
      "pre_mcp_tool_use": [ { "command": "..." } ],
      "post_mcp_tool_use": [ { "command": "..." } ]
    }
  }
  ```
- **Payload (`stdin`) Field Names**:
  - `file_path`: Path to file
  - `code`: File content diff/snippet
  - `user_prompt`: User prompt string
  - `command_string`: Terminal command string
  - `mcp_server_name`: MCP server name
  - `tool_name`: MCP tool name
  - `arguments`: MCP parameters
- **Blocking Contract**: Exit Code **2** explicitly cancels `pre_*` actions.

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
  lint-cmd: "captain-hook dispatch PostWrite"
  auto-test: true
  test-cmd: "python3 -m unittest discover tests"
  auto-commit: true
  ```

---

## 5. Antigravity (AGY)

- **Config Path**: `hooks/prevent.py` (Workspace)
- **Execution**: Python script executed prior to file mutations or `--fix`.
- **Blocking Contract**: Exit Code **2** or throwing an exception blocks the rewrite.

---

## 6. Continue CLI (`cn`)

- **Config Path**: `~/.continue/settings.json`
- **Supported Events**: 17 CLI events including `PreToolUse`, `UserPromptSubmit`, `TaskCompleted`.
- **Blocking Contract**: Exit Code **2** blocks execution.
