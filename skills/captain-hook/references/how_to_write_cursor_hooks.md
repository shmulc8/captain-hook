# How to Write Hooks for Cursor AI (`references/how_to_write_cursor_hooks.md`)

Cursor AI features a native **Hooks** system that triggers custom scripts during the agent execution loop.

---

## 1. File Locations
* **Project Level**: `.cursor/hooks.json` (version controlled per repo)
* **Global Level**: `~/.cursor/hooks.json` (applied across all local projects)

---

## 2. Configuration Schema (`.cursor/hooks.json`)

```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      { "command": "python3 .cursor/hooks/prompt_guard.py" }
    ],
    "beforeShellExecution": [
      { "command": "bash .cursor/hooks/shell_guard.sh" }
    ],
    "beforeMCPExecution": [
      { "command": "python3 .cursor/hooks/mcp_guard.py" }
    ],
    "beforeReadFile": [
      { "command": "python3 .cursor/hooks/read_guard.py" }
    ],
    "afterFileEdit": [
      { "command": "npx prettier --write \"$PATH\"" }
    ],
    "stop": [
      { "command": "python3 .cursor/hooks/on_stop.py" }
    ]
  }
}
```

---

## 3. Stdin JSON Payloads & Field Names

Cursor passes event context as a JSON string over `stdin`:

| Event Name | `stdin` Payload Shape |
| :--- | :--- |
| `beforeSubmitPrompt` | `{ "prompt": "User message string" }` |
| `beforeShellExecution` | `{ "command": "terminal command string" }` |
| `beforeMCPExecution` | `{ "server": "server_name", "tool": "tool_name", "args": {} }` |
| `beforeReadFile` | `{ "filepath": "/abs/path/to/file" }` |
| `afterFileEdit` | `{ "filepath": "/abs/path/to/file", "content": "..." }` |
| `stop` | `{ "status": "completed" \| "error" }` |

---

## 4. Exit Code Rules & Blocking Contract

- **Exit Code 0**: Allow. Cursor proceeds with the action.
- **Exit Code 2 (or non-zero)**: Reject. Cursor **blocks** the action and displays `stderr` in the IDE.

---

## 5. End-to-End Example: Cursor Shell Execution Interceptor

### Step 1: Add to `.cursor/hooks.json`
```json
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [
      { "command": "python3 .cursor/hooks/block_sudo.py" }
    ]
  }
}
```

### Step 2: Write `.cursor/hooks/block_sudo.py`
```python
#!/usr/bin/env python3
import sys, json

payload = json.load(sys.stdin)
cmd = payload.get("command", "")

if "sudo" in cmd:
    sys.stderr.write(f"Cursor Hook Blocked: 'sudo' commands are not permitted! ({cmd})\n")
    sys.exit(2)

sys.exit(0)
```
```bash
chmod +x .cursor/hooks/block_sudo.py
```
