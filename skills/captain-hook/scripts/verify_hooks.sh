#!/usr/bin/env bash
# Automated Verification Suite for Captain Hook Scripts
set -e

echo "🪝 Verifying Captain Hook Policy Script Execution..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
# The repository root, two levels above skills/captain-hook. Tests must not
# depend on where the suite was invoked from: with $PWD as the default, running
# this script from outside the repo made _repo_root() resolve to the caller's
# directory and turned in-repo cases into false "blocked" failures.
REPO_DIR="$(dirname "$(dirname "$ROOT_DIR")")"

TEST_PASSED=0
TEST_FAILED=0

# Fixtures are torn down on any exit path, not just a clean return: `set -e`
# is on, so a failing `ln -s` (a filesystem without symlink support) aborts
# mid-function and a RETURN trap never fires.
CH_TMPDIRS=()
# shellcheck disable=SC2329  # invoked by the EXIT/INT/TERM trap below, not directly
cleanup_tmpdirs() { [ ${#CH_TMPDIRS[@]} -eq 0 ] || rm -rf "${CH_TMPDIRS[@]}"; }
trap cleanup_tmpdirs EXIT INT TERM

# Sets CH_LAST_TMPDIR rather than printing the path: a command substitution
# runs in a subshell, so an array append inside one would be discarded and
# nothing would ever reach the EXIT trap.
new_tmpdir() {
  CH_LAST_TMPDIR="$(mktemp -d)"
  CH_TMPDIRS+=("$CH_LAST_TMPDIR")
}

run_test() {
  local name="$1"
  local payload_file="$2"
  local event="$3"
  local expected_code="$4"
  local workdir="${5:-$REPO_DIR}"
  local expect_err="${6:-}"

  echo -n "  Testing [$name] ... "

  local err
  set +e
  err="$( ( cd "$workdir" && python3 "$ROOT_DIR/scripts/captain_hook.py" dispatch "$event" < "$payload_file" ) 2>&1 >/dev/null )"
  actual_code=$?
  set -e

  if [ "$actual_code" -ne "$expected_code" ]; then
    echo "❌ FAILED (Expected Exit Code $expected_code, Got $actual_code)"
    TEST_FAILED=$((TEST_FAILED + 1))
    return
  fi
  # The message IS the contract for blocks and for override announcements: an
  # override nobody can see is the thing the override design exists to avoid
  # (captain_hook.py, load_config docstring).
  if [ -n "$expect_err" ] && [[ "$err" != *"$expect_err"* ]]; then
    echo "❌ FAILED (stderr missing '$expect_err'; got: ${err:-<empty>})"
    TEST_FAILED=$((TEST_FAILED + 1))
    return
  fi
  echo "✓ PASSED (Exit Code $actual_code)"
  TEST_PASSED=$((TEST_PASSED + 1))
}

# Antigravity decides on stdout JSON, not exit codes, so run_test's exit-code
# assertion cannot see this contract at all. A regression here fails open on
# every Antigravity guard with the suite still green.
run_decision_test() {
  local name="$1" payload_file="$2" event="$3" expected="$4"
  echo -n "  Testing [$name] ... "
  local out
  set +e
  out="$(python3 "$ROOT_DIR/scripts/captain_hook.py" dispatch --decision-json "$event" < "$payload_file" 2>/dev/null)"
  set -e
  if [[ "$out" == *"$expected"* ]]; then
    echo "✓ PASSED"
    TEST_PASSED=$((TEST_PASSED + 1))
  else
    echo "❌ FAILED (stdout '$out' does not contain '$expected')"
    TEST_FAILED=$((TEST_FAILED + 1))
  fi
}

# The path-escape guard needs real symlinks, which cannot be committed
# portably, so these cases build their own fixtures and clean up after
# themselves. Note the split: an in-repo symlink is ALLOWED (being a link is
# not a violation), while a path that resolves outside the repo is blocked
# even when the file does not exist yet.
run_symlink_tests() {
  local tmp repo outside
  new_tmpdir; tmp="$CH_LAST_TMPDIR"
  trap 'rm -rf "$tmp"' RETURN
  repo="$tmp/repo"
  outside="$tmp/outside"
  mkdir -p "$repo/.git" "$outside"

  echo "outside" > "$outside/outside.txt"
  echo "real" > "$repo/real.txt"
  ln -s "$repo/real.txt" "$repo/in_link.txt"
  ln -s "$outside/outside.txt" "$repo/out_link.txt"
  ln -s "$outside" "$repo/outdir"

  payload() {
    printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$1" > "$2"
  }
  payload "$repo/real.txt"        "$tmp/p_real.json"
  payload "$repo/in_link.txt"     "$tmp/p_inlink.json"
  payload "$repo/out_link.txt"    "$tmp/p_outlink.json"
  payload "$repo/outdir/new.txt"  "$tmp/p_newvialink.json"

  run_test "Plain in-repo file (Allow)"          "$tmp/p_real.json"       "PreToolUse" 0 "$repo"
  run_test "In-repo symlink to in-repo (Allow)"  "$tmp/p_inlink.json"     "PreToolUse" 0 "$repo"
  run_test "Symlink escaping the repo (Block)"   "$tmp/p_outlink.json"    "PreToolUse" 2 "$repo"
  run_test "New file via symlinked dir (Block)"  "$tmp/p_newvialink.json" "PreToolUse" 2 "$repo"
}

# The default-workdir cases below do not depend on the repository's own
# .captain-hook.json — verified by running the suite with it moved aside.
# If you add a case that does, give it its own fixture repository instead,
# the way run_override_tests does.

# Run tests
run_test "Clean Command (Allow)" "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_clean.json" "beforeShellExecution" 0
run_test "AWS Key Secret (Block)" "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_secret.json" "beforeShellExecution" 2 "$REPO_DIR" "Secret key pattern detected"
run_test "Git Force Push (Block)" "$ROOT_DIR/examples/payloads/claude_PreToolUse_bash.json" "PreToolUse" 2 "$REPO_DIR" "Blocked: force push"
run_test "Clean Write (Allow)" "$ROOT_DIR/examples/payloads/claude_PreToolUse_write_clean.json" "PreToolUse" 0
run_test "MCP Call (Allow)" "$ROOT_DIR/examples/payloads/cursor_beforeMCPExecution_clean.json" "beforeMCPExecution" 0
run_test "Empty Payload (Allow)" "$ROOT_DIR/examples/payloads/empty.json" "PreToolUse" 0
run_test "Non-JSON stdin (Allow)" "$ROOT_DIR/examples/payloads/malformed.txt" "PreToolUse" 0
run_test "Windsurf tool_info Force Push (Block)" "$ROOT_DIR/examples/payloads/windsurf_pre_run_command_force_push.json" "pre_run_command" 2
run_test "Windsurf tool_info secret (Block)" "$ROOT_DIR/examples/payloads/windsurf_pre_run_command_secret.json" "pre_run_command" 2 "$REPO_DIR" "Secret key pattern detected"
# Non-JSON stdin becomes {"raw": ...}; that chain is the ONLY route by which a
# secret in plain-text stdin is ever scanned.
run_test "Secret in non-JSON stdin (Block)" "$ROOT_DIR/examples/payloads/malformed_secret.txt" "PreToolUse" 2 "$REPO_DIR" "Secret key pattern detected"
run_test "Windsurf tool_info Clean (Allow)" "$ROOT_DIR/examples/payloads/windsurf_pre_run_command_clean.json" "pre_run_command" 0
# Antigravity nests tool fields under a camelCase `toolCall`. Before this was
# handled the dispatcher read "" for every field and allowed everything, on the
# one agent that has no exit-code contract to make the failure visible.
run_test "Antigravity toolCall force push (Block)" "$ROOT_DIR/examples/payloads/antigravity_PreToolUse_run_command.json" "PreCommand" 2
run_test "Antigravity toolCall clean (Allow)"      "$ROOT_DIR/examples/payloads/antigravity_PreToolUse_clean.json"       "PreCommand" 0
# OpenHands is in the blocking roster; its snake_case config keys must reach the
# same guards as every other agent's, and its post events must not pretend to block.
run_test "OpenHands pre_tool_use denylist (Block)" "$ROOT_DIR/examples/payloads/openhands_pre_tool_use_bash.json" "pre_tool_use"  2
run_test "OpenHands post_tool_use cannot block (Allow)" "$ROOT_DIR/examples/payloads/openhands_pre_tool_use_bash.json" "post_tool_use" 0
run_test "GitLab Token (Block)" "$ROOT_DIR/examples/payloads/cursor_beforeSubmitPrompt_gitlab_token.json" "beforeSubmitPrompt" 2
run_test "OpenAI sk-proj Key (Block)" "$ROOT_DIR/examples/payloads/cursor_beforeSubmitPrompt_openai_proj.json" "beforeSubmitPrompt" 2
# Real sk-proj- keys carry hyphens inside the body. A pattern that only accepts
# an unbroken alphanumeric run passes the fixture above and misses every actual key.
run_test "OpenAI sk-proj Key with hyphens (Block)" "$ROOT_DIR/examples/payloads/cursor_beforeSubmitPrompt_openai_proj_hyphens.json" "beforeSubmitPrompt" 2
run_test "Prose containing 'ask-' (Allow)" "$ROOT_DIR/examples/payloads/cursor_beforeSubmitPrompt_clean_prose.json" "beforeSubmitPrompt" 0
run_test "Kebab-case sk- identifier (Allow)" "$ROOT_DIR/examples/payloads/cursor_beforeSubmitPrompt_kebab_case.json" "beforeSubmitPrompt" 0
run_test "rm with split flags (Block)" "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_rm_split_flags.json" "beforeShellExecution" 2
# One destructive flag is enough — `rm -f ~/.ssh/id_rsa` needs no -r to matter.
run_test "rm with a single flag (Block)" "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_rm_single_flag.json" "beforeShellExecution" 2
# Four literal forms that needed no shell syntax to get past the denylist. The
# documented ceiling is shell syntax; these were plain commands.
run_test "dd against a real device (Block)"   "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_dd_device.json"       "beforeShellExecution" 2
run_test "rm with an -- separator (Block)"    "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_rm_dashdash.json"    "beforeShellExecution" 2
run_test "force push, short flag (Block)"     "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_push_short_flag.json" "beforeShellExecution" 2
run_test "chmod with reordered args (Block)"  "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_chmod_reordered.json" "beforeShellExecution" 2
# A non-string field used to raise, and an exception exits 1, which blocks nowhere.
run_test "argv-array command (Block)" "$ROOT_DIR/examples/payloads/claude_PreToolUse_bash_argv_array.json" "PreToolUse" 2
run_test "Force push with lease (Allow)" "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_force_with_lease.json" "beforeShellExecution" 0
# Documents a KNOWN GAP: variable expansion is not detected. If this ever
# starts returning 2, the denylist got stronger — update guards.md's limits
# table rather than deleting this case.
run_test "rm through a variable — KNOWN GAP (Allow)" "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_rm_var.json" "beforeShellExecution" 0
# Exit 2 on Claude Code's PostToolUse does not block — the write already
# happened — it is the only exit code that shows stderr to the model, which is
# the point: the agent that just wrote the key gets told about it.
run_test "Key in written content, post event (Warn via 2)" "$ROOT_DIR/examples/payloads/claude_PostToolUse_write_with_key.json" "PostToolUse" 2 "$REPO_DIR" "cannot be blocked"
run_test "Key in written content, pre event (Block)" "$ROOT_DIR/examples/payloads/claude_PostToolUse_write_with_key.json" "PreToolUse" 2
run_test "Unknown event still guards (Block)" "$ROOT_DIR/examples/payloads/claude_PreToolUse_bash.json" "SomeFutureEvent" 2
run_test "Force push on a post event (Allow)" "$ROOT_DIR/examples/payloads/windsurf_pre_run_command_force_push.json" "post_run_command" 0
run_symlink_tests

# Overrides are repo-scoped, so these run inside a throwaway repo with its own
# .captain-hook.json. The malformed-config case is the important one: a config
# that will not parse must never turn the guards off.
run_override_tests() {
  local tmp key
  new_tmpdir; tmp="$CH_LAST_TMPDIR"
  trap 'rm -rf "$tmp"' RETURN
  mkdir -p "$tmp/.git" "$tmp/fixtures"
  key="AKIAAAAAAAAAAAAAAAAA"

  printf '{"tool_name":"Write","tool_input":{"file_path":"fixtures/a.json","content":"%s"}}' "$key" > "$tmp/p_fixture.json"
  printf '{"tool_name":"Write","tool_input":{"file_path":"src/a.json","content":"%s"}}' "$key" > "$tmp/p_src.json"

  echo '{"allow_secrets_in": ["fixtures/*.json"]}' > "$tmp/.captain-hook.json"
  run_test "Secret in allow_secrets_in path (Allow)" "$tmp/p_fixture.json" "PreToolUse" 0 "$tmp" "allow_secrets_in"
  run_test "Secret in unlisted path (Block)"         "$tmp/p_src.json"     "PreToolUse" 2 "$tmp"

  # A single-level glob must not reach into a subdirectory: `*` stops at `/`,
  # so an exemption for one directory cannot silently cover a whole subtree.
  printf '{"tool_name":"Write","tool_input":{"file_path":"fixtures/deep/a.json","content":"%s"}}' "$key" > "$tmp/p_deep.json"
  run_test "Secret one level below the glob (Block)" "$tmp/p_deep.json" "PreToolUse" 2 "$tmp"

  echo '{"allow_secrets_in": ["fixtures/**"]}' > "$tmp/.captain-hook.json"
  run_test "Secret under an explicit ** glob (Allow)" "$tmp/p_deep.json" "PreToolUse" 0 "$tmp"

  # `**/` matches whole directory components. Dropping the separator made
  # `**/fixtures` also cover `src/myfixtures` — an exemption wider than it
  # reads, in the one file that is supposed to be reviewed like a firewall rule.
  mkdir -p "$tmp/myfixtures"
  printf '{"tool_name":"Write","tool_input":{"file_path":"myfixtures/a.json","content":"%s"}}' "$key" > "$tmp/p_lookalike.json"
  printf '{"tool_name":"Write","tool_input":{"file_path":"deep/fixtures/a.json","content":"%s"}}' "$key" > "$tmp/p_nested_dir.json"
  echo '{"allow_secrets_in": ["**/fixtures/*.json"]}' > "$tmp/.captain-hook.json"
  run_test "Look-alike directory is not exempt (Block)" "$tmp/p_lookalike.json"  "PreToolUse" 2 "$tmp"
  run_test "Nested directory is exempt (Allow)"         "$tmp/p_nested_dir.json" "PreToolUse" 0 "$tmp"

  echo '{"ignore_paths": ["fixtures/*"]}' > "$tmp/.captain-hook.json"
  run_test "Path in ignore_paths (Allow)" "$tmp/p_fixture.json" "PreToolUse" 0 "$tmp" "ignore_paths"

  echo '{not json' > "$tmp/.captain-hook.json"
  run_test "Malformed config still guards (Block)" "$tmp/p_src.json" "PreToolUse" 2 "$tmp" "could not read .captain-hook.json"

  # A string where a list belongs is iterable, so it used to be walked
  # character by character — and one of those characters is `*`.
  echo '{"ignore_paths": "fixtures/**"}' > "$tmp/.captain-hook.json"
  run_test "Wrong-typed config value still guards (Block)" "$tmp/p_src.json" "PreToolUse" 2 "$tmp"

  # An allow_commands entry exempts the pattern it matched, not the denylist.
  printf '{"tool_name":"Bash","tool_input":{"command":"git push origin main --force && rm -rf ~/"}}' > "$tmp/p_chain.json"
  printf '{"tool_name":"Bash","tool_input":{"command":"git push origin main --force"}}' > "$tmp/p_push.json"
  echo '{"allow_commands": ["git push .*--force"]}' > "$tmp/.captain-hook.json"
  run_test "Allowlisted force push (Allow)"                 "$tmp/p_push.json"  "PreToolUse" 0 "$tmp" "allow_commands"
  run_test "Allowlist does not cover a chained rm (Block)"  "$tmp/p_chain.json" "PreToolUse" 2 "$tmp"

  # A config that parses but is not an object, and an invalid allow_commands
  # regex. Both raise without their handlers, and an exception exits 1, which
  # blocks nowhere — every guard off, for that repository, silently.
  echo '["fixtures/**"]' > "$tmp/.captain-hook.json"
  run_test "Non-object config still guards (Block)" "$tmp/p_src.json" "PreToolUse" 2 "$tmp" "must be a JSON object"

  echo '{"allow_commands": ["git push ("]}' > "$tmp/.captain-hook.json"
  run_test "Invalid allow_commands regex still guards (Block)" "$tmp/p_push.json" "PreToolUse" 2 "$tmp" "invalid allow_commands regex"

  # A root-level path is the ONLY shape that detects the character-walk bug:
  # the stray pattern is `*`, which compiles to [^/]* and cannot match
  # `src/a.json`. With `src/a.json` this case passes even with the type guard
  # deleted.
  printf '{"tool_name":"Write","tool_input":{"file_path":"top.json","content":"%s"}}' "$key" > "$tmp/p_top.json"
  echo '{"ignore_paths": "fixtures/**"}' > "$tmp/.captain-hook.json"
  run_test "Wrong-typed config, root-level path (Block)" "$tmp/p_top.json" "PreToolUse" 2 "$tmp"
}
run_override_tests

# Containment: the repository root comes from the payload when the host gives
# one, because a hook is not guaranteed to run with the repo as its cwd.
run_containment_tests() {
  local tmp
  new_tmpdir; tmp="$CH_LAST_TMPDIR"
  trap 'rm -rf "$tmp"' RETURN
  mkdir -p "$tmp/repo/.git" "$tmp/repo/fixtures" "$tmp/elsewhere"

  echo '{"allow_secrets_in": ["fixtures/*.json"]}' > "$tmp/repo/.captain-hook.json"
  printf '{"cwd":"%s","tool_name":"Write","tool_input":{"file_path":"%s","content":"AKIAAAAAAAAAAAAAAAAA"}}' \
    "$tmp/repo" "$tmp/repo/fixtures/a.json" > "$tmp/p_cwd_fixture.json"
  printf '{"cwd":"%s","tool_name":"Write","tool_input":{"file_path":"%s","content":"AKIAAAAAAAAAAAAAAAAA"}}' \
    "$tmp/repo" "$tmp/repo/src.json" > "$tmp/p_cwd_src.json"
  printf '{"tool_info":{"cwd":"%s"},"tool_name":"Write","tool_input":{"file_path":"%s"}}' \
    "$tmp/repo" "/etc/passwd" > "$tmp/p_cwd_escape.json"

  run_test "Payload cwd finds the config (Allow)"   "$tmp/p_cwd_fixture.json" "PreToolUse" 0 "$tmp/elsewhere"
  run_test "Payload cwd keeps guards on (Block)"    "$tmp/p_cwd_src.json"     "PreToolUse" 2 "$tmp/elsewhere"
  run_test "Payload cwd bounds the repo (Block)"    "$tmp/p_cwd_escape.json"  "PreToolUse" 2 "$tmp/elsewhere"
}
run_containment_tests

# The two halves of the containment check must measure from the same origin.
# The root comes from the payload; a relative path must too. When the host
# launches the hook from a directory other than the agent's, resolving the
# path against the PROCESS cwd either lets `../x` read as in-repo (escape) or
# reports an ordinary in-repo file as escaping (false block).
run_relative_path_tests() {
  local tmp
  new_tmpdir; tmp="$CH_LAST_TMPDIR"
  trap 'rm -rf "$tmp"' RETURN
  mkdir -p "$tmp/repo/.git" "$tmp/repo/sub" "$tmp/repo/src" "$tmp/elsewhere"

  printf '{"cwd":"%s","tool_name":"Write","tool_input":{"file_path":"../evil.txt"}}' \
    "$tmp/repo" > "$tmp/p_rel_escape.json"
  printf '{"cwd":"%s","tool_name":"Write","tool_input":{"file_path":"src/app.py"}}' \
    "$tmp/repo" > "$tmp/p_rel_inrepo.json"

  # Hook launched BELOW the agent's cwd: `../evil.txt` is outside the repo.
  run_test "Relative escape, hook run from a subdir (Block)" \
    "$tmp/p_rel_escape.json" "PreToolUse" 2 "$tmp/repo/sub"
  # Hook launched OUTSIDE the repo: `src/app.py` is an ordinary in-repo write.
  run_test "Relative in-repo path, hook run outside (Allow)" \
    "$tmp/p_rel_inrepo.json" "PreToolUse" 0 "$tmp/elsewhere"
}
run_relative_path_tests

# The formatter has the same two-origin hazard, and it is the half the
# containment check above cannot catch: escapes_repo clears the file resolved
# against the PAYLOAD's cwd, so an argv rebuilt from the bare relative path
# sends the formatter at a same-named file next to wherever the host happened
# to launch the hook — guard and tool acting on two different files.
run_formatter_path_tests() {
  local tmp want got
  new_tmpdir; tmp="$CH_LAST_TMPDIR"
  trap 'rm -rf "$tmp"' RETURN
  mkdir -p "$tmp/repo/.git" "$tmp/elsewhere" "$tmp/bin"
  printf 'x = 1\n' > "$tmp/repo/app.py"
  # The decoy is what a bare os.path.exists("app.py") finds when the hook runs
  # from outside the repository — and what the formatter then rewrites.
  printf 'x = 2\n' > "$tmp/elsewhere/app.py"
  # Stub formatter recording the path it was handed. A real ruff is not needed
  # to check the argv, and requiring one would break the no-dependency rule.
  printf '#!/bin/sh\nprintf "%%s\\n" "$2" >> "%s/argv.log"\n' "$tmp" > "$tmp/bin/ruff"
  chmod +x "$tmp/bin/ruff"
  printf '{"cwd":"%s","tool_name":"Write","tool_input":{"file_path":"app.py"}}' \
    "$tmp/repo" > "$tmp/p_fmt.json"

  echo -n "  Testing [Formatter targets the payload's cwd, not the hook's] ... "
  ( cd "$tmp/elsewhere" && PATH="$tmp/bin:$PATH" \
      python3 "$ROOT_DIR/scripts/captain_hook.py" dispatch PostToolUse \
      < "$tmp/p_fmt.json" ) >/dev/null 2>&1 || true
  # pwd -P for the same reason as run_node_bin_tests: macOS hands back /var/...
  # for a path the dispatcher reports as /private/var/....
  want="$(cd "$tmp/repo" && pwd -P)/app.py"
  got="$(cat "$tmp/argv.log" 2>/dev/null || true)"
  if [ "$got" = "$want" ]; then
    echo "✓ PASSED"; TEST_PASSED=$((TEST_PASSED + 1))
  else
    echo "❌ FAILED (formatter got '${got:-<never ran>}', want '$want')"
    TEST_FAILED=$((TEST_FAILED + 1))
  fi
}
run_formatter_path_tests

# The pre-commit fallback is the only enforcement path this repo offers the
# five agents that cannot block. It used to exit 0 unconditionally: git gives
# a commit hook no stdin and no arguments, so every extracted field was empty.
run_precommit_tests() {
  local tmp
  new_tmpdir; tmp="$CH_LAST_TMPDIR"
  trap 'rm -rf "$tmp"' RETURN
  git -C "$tmp" init -q
  git -C "$tmp" config user.email t@example.com
  git -C "$tmp" config user.name t

  printf 'AKIAAAAAAAAAAAAAAAAA\n' > "$tmp/leak.txt"
  git -C "$tmp" add leak.txt
  run_test "Staged secret blocks the commit (Block)" "$ROOT_DIR/examples/payloads/empty.json" "PreCommit" 2 "$tmp"

  git -C "$tmp" reset -q
  printf 'hello world\n' > "$tmp/clean.txt"
  git -C "$tmp" add clean.txt
  run_test "Clean staged change (Allow)" "$ROOT_DIR/examples/payloads/empty.json" "PreCommit" 0 "$tmp"

  git -C "$tmp" reset -q
  run_test "Nothing staged (Allow)" "$ROOT_DIR/examples/payloads/empty.json" "PreCommit" 0 "$tmp"
}
run_precommit_tests

run_decision_test "Decision JSON deny on a blocked command" "$ROOT_DIR/examples/payloads/claude_PreToolUse_bash.json"           "PreToolUse"  '"decision": "deny"'
run_decision_test "Decision JSON carries the block reason"  "$ROOT_DIR/examples/payloads/claude_PreToolUse_bash.json"           "PreToolUse"  '"reason"'
run_decision_test "Decision JSON allow on a clean command"  "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_clean.json" "PreCommand"  '"decision": "allow"'
run_decision_test "Decision JSON is empty on a post event"  "$ROOT_DIR/examples/payloads/claude_PreToolUse_write_clean.json"     "PostToolUse" '{}'

# The walk must stop at the repository root. Without the clamp a stray
# `npm install` in $HOME puts an executable in this hook's path — the
# arbitrary-code-execution problem `npx` was dropped to avoid.
run_node_bin_tests() {
  local tmp
  new_tmpdir; tmp="$CH_LAST_TMPDIR"
  trap 'rm -rf "$tmp"' RETURN
  mkdir -p "$tmp/outer/node_modules/.bin" "$tmp/outer/repo/.git" "$tmp/outer/repo/src"
  printf '#!/bin/sh\nexit 0\n' > "$tmp/outer/node_modules/.bin/prettier"
  chmod +x "$tmp/outer/node_modules/.bin/prettier"

  echo -n "  Testing [node_modules walk stops at the repo root] ... "
  if python3 -c '
import sys
sys.path.insert(0, "'"$SCRIPT_DIR"'")
from captain_hook import _local_node_bin
root = "'"$tmp"'/outer/repo"
assert _local_node_bin("prettier", root, root + "/src") is None, "escaped the repo root"
' 2>/dev/null; then
    echo "✓ PASSED"; TEST_PASSED=$((TEST_PASSED + 1))
  else
    echo "❌ FAILED (the walk reached an ancestor outside the repository)"; TEST_FAILED=$((TEST_FAILED + 1))
  fi

  mkdir -p "$tmp/outer/repo/node_modules/.bin"
  printf '#!/bin/sh\nexit 0\n' > "$tmp/outer/repo/node_modules/.bin/prettier"
  chmod +x "$tmp/outer/repo/node_modules/.bin/prettier"

  echo -n "  Testing [node_modules inside the repo is found] ... "
  if python3 -c '
import os, sys
sys.path.insert(0, "'"$SCRIPT_DIR"'")
from captain_hook import _local_node_bin
root = "'"$tmp"'/outer/repo"
found = _local_node_bin("prettier", root, root + "/src")
# realpath both sides: on macOS mktemp -d hands back /var/..., which resolves
# to /private/var/..., and the returned path is always resolved.
assert found and found.startswith(os.path.realpath(root)), found
' 2>/dev/null; then
    echo "✓ PASSED"; TEST_PASSED=$((TEST_PASSED + 1))
  else
    echo "❌ FAILED (an in-repo binary was not found)"; TEST_FAILED=$((TEST_FAILED + 1))
  fi
}
run_node_bin_tests

echo -n "  Testing [Formatter never raises on a missing or hung binary] ... "
if python3 -c '
import sys
sys.path.insert(0, "'"$SCRIPT_DIR"'")
import captain_hook
# A missing binary must warn, not raise: the formatter is best-effort and must
# never change the hook s decision.
captain_hook._run_formatter(["/nonexistent/captain-hook-formatter"], "x.js")
# A hung formatter must be killed by the timeout, not inherited by the agent.
captain_hook.FORMAT_TIMEOUT_SECONDS = 1
captain_hook._run_formatter(["sleep", "5"], "x.js")
' 2>/dev/null; then
  echo "✓ PASSED"
  TEST_PASSED=$((TEST_PASSED + 1))
else
  echo "❌ FAILED (the formatter raised instead of warning)"
  TEST_FAILED=$((TEST_FAILED + 1))
fi

# aider passes edited filenames as ARGUMENTS and sends no JSON on stdin, so
# argv is the only place the path appears. Both halves of this have broken
# before: a stricter argparse rejected the arguments outright, and dropping the
# fallback silently disables the path guard for aider entirely.
run_argv_tests() {
  local tmp
  new_tmpdir; tmp="$CH_LAST_TMPDIR"
  trap 'rm -rf "$tmp"' RETURN
  mkdir -p "$tmp/.git"
  printf 'x\n' > "$tmp/in_repo.txt"

  echo -n "  Testing [argv path outside the repo (Block)] ... "
  set +e
  ( cd "$tmp" && python3 "$ROOT_DIR/scripts/captain_hook.py" dispatch PreWrite /etc/passwd < /dev/null ) >/dev/null 2>&1
  code=$?
  set -e
  if [ "$code" -eq 2 ]; then echo "✓ PASSED"; TEST_PASSED=$((TEST_PASSED + 1));
  else echo "❌ FAILED (expected 2, got $code)"; TEST_FAILED=$((TEST_FAILED + 1)); fi

  echo -n "  Testing [argv path inside the repo (Allow)] ... "
  set +e
  ( cd "$tmp" && python3 "$ROOT_DIR/scripts/captain_hook.py" dispatch PreWrite "$tmp/in_repo.txt" < /dev/null ) >/dev/null 2>&1
  code=$?
  set -e
  if [ "$code" -eq 0 ]; then echo "✓ PASSED"; TEST_PASSED=$((TEST_PASSED + 1));
  else echo "❌ FAILED (expected 0, got $code)"; TEST_FAILED=$((TEST_FAILED + 1)); fi
}
run_argv_tests

echo -n "  Testing [Repo root of '/' does not blanket-block] ... "
if python3 -c '
import sys
sys.path.insert(0, "'"$SCRIPT_DIR"'")
from captain_hook import escapes_repo
assert escapes_repo("/app/src/main.py", root="/") == (False, "/app/src/main.py")
assert escapes_repo("/README.md", root="/")[0] is False
' 2>/dev/null; then
  echo "✓ PASSED"
  TEST_PASSED=$((TEST_PASSED + 1))
else
  echo "❌ FAILED (a root of '/' still reports every path as escaping)"
  TEST_FAILED=$((TEST_FAILED + 1))
fi

echo -n "  Testing [Flat Claude schema gate sees pretty-printed JSON] ... "
if python3 -c '
import sys
sys.path.insert(0, "'"$SCRIPT_DIR"'")
from verify_docs import FLAT_HOOK_RE
block = "\"PreToolUse\": [\n  {\n    \"command\": \"x\"\n  }\n]"
assert FLAT_HOOK_RE.search(block), "regex no longer spans newlines"
assert not any(FLAT_HOOK_RE.search(l) for l in block.splitlines()), "a per-line scan would suffice"
' 2>/dev/null; then
  echo "✓ PASSED"
  TEST_PASSED=$((TEST_PASSED + 1))
else
  echo "❌ FAILED (the gate is back to a per-line scan it cannot match)"
  TEST_FAILED=$((TEST_FAILED + 1))
fi

echo -n "  Testing [Doc gates cover the repository root, not plans/] ... "
if python3 -c '
import sys
sys.path.insert(0, "'"$SCRIPT_DIR"'")
import verify_docs
md = [verify_docs.rel(p) for p in verify_docs.markdown_files()]
tx = [verify_docs.rel(p) for p in verify_docs.text_files()]
assert "README.md" in md, "repo-root README.md is not scanned"
assert ".claude-plugin/plugin.json" in tx, "plugin.json is not scanned"
assert not any(p.startswith("plans/") for p in md + tx), "plans/ is being scanned"
' 2>/dev/null; then
  echo "✓ PASSED"
  TEST_PASSED=$((TEST_PASSED + 1))
else
  echo "❌ FAILED (gate scope regressed)"
  TEST_FAILED=$((TEST_FAILED + 1))
fi

echo ""
echo "🪝 Verifying secret-pattern catalog is in sync..."
set +e
python3 "$SCRIPT_DIR/sync_patterns.py" --check
sync_status=$?
set -e
if [ "$sync_status" -ne 0 ]; then
  TEST_FAILED=$((TEST_FAILED + 1))
fi

echo ""
echo "🪝 Verifying documentation consistency..."
set +e
python3 "$SCRIPT_DIR/verify_docs.py"
doc_status=$?
set -e
if [ "$doc_status" -ne 0 ]; then
  TEST_FAILED=$((TEST_FAILED + 1))
fi

# A suite whose result depends on where it was invoked from has an ambiguous
# red, and an ambiguous red gets ignored. The environment variable stops the
# inner run from invoking a third one.
if [ -z "${CAPTAIN_HOOK_SELFTEST:-}" ]; then
  echo ""
  echo -n "  Testing [Suite is independent of the caller's directory] ... "
  set +e
  ( cd / && CAPTAIN_HOOK_SELFTEST=1 bash "$SCRIPT_DIR/verify_hooks.sh" >/dev/null 2>&1 )
  selftest_status=$?
  set -e
  if [ "$selftest_status" -eq 0 ]; then
    echo "✓ PASSED"
    TEST_PASSED=$((TEST_PASSED + 1))
  else
    echo "❌ FAILED (the suite does not pass when run from /)"
    TEST_FAILED=$((TEST_FAILED + 1))
  fi
fi

echo ""
echo "Verification Summary: $TEST_PASSED Passed, $TEST_FAILED Failed."
if [ "$TEST_FAILED" -ne 0 ]; then
  exit 1
fi
exit 0

# Known uncovered: the post-write auto-format guard. Asserting it requires npx
# or ruff to be installed on the machine running the suite, which would break
# the zero-dependency constraint. Left explicit rather than silently missing.
