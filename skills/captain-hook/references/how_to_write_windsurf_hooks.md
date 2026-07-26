# How to Write Hooks for Windsurf Cascade (`references/how_to_write_windsurf_hooks.md`)

Windsurf IDE (by Codeium) executes Cascade Hooks at key points during the agent reasoning loop.

---

## 1. File Locations & Hierarchy Precedence

Windsurf loads and merges `hooks.json` files in the following order:
1. **System Level**: `/etc/windsurf/hooks.json` (Linux/WSL), `/Library/Application Support/Windsurf/hooks.json` (macOS), `C:\ProgramData\Windsurf\hooks.json` (Windows)
2. **User Level**: `~/.codeium/windsurf/hooks.json` (Devin Desktop) or `~/.codeium/hooks.json` (JetBrains plugin)
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

Every payload shares one envelope — `agent_action_name`, `trajectory_id`,
`execution_id`, `timestamp`, `model_name` — and the per-event fields live
**nested under `tool_info`**:

```json
{
  "agent_action_name": "run_command",
  "trajectory_id": "traj_5512",
  "execution_id": "exec_8891",
  "timestamp": "2026-07-26T10:00:00Z",
  "model_name": "Claude Sonnet 4",
  "tool_info": { "command_line": "npm install package-name", "cwd": "/Users/developer/project" }
}
```

| Event Name | `tool_info` contents |
| :--- | :--- |
| `pre_user_prompt` | `{ "user_prompt": "..." }` |
| `pre_read_code` / `post_read_code` | `{ "file_path": "/abs/path" }` |
| `pre_write_code` / `post_write_code` | `{ "file_path": "/abs/path", "edits": [ { "old_string": "...", "new_string": "..." } ] }` |
| `pre_run_command` / `post_run_command` | `{ "command_line": "...", "cwd": "/abs/path" }` |
| `pre_mcp_tool_use` / `post_mcp_tool_use` | `{ "mcp_server_name": "...", "mcp_tool_name": "...", "mcp_tool_arguments": {}, "mcp_result": {} }` |

Reading a flat top-level `file_path` or command field yields `""` against a real
payload — Cascade sends neither.

---

## 4. Exit Code Rules & Blocking Contract

- **Exit Code 0**: Allow. Windsurf proceeds.
- **Exit Code 2**: **BLOCK**, but only on the five `pre_*` hooks —
  `pre_user_prompt`, `pre_read_code`, `pre_write_code`, `pre_run_command`,
  `pre_mcp_tool_use`. `stderr` is surfaced to the agent.
- **Any other exit code**: a non-blocking error; the action proceeds. A crashed
  hook fails **open**. `post_*` hooks cannot block at all.

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
file_path = payload.get("tool_info", {}).get("file_path", "")

if file_path.endswith(".env") or "secrets" in file_path:
    sys.stderr.write(f"Windsurf Cascade Blocked: Editing protected environment file '{file_path}' is forbidden!\n")
    sys.exit(2)  # Exit Code 2 explicitly blocks Windsurf Cascade!

sys.exit(0)
```
