# OpenHands Hooks Specification

> Source: https://docs.openhands.dev/openhands/usage/customization/hooks — verified 2026-07-26

## 1. Overview & Architecture

OpenHands has a real lifecycle hook system. Hooks are shell commands declared in
a JSON config file; they receive a JSON payload on `stdin` and can block the
agent's action.

**Naming note**: OpenHands and Devin are different products from different
vendors. This file documents **OpenHands** (`docs.openhands.dev`, formerly
`docs.all-hands.dev`, which 308-redirects there). Nothing here is a claim about
Devin.

---

## 2. Configuration File Location

| Scope | Path | Format |
| :--- | :--- | :--- |
| **Workspace** | `.openhands/hooks.json` | JSON |

Event keys are `snake_case` in the config file, mapping to matcher groups whose
`hooks` array holds `command` and an optional `timeout`.

```json
{
  "pre_tool_use": [
    {
      "matcher": "terminal",
      "hooks": [
        { "command": ".openhands/hooks/block_dangerous.sh", "timeout": 10 }
      ]
    }
  ]
}
```

---

## 3. Lifecycle Events

| Event | Config key | Fires | Can block? |
| :--- | :--- | :--- | :---: |
| `PreToolUse` | `pre_tool_use` | before tool execution | yes |
| `PostToolUse` | `post_tool_use` | after tool execution | no |
| `UserPromptSubmit` | `user_prompt_submit` | before processing a user message | yes |
| `Stop` | `stop` | when the agent attempts to finish | yes |
| `SessionStart` | `session_start` | conversation begins | no |
| `SessionEnd` | `session_end` | conversation ends | no |

> The config file uses the `snake_case` column; the upstream documentation
> names the events in the first column. The bundled dispatcher accepts either
> spelling, so `dispatch post_tool_use` and `dispatch PostToolUse` behave
> identically — including the part that matters, which is that neither can
> block.
>
> `pre_tool_use` and `post_tool_use` are attested in the config example above;
> the other four config keys apply the documented `snake_case` convention to
> the documented event names and have not been observed in a live session.

---

## 4. stdin Payload

Hook scripts receive a JSON object containing `event_type`, `tool_name`,
`tool_input`, `session_id`, and `working_dir`. Environment variables including
`OPENHANDS_PROJECT_DIR` and `OPENHANDS_TOOL_NAME` are also set.

---

## 5. Blocking Contract

* **Exit Code `0`**: success — the operation proceeds.
* **Exit Code `2`**: block — the operation is denied.
* A hook may additionally print JSON on `stdout` to carry a reason, and the
  `decision` field can override the exit code:

  ```json
  { "decision": "deny", "reason": "rm -rf commands are blocked for safety" }
  ```

  `reason` is displayed to the user.

Only the three blockable events above can deny an action; the rest are
observational.

---

## 6. Shipped template

`examples/openhands_hooks.json` wires the three events captain-hook guards.
Copy it to `.openhands/hooks.json` and replace `<CAPTAIN_HOOK>` with the
absolute invocation — see [`../../README-INSTALL.md`](../../README-INSTALL.md).

---

## 7. Corrections made 2026-07-26

This file previously described "Action Interceptors" registered as Python
middleware on an event stream, configured through `config.toml`, blocking via
`ActionRejectionException` or `HookResult(blocked=True)`, and intercepting
`CmdRunAction` / `FileEditAction`. **None of those names appear in the
OpenHands documentation.** They have been replaced with the documented
`.openhands/hooks.json` contract above.

No runtime testing against a live OpenHands install was performed; every claim
here is documentation-based.
