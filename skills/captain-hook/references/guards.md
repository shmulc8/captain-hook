# Security & Safety Guards Reference (`references/guards.md`)

This document details the built-in policy rules enforced by `captain-hook`.

---

## 1. Secret Scanner Guard (`secret_scanner`)

Enforced during `PrePrompt`, `PreCommand`, `PreToolUse`, `pre_user_prompt`.

> Not enforced on post-* events: the action has already happened, so a block is
> not possible. A secret detected there is reported as a warning instead.

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

## 2. Dangerous Command Denylist (`command_denylist`)

Enforced during `PreCommand`, `beforeShellExecution`, `pre_run_command`, `PreToolUse`.

> Not enforced on post-* events: the command has already run, so a block is not
> possible.

### Blocked Command Patterns:
* `rm -rf /` or `rm -rf ~` or `rm -rf *`
* `mkfs` or `dd if=`
* `git push --force`
* `chmod -R 777`
* `chown -R root`

### Known limits — read before relying on this

This is a **regex denylist over a command string**, not a sandbox. It does not
parse shell syntax, so it is bypassed by ordinary constructs:

| Command | Blocked? |
| :--- | :---: |
| `rm -rf /` | yes |
| `rm -r -f /` | yes (split flags, since the v1.1 tightening) |
| `rm -rf "/"` | yes (quoted target, same change) |
| `rm -rf $HOME` | no — variable expansion |
| `cd / && rm -rf .` | no — relative target |
| `$(echo rm) -rf /` | no — command substitution |

It stops the accident — a model emitting a literal destructive command — which
is the common case and worth stopping. It does not stop an adversary, and it is
not a containment boundary.

For an actual guarantee, put the agent somewhere it cannot do the damage:
a container or VM, a non-privileged user, a repository checkout with no
credentials, and branch protection on the remote. A hook is a seatbelt, not
a roll cage.

---

## 3. Path-Escape Guard (`symlink_guard`)

Enforced during `PreWrite`, `beforeReadFile`, `pre_write_code`.

> Not enforced on post-* events: the write has already happened, so a block is
> not possible.

### Behavior:
* Resolves the target path (and every parent component) with `os.path.realpath`, then checks it is under the repository root.
* Blocks writes that resolve outside the repo, including new files created through a symlinked directory.
* Allows symlinks that stay inside the repository — a link is not by itself a violation.
* Repository root is the nearest ancestor containing `.git`; falls back to the working directory outside a repo.

### Known limitation:
* Windows junctions and reparse points are **not** handled. `realpath` resolves them inconsistently across Python versions, so treat this guard as POSIX-only.

---

## 4. Auto-Formatter Guard (`auto_formatter`)

Enforced during `PostWrite`, `afterFileEdit`, `post_write_code`, `PostToolUse`.

### Behavior:
* Runs `prettier --write <path>` for JS/TS/JSX/TSX/JSON files **only when
  `prettier` is already installed** — resolved from `PATH` or the nearest
  `node_modules/.bin`. `npx` is deliberately not used: it downloads an unpinned
  package from the npm registry, which is a network fetch and arbitrary code
  execution inside a hook.
* Runs `ruff format <path>` for Python files when `ruff` is on `PATH`.
* Both calls are bounded by a 10-second timeout. On timeout or failure the file
  is left unformatted and a warning is written to `stderr`; the hook never fails
  the write because of a formatter.

---

## 5. Overrides (`.captain-hook.json`)

Every guard here has false positives. A repository that legitimately contains
key-shaped strings — test fixtures, a rotated-key postmortem, documentation
examples — would otherwise be unmaintainable under its own guard, and the
usual outcome is that the hook gets uninstalled. That is strictly worse than
imperfect protection.

Put a `.captain-hook.json` at the repository root. A missing file means no
overrides. Every key is optional:

| Key | Matches | Effect |
| :--- | :--- | :--- |
| `ignore_paths` | glob | Skips **all** guards for matching paths |
| `allow_secrets_in` | glob | Skips only the secret scan for matching paths |
| `allow_commands` | **regex** | Exempts matching commands from the denylist |

```json
{
  "ignore_paths": ["vendor/**"],
  "allow_secrets_in": ["tests/fixtures/*.json"],
  "allow_commands": ["^rm -rf \\./build/?$"]
}
```

- Globs are matched against the path **relative to the repository root**, and
  also against the absolute path.
- `allow_commands` takes regexes, not globs — deliberately, because commands
  are matched by regex everywhere else in this script. An invalid regex is
  reported and ignored rather than crashing the hook.
- A malformed or unreadable config emits a `Warning:` and is treated as empty.
  **All guards stay on.** A config parse error must never become a global
  disable.
- Every suppression writes a `Note:` line to `stderr` naming the path and the
  key that allowed it. An override you cannot see is an override that goes
  stale silently.
- Overrides only loosen. There is no way to add patterns from config, which
  keeps it from becoming a second, competing source of truth.

> Every override is a hole in the guard. Prefer the narrowest key that works —
> `allow_secrets_in` for a fixture directory rather than `ignore_paths` for a
> whole tree — and review this file the way you would review a firewall rule.

This repository ships its own `.captain-hook.json`, allowlisting only the
directories whose synthetic key-shaped strings are the point.
