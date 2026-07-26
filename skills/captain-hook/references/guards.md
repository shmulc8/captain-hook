# Security & Safety Guards Reference (`references/guards.md`)

This document details the built-in policy rules enforced by `captain-hook`.

---

## 1. Secret Scanner Guard (`secret_scanner`)

Enforced during `PrePrompt`, `PreCommand`, `PreToolUse`, `pre_user_prompt`.

### Blocked Regex Patterns:

Generated from `SECRET_PATTERNS` in `scripts/captain_hook.py` — edit there, then run `python3 scripts/sync_patterns.py`.

<!-- BEGIN:SECRET_PATTERNS -->
* **AWS Access Key**: `\bAKIA[0-9A-Z]{16}\b`
* **GitHub Personal Access Token**: `(?i)ghp_[0-9a-zA-Z]{36}`
* **GitHub OAuth Access Token**: `(?i)gho_[0-9a-zA-Z]{36}`
* **GitLab Personal Access Token**: `(?i)glpat-[0-9a-zA-Z\-]{20}`
* **Private Key**: `-----BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY-----`
* **OpenAI API Key**: `(?i)\bsk-(?!ant-)(proj-|svcacct-|admin-)?[a-zA-Z0-9_]{20,}[a-zA-Z0-9_\-]{12,}`
* **Anthropic API Key**: `(?i)sk-ant-[a-zA-Z0-9\-]{40,}`
<!-- END:SECRET_PATTERNS -->

---

## 2. Command Sandbox Guard (`command_sandbox`)

Enforced during `PreCommand`, `beforeShellExecution`, `pre_run_command`, `PreToolUse`.

### Blocked Command Patterns:
* `rm -rf /` or `rm -rf ~` or `rm -rf *`
* `mkfs` or `dd if=`
* `git push --force`
* `chmod -R 777`
* `chown -R root`

---

## 3. Symlink Guard (`symlink_guard`)

Enforced during `PreWrite`, `beforeReadFile`, `pre_write_code`.

### Behavior:
* Checks if `path` exists and returns `islink(path) == True`.
* Refuses writes through symlinks pointing outside the repository boundaries to prevent out-of-tree file clobbering.

---

## 4. Auto-Formatter Guard (`auto_formatter`)

Enforced during `PostWrite`, `afterFileEdit`, `post_write_code`, `PostToolUse`.

### Behavior:
* Runs `prettier --write <path>` for JS/TS/JSX/TSX/JSON files if `npx` is available.
* Runs `ruff format <path>` for Python files if `ruff` is available.
