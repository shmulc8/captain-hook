# Universal AI Agent Hook Specification (`captain-hook` v1.0)

## Overview

`captain-hook` defines a **Universal Event Mapping Standard** for lifecycle hooks across AI coding agents. While agent vendors implement different configuration filenames, JSON payloads, and event identifiers, `captain-hook` normalizes them into a single coherent interface for security policies, code formatters, and audit logging.

---

## 1. Canonical Hook Event Standard

`captain-hook` maps vendor-specific events into 8 canonical lifecycle events:

| Canonical Event | Event Description | Typical Input Payload |
| :--- | :--- | :--- |
| `PrePrompt` | Intercepts user prompt before sending to LLM model | `{ "prompt": "...", "session_id": "..." }` |
| `PreWrite` | Intercepts file creation, modification, or deletion | `{ "path": "...", "content": "...", "diff": "..." }` |
| `PostWrite` | Fires after a file modification has been saved | `{ "path": "...", "bytes_written": N }` |
| `PreCommand` | Intercepts terminal command execution | `{ "command": "...", "cwd": "..." }` |
| `PostCommand` | Fires after terminal command execution completes | `{ "command": "...", "exit_code": N, "output": "..." }` |
| `PreMCP` | Intercepts Model Context Protocol tool execution | `{ "server": "...", "tool": "...", "args": {} }` |
| `PostMCP` | Fires after MCP tool execution finishes | `{ "server": "...", "tool": "...", "result": {} }` |
| `SessionEnd` | Fires when an agent task, session, or turn finishes | `{ "status": "completed" \| "error", "summary": "..." }` |

---

## 2. Universal Exit Code Protocol

To ensure consistent policy enforcement across agents, `captain-hook` scripts and dispatches adhere to standard exit codes:

* **`Exit Code 0` (ALLOW)**: Action permitted. Handlers may output diagnostic text or log metrics to stdout.
* **`Exit Code 1` (ERROR)**: Fatal hook execution error. The hook script failed internally (e.g. syntax error or missing dependency).
* **`Exit Code 2` (BLOCK / REJECT)**: Policy violation. The action is **BLOCKED**. The hook MUST print the rejection reason to `stderr`, which the host agent displays to the user or feeds back into the AI context.

---

## 3. Comprehensive Agent Capability Matrix

`captain-hook` targets 10 major AI coding agent ecosystems:

| AI Coding Agent | Config File / Path | Pre-Hook Blocking | Post-Hook Triggers | Config Schema Format |
| :--- | :--- | :---: | :---: | :--- |
| **Claude Code** | `~/.claude/settings.json`<br>`.claude/settings.json` | ✅ (`PreToolUse`, Exit Code > 0) | ✅ (`PostToolUse`, `Stop`) | `JSON` (`hooks` object) |
| **Cursor AI** | `~/.cursor/hooks.json`<br>`.cursor/hooks.json` | ✅ (Exit Code > 0) | ✅ (`afterFileEdit`, `stop`) | `JSON` (`version: 1`, `hooks`) |
| **Windsurf (Cascade)** | `~/.codeium/windsurf/hooks.json`<br>`.windsurf/hooks.json` | ✅ (**Exit Code 2**) | ✅ (`post_write_code`, `post_run_command`) | `JSON` (`hooks` object) |
| **Antigravity (AGY)** | `hooks/prevent.py`<br>`skills/` | ✅ (Exit Code 2 / Exception) | ✅ (Post-pass analysis) | Python script / CLI flags |
| **Aider** | `.aider.conf.yml`<br>`~/.aider.conf.yml` | ✅ (`lint-cmd`, `test-cmd`) | ✅ (`auto-lint`, `auto-test`) | `YAML` (`lint-cmd: ...`) |
| **Continue CLI (`cn`)** | `~/.continue/settings.json` | ✅ (**Exit Code 2**) | ✅ (`TaskCompleted`) | `JSON` (17 CLI events) |
| **Roo Code / Cline** | `.clinerules`<br>`.roomodes` | ✅ (Custom tool guards) | ✅ (Mode hooks) | Markdown / JSON |
| **OpenHands** | `config.toml`<br>Runtime Interceptors | ✅ (Action Interceptor) | ✅ (Observation Listener) | TOML / Event Stream |
| **GitHub Copilot** | `.github/copilot-instructions.md`<br>`.git/hooks/pre-commit` | ✅ (Git hook wrapper) | ✅ (Commit verification) | Markdown / Bash |
| **Amazon Q** | `.amazonq/rules` | ✅ (Rule guards) | ✅ (Post-check) | JSON / YAML |

---

## 4. Vendor Configuration Mappings

### Cursor (`.cursor/hooks.json`)
```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [ { "command": "captain-hook dispatch PrePrompt" } ],
    "beforeShellExecution": [ { "command": "captain-hook dispatch PreCommand" } ],
    "beforeMCPExecution": [ { "command": "captain-hook dispatch PreMCP" } ],
    "beforeReadFile": [ { "command": "captain-hook dispatch PreRead" } ],
    "afterFileEdit": [ { "command": "captain-hook dispatch PostWrite" } ],
    "stop": [ { "command": "captain-hook dispatch SessionEnd" } ]
  }
}
```

### Windsurf (`.windsurf/hooks.json`)
```json
{
  "hooks": {
    "pre_user_prompt": [ { "command": "captain-hook dispatch PrePrompt" } ],
    "pre_write_code": [ { "command": "captain-hook dispatch PreWrite" } ],
    "post_write_code": [ { "command": "captain-hook dispatch PostWrite" } ],
    "pre_run_command": [ { "command": "captain-hook dispatch PreCommand" } ],
    "post_run_command": [ { "command": "captain-hook dispatch PostCommand" } ],
    "pre_mcp_tool_use": [ { "command": "captain-hook dispatch PreMCP" } ],
    "post_mcp_tool_use": [ { "command": "captain-hook dispatch PostMCP" } ]
  }
}
```

### Claude Code (`.claude/settings.json`)
```json
{
  "hooks": {
    "UserPromptSubmit": [ { "command": "captain-hook dispatch PrePrompt" } ],
    "PreToolUse": [ { "command": "captain-hook dispatch PreToolUse" } ],
    "PostToolUse": [ { "command": "captain-hook dispatch PostToolUse" } ],
    "Stop": [ { "command": "captain-hook dispatch SessionEnd" } ]
  }
}
```

### Aider (`.aider.conf.yml`)
```yaml
auto-lint: true
lint-cmd: "captain-hook dispatch PostWrite"
auto-test: true
test-cmd: "captain-hook dispatch TestGate"
```

---

## 5. Security & Safety Invariants

1. **Fail-Closed for Security Guards**: Critical safety policies (e.g. `symlink-guard`, `secret-scanner`) exit with Code 2 on any unresolvable error to prevent unsafe mutations.
2. **Fail-Open for Performance Formatters**: Non-critical formatters exit 0 on minor issues to avoid blocking developer flow.
3. **No Unbounded Loops**: All hooks must complete execution within 5 seconds.
