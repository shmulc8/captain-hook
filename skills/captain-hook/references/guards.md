# Security & Safety Guards Reference (`references/guards.md`)

This document details the built-in policy rules enforced by `captain-hook`.

---

## 1. Secret Scanner Guard (`secret_scanner`)

Enforced during `PrePrompt`, `PreCommand`, `PreToolUse`, `pre_user_prompt`.

> Not enforced on post-* events: the action has already happened, so a block is
> not possible. A secret detected there is reported as a warning instead. On
> Claude Code's `PostToolUse` the warning exits `2` — which still blocks
> nothing there (the tool already ran) but is the only exit code that shows
> `stderr` to the model, so the agent that just wrote the key is told about it.

### Blocked Regex Patterns:

Generated from `SECRET_PATTERNS` in `scripts/captain_hook.py` — edit there, then run `python3 skills/captain-hook/scripts/sync_patterns.py`.

<!-- BEGIN:SECRET_PATTERNS -->
* **AWS Access Key**: `\bAKIA[0-9A-Z]{16}\b`
* **GitHub Personal Access Token**: `(?i)ghp_[0-9a-zA-Z]{36}`
* **GitHub OAuth Access Token**: `(?i)gho_[0-9a-zA-Z]{36}`
* **GitLab Personal Access Token**: `(?i)glpat-[0-9a-zA-Z\-]{20}`
* **Private Key**: `-----BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY-----`
* **OpenAI API Key**: `(?i)\bsk-(?:(?:proj|svcacct|admin)-[a-zA-Z0-9_\-]{40,}|(?!ant-)[a-zA-Z0-9]{32,})`
* **Anthropic API Key**: `(?i)sk-ant-[a-zA-Z0-9\-]{40,}`
<!-- END:SECRET_PATTERNS -->

---

## 2. Dangerous Command Denylist (`command_denylist`)

Enforced during `PreCommand`, `beforeShellExecution`, `pre_run_command`, `PreToolUse`.

> Not enforced on post-* events: the command has already run, so a block is not
> possible.

### Blocked Command Patterns:
* `rm` carrying `-r`, `-R`, or `-f` against `/`, `~`, or `*` — one flag is
  enough, since `rm -f ~/.ssh/id_rsa` needs no `-r` to be irreversible. Long
  flags and a `--` separator are covered.
* `mkfs`, or `dd if=` against any target
* `git push --force` or `git push -f` — but **not** `--force-with-lease`
* `chmod` making a tree world-writable, in either argument order, octal or symbolic
* `chown -R root`

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

## 3. Path-Escape Guard (`symlink_guard`)

Enforced during `PreWrite`, `PreRead`, `beforeReadFile`, `pre_read_code`, `pre_write_code`.

> Not enforced on post-* events: the write has already happened, so a block is
> not possible.

### Behavior:
* Resolves the target path (and every parent component) with `os.path.realpath`, then checks it is under the repository root.
* Blocks writes that resolve outside the repo, including new files created through a symlinked directory.
* Allows symlinks that stay inside the repository — a link is not by itself a violation.
* Repository root is the nearest ancestor containing `.git`, searched from the
  `cwd` the payload carries when the host supplies one (Cursor's `cwd`,
  Windsurf's `tool_info.cwd`) and from the hook process's own working directory
  otherwise. Hooks are not guaranteed to run with the repository as their
  working directory, and the wrong root both blocks in-repo paths and looks for
  `.captain-hook.json` in the wrong place. Falls back to that directory outside
  a repo.
* A **relative** path in the payload is measured from the working directory the
  payload carries — the agent's, not the hook process's. The host chooses where
  to launch the hook; measuring the root from one directory and the path from
  another is how `../x` reads as in-repo while the agent writes it outside.

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
* Only ever runs against a path inside the repository, and the
  `node_modules/.bin` walk stops at the repository root — a stray `npm install`
  in `$HOME` must not put an executable in this hook's path.
* The formatter is pointed at the path resolved the same way the path-escape
  guard resolves it — from the payload's working directory (guard 3). Resolving
  it a second time from the hook process's own would let the guard clear the
  in-repo file while the formatter rewrote a same-named file beside wherever the
  host launched the hook.
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
  "allow_commands": ["^rm -rf ~/\\.cache/myapp/?$"]
}
```

Anchor `allow_commands` entries. `rm -rf ./build` needs no entry — a relative
target is not on the denylist to begin with — so an entry that exempts nothing
reads as protection that was never there.

- Globs are matched against the path **relative to the repository root**, and
  also against the absolute path.
- `*` does **not** cross a `/`. `tests/fixtures/*.json` exempts that one
  directory, not the subtree under it; write `tests/fixtures/**` when a whole
  subtree is what you mean. An override that reads as one directory must not
  silently cover everything beneath it.
- `**/` matches whole directory components, as in `.gitignore`.
  `**/fixtures/*.json` covers `fixtures/a.json` and `deep/fixtures/a.json`, and
  does **not** cover `myfixtures/a.json` — a directory whose name merely ends
  the same way is a different directory.
- `allow_commands` takes regexes, not globs — deliberately, because commands
  are matched by regex everywhere else in this script. An invalid regex is
  reported and ignored rather than crashing the hook.
- An `allow_commands` entry exempts **the text the denylist matched**, not the
  whole command line. Allowing your release script's `git push --force` does
  not also allow the `rm -rf ~/` someone chains onto it.
- A malformed or unreadable config emits a `Warning:` and is treated as empty.
  **All guards stay on.** A config parse error must never become a global
  disable. The same applies to a key with the wrong value type: `"ignore_paths":
  "vendor/**"` (a string where a list belongs) is reported and ignored, because
  iterating it would test every guard against its individual characters — one
  of which is `*`.
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
