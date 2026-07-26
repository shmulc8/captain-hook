# GitHub Copilot Instructions & Git Hooks Specification

> Source: https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions — verified 2026-07-26

## 1. Overview & Architecture

GitHub Copilot's repository-level customization surface is a Markdown
instructions file. Upstream, verbatim: instructions "are specified in a
`copilot-instructions.md` file in the `.github` directory of the repository",
and "The instructions in the file(s) are available for use by Copilot as soon as
you save the file(s). Instructions are automatically added to requests that you
submit to Copilot."

**Copilot custom instructions cannot block or intercept anything.** They are
passive text that shapes responses. Any deterministic gate in a Copilot workflow
therefore lives outside Copilot — in a git `pre-commit` hook or in CI.

When several instruction sources exist, personal instructions take highest
priority, then repository instructions, then organization instructions.

---

## 2. Configuration Paths

- **Repository instructions**: `.github/copilot-instructions.md` (Markdown)
- **Pre-commit git hook**: `.git/hooks/pre-commit`, or `.pre-commit-config.yaml`
  if you use the `pre-commit` framework

---

## 3. Enforcement Contract

| Mechanism | Blocks? | How |
| :--- | :---: | :--- |
| `.github/copilot-instructions.md` | no | Advisory context added to requests |
| `.git/hooks/pre-commit` | yes | Non-zero exit aborts the commit |

The git hook is the only part of this page with a blocking contract, and it is
git's, not Copilot's.

---

## 4. Implementation Example

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
python3 /abs/path/to/skills/captain-hook/scripts/captain_hook.py dispatch PreCommit
if [ $? -ne 0 ]; then
    echo "Commit blocked by captain-hook!" >&2
    exit 1
fi
```

Remember that a `pre-commit` hook runs at commit time, not at edit time: it
catches what reaches a commit, not what the agent writes to your working tree.
