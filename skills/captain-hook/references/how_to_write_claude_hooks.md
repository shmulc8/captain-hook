# How to Write Hooks for Claude Code (`references/how_to_write_claude_hooks.md`)

Claude Code supports shell script execution hooks defined in `.claude/settings.json`.

---

## 1. File Locations
* **Project Level**: `.claude/settings.json`
* **Global User Level**: `~/.claude/settings.json`

---

## 2. Configuration Schema (`.claude/settings.json`)

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "python3 .claude/hooks/prompt_filter.py" } ] }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [ { "type": "command", "command": "python3 .claude/hooks/pre_tool_guard.py", "timeout": 60 } ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [ { "type": "command", "command": "bash .claude/hooks/post_tool.sh" } ]
      }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "python3 .claude/hooks/on_stop.py" } ] }
    ]
  }
}
```

### Schema Parameters
- `matcher`: regex matching the target tool name (`Bash`, `Edit|Write`, `*`). Only meaningful for `PreToolUse` / `PostToolUse`; omit it for lifecycle events.
- `type`: must be `"command"`.
- `command`: the executable script or shell command string.
- `timeout`: execution timeout in seconds (default 60).

---

## 3. Stdin JSON Payloads & Field Names

Claude Code passes event context as JSON over `stdin`:

| Event Name | `stdin` Payload Shape |
| :--- | :--- |
| `UserPromptSubmit` | `{ "prompt": "User prompt text" }` |
| `PreToolUse` | `{ "tool_name": "Edit" \| "Write" \| "Bash" \| "Glob", "tool_input": { "file_path": "...", "command": "..." } }` |
| `PostToolUse` | `{ "tool_name": "...", "tool_input": {}, "tool_response": {} }` |
| `Stop` | `{ "session_id": "..." }` |

---

## 4. Exit Code Rules & Blocking Contract

- **Exit Code 0**: Allow.
- **Exit Code 2**: Block — but only on `PreToolUse`, `UserPromptSubmit`, `Stop`,
  `SubagentStop`, and `PreCompact`. On `PostToolUse`, `SessionStart`,
  `SessionEnd`, and `Notification`, exit 2 does **not** block; `stderr` is just
  surfaced (to Claude for `PostToolUse`, to the user for the rest).
- **Exit Code 1 or any other code that is not 0 or 2**: a non-blocking hook
  error. Claude Code shows a `hook error` notice and **proceeds with the
  action**. Never rely on a crash to stop anything.

---

## 5. End-to-End Example: Claude Code PreToolUse Guard

### Step 1: Add to `.claude/settings.json`
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [ { "type": "command", "command": "python3 .claude/hooks/guard.py" } ]
      }
    ]
  }
}
```

### Step 2: Write `.claude/hooks/guard.py`
```python
#!/usr/bin/env python3
import sys, json

payload = json.load(sys.stdin)
tool_name = payload.get("tool_name")
tool_input = payload.get("tool_input", {})

if tool_name == "Bash":
    cmd = tool_input.get("command", "")
    if "rm -rf" in cmd or "git push --force" in cmd:
        sys.stderr.write(f"Claude Code Hook Blocked: Forbidden Bash command: {cmd}\n")
        sys.exit(2)

sys.exit(0)
```
