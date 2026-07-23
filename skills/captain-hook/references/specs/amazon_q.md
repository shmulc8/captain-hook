# Exhaustive Amazon Q Developer Hooks Specification

## 1. Overview & Architecture

Amazon Q Developer uses `.amazonq/rules` configuration files to define repository-level rules, pre-check constraints, and code generation boundaries for the Amazon Q CLI and IDE extensions.

---

## 2. Configuration Path

- **Workspace Rules**: `.amazonq/rules` (JSON / YAML)

---

## 3. Configuration Schema Example

```yaml
# .amazonq/rules
rules:
  - name: "block-force-push"
    event: "before_command"
    pattern: "git push --force"
    action: "block"
    message: "Force push is forbidden in this repository."
```
