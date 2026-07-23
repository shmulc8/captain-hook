# Pre-Commit & CI/CD Integration Guide (`references/ci_cd_integration.md`)

This guide explains how to integrate `captain-hook` verification into your Git pre-commit hooks and GitHub Actions CI workflow.

---

## 1. Git Pre-Commit Hook Integration

Add the following to `.git/hooks/pre-commit` to prevent committing invalid or unsafe code:

```bash
#!/usr/bin/env bash
# .git/hooks/pre-commit
./scripts/verify_hooks.sh
if [ $? -ne 0 ]; then
    echo "Pre-commit hook failed! Please resolve policy issues." >&2
    exit 1
fi
```
```bash
chmod +x .git/hooks/pre-commit
```

---

## 2. GitHub Actions CI Workflow (`.github/workflows/verify-hooks.yml`)

```yaml
name: Verify AI Agent Hooks

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Run Hook Verification Suite
        run: |
          chmod +x scripts/verify_hooks.sh
          ./scripts/verify_hooks.sh
```
