# How to Write Hooks for Windsurf Cascade (`references/how_to_write_windsurf_hooks.md`)

Windsurf IDE (by Codeium) executes Cascade Hooks at key points during the agent reasoning loop.

---

## 1. File Locations & Hierarchy Precedence

Windsurf loads and merges `hooks.json` files in the following order:
1. **System Level**: `/etc/windsurf/hooks.json` (Linux) or `/Library/.../hooks.json` (macOS)
2. **User Level**: `~/.codeium/windsurf/hooks.json`
3. **Workspace Level**: `.windsurf/hooks.json` (in repository root)

---

## 2. Configuration Schema (`.windsurf/hooks.json`)

```json
{
  "hooks": {
    "pre_user_prompt": [
      { "command": "python3 .windsurf/hooks/prompt_filter.py", "show_output": false }
    ],
    "pre_write_code": [
      { "command": "python3 .windsurf/hooks/write_guard.py" }
    ],
    "post_write_code": [
      { "command": "ruff format" }
    ],
    "pre_run_command": [
      { "command": "bash .windsurf/hooks/cmd_filter.sh" }
    ],
    "post_run_command": [
      { "command": "python3 .windsurf/hooks/log_command.py" }
    ],
    "pre_mcp_tool_use": [
      { "command": "python3 .windsurf/hooks/mcp_filter.py" }
    ],
    "post_mcp_tool_use": [
      { "command": "python3 .windsurf/hooks/mcp_log.py" }
    ]
  }
}
```

---

## 3. Stdin JSON Payloads & Field Names

Windsurf passes event context as JSON over `stdin`:

| Event Name | `stdin` Payload Shape |
| :--- | :--- |
| `pre_user_prompt` | `{ "user_prompt": "..." }` |
| `pre_write_code` | `{ "file_path": "/abs/path", "code": "..." }` |
| `post_write_code` | `{ "file_path": "/abs/path" }` |
| `pre_run_command` | `{ "command_string": "..." }` |
| `post_run_command` | `{ "command_string": "...", "exit_code": 0 }` |
| `pre_mcp_tool_use` | `{ "tool_name": "...", "mcp_server_name": "...", "arguments": {} }` |
| `post_mcp_tool_use` | `{ "tool_name": "...", "mcp_server_name": "...", "result": {} }` |

---

## 4. Exit Code Rules & Blocking Contract

- **Exit Code 0**: Allow. Windsurf proceeds.
- **Exit Code 2**: **BLOCK / REJECT**. Windsurf specifically uses **Exit Code 2** to cancel `pre_*` actions and displays `stderr` in the Cascade UI!

---

## 5. End-to-End Example: Windsurf Pre-Write Code Guard

### Step 1: Add to `.windsurf/hooks.json`
```json
{
  "hooks": {
    "pre_write_code": [
      { "command": "python3 .windsurf/hooks/block_env.py" }
    ]
  }
}
```

### Step 2: Write `.windsurf/hooks/block_env.py`
```python
#!/usr/bin/env python3
import sys, json

payload = json.load(sys.stdin)
file_path = payload.get("file_path", "")

if file_path.endswith(".env") or "secrets" in file_path:
    sys.stderr.write(f"Windsurf Cascade Blocked: Editing protected environment file '{file_path}' is forbidden!\n")
    sys.exit(2)  # Exit Code 2 explicitly blocks Windsurf Cascade!

sys.exit(0)
```
