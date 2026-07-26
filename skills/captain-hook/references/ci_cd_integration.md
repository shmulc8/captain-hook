# Pre-Commit & CI/CD Integration Guide (`references/ci_cd_integration.md`)

This guide explains how to integrate `captain-hook` verification into your Git pre-commit hooks and GitHub Actions CI workflow.

---

## 1. Git Pre-Commit Hook Integration

Add the following to `.git/hooks/pre-commit` to prevent committing invalid or unsafe code:

```bash
#!/usr/bin/env bash
# .git/hooks/pre-commit
./skills/captain-hook/scripts/verify_hooks.sh
if [ $? -ne 0 ]; then
    echo "Pre-commit hook failed! Please resolve policy issues." >&2
    exit 1
fi
```
```bash
chmod +x .git/hooks/pre-commit
```

---

## 2. GitHub Actions CI Workflow (`.github/workflows/verify.yml`)

This repository runs exactly this workflow — see [`.github/workflows/verify.yml`](../../../.github/workflows/verify.yml).

```yaml
name: Verify

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.9', '3.12']
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Confirm no dependencies are needed
        run: |
          python3 -c "import json, re, os, sys, shutil, subprocess, argparse; print('stdlib ok')"

      - name: Run verification suite
        run: bash skills/captain-hook/scripts/verify_hooks.sh

  shellcheck:
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
      - name: Shellcheck
        run: shellcheck skills/captain-hook/scripts/*.sh
```

The script's mode bit (`100755`) is committed, so no `chmod` step is needed;
invoking through `bash` works regardless. The workflow installs nothing — the
suite is bash plus stdlib Python, and the 3.9 leg is there because hook scripts
run on whatever Python a developer happens to have.
