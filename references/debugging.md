# Interactive Hook Debugging & Testing Guide (`references/debugging.md`)

This guide explains how to test and debug agent hook scripts locally before deploying them into Cursor, Windsurf, or Claude Code.

---

## 1. Testing Hooks via Terminal Piping (`stdin`)

You can test any hook script directly in your terminal by piping sample JSON payloads to `stdin`:

```bash
# Test a clean shell command (should exit 0)
python3 scripts/captain_hook.py dispatch beforeShellExecution < examples/payloads/cursor_beforeShellExecution_clean.json
echo $?  # Outputs: 0

# Test a secret leak payload (should exit 2 and output error message to stderr)
python3 scripts/captain_hook.py dispatch beforeShellExecution < examples/payloads/cursor_beforeShellExecution_secret.json
echo $?  # Outputs: 2
```

---

## 2. Running the Automated Verification Suite

Run the included verification suite to validate your project's hook policies:

```bash
./scripts/verify_hooks.sh
```

---

## 3. Inspecting Agent Output Logs

- **Cursor AI**: Open `Ctrl+Shift+P` ➔ "Output: Show Output Channels" ➔ Select **"Hooks"**.
- **Windsurf Cascade**: Ensure `"show_output": true` is set in `.windsurf/hooks.json`.
- **Claude Code**: View terminal execution output or check `.claude/logs/`.
