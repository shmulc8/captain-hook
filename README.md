# 🪝 `captain-hook`

> **Universal Lifecycle Hooks, Security Guardrails, and Quality Gates for AI Coding Agents.**

![Captain Hook AI Agent Infinity Gauntlet](assets/captain_hook_gauntlet.jpg)

`captain-hook` is an open-source Claude Plugin and Agent Skill providing exhaustive specifications, executable hook scripts, and security guardrails for **10+ major AI coding agents** (Claude Code, Cursor, Windsurf, Aider, Antigravity, Continue, Roo Code, OpenHands, Copilot, Amazon Q).

---

## 📦 Installation & Setup

### 1. Install as a Claude Plugin

To install `captain-hook` directly inside Claude Code or compatible AI plugin environments:

```bash
/plugin install shmulc8/captain-hook
```

### 2. Manual Clone & Verification

```bash
git clone https://github.com/shmulc8/captain-hook.git
cd captain-hook

# Run local hook verification suite
./skills/captain-hook/scripts/verify_hooks.sh
```

---

## 🌟 Features & Guardrails

- 🔒 **Secret & Token Leak Scanner**: Intercepts AWS keys, GitHub PATs, OpenAI/Anthropic API keys, and SSH Private Keys in prompts, file edits, or terminal commands.
- 🛡️ **Command Sandbox**: Blocks destructive commands (`rm -rf`, `git push --force`, `dd`, `chmod 777`) before execution.
- 🔗 **Symlink Write Guard**: Prevents out-of-tree file clobbering through symlinks.
- 🧹 **Code Auto-Formatter**: Automatically runs `prettier` or `ruff` post-write.
- 🧪 **Verification Runner**: Test project hook scripts locally against mock `stdin` JSON payloads before going live.

---

## 🌐 Complete 10-Agent Specification Library

`captain-hook` includes self-contained, official specification guides cross-referenced with live documentation sources:

| AI Coding Agent | Config File Location | Blocking Exit Code | Specification Guide |
| :--- | :--- | :---: | :--- |
| **Cursor AI** | `.cursor/hooks.json` | Exit Code 2 | [Cursor Hooks Spec](skills/captain-hook/references/specs/cursor.md) |
| **Windsurf (Cascade)** | `.windsurf/hooks.json` | **Exit Code 2** | [Windsurf Hooks Spec](skills/captain-hook/references/specs/windsurf.md) |
| **Claude Code** | `.claude/settings.json` | **Exit Code 2** | [Claude Code Hooks Spec](skills/captain-hook/references/specs/claude_code.md) |
| **Antigravity (AGY)** | `hooks/prevent.py` | Exit Code 2 | [Antigravity Spec](skills/captain-hook/references/specs/antigravity.md) |
| **Aider AI** | `.aider.conf.yml` | Non-zero | [Aider Hooks Spec](skills/captain-hook/references/specs/aider.md) |
| **Continue CLI (`cn`)** | `~/.continue/settings.json` | **Exit Code 2** | [Continue CLI Spec](skills/captain-hook/references/specs/continue.md) |
| **Roo Code / Cline** | `.clinerules` | Non-zero | [Roo Code Spec](skills/captain-hook/references/specs/roo_cline.md) |
| **OpenHands / Devin** | `config.toml` | Non-zero | [OpenHands Spec](skills/captain-hook/references/specs/openhands_devin.md) |
| **GitHub Copilot** | `.github/copilot-instructions.md` | Non-zero | [Copilot Spec](skills/captain-hook/references/specs/copilot.md) |
| **Amazon Q** | `.amazonq/rules` | Non-zero | [Amazon Q Spec](skills/captain-hook/references/specs/amazon_q.md) |

---

## 📂 Repository Layout

```text
captain-hook/
├── README.md                            # Main project overview & hero artwork
├── .claude-plugin/
│   └── plugin.json                      # Claude Plugin manifest
├── assets/
│   └── captain_hook_gauntlet.jpg        # Hero artwork
└── skills/captain-hook/                 # 📚 Agent Skill Handbook & Specifications
    ├── SKILL.md                         # Standard Agent Skill manual
    ├── scripts/
    │   ├── captain_hook.py              # Standalone executable dispatcher & policy script
    │   └── verify_hooks.sh              # Automated verification runner
    ├── examples/                        # Reference configuration templates
    │   ├── cursor_hooks.json
    │   ├── windsurf_hooks.json
    │   ├── claude_settings.json
    │   ├── aider_conf.yml
    │   └── payloads/                    # Mock JSON stdin payloads
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
