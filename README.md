# 🪝 `captain-hook`

[![Verify](https://github.com/shmulc8/captain-hook/actions/workflows/verify.yml/badge.svg)](https://github.com/shmulc8/captain-hook/actions/workflows/verify.yml)

> **The Universal Agent Skill & Claude Plugin for Navigating AI Coding Agent Hooks.**

![Captain Hook AI Agent Infinity Gauntlet](assets/captain_hook_gauntlet.jpg)

`captain-hook` is an open-source Agent Skill and Claude Plugin that equips AI agents and developers to command, write, scaffold, and configure native lifecycle hooks across AI coding agents — **5 of them with executable hooks that can actually block an action** (Claude Code, Cursor, Windsurf, OpenHands, Antigravity), plus rules-file specs for the 4 that can only be asked nicely (Aider, Roo Code, Copilot, Amazon Q) and an honest not-verified entry for Continue CLI.

---

## ⛵ Navigating the High Seas of AI Agent Hooks

- **The Pain Point**: Lifecycle hooks are a captain's most powerful weapon for deterministic security guardrails, dangerous-command denylisting, and quality gates in AI coding. However, unlike open skill standards, **every AI coding agent uses completely different, constantly changing hook specifications**, configuration schemas, JSON payload shapes, and exit code semantics.
- **The Solution**: `captain-hook` chart-maps all this fragmented information into one unified handbook, scaffolding library, and verification suite—saving developers and AI agents from drifting lost in the open sea of documentation for each individual agent.

---

## ⚓ Boarding the Ship (Installation & Setup)

### 1. Install as a Claude Plugin

Install `captain-hook` directly into Claude Code or compatible AI agent environments. This repository is its own plugin marketplace, so register it first, then install:

```bash
/plugin marketplace add shmulc8/captain-hook
/plugin install captain-hook@captain-hook
```

### 2. Manual Clone & Local Verification

```bash
git clone https://github.com/shmulc8/captain-hook.git
cd captain-hook

# Run local hook verification suite before setting sail
./skills/captain-hook/scripts/verify_hooks.sh
```

---

## 🏴‍☠️ What Lies in the Treasure Chest

- 📚 **Handbook & Guide (`SKILL.md`)**: Complete instructions on hook fundamentals, event lifecycles, stdin/stdout JSON contracts, and exit code blocking protocols (`0` ALLOW, `2` BLOCK).
- 🧭 **10-Agent Specifications (`references/specs/`)**: each spec carries a `> Source:` line naming the upstream URL and the date it was last checked against it. The verification suite fails if one is missing.
- 🗡️ **Production Hook Recipes (`references/recipes.md`)**: Copy-pasteable standalone Python, Bash, and Node.js hook scripts for Secret Scanning, Dangerous Command Denylisting, Path-Escape Guards, Auto-Formatting, and Test Gates.
- 📄 **Scaffolding Templates (`examples/`)**: Valid starter configuration files for `.cursor/hooks.json`, `.windsurf/hooks.json`, `.claude/settings.json`, `.aider.conf.yml`, and `.agents/hooks.json`.
- 🛠️ **Local Verification Suite (`skills/captain-hook/scripts/verify_hooks.sh`)**: Runs the bundled dispatcher against the sample payloads and lints the shipped docs and templates. It verifies *this skill*, not your own hook scripts — to test yours, pipe a fixture from `examples/payloads/` into them directly.

---

## 🧭 Captain's Navigation Chart

### ⚔️ Agents with executable hooks (can block an action)

| AI Coding Agent | Config File | How it blocks | Specification Guide |
| :--- | :--- | :--- | :--- |
| **Claude Code** | `.claude/settings.json` | exit `2`, on gate events only — `PreToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `PreCompact` | [Claude Code Hooks Spec](skills/captain-hook/references/specs/claude_code.md) |
| **Cursor AI** | `.cursor/hooks.json` | exit `2` or `{"permission":"deny"}` — **fail-open unless `failClosed: true`** | [Cursor Hooks Spec](skills/captain-hook/references/specs/cursor.md) |
| **Windsurf (Cascade)** | `.windsurf/hooks.json` | exit `2`, the five `pre_*` hooks only | [Windsurf Hooks Spec](skills/captain-hook/references/specs/windsurf.md) |
| **OpenHands** | `.openhands/hooks.json` | exit `2`, or `{"decision":"deny"}` on stdout | [OpenHands Hooks Spec](skills/captain-hook/references/specs/openhands_devin.md) |
| **Antigravity (AGY)** | `.agents/hooks.json` | `{"decision":"deny"}` on stdout — **not** exit codes — payload extraction is documentation-derived, not yet run against a live session | [Antigravity Spec](skills/captain-hook/references/specs/antigravity.md) |

### 📜 Agents with rules and instruction files (advisory only — cannot block)

| AI Coding Agent | Config File | Enforcement | Specification Guide |
| :--- | :--- | :--- | :--- |
| **Aider AI** | `.aider.conf.yml` | none — `lint-cmd` / `test-cmd` run *after* the edit and feed errors back | [Aider Spec](skills/captain-hook/references/specs/aider.md) |
| **Roo Code / Cline** | `.clinerules`, `.roomodes` | none — model context and permission groups | [Roo Code Spec](skills/captain-hook/references/specs/roo_cline.md) |
| **GitHub Copilot** | `.github/copilot-instructions.md` | none in-agent; use a git `pre-commit` hook | [Copilot Spec](skills/captain-hook/references/specs/copilot.md) |
| **Amazon Q** | `.amazonq/rules/*.md` | none — model context | [Amazon Q Project Rules](skills/captain-hook/references/specs/amazon_q.md) |

### ❓ Unverified

| AI Coding Agent | Status | Specification Guide |
| :--- | :--- | :--- |
| **Continue CLI (`cn`)** | No official hooks documentation could be located on 2026-07-26. Nothing is claimed. | [Continue CLI — unverified](skills/captain-hook/references/specs/continue.md) |

> An advisory rule file asks the model not to do something. An executable hook
> stops it. If you need a guarantee, you need the first table — or a git hook /
> CI gate outside the agent entirely.

---

## 🗺️ Ship Manifest & Repository Layout

```text
captain-hook/
├── README.md                            # Project overview & hero artwork
├── .claude-plugin/
│   ├── plugin.json                      # Claude Plugin manifest
│   └── marketplace.json                 # Marketplace manifest (makes the repo installable)
├── assets/
│   └── captain_hook_gauntlet.jpg        # Hero artwork
└── skills/captain-hook/                 # 📚 Agent Skill Handbook & Specifications
    ├── SKILL.md                         # Main skill manual
    ├── scripts/
    │   ├── captain_hook.py              # Standalone reference dispatcher
    │   └── verify_hooks.sh              # Local verification runner
    ├── examples/                        # Starter configuration templates & mock payloads
    │   ├── cursor_hooks.json
    │   ├── windsurf_hooks.json
    │   ├── claude_settings.json
    │   ├── aider_conf.yml
    │   └── payloads/
    └── references/                      # Deep-dive guides & official specs
        ├── matrix.md
        ├── recipes.md
        ├── security_rules.md
        ├── debugging.md
        ├── ci_cd_integration.md
        └── specs/                       # 10 Official Agent Specs
```

---

## 📜 License

MIT License © 2026 shmulc8
