# Exhaustive Aider AI Coding Agent Specification

## 1. Overview & Architecture

Aider AI implements an automated **Closed Feedback Loop** using `--lint-cmd` and `--test-cmd` hooks. When enabled via `auto-lint` or `auto-test`, Aider automatically executes these commands after every code edit, captures `stdout`/`stderr` upon failure, and feeds the failure output back to the LLM agent to automatically fix issues.

---

## 2. Configuration Files & Hierarchy

| Precedence | Location | Scope |
| :---: | :--- | :--- |
| **1. CLI Flags** | `--lint-cmd "..." --test-cmd "..."` | Overrides configuration files. |
| **2. Environment Variables** | `AIDER_LINT_CMD=... AIDER_TEST_CMD=...` | Environment-specific overrides. |
| **3. Workspace Config** | `.aider.conf.yml` | Repository root settings (version controlled). |
| **4. User Config** | `~/.aider.conf.yml` | User global settings across repositories. |

---

## 3. Configuration File Schema Specification (`.aider.conf.yml`)

```yaml
# .aider.conf.yml

# Enable automatic linting after every file write
auto-lint: true

# Command executed on edited files
lint-cmd: "ruff check --fix"

# Enable automatic test execution after file writes
auto-test: true

# Command executed to run test suite
test-cmd: "pytest -x"

# Enable auto-commit after successful edits
auto-commit: true
```

---

## 4. Execution & Feedback Protocol

- **`lint-cmd`**: Aider passes modified file paths to the `lint-cmd`. Non-zero exit codes trigger Aider's auto-fix prompt cycle.
- **`test-cmd`**: Aider executes `test-cmd` without additional file parameters. Non-zero exit code captures stderr/stdout and prompts the LLM to fix the failing tests.

---

## 5. Complete Implementation Example

### `.aider.conf.yml`
```yaml
auto-lint: true
lint-cmd: "python3 -m captain_hook dispatch PostWrite"
auto-test: true
test-cmd: "python3 -m unittest discover tests"
```
