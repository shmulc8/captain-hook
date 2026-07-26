# Exhaustive Windsurf (Cascade) Hooks Specification

> Source: https://docs.devin.ai/desktop/cascade/hooks — verified 2026-07-26

## 1. Overview & Architecture

Windsurf provides **Cascade Hooks**, an extension interface that runs custom shell commands, Python scripts, or binaries during Cascade's autonomous AI reasoning loop.

Cascade passes action payloads to hook scripts as a JSON object on standard input (`stdin`). For the five `pre_*` hooks, scripts can abort or block the action by returning **Exit Code 2**.

Windsurf/Cascade now ships under Cognition's Devin documentation; `docs.windsurf.com/windsurf/cascade/hooks` redirects there.

---

## 2. Configuration File Locations & Hierarchy

Windsurf merges hook configurations from three hierarchical levels, evaluated in order: **System ➔ User ➔ Workspace**.

| Precedence Level | Environment | Default File Path | Scope |
| :--- | :--- | :--- | :--- |
| **1. System Level** | macOS | `/Library/Application Support/Windsurf/hooks.json` | Enterprise/machine-wide policies |
| | Linux / WSL | `/etc/windsurf/hooks.json` | Enterprise/machine-wide policies |
| | Windows | `C:\ProgramData\Windsurf\hooks.json` | Enterprise/machine-wide policies |
| **2. User Level** | Devin Desktop | `~/.codeium/windsurf/hooks.json` | Personal preferences across projects |
| | JetBrains plugin | `~/.codeium/hooks.json` | Personal preferences across projects |
| **3. Workspace Level** | All | `.windsurf/hooks.json` | Repository-specific rules (git tracked) |

---

## 3. Configuration Schema Specification

Cascade defines **12 events**. Only the five `pre_*` events can block.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "WindsurfCascadeHooksConfig",
  "type": "object",
  "properties": {
    "hooks": {
      "type": "object",
      "properties": {
        "pre_read_code": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "post_read_code": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "pre_write_code": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "post_write_code": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "pre_run_command": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "post_run_command": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "pre_mcp_tool_use": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "post_mcp_tool_use": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "pre_user_prompt": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "post_cascade_response": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "post_cascade_response_with_transcript": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "post_setup_worktree": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } }
      }
    }
  },
  "definitions": {
    "HookItem": {
      "type": "object",
      "required": ["command"],
      "properties": {
        "command": { "type": "string" },
        "powershell": { "type": "string" },
        "show_output": { "type": "boolean" },
        "working_directory": { "type": "string" }
      }
    }
  }
}
```

### Schema Parameters
- `command` — **required**. Runs via `bash -c` on macOS/Linux.
- `powershell` — optional Windows equivalent, run via `powershell -Command`.
- `show_output` — boolean; whether hook output is surfaced in the Cascade UI.
- `working_directory` — defaults to the workspace root.

**Cascade does not document a per-hook timeout field.** Any `timeout` key you find in a third-party template is invented.

---

## 4. Complete Lifecycle Event Payloads (`stdin`)

### 4.0 The common envelope

Every hook receives the same outer object. The per-event data lives **nested under `tool_info`**. There are no flat top-level command, code, or session-id fields — templates showing them are describing a shape Cascade does not send.

| Field | Meaning |
| :--- | :--- |
| `agent_action_name` | The action that triggered the hook (e.g. `run_command`) |
| `trajectory_id` | Identifier for the overall Cascade conversation |
| `execution_id` | Identifier for the single agent turn |
| `timestamp` | ISO 8601 timestamp |
| `model_name` | Human-readable model name (e.g. `Claude Sonnet 4`) |
| `tool_info` | Object holding the per-event fields below |

```json
{
  "agent_action_name": "run_command",
  "trajectory_id": "traj_5512",
  "execution_id": "exec_8891",
  "timestamp": "2026-07-26T10:00:00Z",
  "model_name": "Claude Sonnet 4",
  "tool_info": { "command_line": "npm install package-name", "cwd": "/Users/developer/project" }
}
```

### 4.1 `pre_user_prompt`
Triggered when the user submits a prompt to Cascade, before processing starts.

* **`tool_info`**:
  ```json
  { "user_prompt": "Fix memory leak in database connector" }
  ```

### 4.2 `pre_read_code` / `post_read_code`
Triggered around Cascade reading a file.

* **`tool_info`**:
  ```json
  { "file_path": "/Users/developer/project/src/db.py" }
  ```

### 4.3 `pre_write_code` / `post_write_code`
Triggered around Cascade writing or editing a file.

* **`tool_info`**:
  ```json
  {
    "file_path": "/Users/developer/project/src/db.py",
    "edits": [ { "old_string": "def connect(): ...", "new_string": "def connect(dsn): ..." } ]
  }
  ```

### 4.4 `pre_run_command` / `post_run_command`
Triggered around Cascade running a terminal command.

* **`tool_info`**:
  ```json
  { "command_line": "python3 manage.py migrate", "cwd": "/Users/developer/project" }
  ```

### 4.5 `pre_mcp_tool_use` / `post_mcp_tool_use`
Triggered around an MCP tool call.

* **`tool_info`**:
  ```json
  {
    "mcp_server_name": "sqlite-server",
    "mcp_tool_name": "query_db",
    "mcp_tool_arguments": { "sql": "SELECT * FROM users;" },
    "mcp_result": { "rows": 42 }
  }
  ```
  `mcp_result` is populated on `post_mcp_tool_use` only.

### 4.6 `post_cascade_response` / `post_cascade_response_with_transcript`
Triggered after Cascade finishes responding. The `_with_transcript` variant additionally carries the conversation transcript. These are the closest real equivalents to an "end of turn" event. Note that `pre_user_prompt` has **no** `post_` counterpart — templates wiring one are describing an event Cascade does not define.

### 4.7 `post_setup_worktree`
Triggered after a worktree is set up.

---

## 5. Exit Code Semantics & Response Protocol

* **Exit Code `0`**: Allow. Cascade proceeds.
* **Exit Code `2`**: **BLOCK**, but only on the five `pre_*` hooks — `pre_user_prompt`, `pre_read_code`, `pre_write_code`, `pre_run_command`, `pre_mcp_tool_use`. The `stderr` message is surfaced to the agent.
* **Any other exit code**: treated as a non-blocking error; the action proceeds. **A crashed hook fails open.**

`post_*` hooks cannot block anything — the action has already happened.

---

## 6. Complete Implementation Example

### `.windsurf/hooks.json`
```json
{
  "hooks": {
    "pre_write_code": [
      { "command": "python3 .windsurf/hooks/guard_write.py" }
    ]
  }
}
```

### `.windsurf/hooks/guard_write.py`
```python
#!/usr/bin/env python3
import sys, json

payload = json.load(sys.stdin)
path = payload.get("tool_info", {}).get("file_path", "")

if path.endswith(".env") or "secrets" in path:
    sys.stderr.write(f"Cascade Blocked: Editing protected environment file '{path}' is prohibited.\n")
    sys.exit(2)  # Exit Code 2 blocks a pre_* Cascade hook

sys.exit(0)
```
