# 🪝 `captain-hook`

> **Universal Lifecycle Hooks, Security Guardrails, and Quality Gates for AI Coding Agents.**

`captain-hook` is a unified hook specification, dispatcher, and policy engine supporting **10+ major AI coding agents** (Claude Code, Cursor, Windsurf, Aider, Antigravity, Continue CLI, Roo Code / Cline, OpenHands, GitHub Copilot, and Amazon Q).

---

## 🌟 Why `captain-hook`?

As AI coding agents proliferate, every tool introduces its own proprietary hook formats, configuration filenames, and event names. `captain-hook` provides:

1. **Universal Specification Standard (`SPEC.md`)**: A normalized 8-event lifecycle schema (`PrePrompt`, `PreWrite`, `PostWrite`, `PreCommand`, `PostCommand`, `PreMCP`, `PostMCP`, `SessionEnd`).
2. **One-Command Initialization (`captain-hook init`)**: Auto-generates native configuration files (`.cursor/hooks.json`, `.windsurf/hooks.json`, `.claude/settings.json`, `.aider.conf.yml`, `hooks/prevent.py`) for your project.
3. **Built-in Security Guards**:
   - 🔒 **Secret Scanner**: Intercepts AWS keys, GitHub PATs, OpenAI/Anthropic API keys, and private SSH keys in prompts or tool calls.
   - 🛡️ **Command Sandbox**: Blocks dangerous destructive shell commands (`rm -rf /`, `git push --force`, `dd`, `chmod -R 777`).
   - 🔗 **Symlink Guard**: Prevents reads or writes through symlinks pointing outside the repository boundaries.
   - 🧹 **Auto-Formatter**: Automatically runs `prettier` or `ruff` on code post-write.

---

## 📊 Supported Coding Agent Matrix

| AI Coding Agent | Config File Location | Hook Support | Native Hook Mechanism |
| :--- | :--- | :---: | :--- |
| **Claude Code** | `.claude/settings.json` | Native | `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop` |
| **Cursor AI** | `.cursor/hooks.json` | Native | `beforeSubmitPrompt`, `beforeShellExecution`, `afterFileEdit`, `stop` |
| **Windsurf (Cascade)** | `.windsurf/hooks.json` | Native | `pre_user_prompt`, `pre_write_code`, `post_write_code`, `pre_run_command` |
| **Antigravity (AGY)** | `hooks/prevent.py` | Native | Prevention hooks, Python/TS scanners, `--check` CI gates |
| **Aider AI** | `.aider.conf.yml` | Native | `lint-cmd`, `test-cmd`, `auto-lint`, `auto-test` |
| **Continue CLI (`cn`)** | `~/.continue/settings.json` | Native | 17 CLI event hooks, `PreToolUse`, `TaskCompleted` |
| **Roo Code / Cline** | `.clinerules` / `.roomodes` | Native | Mode rules & MCP tool interceptors |
| **OpenHands / Devin** | `config.toml` | Native | Runtime action/observation interceptors |
| **GitHub Copilot** | `.github/copilot-instructions.md` | Native | Pre-commit git hooks & Copilot extensions |
| **Amazon Q** | `.amazonq/rules` | Native | Rule guards & CLI customization hooks |

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/shmulc8/captain-hook.git
cd captain-hook
python3 -m unittest discover tests
```

### Initialize Hooks for Your Project

To generate native hook configurations for **all supported agents** in your repository:

```bash
captain-hook init --agent all
```

Or target a specific agent:

```bash
captain-hook init --agent cursor
captain-hook init --agent windsurf
captain-hook init --agent claude
captain-hook init --agent aider
captain-hook init --agent antigravity
```

---

## 🔧 CLI & Dispatcher Usage

### Universal Event Dispatch

Agents pass JSON event context to `captain-hook dispatch` over `stdin`:

```bash
echo '{"prompt": "my aws key is AKIA1234567890ABCDEF"}' | captain-hook dispatch PrePrompt
# Output: captain-hook: Blocked: Secret key pattern detected (AWS Access Key)
# Exit Code: 2 (BLOCK)
```

### Standard Exit Code Protocol

* `0`: **ALLOW** — Action permitted.
* `1`: **ERROR** — Hook script execution failure.
* `2`: **BLOCK / REJECT** — Policy violation. The host agent cancels the action and displays `stderr` to the user or AI model.

---

## 📜 Specification & Docs

Read [`SPEC.md`](SPEC.md) for the complete cross-agent technical specification, payload contracts, and security invariants.
