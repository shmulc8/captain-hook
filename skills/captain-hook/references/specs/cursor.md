# Exhaustive Cursor AI Hooks Specification

## 1. Overview & Architecture

Cursor AI provides a native **Hooks System** (beta) that enables executing external shell commands, Python scripts, or Node.js executables at specific points during the AI agent loop.

Hooks receive contextual information via `stdin` as a formatted JSON object. Pre-hooks can block execution by exiting with a non-zero status code (specifically Exit Code `2`), returning standard error messages directly into Cursor's IDE and agent context.

---

## 2. Configuration Files & Precedence

Cursor loads hook configurations from two locations:

| Level | File Path | Scope & Usage |
| :--- | :--- | :--- |
| **Workspace (Project)** | `.cursor/hooks.json` | Project-specific hook definitions (version-controlled in git). |
| **User (Global)** | `~/.cursor/hooks.json` | Personal developer hooks applied across all projects locally. |

---

## 3. Configuration Schema Specification

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CursorHooksConfig",
  "type": "object",
  "properties": {
    "version": {
      "type": "integer",
      "enum": [1]
    },
    "hooks": {
      "type": "object",
      "properties": {
        "beforeSubmitPrompt": { "type": "array", "items": { "$ref": "#/definitions/HookCommand" } },
        "beforeShellExecution": { "type": "array", "items": { "$ref": "#/definitions/HookCommand" } },
        "beforeMCPExecution": { "type": "array", "items": { "$ref": "#/definitions/HookCommand" } },
        "beforeReadFile": { "type": "array", "items": { "$ref": "#/definitions/HookCommand" } },
        "afterFileEdit": { "type": "array", "items": { "$ref": "#/definitions/HookCommand" } },
        "stop": { "type": "array", "items": { "$ref": "#/definitions/HookCommand" } }
      }
    }
  },
  "definitions": {
    "HookCommand": {
      "type": "object",
      "required": ["command"],
      "properties": {
        "command": { "type": "string" },
        "timeout_ms": { "type": "integer", "default": 5000 }
      }
    }
  }
}
```

---

## 4. Complete Lifecycle Event Payloads (`stdin`)

### 4.1 `beforeSubmitPrompt`
Triggered after a user clicks "Submit" or presses Enter, before sending the user's prompt to the LLM.

* **Payload (`stdin`)**:
  ```json
  {
    "prompt": "Refactor calculate_total in app.py to be async",
    "conversation_id": "conv_8912312a",
    "model": "claude-3-5-sonnet"
  }
  ```

### 4.2 `beforeShellExecution`
Triggered when the agent decides to execute a terminal command.

* **Payload (`stdin`)**:
  ```json
  {
    "command": "rm -rf build/ && pytest",
    "cwd": "/Users/developer/project",
    "conversation_id": "conv_8912312a"
  }
  ```

### 4.3 `beforeMCPExecution`
Triggered before executing a tool from a Model Context Protocol (MCP) server.

* **Payload (`stdin`)**:
  ```json
  {
    "server": "github-mcp",
    "tool": "create_issue",
    "args": {
      "title": "Bug in auth module",
      "body": "Details..."
    }
  }
  ```

### 4.4 `beforeReadFile`
Triggered before the agent opens and reads a repository file.

* **Payload (`stdin`)**:
  ```json
  {
    "filepath": "/Users/developer/project/config/secrets.json",
    "relative_path": "config/secrets.json"
  }
  ```

### 4.5 `afterFileEdit`
Triggered after the agent completes a modification to a file.

* **Payload (`stdin`)**:
  ```json
  {
    "filepath": "/Users/developer/project/src/app.py",
    "relative_path": "src/app.py",
    "content": "def calculate_total(): ...",
    "diff": "--- src/app.py\n+++ src/app.py\n@@ -1,3 +1,3 @@\n-def total():\n+def calculate_total():"
  }
  ```

### 4.6 `stop`
Triggered when an agent task finishes, is cancelled by the user, or encounters an error.

* **Payload (`stdin`)**:
  ```json
  {
    "status": "completed",
    "reason": "task_finished"
  }
  ```

---

## 5. Exit Code Semantics & Response Protocol

* **Exit Code `0`**: Proceed. The action is allowed.
* **Exit Code `2` (or non-zero)**: Reject. The action is **BLOCKED**. Standard error output (`stderr`) is displayed in Cursor UI.

---

## 6. Complete Implementation Example

### `.cursor/hooks.json`
```json
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [
      { "command": "python3 .cursor/hooks/guard_shell.py" }
    ]
  }
}
```

### `.cursor/hooks/guard_shell.py`
```python
#!/usr/bin/env python3
import sys, json, re

payload = json.load(sys.stdin)
cmd = payload.get("command", "")

if re.search(r"\brm\s+-[rRf]{1,2}\s+[/~*]", cmd):
    sys.stderr.write(f"Cursor Safety Block: Destructive command '{cmd}' is prohibited.\n")
    sys.exit(2)

sys.exit(0)
```
