# Exhaustive Cursor AI Hooks Specification

## 1. Overview & Architecture

Cursor AI provides a native **Executable Hooks System** (`https://cursor.com/docs/hooks`) that intercepts agent operations by executing local binaries or scripts (Python, Bash, Node.js) at key lifecycle events.

Hooks receive contextual event data via standard input (`stdin`) as a JSON string and return response directives via standard output (`stdout`) or process exit codes.

---

## 2. Configuration File Locations

| Scope | Path | Description |
| :--- | :--- | :--- |
| **Workspace (Project)** | `.cursor/hooks.json` | Repo-specific hooks (committed to git). |
| **User (Global)** | `~/.cursor/hooks.json` | Applied across all local projects. |

---

## 3. Configuration Schema Specification (`.cursor/hooks.json`)

```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      {
        "command": "python3 .cursor/hooks/check_prompt.py",
        "timeout_ms": 5000,
        "failClosed": false
      }
    ],
    "beforeShellExecution": [
      {
        "command": "bash .cursor/hooks/check_cmd.sh",
        "failClosed": true
      }
    ],
    "beforeMCPExecution": [
      {
        "command": "python3 .cursor/hooks/mcp_guard.py"
      }
    ],
    "beforeReadFile": [
      {
        "command": "python3 .cursor/hooks/read_guard.py"
      }
    ],
    "afterFileEdit": [
      {
        "command": "npx prettier --write \"$PATH\""
      }
    ],
    "stop": [
      {
        "command": "python3 .cursor/hooks/on_stop.py"
      }
    ]
  }
}
```

### Key Configuration Options:
- `command`: The executable shell string to run.
- `timeout_ms`: Maximum execution time in milliseconds (default: `5000` ms).
- `failClosed`: If `true`, blocks the action if the hook command fails or times out. Default is `false` (fail-open).

---

## 4. Lifecycle Event Payloads (`stdin`)

### 4.1 `beforeSubmitPrompt`
* **Trigger**: Fires when a prompt is submitted to the agent, before sending to LLM.
* **`stdin` Payload**:
  ```json
  {
    "prompt": "User prompt text...",
    "conversation_id": "conv_12345",
    "model": "claude-3-5-sonnet"
  }
  ```

### 4.2 `beforeShellExecution`
* **Trigger**: Intercepts shell commands before execution.
* **`stdin` Payload**:
  ```json
  {
    "command": "rm -rf build/",
    "cwd": "/path/to/project",
    "conversation_id": "conv_12345"
  }
  ```

### 4.3 `beforeMCPExecution`
* **Trigger**: Intercepts MCP tool execution.
* **`stdin` Payload**:
  ```json
  {
    "server": "github-mcp",
    "tool": "create_issue",
    "args": { "title": "Bug" }
  }
  ```

### 4.4 `beforeReadFile`
* **Trigger**: Intercepts file reads.
* **`stdin` Payload**:
  ```json
  {
    "filepath": "/path/to/project/config/secrets.json",
    "relative_path": "config/secrets.json"
  }
  ```

### 4.5 `afterFileEdit`
* **Trigger**: Runs after file modifications complete.
* **`stdin` Payload**:
  ```json
  {
    "filepath": "/path/to/project/src/index.js",
    "relative_path": "src/index.js",
    "content": "...",
    "diff": "..."
  }
  ```

### 4.6 `stop`
* **Trigger**: Runs when task completes, fails, or is stopped.
* **`stdin` Payload**:
  ```json
  {
    "status": "completed",
    "reason": "task_finished"
  }
  ```

---

## 5. Exit Code Semantics & Responses

* **Exit Code `0`**: Allow.
* **Exit Code `2`**: Block — equivalent to returning `{"permission": "deny"}` on stdout. Standard error (`stderr`) is displayed in the Cursor UI and fed to the agent.
* **Any other exit code that is not 0 or 2, a timeout, or invalid JSON**: Cursor is **fail-open by default** and the action proceeds. Set `"failClosed": true` on the hook entry to reverse this. `beforeReadFile` in particular logs the failure and allows the read through; `failClosed: true` is required there too.
* **Alternative to exit codes** — print JSON on `stdout`:

  | Event | Response shape |
  | :--- | :--- |
  | `beforeShellExecution`, `beforeMCPExecution` | `{"permission": "allow" \| "deny" \| "ask", "user_message": "...", "agent_message": "..."}` |
  | `beforeReadFile` | `{"permission": "allow" \| "deny", "user_message": "..."}` |
  | `beforeSubmitPrompt` | `{"continue": true \| false, "user_message": "..."}` |

  `user_message` is shown to the developer; `agent_message` is fed back into the agent's context.

---

## 6. Debugging Hooks in Cursor
Inspect hook execution in Cursor IDE:
`Ctrl+Shift+P` (or `Cmd+Shift+P`) ➔ **"Output: Show Output Channels"** ➔ Select **"Hooks"**.
