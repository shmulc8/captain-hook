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
      { "command": "bash .cursor/hooks/format.sh" }
    ],
    "stop": [
      { "command": "python3 .cursor/hooks/on_stop.py" }
    ]
  }
}
```
```bash
#!/usr/bin/env bash
# .cursor/hooks/format.sh — the edited file's path arrives in the stdin
# payload, not as a shell variable. `$PATH` is the shell's search path and is
# never a filename.
FILE=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('filepath') or d.get('tool_input',{}).get('file_path',''))")
[ -n "$FILE" ] || exit 0
# The local binary, never the npm auto-install runner: it downloads an unpinned
# package from the registry when prettier is absent, which is a network fetch
# and arbitrary code execution inside a hook that runs on every write.
[ -x ./node_modules/.bin/prettier ] || exit 0
./node_modules/.bin/prettier --write "$FILE"
```

> ⚠️ The edited file's path arrives in the **stdin payload**, not on the
> command line, and the local binary is used rather than `npx`, which downloads
> an unpinned package from the npm registry inside a hook.

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
