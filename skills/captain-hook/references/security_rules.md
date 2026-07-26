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
- **OpenAI API Key**: `(?i)\bsk-(?:(?:proj|svcacct|admin)-[a-zA-Z0-9_\-]{40,}|(?!ant-)[a-zA-Z0-9]{32,})`
- **Anthropic API Key**: `(?i)sk-ant-[a-zA-Z0-9\-]{40,}`
<!-- END:SECRET_PATTERNS -->

---

## 2. Dangerous Command Denylist (`command_denylist`)

Blocks a fixed list of irreversible shell commands before they run.

### Blocked Commands:
- `rm` carrying `-r`, `-R`, or `-f` against `/`, `~`, or `*` — one flag is
  enough, since `rm -f ~/.ssh/id_rsa` needs no `-r` to be irreversible. Long
  flags and a `--` separator are covered.
- `mkfs`, or `dd if=` against any target
- `git push --force` or `git push -f` — but **not** `--force-with-lease`
- `chmod` making a tree world-writable, in either argument order, octal or symbolic
- `chown -R root`

### Known limits — read before relying on this

This is a **regex denylist over a command string**, not a sandbox. It does not
parse shell syntax, so it is bypassed by ordinary constructs:

| Command | Blocked? |
| :--- | :---: |
| `rm -rf /` | yes |
| `rm -r -f /` | yes — split flags |
| `rm -rf "/"` | yes — quoted target |
| `rm -f ~/.ssh/id_rsa` | yes — a single destructive flag counts |
| `rm -rf -- /` | yes — `--` end-of-options separator |
| `rm --recursive --force /` | yes — long flags |
| `git push -f origin main` | yes — short flag |
| `git push --force-with-lease` | **no, deliberately** — the safe form |
| `chmod 777 -R /` | yes — order-insensitive |
| `chmod -R a+rwx /` | yes — symbolic modes granting write |
| `dd if=/dev/zero of=/dev/sda` | yes |
| `rm -rf $HOME` | no — variable expansion |
| `cd / && rm -rf .` | no — relative target |
| `$(echo rm) -rf /` | no — command substitution |
| `sudo rm -rf /` prefixed by any wrapper | no — only the literal command text is matched |
| `curl … \| sh` | no — not on the list at all; the denylist is five rules, not a policy engine |

It stops the accident — a model emitting a literal destructive command — which
is the common case and worth stopping. It does not stop an adversary, and it is
not a containment boundary.

For an actual guarantee, put the agent somewhere it cannot do the damage:
a container or VM, a non-privileged user, a repository checkout with no
credentials, and branch protection on the remote. A hook is a seatbelt, not
a roll cage.

---

## 3. Out-of-Tree Path-Escape Guard (`symlink_guard`)

Prevents AI agents from clobbering files outside the repository boundary. The
target path is resolved with `os.path.realpath` — every component, parent
directories included, and paths that do not exist yet — and blocked if it lands
outside the repository root. That covers a new file written through a symlinked
directory, which a plain "is this a symlink?" test misses.

Symlinks that stay inside the repository are allowed: a link is not by itself a
violation. The repository root is the nearest ancestor containing `.git`.

**Limitation**: POSIX only. Windows junctions and reparse points are not handled.

---

## 4. MCP Tool Governance (`mcp_governance`)

Restricts execution of high-risk Model Context Protocol (MCP) tools (e.g. database schema deletion, production API deployments).

---

## 5. Turn Audit & Observability Logger (`audit_logger`)

Appends every agent action, tool invocation, and decision result to `.hooks/audit.jsonl` for compliance auditing.
