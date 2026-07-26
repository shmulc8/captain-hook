# Invoking `captain-hook`

There is no `captain-hook` binary on your `PATH`. The dispatcher is a single
standalone Python 3 script. Invoke it by path.

## The canonical invocation

```bash
python3 /absolute/path/to/captain-hook/skills/captain-hook/scripts/captain_hook.py dispatch <EventName>
```

The script reads the host agent's JSON payload from `stdin` and exits `0`
(allow) or `2` (block) on the agents that use exit codes. Antigravity does not:
it reads a `decision` object from stdout, so pass `--decision-json` there — see
the table in [`SKILL.md`](SKILL.md) section 1. Requires Python 3.9+ and no
third-party packages.

## Substituting the path in the shipped templates

Every template in `examples/` uses the placeholder `<CAPTAIN_HOOK>`. Replace it
with the absolute path above before use:

```bash
CH="python3 $(pwd)/skills/captain-hook/scripts/captain_hook.py"
# Run this against whichever config file(s) you copied — one per agent.
for f in .cursor/hooks.json .windsurf/hooks.json .agents/hooks.json .claude/settings.json .aider.conf.yml; do
  [ -f "$f" ] || continue
  python3 - "$f" "$CH" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text(encoding="utf-8").replace("<CAPTAIN_HOOK>", sys.argv[2]), encoding="utf-8")
print("substituted:", p)
PY
done
```

Use an **absolute** path. Hooks do not reliably run with your repository as the
working directory.

For Claude Code specifically there is a second, substitution-free form: install
captain-hook as a Claude Code plugin and use `${CLAUDE_PLUGIN_ROOT}` instead of
an absolute path — see the next section. The shipped template uses the
placeholder so that both install paths start from the same file; a `git clone`
install has no `${CLAUDE_PLUGIN_ROOT}`, and a hook whose command does not
resolve exits 1, which permits the action rather than blocking it.

## Claude Code plugin installs

When `captain-hook` is installed as a Claude Code plugin, the plugin root is
available to hook commands as `${CLAUDE_PLUGIN_ROOT}`, so no substitution is
needed:

```
python3 "${CLAUDE_PLUGIN_ROOT}"/skills/captain-hook/scripts/captain_hook.py dispatch PreToolUse
```

## Verifying it works

```bash
echo '{"command":"git push origin main --force"}' \
  | python3 skills/captain-hook/scripts/captain_hook.py dispatch PreCommand
echo $?   # 2 — blocked
```

If you get `command not found` or `No such file or directory`, the path is
wrong. **Do not ignore it**: Cursor and Windsurf are fail-open by default, so a
hook that cannot start is a hook that silently permits everything.
