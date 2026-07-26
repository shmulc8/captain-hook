# Interactive Hook Debugging & Testing Guide (`references/debugging.md`)

This guide explains how to test and debug agent hook scripts locally before deploying them into Cursor, Windsurf, or Claude Code.

---

## 1. Testing Hooks via Terminal Piping (`stdin`)

You can test any hook script directly in your terminal by piping sample JSON payloads to `stdin`. Run these from the **repository root**:

```bash
# Test a clean shell command (should exit 0)
python3 skills/captain-hook/scripts/captain_hook.py dispatch beforeShellExecution \
  < skills/captain-hook/examples/payloads/cursor_beforeShellExecution_clean.json
echo $?  # Outputs: 0

# Test a secret leak payload (should exit 2, with an error on stderr)
python3 skills/captain-hook/scripts/captain_hook.py dispatch beforeShellExecution \
  < skills/captain-hook/examples/payloads/cursor_beforeShellExecution_secret.json
echo $?  # Outputs: 2
```

---

## 2. Running the Automated Verification Suite

The suite verifies *this skill* — the bundled dispatcher, the shipped config
templates, and the documentation. It does not test your own hook scripts; for
that, pipe a fixture into them as shown in section 1.

Two scripts, both run by the first. Paths are relative to the repository root:

```bash
# Behavioral cases against the bundled dispatcher, then the documentation gates
bash skills/captain-hook/scripts/verify_hooks.sh

# The documentation gates alone (JSON/Python blocks, schema drift, dead links)
python3 skills/captain-hook/scripts/verify_docs.py
```

`npm test` runs the same suite.

---

## 2b. Payload fixtures

`examples/payloads/` holds one JSON payload per agent, event and case, named
`<agent>_<event>_<case>.json`. They are the inputs the verification suite pipes
into the dispatcher, and the ones to pipe into your own hook scripts when
testing them (section 1).

Every agent that can block — Claude Code, Cursor, Windsurf, OpenHands,
Antigravity — must have at least one fixture in its own payload shape, and the
suite must run it. `verify_docs.py` enforces both. The reason is specific:
Antigravity shipped in the blocking roster with no fixture, so nothing caught
that the dispatcher could not read any of its fields.

Every fixture's shape comes from that agent's file in `references/specs/`. If
you cannot point at the spec section a field came from, do not add the fixture.

---

## 3. Inspecting Agent Output Logs

- **Cursor AI**: Open `Ctrl+Shift+P` ➔ "Output: Show Output Channels" ➔ Select **"Hooks"**.
- **Windsurf Cascade**: Ensure `"show_output": true` is set in `.windsurf/hooks.json`.
- **Claude Code**: View terminal execution output or check `.claude/logs/`.
