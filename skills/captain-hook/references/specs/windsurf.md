# Exhaustive Windsurf (Cascade) Hooks Specification

## 1. Overview & Architecture

Windsurf IDE (developed by Codeium) provides **Cascade Hooks**, an enterprise-grade extension interface that allows executing custom shell commands, Python scripts, or binaries during Cascade's autonomous AI reasoning loop.

Cascade passes action payloads to hook scripts as a JSON object on standard input (`stdin`). For pre-hooks (`pre_*`), scripts can abort or block the action by returning **Exit Code 2**.

---

## 2. Configuration File Locations & Hierarchy

Windsurf merges hook configurations from three hierarchical levels, evaluated in order: **System ➔ User ➔ Workspace**.

| Precedence Level | Operating System | Default File Path | Scope |
| :--- | :--- | :--- | :--- |
| **1. System Level** | macOS | `/Library/Application Support/Windsurf/hooks.json` | Enterprise/Machine-wide policies |
| | Linux | `/etc/windsurf/hooks.json` | Enterprise/Machine-wide policies |
| | Windows | `C:\ProgramData\Windsurf\hooks.json` | Enterprise/Machine-wide policies |
| **2. User Level** | macOS/Linux | `~/.codeium/windsurf/hooks.json` | Personal preferences across projects |
| | Windows | `%USERPROFILE%\.codeium\windsurf\hooks.json` | Personal preferences across projects |
| **3. Workspace Level** | All OS | `.windsurf/hooks.json` | Repository-specific rules (git tracked) |

---

## 3. Configuration Schema Specification

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "WindsurfCascadeHooksConfig",
  "type": "object",
  "properties": {
    "hooks": {
      "type": "object",
      "properties": {
        "pre_user_prompt": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "pre_write_code": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "post_write_code": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "pre_run_command": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "post_run_command": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "pre_mcp_tool_use": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } },
        "post_mcp_tool_use": { "type": "array", "items": { "$ref": "#/definitions/HookItem" } }
      }
    }
  },
  "definitions": {
    "HookItem": {
      "type": "object",
      "required": ["command"],
      "properties": {
        "command": { "type": "string" },
        "show_output": { "type": "boolean", "default": true },
        "timeout": { "type": "integer", "default": 10 }
      }
    }
  }
}
```

---

## 4. Complete Lifecycle Event Payloads (`stdin`)

### 4.1 `pre_user_prompt`
Triggered when the user submits a prompt to Cascade, before processing starts.

* **Payload (`stdin`)**:
  ```json
  {
    "user_prompt": "Fix memory leak in database connector",
    "cascade_session_id": "cas_712984192"
  }
  ```

### 4.2 `pre_write_code`
Triggered before Cascade writes or edits a file in the workspace.

* **Payload (`stdin`)**:
  ```json
  {
    "file_path": "/Users/developer/project/src/db.py",
    "code": "def connect(): ...",
    "cascade_session_id": "cas_712984192"
  }
  ```

### 4.3 `post_write_code`
Triggered immediately after Cascade completes a file edit.

* **Payload (`stdin`)**:
  ```json
  {
    "file_path": "/Users/developer/project/src/db.py",
    "cascade_session_id": "cas_712984192"
  }
  ```

### 4.4 `pre_run_command`
Triggered before Cascade runs a terminal command.

* **Payload (`stdin`)**:
  ```json
  {
    "command_string": "python3 manage.py migrate",
    "working_directory": "/Users/developer/project"
  }
  ```

### 4.5 `post_run_command`
Triggered after terminal command execution completes.

* **Payload (`stdin`)**:
  ```json
  {
    "command_string": "python3 manage.py migrate",
    "exit_code": 0,
    "output_snippet": "Operations to perform: ..."
  }
  ```

### 4.6 `pre_mcp_tool_use`
Triggered before calling an MCP tool.

* **Payload (`stdin`)**:
  ```json
  {
    "mcp_server_name": "sqlite-server",
    "tool_name": "query_db",
    "arguments": { "sql": "SELECT * FROM users;" }
  }
  ```

### 4.7 `post_mcp_tool_use`
Triggered after an MCP tool responds.

* **Payload (`stdin`)**:
  ```json
  {
    "mcp_server_name": "sqlite-server",
    "tool_name": "query_db",
    "result": { "rows": 42 }
  }
  ```

---

## 5. Exit Code Semantics & Response Protocol

* **Exit Code `0`**: Allow. Cascade proceeds.
* **Exit Code `2`**: **BLOCK / REJECT**. Windsurf specifically relies on **Exit Code 2** to cancel pre-actions. `stderr` message is shown in Cascade UI.

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
path = payload.get("file_path", "")

if path.endswith(".env") or "secrets" in path:
    sys.stderr.write(f"Cascade Blocked: Editing protected environment file '{path}' is prohibited.\n")
    sys.exit(2)  # Exit Code 2 explicitly blocks Windsurf Cascade!

sys.exit(0)
```
