# Exhaustive Google Antigravity Hooks Specification

> Source: https://antigravity.google/docs/hooks — verified 2026-07-26

## 1. Overview & Architecture

Google Antigravity executes hooks defined in a `hooks.json` file in its
customization directory. Hooks receive a JSON payload on `stdin` and return a
JSON object on `stdout`. **Antigravity does not use exit codes to allow or deny
actions** — unlike Claude Code, Cursor, and Windsurf, the decision is carried in
a `decision` field.

---

## 2. Configuration File Locations

| Scope | Path |
| :--- | :--- |
| **Workspace** | `.agents/hooks.json` |
| **User (Global)** | `~/.gemini/config/hooks.json` |

---

## 3. Configuration Schema (`hooks.json`)

```json
{
  "enabled": true,
  "PreToolUse": [
    {
      "matcher": "run_command",
      "hooks": [
        { "type": "command", "command": "python3 .agents/hooks/guard_command.py", "timeout": 30 }
      ]
    }
  ],
  "PostToolUse": [
    {
      "matcher": "write_file|edit_file",
      "hooks": [
        { "type": "command", "command": "python3 .agents/hooks/log_write.py" }
      ]
    }
  ],
  "PreInvocation": [
    { "hooks": [ { "type": "command", "command": "python3 .agents/hooks/pre_invocation.py" } ] }
  ],
  "PostInvocation": [
    { "hooks": [ { "type": "command", "command": "python3 .agents/hooks/post_invocation.py" } ] }
  ],
  "Stop": [
    { "hooks": [ { "type": "command", "command": "python3 .agents/hooks/on_stop.py" } ] }
  ]
}
```

### Schema Parameters
- `enabled`: boolean, defaults to `true`.
- `matcher`: regex over tool names (`"run_command"`, `"browser_.*"`, `"*"`). Applies to
  `PreToolUse` and `PostToolUse` only.
- `type`: must be `"command"` — the only handler type currently supported.
- `command`: shell command string.
- `timeout`: seconds, default `30`.

---

## 4. Lifecycle Events

| Event | Trigger |
| :--- | :--- |
| `PreToolUse` | before a tool runs |
| `PostToolUse` | after a tool completes |
| `PreInvocation` | before the model is called |
| `PostInvocation` | after tool calls finish |
| `Stop` | when execution terminates |

---

## 5. stdin Payload

JSON with **camelCase** field names — not the `snake_case` used by Windsurf or
the mixed shapes used by Cursor. Common metadata is present on every event:

| Field | Meaning |
| :--- | :--- |
| `conversationId` | Identifier for the conversation |
| `workspacePaths` | Workspace roots |
| `transcriptPath` | Path to the conversation transcript |
| `artifactDirectoryPath` | Path to the artifact directory |

Event-specific fields are also camelCase — for example `toolCall` on
`PreToolUse` / `PostToolUse`, `stepIdx` and `invocationNum` on the invocation
events, and `terminationReason` on `Stop`.

> **Verification status**: these field names come from the upstream
> documentation cited above, not from a captured payload. The bundled
> dispatcher reads `toolCall.command`, `toolCall.filePath`, `toolCall.toolName`
> and `workspacePaths` on that basis. If you run captain-hook against a live
> Antigravity session, capture one `PreToolUse` payload into
> `examples/payloads/` and correct this note — that is the one piece of
> evidence this file does not have.

---

## 6. Decision Contract (stdout JSON, not exit codes)

- `PreToolUse` — output **must** include `decision`, one of:

  | Value | Effect |
  | :--- | :--- |
  | `"allow"` | Allows the tool execution |
  | `"deny"` | Hard blocks execution immediately |
  | `"ask"` | Prompts the user, respecting "Always Allow" settings |
  | `"force_ask"` | Always prompts, ignoring cached permissions |

  Optional `reason` explains the decision; optional `permissionOverrides` adjusts
  permissions for the call.
- `PostToolUse`, `PreInvocation`, `PostInvocation` — return `{}` or inject steps.
- `Stop` — `{"decision": "continue"}` prevents termination and re-enters the
  execution loop; any other value allows the stop to proceed.

There is no exit-code-2 contract. A guard that signals by exiting with a
non-zero status will not block anything in Antigravity.

**How this repository handles it**: the bundled dispatcher
(`scripts/captain_hook.py`) signals allow/deny through its exit code by
default, which blocks nothing here. Pass `--decision-json` and it also writes
the decision object this contract requires to stdout — `{"decision": "deny",
"reason": "<the guard that fired>"}` on a block, `{"decision": "allow"}`
otherwise, `{}` on post events. `examples/antigravity_hooks.json` uses the flag
on `PreToolUse`. Without it, an Antigravity hook runs the guards and then
allows the action regardless of what they found.

---

## 7. Implementation Example

### `.agents/hooks.json`
```json
{
  "enabled": true,
  "PreToolUse": [
    {
      "matcher": "run_command",
      "hooks": [
        { "type": "command", "command": "python3 .agents/hooks/guard_command.py", "timeout": 30 }
      ]
    }
  ]
}
```

### `.agents/hooks/guard_command.py`
```python
#!/usr/bin/env python3
"""Antigravity PreToolUse guard: denies dangerous shell commands via stdout JSON."""
import json
import sys

payload = json.load(sys.stdin)
tool_call = payload.get("toolCall", {}) or {}
command = tool_call.get("command", "") or ""

if "rm -rf /" in command or "--force" in command:
    print(json.dumps({"decision": "deny", "reason": f"Blocked by policy: {command}"}))
else:
    print(json.dumps({"decision": "allow"}))
```

Note the shape: the script exits `0` in both branches and carries its verdict in
the printed JSON. A non-zero exit here would let the command through.
