# Exhaustive Antigravity (AGY) Hooks & Guardrails Specification

## 1. Overview & Architecture

Google Antigravity (AGY CLI / IDE) features a native **Write-Time Prevention Hook** system (`hooks/prevent.py`) and a report-only **CI Gate** (`--check --base <ref>`). Prevention hooks execute before `--fix` operations or file mutations to guarantee git cleanliness, line integrity, and prevent out-of-tree symlink rewrites.

---

## 2. Configuration & Hook Locations

| Level | Path | Purpose |
| :--- | :--- | :--- |
| **Workspace (Project)** | `hooks/prevent.py` | Write-time prevention hook executed before `--fix` mutations. |
| **Skill Level** | `skills/captain-obvious/scripts/` | Scanner engine & AST classifiers (`co_py`, `co_ts`). |
| **CI Gate** | `action.yml` / `.pre-commit-hooks.yaml` | Syntactic check gate for pull requests. |

---

## 3. `hooks/prevent.py` Prevention Hook Contract

Antigravity executes `hooks/prevent.py` as a Python script prior to performing write-time fixes.

### Execution Contract:
- **Environment**: Python 3.9+ runtime in repository working directory.
- **Inputs**: CLI flags (`--path`, `--fix`, `--force`).
- **Outputs**:
  - **Exit Code `0`**: Allow write-time fix to proceed.
  - **Exit Code `2`**: **BLOCK / REJECT**. The fix operation is cancelled, and error text on `stderr` is presented to the agent.

---

## 4. Complete Implementation Example

### `hooks/prevent.py`
```python
#!/usr/bin/env python3
"""Antigravity Write-Time Prevention Hook."""
import sys, subprocess, os

# 1. Require clean working tree before allowing --fix
proc = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
if proc.stdout.strip():
    sys.stderr.write("captain-obvious: uncommitted changes present — commit or stash before running --fix\n")
    sys.exit(2)

# 2. Refuse writes if git is absent
if not subprocess.run(["git", "--version"], capture_output=True).returncode == 0:
    sys.stderr.write("captain-obvious: git command unavailable — refusal to rewrite without undo path\n")
    sys.exit(2)

sys.exit(0)
```
