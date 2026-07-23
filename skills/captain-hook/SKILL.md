---
name: captain-hook
description: Universal lifecycle hooks, security guardrails, and quality gates for AI coding agents (Claude Code, Cursor, Windsurf, Aider, Antigravity, Continue, and more). Use this skill whenever setting up project hooks, enforcing security guardrails, intercepting tool calls, blocking dangerous shell commands, or managing agent lifecycle events.
---

# captain-hook: Universal AI Agent Hooks & Guardrails

`captain-hook` provides a unified specification, CLI dispatcher, and security policy engine for AI coding agents.

## When to use this skill

Trigger this skill when the user asks to:
- Configure, setup, or audit hooks for any AI coding agent (Claude Code, Cursor, Windsurf, Aider, Antigravity, Continue, Roo Code, etc.).
- Add write-time guards, symlink protection, secret scanning, or command sandboxing to a project.
- Automatically format code (`prettier`, `ruff`, `black`) post-edit across AI agent turns.
- Block dangerous terminal commands (e.g. `rm -rf /`, `git push --force`) or secret leaks.

---

## 1. Quick Initialization Command

To generate native hook configuration files for all agents in the current project:

```bash
captain-hook init --agent all
```

Or initialize for a specific agent:

```bash
captain-hook init --agent cursor
captain-hook init --agent windsurf
captain-hook init --agent claude
captain-hook init --agent aider
captain-hook init --agent antigravity
```

---

## 2. Supported Agents & Native Specs

| AI Agent | Native Config File | Blocking Exit Code |
| :--- | :--- | :---: |
| **Claude Code** | `.claude/settings.json` | Non-zero |
| **Cursor AI** | `.cursor/hooks.json` | Non-zero |
| **Windsurf (Cascade)** | `.windsurf/hooks.json` | **Exit Code 2** |
| **Antigravity (AGY)** | `hooks/prevent.py` | Exit Code 2 |
| **Aider AI** | `.aider.conf.yml` | Non-zero |
| **Continue CLI (`cn`)** | `~/.continue/settings.json` | **Exit Code 2** |

Read [`references/specs.md`](references/specs.md) for detailed JSON schemas, stdin payload definitions, and exact field mappings per agent.

---

## 3. Built-in Security & Safety Policies

`captain-hook` automatically executes 4 core security policies during event dispatch:

1. **`secret_scanner`**: Intercepts AWS Access Keys, GitHub PATs, OpenAI/Anthropic API keys, and SSH Private Keys in prompts and tool inputs.
2. **`command_sandbox`**: Blocks dangerous destructive shell commands (`rm -rf /`, `git push --force`, `dd`, `chmod -R 777`).
3. **`symlink_guard`**: Prevents reading/writing through symlinks pointing outside repository boundaries.
4. **`auto_formatter`**: Automatically runs `prettier` or `ruff` on changed files after post-write events.

Read [`references/guards.md`](references/guards.md) for detailed policy configuration and custom rule definitions.

---

## 4. Universal Exit Code Protocol

When dispatching events via `captain-hook dispatch <event>`:
- **`0` (ALLOW)**: Action permitted.
- **`1` (ERROR)**: Fatal hook script execution failure.
- **`2` (BLOCK / REJECT)**: Policy violation. The host agent cancels the action and displays `stderr` to the user or AI model.
