# Aider AI Coding Agent Specification

> Source: https://aider.chat/docs/usage/lint-test.html and https://aider.chat/docs/config/aider_conf.html — verified 2026-07-26

## 1. Overview & Architecture

Aider has no event-hook system. What it has is a **closed feedback loop**: when
`auto-lint` or `auto-test` is enabled, Aider runs your command after an edit, and
on a non-zero exit code feeds the command's output back to the LLM so it can fix
the problem.

That makes Aider a **quality gate, not a guardrail**. The commands run *after*
the edit, so they cannot prevent one. Upstream, verbatim: "If there are linting
errors, aider expects the command to print them on stdout/stderr and return a
non-zero exit code."

---

## 2. Configuration File Locations

`.aider.conf.yml` is searched for in three places, in this order, with **later
files taking priority**:

| Order | Location |
| :---: | :--- |
| 1 | Your home directory |
| 2 | The root of your git repo |
| 3 | The current directory |

`--config <filename>` loads only that single file instead.

Options can also be set as command-line switches, environment variables, or
entries in a `.env` file. **The docs do not state the precedence between those
four mechanisms**, so this file does not claim one — the four-level table
previously here (CLI > env > workspace > user) was unsourced. Checked against
https://aider.chat/docs/config.html on 2026-07-26.

---

## 3. Configuration File Schema (`.aider.conf.yml`)

```yaml
# .aider.conf.yml

# Lint files after every edit
auto-lint: true

# Command executed on the edited files
lint-cmd: "ruff check --fix"

# Run the test command after every edit
auto-test: true

# Command executed to run the test suite
test-cmd: "pytest -x"

# Commit after successful edits — note the plural
auto-commits: true
```

Keys use hyphens, not underscores. The commit key is **`auto-commits`**, not
`auto-commit`; the singular form is silently ignored.

---

## 4. Execution & Feedback Protocol

- **`lint-cmd`** receives the filenames of the modified files as arguments.
  "The lint command should accept the filenames of the files to lint."
  A non-zero exit code, with the errors printed to stdout/stderr, starts the fix
  cycle. Automatic linting can be turned off with `--no-auto-lint`.
- **`test-cmd`** runs with **no arguments**: "Aider will run the test command
  without any arguments." A non-zero exit code with output on stdout/stderr
  prompts the model to fix the failing tests. Enabled with `--auto-test`.

The asymmetry is the thing to remember: lint gets the file list, test does not.

---

## 5. Complete Implementation Example

### `.aider.conf.yml`
```yaml
auto-lint: true
lint-cmd: "python3 /abs/path/to/skills/captain-hook/scripts/captain_hook.py dispatch PostWrite"
auto-test: true
test-cmd: "python3 -m unittest discover tests"
```

Note what this can and cannot do: the dispatcher runs after the write, so it
reports rather than blocks. For blocking with Aider, use a git `pre-commit`
hook — see [`../ci_cd_integration.md`](../ci_cd_integration.md).
