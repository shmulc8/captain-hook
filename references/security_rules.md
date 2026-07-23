# Security & Policy Rule Catalog (`references/security_rules.md`)

This catalog provides modular, production-ready security rules and quality policies that can be added to your agent hooks.

---

## 1. Secret & Credentials Guard (`secret_guard`)

Prevents accidental exposure of API keys, database credentials, or private keys in prompts, shell commands, or source code edits.

### Covered Patterns:
- **AWS Access Key ID**: `\bAKIA[0-9A-Z]{16}\b`
- **GitHub Personal Access Token**: `ghp_[0-9a-zA-Z]{36}`
- **GitHub OAuth Token**: `gho_[0-9a-zA-Z]{36}`
- **GitLab Token**: `glpat-[0-9a-zA-Z\-]{20}`
- **OpenAI API Key**: `sk-[a-zA-Z0-9]{48}`
- **Anthropic API Key**: `sk-ant-[a-zA-Z0-9\-]{40,}`
- **Private Keys**: `-----BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY-----`

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
