# Amazon Q Developer Project Rules Specification

> Source: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/context-project-rules.html — verified 2026-07-26

## 1. What this is — and what it is not

Amazon Q Developer has **no executable hook system**. It has *project rules*:
Markdown files that are injected as context into every chat in the project.
They shape what Amazon Q generates; they cannot intercept, inspect, or block a
tool call, a shell command, or a file write.

If you need deterministic blocking with Amazon Q, put it outside the agent — a
git `pre-commit` hook or a CI gate. See
[`../ci_cd_integration.md`](../ci_cd_integration.md).

---

## 2. Configuration Path

| Scope | Path | Format |
| :--- | :--- | :--- |
| **Workspace** | `{project-root}/.amazonq/rules/*.md` | Markdown — one rule per file |

Each rule file must be a Markdown file (`.md` extension). Rules can also be
created from the chat panel's **Rules** button, which writes into the same
folder.

---

## 3. Content Format

Free-text prose. There is no schema, no front matter, no event field, and no
action field. Example (`.amazonq/rules/security-rules.md`):

```markdown
All Amazon S3 buckets must have encryption enabled, enforce SSL, and block public access.
All Amazon DynamoDB Streams tables must have encryption enabled.
Never generate code that force-pushes to a shared branch.
```

---

## 4. Activation

Rules in `.amazonq/rules` are applied automatically to every chat in the
project. Individual rules can be toggled per session from the **Rules** button
in the chat panel — a checkmark means active.

---

## 5. Enforcement Contract

**None.** Rules are advisory context sent to the model. There is no exit code,
no stdin payload, no allow/deny decision, and no guarantee the model complies.
Treat them as a strong prompt, not a guardrail.
