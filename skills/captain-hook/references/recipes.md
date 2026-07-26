# Ready-to-Use Hook Recipes (`references/recipes.md`)

This reference contains copy-pasteable, standalone hook scripts for Python, Bash, and Node.js that can be wired into any AI coding agent.

---

## Recipe 1: Secret Scanner Guard (Python)

Blocks prompts, shell commands, and file writes carrying API keys, AWS
credentials, or SSH private keys. Wire it to a **pre** event: `PrePrompt`,
`PreCommand`, `PreToolUse`, `beforeShellExecution`, or `pre_user_prompt`. On a
post event the write has already happened and exit 2 blocks nothing.

```python
#!/usr/bin/env python3
"""Secret Scanner Hook Script for AI Coding Agents."""
import sys, json, re

SECRET_PATTERNS = [
    # BEGIN:SECRET_PATTERNS
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS Access Key"),
    (re.compile(r"(?i)ghp_[0-9a-zA-Z]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"(?i)gho_[0-9a-zA-Z]{36}"), "GitHub OAuth Access Token"),
    (re.compile(r"(?i)glpat-[0-9a-zA-Z\-]{20}"), "GitLab Personal Access Token"),
    (re.compile(r"-----BEGIN (RSA|OPENSSH|EC|PGP) PRIVATE KEY-----"), "Private Key"),
    (re.compile(r"(?i)\bsk-(?:(?:proj|svcacct|admin)-[a-zA-Z0-9_\-]{40,}|(?!ant-)[a-zA-Z0-9]{32,})"), "OpenAI API Key"),
    (re.compile(r"(?i)sk-ant-[a-zA-Z0-9\-]{40,}"), "Anthropic API Key"),
    # END:SECRET_PATTERNS
]

def main():
    stdin_data = sys.stdin.read()
    if not stdin_data.strip():
        sys.exit(0)

    try:
        payload = json.loads(stdin_data)
    except json.JSONDecodeError:
        payload = {"raw": stdin_data}

    tool_in = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    tool_info = payload.get("tool_info") if isinstance(payload.get("tool_info"), dict) else {}

    # Every field a user controls, across agents. Reading only `prompt` here
    # meant this guard saw "" on a Claude Code PreToolUse write and on every
    # Cursor beforeShellExecution — it exited 0 and looked like it was working.
    # `str(...)` because a non-string field reaching re.search raises, and an
    # unhandled exception exits 1, which blocks nowhere.
    candidates = [
        payload.get("prompt"),
        payload.get("user_prompt"),
        payload.get("raw"),
        payload.get("command"),
        tool_in.get("command"),
        tool_in.get("content"),
        tool_info.get("command_line"),
        tool_info.get("user_prompt"),
    ]
    text = "\n".join(str(c) for c in candidates if c)

    for pattern, label in SECRET_PATTERNS:
        if pattern.search(text):
            sys.stderr.write(f"Blocked by captain-hook: Secret key pattern detected ({label})!\n")
            sys.exit(2)  # Exit Code 2 blocks execution

    sys.exit(0)

if __name__ == "__main__":
    main()
```

---

## Recipe 2: Dangerous Command Denylist (Bash)

Blocks a fixed list of dangerous terminal commands: `rm` with a destructive
flag against a root-ish path (long flags and a `--` separator included),
`mkfs`, `dd if=`, `git push --force` or `-f` (but not `--force-with-lease`),
a `chmod` making a tree world-writable in either argument order, and
`chown -R root`. It mirrors `BLOCKED_COMMANDS` in `scripts/captain_hook.py`.

This is a denylist over a command string, not a containment boundary — ordinary
shell syntax gets past it. See the **Known limits** table in
[`guards.md`](guards.md) before relying on it.

```bash
#!/usr/bin/env bash
# Dangerous Command Denylist Hook Script for AI Coding Agents

PAYLOAD=$(cat)

# Extract command string handling Cursor, Windsurf, Claude Code and Antigravity
# key names. A parse failure must not look like "no command": `json.load(...)
# if sys.stdin` guarded nothing — sys.stdin is always truthy — and a raised
# exception left CMD empty, which fell straight through to exit 0.
CMD=$(printf '%s' "$PAYLOAD" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
except Exception:
    print('__CAPTAIN_HOOK_PARSE_ERROR__')
    raise SystemExit(0)
if not isinstance(data, dict):
    data = {}
tool_in = data.get('tool_input', {}) if isinstance(data.get('tool_input'), dict) else {}
tool_info = data.get('tool_info', {}) if isinstance(data.get('tool_info'), dict) else {}
tool_call = data.get('toolCall', {}) if isinstance(data.get('toolCall'), dict) else {}
cmd = (data.get('command') or tool_in.get('command') or tool_info.get('command_line')
       or tool_call.get('command') or data.get('command_string') or '')
print(cmd if isinstance(cmd, str) else ' '.join(map(str, cmd)))
")

if [[ "$CMD" == "__CAPTAIN_HOOK_PARSE_ERROR__" ]]; then
    echo "Blocked by captain-hook: unreadable hook payload" >&2
    exit 2
fi

if [[ -z "$CMD" ]]; then
    exit 0
fi

# Mirrors BLOCKED_COMMANDS in scripts/captain_hook.py. --force-with-lease is
# deliberately NOT blocked: it is the safe form, and blocking it pushes people
# to plain --force. bash `=~` has no negative lookahead, so the alternation
# below tests the character AFTER the flag instead.
if [[ "$CMD" =~ rm[[:space:]]+((--?[[:alnum:]_-]+|--)[[:space:]]+)*-{1,2}[[:alnum:]]*[rRf][[:alnum:]]*[[:space:]]+((--?[[:alnum:]_-]+|--)[[:space:]]+)*[\"\']?[/~*] ]] || \
   [[ "$CMD" =~ (mkfs|dd[[:space:]]+if=) ]] || \
   [[ "$CMD" =~ git[[:space:]]+push[[:space:]].*(--force([^-]|$)|-f([^[:alnum:]-]|$)) ]] || \
   [[ "$CMD" =~ chmod[[:space:]]+(-R[[:space:]]+(777|[ugoa]*\+[[:alnum:]]*w)|((777|[ugoa]*\+[[:alnum:]]*w)[[:space:]]+-R)) ]] || \
   [[ "$CMD" =~ chown[[:space:]]+-R[[:space:]]+root ]]; then
    echo "Blocked by captain-hook: Destructive command '$CMD' is forbidden!" >&2
    exit 2 # Exit Code 2 blocks execution
fi

exit 0
```

---

## Recipe 3: Symlink Guard (Python)

Prevents the agent from writing to paths that resolve outside the repository, including through symlinked parent directories.

```python
#!/usr/bin/env python3
"""Path-Escape Write Guard for AI Coding Agents."""
import sys, json, os

def repo_root():
    """Nearest ancestor containing .git, else the cwd. No subprocess."""
    current = os.path.abspath(os.getcwd())
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.abspath(os.getcwd())
        current = parent

def escapes_repo(path, root):
    # realpath resolves every component, including parents, and works on paths
    # that do not exist yet — that is what catches a NEW file written through
    # a symlinked directory.
    resolved = os.path.realpath(os.path.abspath(path))
    if resolved == root:
        return False, resolved
    # startswith(root + os.sep) avoids the /repo vs /repo-backup prefix bug.
    return not resolved.startswith(root + os.sep), resolved

def main():
    stdin_data = sys.stdin.read()
    if not stdin_data.strip():
        sys.exit(0)

    try:
        payload = json.loads(stdin_data)
    except json.JSONDecodeError:
        # An unhandled exception exits 1, and exit 1 is a hook *error*, not a
        # block — the host proceeds with the write. A guard must never fail
        # open on the payload it has the most reason to distrust.
        sys.stderr.write("Blocked by captain-hook: unreadable hook payload!\n")
        sys.exit(2)
    if not isinstance(payload, dict):
        sys.stderr.write("Blocked by captain-hook: unexpected payload shape!\n")
        sys.exit(2)
    tool_in = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    tool_info = payload.get("tool_info") if isinstance(payload.get("tool_info"), dict) else {}
    path = (
        payload.get("path")
        or payload.get("filepath")
        or payload.get("file_path")
        or payload.get("file")
        or tool_in.get("file_path")
        or tool_info.get("file_path")
        or ""
    )

    if path:
        escapes, resolved = escapes_repo(path, os.path.realpath(repo_root()))
        if escapes:
            sys.stderr.write(f"Blocked by captain-hook: '{path}' resolves to '{resolved}', outside the repository root!\n")
            sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
```

A symlink that stays inside the repository is allowed — being a link is not by
itself a violation. POSIX only; Windows junctions are not handled.

---

## Recipe 4: Code Auto-Formatter Hook (Node.js)

Automatically runs `prettier` or `eslint` after code writes.

```javascript
#!/usr/bin/env node
// Auto-Formatter Post-Hook for Node.js
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

let rawData = '';
process.stdin.on('data', chunk => rawData += chunk);
process.stdin.on('end', () => {
  if (!rawData.trim()) process.exit(0);

  try {
    const payload = JSON.parse(rawData);
    const filePath = payload.path || payload.filepath || payload.file_path;

    if (filePath && fs.existsSync(filePath)) {
      // Containment first: this formatter REWRITES the file it is pointed at,
      // and the path comes from the payload. A post event naming a path
      // outside the repository is not something a hook should run a tool
      // against.
      const repoRoot = process.cwd();
      const resolved = fs.realpathSync(path.resolve(filePath));
      if (!resolved.startsWith(repoRoot + path.sep)) process.exit(0);

      if (resolved.match(/\.(js|ts|jsx|tsx|json)$/)) {
        // Resolve the local binary; never the npm auto-install runner, which
        // downloads an unpinned package from the registry when prettier is
        // not installed. The timeout keeps a hung formatter from stalling
        // the agent's tool call.
        const local = path.join(repoRoot, 'node_modules', '.bin', 'prettier');
        if (fs.existsSync(local)) {
          // execFileSync with an argv array, never execSync with a template
          // string: `filePath` is attacker-influenced input and execSync runs
          // its argument through a shell, where quotes do not neutralise
          // command substitution.
          execFileSync(local, ['--write', resolved], { stdio: 'ignore', timeout: 10000 });
        }
      }
    }
  } catch (err) {
    // Ignore non-fatal formatting errors
  }
  process.exit(0);
});
```

---

## Recipe 5: Test-Suite Gate Hook (Python)

Runs the unit test suite before allowing turn completion or commit.

The 120-second timeout below is a starting point: set it *below* the host's own
hook timeout (30s on Antigravity, 60s on Claude Code, unspecified on Windsurf).
A `Stop` hook that outlives the host's timeout is killed with no verdict.

```python
#!/usr/bin/env python3
"""Test Gate Hook Script."""
import sys, subprocess

# A hook must not outlive the host's own hook timeout — 30s on Antigravity,
# 60s on Claude Code, unspecified on Windsurf — so it gets its own, shorter
# one. Without it a hung test suite stalls the agent indefinitely.
TEST_TIMEOUT_SECONDS = 120

def main():
    try:
        res = subprocess.run(
            ["python3", "-m", "unittest", "discover", "tests"],
            capture_output=True, text=True, timeout=TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"Blocked: test suite exceeded {TEST_TIMEOUT_SECONDS}s\n")
        sys.exit(2)
    if res.returncode != 0:
        sys.stderr.write(f"Blocked: Test suite failed!\n{res.stdout}\n{res.stderr}\n")
        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
```
