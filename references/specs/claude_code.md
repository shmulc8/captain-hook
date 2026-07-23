# Exhaustive Claude Code Hooks Specification

## 1. Overview & Architecture

Claude Code (Anthropic's CLI agent) supports user-defined hooks configured inside `settings.json`. Hooks execute automatically at session lifecycle points and before/after tool calls, receiving JSON payloads on standard input (`stdin`).

---

## 2. Configuration File Locations

| Level | Path | Scope |
| :--- | :--- | :--- |
| **Workspace (Project)** | `.claude/settings.json` | Project-specific hook definitions (shared via git). |
| **Workspace (Local)** | `.claude/settings.local.json` | Local developer hooks (git ignored). |
| **User (Global)** | `~/.claude/settings.json` | Global developer hook configuration across repos. |

---

## 3. Configuration Schema Specification (`settings.json`)

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/check_prompt.py"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/guard_bash.sh",
            "timeout": 60
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/guard_write.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write \"$PATH\""
          }
        ]
      }
    ]
  }
}
```

### Schema Parameters:
- `matcher`: Regex string matching the target tool name (e.g. `Bash`, `Edit|Write`, `Glob`, `Grep`).
- `type`: Must be `"command"` (or `"http"`).
- `command`: The executable script or shell command string.
- `timeout`: Execution timeout in seconds (default: 60).

---

## 4. Lifecycle Event Payloads (`stdin`)

### 4.1 `UserPromptSubmit`
* **Trigger**: Fires after user submits a prompt, before LLM processing.
* **Payload (`stdin`)**:
  ```json
  {
    "prompt": "Fix bug in auth middleware",
    "session_id": "sess_891231"
  }
  ```

### 4.2 `PreToolUse`
* **Trigger**: Fires before a tool call is executed.
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
* **Trigger**: Fires immediately after a tool call completes.
* **Payload (`stdin`)**:
  ```json
  {
    "session_id": "sess_891231",
    "tool_name": "Bash",
    "tool_input": { "command": "pytest" },
    "tool_response": { "output": "Ran 10 tests... OK", "exit_code": 0 }
  }
  ```

---

## 5. Exit Code Semantics

* **Exit Code `0`**: Success. The action proceeds.
* **Exit Code `2`**: **BLOCK / REJECT**. Claude Code blocks tool execution and feeds `stderr` back to the agent LLM context.
* **Exit Code `1` (or other non-zero)**: Non-blocking error. Logged to console.

---

## 6. Implementation Example

### `.claude/hooks/guard_bash.sh`
```bash
#!/usr/bin/env bash
PAYLOAD=$(cat)
CMD=$(echo "$PAYLOAD" | python3 -c "import sys, json; print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))")

if [[ "$CMD" =~ "rm -rf" ]] || [[ "$CMD" =~ "git push --force" ]]; then
    echo "Claude Code Blocked: Command '$CMD' is forbidden!" >&2
    exit 2 # Exit Code 2 explicitly blocks execution!
fi

exit 0
```
