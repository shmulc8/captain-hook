# Roo Code & Cline Rules Specification

> Source: https://roocodeinc.github.io/Roo-Code/features/custom-modes (docs.roocode.com 301-redirects there) — verified 2026-07-26

## 1. Overview & Architecture

Roo Code and Cline configure agent behavior with **rules files and custom
modes** — text appended to the system prompt, plus per-mode tool and file
permissions.

**There is no executable hook.** Nothing here runs a script, receives a payload,
or returns an exit code. Rules shape what the agent is told; they do not
intercept a tool call. Mode `groups` and their `fileRegex` restrictions limit
which tools and files a mode may touch, but that is the agent's own permission
logic, not a hook you can extend.

---

## 2. File Locations

| File | Purpose |
| :--- | :--- |
| `.roomodes` | Custom mode definitions (YAML **or** JSON — Roo Code detects the format) |
| `.roo/rules-{mode-slug}/` | Preferred: a directory of instruction files for one mode |
| `.roorules-{mode-slug}` | Fallback: a single instruction file in the workspace root |
| `.clinerules` | Cline's equivalent rules file |

---

## 3. Schema & Rule Specification

### `.clinerules`
Free-text Markdown appended to the system prompt.

```markdown
# Project Guardrails & Rules

## Security Rules
- NEVER reveal or output contents of `.env` files.
- NEVER force-push or run `rm -rf`.

## Formatting Rules
- Always run the project's formatter on edited files.
```

### `.roomodes`
A `customModes` array. YAML shown; JSON is equally valid.

```yaml
customModes:
  - slug: security-auditor          # unique internal identifier
    name: Security Auditor          # display name in the UI
    description: Reviews code for vulnerabilities   # shown in the mode selector
    roleDefinition: You check code for vulnerabilities.   # core identity and expertise
    groups: [read]                  # allowed toolsets and file-access permissions
    whenToUse: Use when auditing dependencies or auth code.   # optional
    customInstructions: Prefer citing CWE ids.                # optional
```

| Field | Required | Meaning |
| :--- | :---: | :--- |
| `slug` | yes | Unique internal identifier for the mode |
| `name` | yes | Display name shown in the UI |
| `description` | — | Short summary for the mode selector |
| `roleDefinition` | yes | Core identity and expertise |
| `groups` | yes | Allowed toolsets and file-access permissions |
| `whenToUse` | — | Guidance for automated mode selection |
| `customInstructions` | — | Additional behavioral guidelines |

---

## 4. Enforcement Contract

**None that a hook author can use.** These are prompt-level instructions and
permission groups. There is no stdin payload, no exit code, and no way to run
your own code at a lifecycle point.

For deterministic blocking alongside Roo Code or Cline, put the gate outside the
agent — a git `pre-commit` hook or CI. See
[`../ci_cd_integration.md`](../ci_cd_integration.md).

---

## 5. Corrections made 2026-07-26

`.roomodes` was described as JSON-only; it accepts YAML or JSON. The field list
was missing `description`, `whenToUse`, and `customInstructions`. The claim of
"tool interception constraints" overstated what mode `groups` do.
