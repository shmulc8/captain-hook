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
> ⚠️ `npx` downloads `prettier` from the npm registry if it is not installed
> locally. In a hook that runs on every file write, prefer
> `./node_modules/.bin/prettier` and pin the version.

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

- **Exit Code 0**: Allow.
- **Exit Code 2**: Block — equivalent to returning `{"permission": "deny"}` on
  stdout.
- **Any other exit code that is not 0 or 2, a timeout, or invalid JSON**: Cursor
  is **fail-open by default** and the action proceeds. Set `"failClosed": true`
  on the hook entry to reverse this. `beforeReadFile` in particular logs the
  failure and allows the read through; `failClosed: true` is required there too.
- **Alternative to exit codes**: print JSON on stdout —
  `{"permission": "deny", "user_message": "...", "agent_message": "..."}` for
  `beforeShellExecution` / `beforeMCPExecution`, `{"permission": "deny", "user_message": "..."}`
  for `beforeReadFile`, and `{"continue": false, "user_message": "..."}` for
  `beforeSubmitPrompt`.

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
