# 🪝 `captain-hook`

> **The Agent Skill & Claude Plugin for writing, scaffolding, and configuring lifecycle hooks across AI coding agents.**

![Captain Hook AI Agent Infinity Gauntlet](assets/captain_hook_gauntlet.jpg)

`captain-hook` is an open-source Agent Skill and Claude Plugin that teaches AI agents and developers how to design, write, scaffold, and configure native lifecycle hooks for **10+ major AI coding agents** (Claude Code, Cursor, Windsurf, Aider, Antigravity, Continue CLI, Roo Code, OpenHands, Copilot, and Amazon Q).

---

## 📦 Installation & Setup

### 1. Install as a Claude Plugin

Install `captain-hook` directly into Claude Code or compatible AI agent environments:

```bash
/plugin install shmulc8/captain-hook
```

### 2. Manual Clone

```bash
git clone https://github.com/shmulc8/captain-hook.git
cd captain-hook

# Test your project's hook scripts using the included verification suite
./skills/captain-hook/scripts/verify_hooks.sh
```

---

## 🌟 What `captain-hook` Provides

- 📚 **Handbook & Guide (`SKILL.md`)**: Complete instructions on hook fundamentals, event lifecycles, stdin/stdout JSON contracts, and exit code blocking protocols (`0` ALLOW, `2` BLOCK).
- 🌐 **Exhaustive 10-Agent Specifications (`references/specs/`)**: Self-contained, live-verified specification guides cross-referenced with official documentation.
- 🧪 **Production Hook Recipes (`references/recipes.md`)**: Copy-pasteable standalone Python, Bash, and Node.js hook scripts for Secret Scanning, Command Sandboxing, Symlink Guards, Auto-Formatting, and Test Gates.
- 📄 **Scaffolding Templates (`examples/`)**: Valid starter configuration files for `.cursor/hooks.json`, `.windsurf/hooks.json`, `.claude/settings.json`, `.aider.conf.yml`, and `hooks/prevent.py`.
- 🛠️ **Local Verification Suite (`scripts/verify_hooks.sh`)**: Test runner script that pipes sample JSON payloads to `stdin` to test your hook scripts locally before deploying.

---

## 🌐 Complete 10-Agent Specification Library

| AI Coding Agent | Config File Location | Specification Guide |
| :--- | :--- | :--- |
| **Cursor AI** | `.cursor/hooks.json` | [Cursor Hooks Spec](skills/captain-hook/references/specs/cursor.md) |
| **Windsurf (Cascade)** | `.windsurf/hooks.json` | [Windsurf Hooks Spec](skills/captain-hook/references/specs/windsurf.md) |
| **Claude Code** | `.claude/settings.json` | [Claude Code Hooks Spec](skills/captain-hook/references/specs/claude_code.md) |
| **Antigravity (AGY)** | `hooks/prevent.py` | [Antigravity Spec](skills/captain-hook/references/specs/antigravity.md) |
| **Aider AI** | `.aider.conf.yml` | [Aider Hooks Spec](skills/captain-hook/references/specs/aider.md) |
| **Continue CLI (`cn`)** | `~/.continue/settings.json` | [Continue CLI Spec](skills/captain-hook/references/specs/continue.md) |
| **Roo Code / Cline** | `.clinerules` | [Roo Code Spec](skills/captain-hook/references/specs/roo_cline.md) |
| **OpenHands / Devin** | `config.toml` | [OpenHands Spec](skills/captain-hook/references/specs/openhands_devin.md) |
| **GitHub Copilot** | `.github/copilot-instructions.md` | [Copilot Spec](skills/captain-hook/references/specs/copilot.md) |
| **Amazon Q** | `.amazonq/rules` | [Amazon Q Spec](skills/captain-hook/references/specs/amazon_q.md) |

---

## 📂 Repository Layout

```text
captain-hook/
├── README.md                            # Project overview & hero artwork
├── .claude-plugin/
│   └── plugin.json                      # Claude Plugin manifest
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
