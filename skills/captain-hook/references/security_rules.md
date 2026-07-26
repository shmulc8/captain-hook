# Security & Policy Rule Catalog (`references/security_rules.md`)

This catalog provides modular, production-ready security rules and quality policies that can be added to your agent hooks.

---

## 1. Secret & Credentials Guard (`secret_guard`)

Prevents accidental exposure of API keys, database credentials, or private keys in prompts, shell commands, or source code edits.

### Covered Patterns:

Generated from `SECRET_PATTERNS` in `scripts/captain_hook.py` — edit there, then run `python3 scripts/sync_patterns.py`.

<!-- BEGIN:SECRET_PATTERNS -->
- **AWS Access Key**: `\bAKIA[0-9A-Z]{16}\b`
- **GitHub Personal Access Token**: `(?i)ghp_[0-9a-zA-Z]{36}`
- **GitHub OAuth Access Token**: `(?i)gho_[0-9a-zA-Z]{36}`
- **GitLab Personal Access Token**: `(?i)glpat-[0-9a-zA-Z\-]{20}`
- **Private Key**: `-----BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY-----`
- **OpenAI API Key**: `(?i)\bsk-(?!ant-)(proj-|svcacct-|admin-)?[a-zA-Z0-9_]{20,}[a-zA-Z0-9_\-]{12,}`
- **Anthropic API Key**: `(?i)sk-ant-[a-zA-Z0-9\-]{40,}`
<!-- END:SECRET_PATTERNS -->

---

## 2. Destructive Command Interceptor (`command_sandbox`)

Blocks execution of irreversible shell commands before they run in your local shell or terminal container.

### Blocked Commands:
- `rm -rf /` or `rm -rf ~` or `rm -rf *`
- `mkfs` or `dd if=`
- `git push --force`
- `chmod -R 777`
- `chown -R root`

---

## 3. Out-of-Tree Symlink Guard (`symlink_guard`)

Prevents AI agents from clobbering or overwriting files outside the repository boundary through symlink redirection.

---

## 4. MCP Tool Governance (`mcp_governance`)

Restricts execution of high-risk Model Context Protocol (MCP) tools (e.g. database schema deletion, production API deployments).

---

## 5. Turn Audit & Observability Logger (`audit_logger`)

Appends every agent action, tool invocation, and decision result to `.hooks/audit.jsonl` for compliance auditing.
