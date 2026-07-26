# Invoking `captain-hook`

There is no `captain-hook` binary on your `PATH`. The dispatcher is a single
standalone Python 3 script. Invoke it by path.

## The canonical invocation

```bash
python3 /absolute/path/to/captain-hook/skills/captain-hook/scripts/captain_hook.py dispatch <EventName>
```

The script reads the host agent's JSON payload from `stdin` and exits `0`
(allow) or `2` (block). It requires Python 3.9+ and no third-party packages.

## Substituting the path in the shipped templates

Every template in `examples/` uses the placeholder `<CAPTAIN_HOOK>`. Replace it
with the absolute path above before use:

```bash
CH="$(pwd)/skills/captain-hook/scripts/captain_hook.py"
sed -i '' "s|<CAPTAIN_HOOK>|python3 $CH|g" .cursor/hooks.json   # macOS
sed -i    "s|<CAPTAIN_HOOK>|python3 $CH|g" .cursor/hooks.json   # Linux
```

Use an **absolute** path. Hooks do not reliably run with your repository as the
working directory.

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
