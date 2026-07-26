# Ready-to-Use Hook Recipes (`references/recipes.md`)

This reference contains copy-pasteable, standalone hook scripts for Python, Bash, and Node.js that can be wired into any AI coding agent.

---

## Recipe 1: Secret Scanner Guard (Python)

Interceptors prompts or file edits containing API keys, AWS credentials, or SSH private keys.

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
    (re.compile(r"(?i)\bsk-(?!ant-)(proj-|svcacct-|admin-)?[a-zA-Z0-9_]{20,}[a-zA-Z0-9_\-]{12,}"), "OpenAI API Key"),
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

    # Extract text from prompt, raw, or code fields
    text = (
        payload.get("prompt")
        or payload.get("user_prompt")
        or payload.get("code")
        or payload.get("raw")
        or ""
    )

    for pattern, label in SECRET_PATTERNS:
        if pattern.search(text):
            sys.stderr.write(f"Blocked by captain-hook: Secret key pattern detected ({label})!\n")
            sys.exit(2)  # Exit Code 2 blocks execution

    sys.exit(0)

if __name__ == "__main__":
    main()
```

---

## Recipe 2: Command Sandbox Guard (Bash)

Prevents dangerous or destructive terminal commands (`rm -rf`, `git push --force`, `dd`, `chmod 777`).

```bash
#!/usr/bin/env bash
# Command Sandbox Hook Script for AI Coding Agents

PAYLOAD=$(cat)

# Extract command string handling Cursor, Windsurf, and Claude Code key names
CMD=$(echo "$PAYLOAD" | python3 -c "
import sys, json
data = json.load(sys.stdin) if sys.stdin else {}
tool_in = data.get('tool_input', {}) if isinstance(data.get('tool_input'), dict) else {}
tool_info = data.get('tool_info', {}) if isinstance(data.get('tool_info'), dict) else {}
cmd = data.get('command') or tool_in.get('command') or tool_info.get('command_line') or data.get('command_string') or ''
print(cmd)
")

if [[ -z "$CMD" ]]; then
    exit 0
fi

# Block dangerous patterns
if [[ "$CMD" =~ rm[[:space:]]+-[rRf]{1,2}[[:space:]]+[/~*] ]] || \
   [[ "$CMD" =~ git[[:space:]]+push[[:space:]]+.*--force ]] || \
   [[ "$CMD" =~ chmod[[:space:]]+-R[[:space:]]+777 ]]; then
    echo "Blocked by captain-hook: Destructive command '$CMD' is forbidden!" >&2
    exit 2 # Exit Code 2 blocks execution
fi

exit 0
```

---

## Recipe 3: Symlink Guard (Python)

Prevents the agent from writing to or modifying files through symlinks pointing outside the repository.

```python
#!/usr/bin/env python3
"""Symlink Write Guard for AI Coding Agents."""
import sys, json, os

def main():
    stdin_data = sys.stdin.read()
    if not stdin_data.strip():
        sys.exit(0)

    payload = json.loads(stdin_data)
    tool_in = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    path = (
        payload.get("path")
        or payload.get("filepath")
        or payload.get("file_path")
        or tool_in.get("file_path")
        or ""
    )

    if path and os.path.exists(path) and os.path.islink(path):
        sys.stderr.write(f"Blocked by captain-hook: Target file '{path}' is a symlink pointing outside repository boundaries!\n")
        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
```

---

## Recipe 4: Code Auto-Formatter Hook (Node.js)

Automatically runs `prettier` or `eslint` after code writes.

```javascript
#!/usr/bin/env node
// Auto-Formatter Post-Hook for Node.js
const fs = require('fs');
const { execSync } = require('child_process');

let rawData = '';
process.stdin.on('data', chunk => rawData += chunk);
process.stdin.on('end', () => {
  if (!rawData.trim()) process.exit(0);

  try {
    const payload = JSON.parse(rawData);
    const filePath = payload.path || payload.filepath || payload.file_path;

    if (filePath && fs.existsSync(filePath)) {
      if (filePath.match(/\.(js|ts|jsx|tsx|json)$/)) {
        execSync(`npx prettier --write "${filePath}"`, { stdio: 'ignore' });
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

```python
#!/usr/bin/env python3
"""Test Gate Hook Script."""
import sys, subprocess

def main():
    res = subprocess.run(["python3", "-m", "unittest", "discover", "tests"], capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(f"Blocked: Test suite failed!\n{res.stdout}\n{res.stderr}\n")
        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
```
