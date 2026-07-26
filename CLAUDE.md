# captain-hook — working rules

**What this is**: an Agent Skill and Claude Code plugin that teaches people and
AI agents how to write lifecycle hooks for AI coding agents. The documentation
*is* the product. A wrong config schema in `SKILL.md` ships a broken security
guardrail to every reader, so treat a false doc claim as a bug, not a nit.

## Verify

```bash
npm test    # from the repository root — behavioral cases, pattern sync, doc gates
```

That is the only entry point. It must be green before any commit.

## Five rules that are not obvious from the code

1. **Zero runtime dependencies.** Never add a package — not pytest, not jest,
   not PyYAML. The suite is bash plus stdlib Python on purpose: a hook-adjacent
   script must run with no install step, and CI asserts it with an import-only
   check.

2. **`SECRET_PATTERNS` is generated into the docs.** Edit the list in
   `skills/captain-hook/scripts/captain_hook.py`, then run
   `python3 skills/captain-hook/scripts/sync_patterns.py`. Never hand-edit the
   copies in `references/guards.md`, `references/security_rules.md`, or
   `references/recipes.md` — they sit between `BEGIN:`/`END:` markers and the
   next sync overwrites them. `npm test` fails if you skip the generator.

3. **`verify_docs.py` spells out the forbidden strings on purpose** and
   excludes itself from its own substring gates. Do not "fix" that exclusion.

4. **`plans/` is gitignored.** It holds the audit trail behind most recent
   commits and is not in a fresh clone. If a change needs justifying to a
   future reader, the justification goes in a code comment or a doc, not there.

5. **Every behavior change gets a case in
   `skills/captain-hook/scripts/verify_hooks.sh`**, and where the message is
   the contract — a block reason, an override announcement — the case asserts
   stderr, not just the exit code.

## House style

Comments and docs state the *reason* at the point of the decision. A guard that
deliberately does not fire says why, next to the pattern. That density is
intentional: this repository's whole subject is the gap between what a hook
appears to do and what it does.
