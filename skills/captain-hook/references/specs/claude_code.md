# Exhaustive Claude Code Hooks Specification

## 1. Overview & Architecture

Claude Code (Anthropic's CLI agent) supports shell-based hooks configured inside `settings.json`. Hooks execute automatically at session lifecycle points and before/after tool calls, receiving JSON payloads on standard input (`stdin`).

---

## 2. Configuration File Locations

| Level | Path | Scope |
| :--- | :--- | :--- |
| **Workspace (Project)** | `.claude/settings.json` | Project-specific hook definitions |
| **User (Global)** | `~/.claude/settings.json` | Global developer hook configuration |

---

## 3. Configuration Schema Specification

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "command": "python3 .claude/hooks/check_prompt.py" }
    ],
    "PreToolUse": [
      { "command": "python3 .claude/hooks/pre_tool_guard.py" }
    ],
    "PostToolUse": [
      { "command": "bash .claude/hooks/post_tool.sh" }
    ],
    "SessionStart": [
      { "command": "echo 'Session Started'" }
    ],
    "SessionEnd": [
      { "command": "python3 .claude/hooks/session_end.py" }
    ],
    "Stop": [
      { "command": "python3 .claude/hooks/on_stop.py" }
    ],
    "StopFailure": [
      { "command": "python3 .claude/hooks/on_error.py" }
    ]
  }
}
```

---

## 4. Complete Lifecycle Event Payloads (`stdin`)

### 4.1 `UserPromptSubmit`
Triggered after a user submits a prompt.

* **Payload (`stdin`)**:
  ```json
  {
    "prompt": "Fix bug in auth middleware",
    "session_id": "sess_891231"
  }
  ```

### 4.2 `PreToolUse`
Triggered after Claude Code selects a tool to invoke, before tool execution.

* **Supported Tool Names**: `Edit`, `Write`, `Bash`, `Glob`, `Grep`, `NotebookEdit`, `Agent`
* **Payload (`stdin`) Example (Bash Tool)**:
  ```json
  {
    "session_id": "sess_891231",
    "tool_name": "Bash",
    "tool_input": {
      "command": "git push origin main --force"
    }
  }
  ```
* **Payload (`stdin`) Example (Edit/Write Tool)**:
  ```json
  {
    "session_id": "sess_891231",
    "tool_name": "Edit",
    "tool_input": {
      "file_path": "/Users/developer/project/src/auth.py",
      "text_to_replace": "old_code",
      "replacement_text": "new_code"
    }
  }
  ```

### 4.3 `PostToolUse`
Triggered immediately after a tool finishes execution.

* **Payload (`stdin`)**:
  ```json
  {
    "session_id": "sess_891231",
    "tool_name": "Bash",
    "tool_input": { "command": "pytest" },
    "tool_response": { "output": "Ran 10 tests... OK", "exit_code": 0 }
  }
  ```

### 4.4 `SessionStart` / `SessionEnd` / `Stop`
Triggered on session lifecycle boundaries.

* **Payload (`stdin`)**:
  ```json
  {
    "session_id": "sess_891231"
  }
  ```

---

## 5. Exit Code Semantics

* **Exit Code `0`**: Allow tool invocation.
* **Exit Code `2` (or non-zero)**: Reject tool invocation. Claude Code **blocks** the tool call and passes standard error (`stderr`) to the model context.

---

## 6. Implementation Example

### `.claude/settings.json`
```json
{
  "hooks": {
    "PreToolUse": [
      { "command": "python3 .claude/hooks/guard.py" }
    ]
  }
}
```

### `.claude/hooks/guard.py`
```python
#!/usr/bin/env python3
import sys, json

payload = json.load(sys.stdin)
tool_name = payload.get("tool_name")
tool_input = payload.get("tool_input", {})

if tool_name == "Bash":
    cmd = tool_input.get("command", "")
    if "rm -rf" in cmd or "git push --force" in cmd:
        sys.stderr.write(f"Claude Code Blocked: Dangerous command '{cmd}' is prohibited.\n")
        sys.exit(2)

sys.exit(0)
```
