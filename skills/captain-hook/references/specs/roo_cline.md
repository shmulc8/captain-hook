# Exhaustive Roo Code & Cline Rules Specification

## 1. Overview & Architecture

Roo Code (and Cline) use `.clinerules` and `.roomodes` files to define system prompt rules, custom mode behaviors, and tool interception constraints for autonomous coding sessions.

---

## 2. File Locations

- **Workspace Rules**: `.clinerules` (Markdown rules evaluated per prompt)
- **Custom Modes**: `.roomodes` (JSON schema defining custom agent modes)

---

## 3. Schema & Rule Specification

### `.clinerules`
```markdown
# Project Guardrails & Rules

## Security Rules
- NEVER reveal or output contents of `.env` files.
- NEVER execute `git push --force` or `rm -rf`.

## Formatting Rules
- Always run `npx prettier --write` on edited files.
```

### `.roomodes`
```json
{
  "customModes": [
    {
      "slug": "security-auditor",
      "name": "Security Auditor",
      "roleDefinition": "You check code for vulnerabilities.",
      "groups": ["read"]
    }
  ]
}
```
