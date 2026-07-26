# Pre-Commit & CI/CD Integration Guide (`references/ci_cd_integration.md`)

This guide explains how to integrate `captain-hook` verification into your Git pre-commit hooks and GitHub Actions CI workflow.

---

## 1. Git Pre-Commit Hook Integration

A git `pre-commit` hook is the fallback gate for every agent that cannot block
on its own — Aider, Roo Code / Cline, Copilot, Amazon Q, and Continue CLI. It
runs the **dispatcher** against your staged changes. It does not run this
repository's verification suite: that suite tests captain-hook itself and knows
nothing about your code.

```bash
cp /abs/path/to/captain-hook/skills/captain-hook/examples/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Then open `.git/hooks/pre-commit` and replace `<CAPTAIN_HOOK>` with the
absolute invocation — see [`../README-INSTALL.md`](../README-INSTALL.md):

```bash
python3 /abs/path/to/captain-hook/skills/captain-hook/scripts/captain_hook.py
```

Use an absolute path. A hook that cannot start exits non-zero, and for a git
hook that means **every commit is refused** until you notice.

What this gate can and cannot see: it inspects the staged diff, so it catches a
secret or an escaping path that reaches a commit. It cannot see the shell
commands an agent ran — nothing at commit time can. For that you need an
executable hook in the agent itself; see the roster in
[`../SKILL.md`](../SKILL.md) section 5.

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
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ['3.9', '3.12']
        # macOS runners bill at a higher multiplier, and the reason this leg
        # exists is the platform's path semantics (/var vs /private/var), not
        # its Python versions — one version is enough to catch that.
        exclude:
          - os: macos-latest
            python-version: '3.9'
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
    steps:
      - uses: actions/checkout@v4
      - name: Shellcheck
        run: shellcheck skills/captain-hook/scripts/*.sh
```

The script's mode bit (`100755`) is committed, so no `chmod` step is needed;
invoking through `bash` works regardless. The workflow installs nothing — the
suite is bash plus stdlib Python. The 3.9 leg is there because hook scripts run
on whatever Python a developer happens to have; the macOS leg is there because
every containment guard compares resolved paths, and macOS is the platform
where `/var` and `/private/var` spell the same directory two ways. It runs one
Python version, since the platform is what is being tested, not the interpreter.
