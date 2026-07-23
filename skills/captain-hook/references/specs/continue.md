# Exhaustive Continue CLI (`cn`) Hooks Specification

## 1. Overview & Architecture

The Continue CLI (`cn`) features an agent lifecycle **Hooks System** configured via `~/.continue/settings.json` or project settings. It allows shell scripts or HTTP endpoints to intercept 17 CLI events.

---

## 2. Configuration File Locations

| Level | File Path |
| :--- | :--- |
| **Workspace** | `.continue/settings.json` |
| **User Global** | `~/.continue/settings.json` |

---

## 3. Configuration Schema (`settings.json`)

```json
{
  "hooks": {
    "PreToolUse": [
      { "command": "python3 .continue/hooks/tool_guard.py" }
    ],
    "UserPromptSubmit": [
      { "command": "python3 .continue/hooks/prompt_guard.py" }
    ],
    "TaskCompleted": [
      { "command": "echo 'Task Done'" }
    ]
  }
}
```

---

## 4. Stdin Payload & Exit Code Semantics

- **Input (`stdin`)**: JSON object containing event type, prompt text, tool inputs, and session ID.
- **Exit Code 0**: Allow operation.
- **Exit Code 2**: **BLOCK / REJECT**. Continue CLI cancels execution and feeds `stderr` to the model.
