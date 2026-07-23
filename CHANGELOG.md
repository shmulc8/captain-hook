# Changelog (`CHANGELOG.md`)

All notable changes to `captain-hook` will be documented in this file.

## [1.0.0] - 2026-07-24

### Added
- **Claude Plugin Integration**: `.claude-plugin/plugin.json` for one-command `/plugin install`.
- **Universal Event Dispatcher**: Executable script supporting 8 canonical events (`PrePrompt`, `PreWrite`, `PostWrite`, `PreCommand`, `PostCommand`, `PreMCP`, `PostMCP`, `SessionEnd`).
- **Security & Safety Guards**: Secret scanner (AWS, GitHub, GitLab, OpenAI, Anthropic, SSH keys), command sandboxing (`rm -rf`, `git push --force`), symlink write guard, auto-formatter (`prettier`, `ruff`).
- **10 Exhaustive Agent Specifications**: Live-verified specification guides for Cursor, Windsurf, Claude Code, Antigravity, Aider, Continue CLI, Roo Code, OpenHands, Copilot, and Amazon Q.
- **Automated Verification Suite**: `./skills/captain-hook/scripts/verify_hooks.sh` test runner.
- **Hero Artwork**: Captain Hook AI Agent Infinity Gauntlet illustration.
