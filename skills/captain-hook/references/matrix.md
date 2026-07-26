# Executable Lifecycle Hooks Matrix (`references/matrix.md`)

This document maps canonical lifecycle events to vendor-native **Executable Hook Systems** across AI coding agents. Non-executable prompt files or rules files are explicitly excluded.

---

## 1. Executable Hook Mapping Table

The **Git Hooks** column is not an AI coding agent — it is included because a git
`pre-commit` hook is the fallback gate for every agent that cannot block on its
own.

| Canonical Event | Cursor AI | Windsurf (Cascade) | Claude Code | Antigravity (AGY) | Aider AI | Git Hooks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`PrePrompt`** | `beforeSubmitPrompt` | `pre_user_prompt` | `UserPromptSubmit` | `PreInvocation` | N/A | Pre-commit |
| **`PreWrite`** | `beforeReadFile` | `pre_write_code` | `PreToolUse` (`Edit`/`Write`) | `PreToolUse` (matcher `write_file` / `edit_file`) | N/A | Pre-commit |
| **`PostWrite`** | `afterFileEdit` | `post_write_code` | `PostToolUse` (`Edit`/`Write`) | `PostToolUse` (matcher `write_file` / `edit_file`) | `lint-cmd` (post-edit) | Post-commit |
| **`PreCommand`** | `beforeShellExecution` | `pre_run_command` | `PreToolUse` (`Bash`) | `PreToolUse` (matcher `run_command`) | N/A | Pre-commit |
| **`PostCommand`** | N/A | `post_run_command` | `PostToolUse` (`Bash`) | `PostToolUse` (matcher `run_command`) | N/A | Post-commit |
| **`PreMCP`** | `beforeMCPExecution` | `pre_mcp_tool_use` | `PreToolUse` (MCP) | `PreToolUse` (MCP matcher) | N/A | N/A |
| **`PostMCP`** | N/A | `post_mcp_tool_use` | `PostToolUse` (MCP) | `PostToolUse` (MCP matcher) | N/A | N/A |
| **`SessionEnd`** | `stop` | `post_cascade_response` | `Stop` / `SessionEnd` | `Stop` | `test-cmd` (post-edit) | Post-commit |

> **Continue CLI is not listed.** Its hook system could not be verified against
> any official documentation on 2026-07-26 — see
> [`specs/continue.md`](specs/continue.md) for the URLs checked. A column of
> guessed event names is worse than no column.
>
> **Aider** appears with only its two real hooks. `lint-cmd` and `test-cmd` run
> *after* an edit, so Aider cannot gate a `Pre*` event; the previous entries
> ("Pre-Chat Hook", "Pre-exec Hook", "MCP Proxy Hook") had no upstream basis.
>
> **OpenHands** has a real executable hook system (`.openhands/hooks.json`) and
> is not yet mapped here — see [`specs/openhands_devin.md`](specs/openhands_devin.md).

---

## 2. Exit Code Semantics by Agent

Exit `0` allows, everywhere. Exit `1` — and every other non-zero code that is
not `2` — is a **non-blocking hook error** on every agent in this table: the
host surfaces the message and **proceeds with the action**. A hook that raises
an unhandled exception exits `1` and therefore fails **open**.

Exit `2` is the block signal, but only where the host is still able to act:

| Agent | Exit 2 blocks? | Fail-open on crash? |
| :--- | :--- | :--- |
| **Claude Code** | Only on gate events — `PreToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `PreCompact` among them. Not on `PostToolUse`, `SessionStart`, `SessionEnd`, or `Notification` | Yes — non-2 codes proceed |
| **Cursor** | Yes, equivalent to `permission: "deny"` | **Yes by default** — set `failClosed: true` per hook to fail closed |
| **Windsurf** | Only on the five `pre_*` hooks | Yes — other codes proceed |
| **Antigravity** | **No** — decide via `{"decision": "deny"}` on stdout | See its spec |

---

## 3. Agents excluded from the matrix above

These agents have no executable hook system, so there is nothing to map to a
canonical event. Their specs cover what they *do* offer:

| Agent | Mechanism | Spec |
| :--- | :--- | :--- |
| Aider AI | `lint-cmd` / `test-cmd` feedback loop, post-edit only | [spec](specs/aider.md) |
| Roo Code / Cline | `.clinerules`, `.roomodes` mode definitions | [spec](specs/roo_cline.md) |
| GitHub Copilot | `.github/copilot-instructions.md` + git hooks | [spec](specs/copilot.md) |
| Amazon Q | `.amazonq/rules/*.md` Markdown context | [spec](specs/amazon_q.md) |
| Continue CLI (`cn`) | unverified — no upstream hooks documentation found | [spec](specs/continue.md) |

**OpenHands** does have an executable hook system (`.openhands/hooks.json`, exit
`2` blocks) and is neither excluded nor yet mapped to canonical events — see
[its spec](specs/openhands_devin.md).
