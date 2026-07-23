# Exhaustive GitHub Copilot & Git Hooks Specification

## 1. Overview & Architecture

GitHub Copilot Workspace and Copilot CLI use repository instruction files (`.github/copilot-instructions.md`) and standard Git Pre-Commit Hooks (`.git/hooks/pre-commit`) to enforce security policies and build checks before commits or agent actions are finalized.

---

## 2. Configuration Paths

- **Copilot Workspace Instructions**: `.github/copilot-instructions.md`
- **Pre-Commit Git Hook**: `.git/hooks/pre-commit` or `.pre-commit-config.yaml`

---

## 3. Implementation Example

### `.github/copilot-instructions.md`
```markdown
# Repository Instructions for Copilot
- Enforce strict type checking on all TypeScript files.
- Run `npm test` before declaring a task finished.
- Do not modify `.env` or credentials files.
```

### `.git/hooks/pre-commit`
```bash
#!/usr/bin/env bash
python3 -m captain_hook dispatch PreCommit
if [ $? -ne 0 ]; then
    echo "Commit blocked by captain-hook!" >&2
    exit 1
fi
```
