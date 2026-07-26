# Continue CLI (`cn`) — Unverified

> Source: https://docs.continue.dev/ (index and CLI section) — checked 2026-07-26, no hooks documentation found

> **Not aged**: this file asserts nothing about Continue CLI's hooks, so there
> is nothing in it to go stale. The provenance gate exempts it by name (see
> `scripts/verify_docs.py`, `PROVENANCE_EXEMPT`). If Continue CLI's hook
> documentation is ever located, remove the exemption in the same change that
> adds the claims.

## Verification Status

**No official documentation could be located for a Continue CLI hooks system as
of 2026-07-26.**

URLs checked:

- `https://docs.continue.dev/` — documents `config.yaml`, the deprecated
  `config.json`, model providers, model roles, MCP servers, Rules, and Prompts.
  No lifecycle hooks, no event names, no event count.
- `https://docs.continue.dev/cli/hooks` — 404
- `https://docs.continue.dev/guides/cli-hooks` — 404
- `https://docs.continue.dev/guides/cli` — 404

The claims previously made in this file — a `~/.continue/settings.json` /
`.continue/settings.json` hooks block, "17 CLI events", the event names
`PreToolUse` / `UserPromptSubmit` / `TaskCompleted`, and an exit-code-2 blocking
contract — were unsourced and have been removed. The event names were
Claude Code's, which is what first made them suspect.

Two open issues in the Continue repository request that hooks documentation be
written, which is consistent with the feature existing in the CLI while being
undocumented. **A GitHub issue is not a specification.** Nothing is asserted
here about the shape of that feature, because nothing could be sourced.

---

## What is documented

Continue's configuration surface is `config.yaml` (with `config.json`
deprecated). Rules and Prompts are text injected as model context — they shape
generation, they do not intercept or block a tool call.

---

## If you need blocking with Continue

Put the guard outside the agent: a git `pre-commit` hook or a CI gate. See
[`../ci_cd_integration.md`](../ci_cd_integration.md).

---

## Re-verifying this file

When Continue publishes hooks documentation, replace this file with the real
contract and update the provenance line. Until then, treat any Continue hook
example found elsewhere — including in this repository's history — as
unverified.
