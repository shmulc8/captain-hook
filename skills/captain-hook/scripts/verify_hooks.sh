#!/usr/bin/env bash
# Automated Verification Suite for Captain Hook Scripts
set -e

echo "🪝 Verifying Captain Hook Policy Script Execution..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

TEST_PASSED=0
TEST_FAILED=0

run_test() {
  local name="$1"
  local payload_file="$2"
  local event="$3"
  local expected_code="$4"
  local workdir="${5:-$PWD}"

  echo -n "  Testing [$name] ... "

  set +e
  ( cd "$workdir" && python3 "$ROOT_DIR/scripts/captain_hook.py" dispatch "$event" < "$payload_file" ) > /dev/null 2>&1
  actual_code=$?
  set -e

  if [ "$actual_code" -eq "$expected_code" ]; then
    echo "✓ PASSED (Exit Code $actual_code)"
    TEST_PASSED=$((TEST_PASSED + 1))
  else
    echo "❌ FAILED (Expected Exit Code $expected_code, Got $actual_code)"
    TEST_FAILED=$((TEST_FAILED + 1))
  fi
}

# The path-escape guard needs real symlinks, which cannot be committed
# portably, so these cases build their own fixtures and clean up after
# themselves. Note the split: an in-repo symlink is ALLOWED (being a link is
# not a violation), while a path that resolves outside the repo is blocked
# even when the file does not exist yet.
run_symlink_tests() {
  local tmp inrepo
  tmp="$(mktemp -d)"
  inrepo="$ROOT_DIR/.verify_symlink_tmp"
  mkdir -p "$inrepo"
  trap 'rm -rf "$tmp" "$inrepo"' RETURN

  echo "outside" > "$tmp/outside.txt"
  echo "real" > "$inrepo/real.txt"
  ln -s "$inrepo/real.txt" "$inrepo/in_link.txt"
  ln -s "$tmp/outside.txt" "$inrepo/out_link.txt"
  ln -s "$tmp" "$inrepo/outdir"

  payload() {
    printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$1" > "$2"
  }
  payload "$inrepo/real.txt"        "$tmp/p_real.json"
  payload "$inrepo/in_link.txt"     "$tmp/p_inlink.json"
  payload "$inrepo/out_link.txt"    "$tmp/p_outlink.json"
  payload "$inrepo/outdir/new.txt"  "$tmp/p_newvialink.json"

  run_test "Plain in-repo file (Allow)"          "$tmp/p_real.json"       "PreToolUse" 0
  run_test "In-repo symlink to in-repo (Allow)"  "$tmp/p_inlink.json"     "PreToolUse" 0
  run_test "Symlink escaping the repo (Block)"   "$tmp/p_outlink.json"    "PreToolUse" 2
  run_test "New file via symlinked dir (Block)"  "$tmp/p_newvialink.json" "PreToolUse" 2
}

# Run tests
run_test "Clean Command (Allow)" "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_clean.json" "beforeShellExecution" 0
run_test "AWS Key Secret (Block)" "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_secret.json" "beforeShellExecution" 2
run_test "Git Force Push (Block)" "$ROOT_DIR/examples/payloads/claude_PreToolUse_bash.json" "PreToolUse" 2
run_test "Clean Write (Allow)" "$ROOT_DIR/examples/payloads/claude_PreToolUse_write_clean.json" "PreToolUse" 0
run_test "MCP Call (Allow)" "$ROOT_DIR/examples/payloads/cursor_beforeMCPExecution_clean.json" "beforeMCPExecution" 0
run_test "Empty Payload (Allow)" "$ROOT_DIR/examples/payloads/empty.json" "PreToolUse" 0
run_test "Non-JSON stdin (Allow)" "$ROOT_DIR/examples/payloads/malformed.txt" "PreToolUse" 0
run_test "Windsurf tool_info Force Push (Block)" "$ROOT_DIR/examples/payloads/windsurf_pre_run_command_secret.json" "pre_run_command" 2
run_test "Windsurf tool_info Clean (Allow)" "$ROOT_DIR/examples/payloads/windsurf_pre_run_command_clean.json" "pre_run_command" 0
# Antigravity nests tool fields under a camelCase `toolCall`. Before this was
# handled the dispatcher read "" for every field and allowed everything, on the
# one agent that has no exit-code contract to make the failure visible.
run_test "Antigravity toolCall force push (Block)" "$ROOT_DIR/examples/payloads/antigravity_PreToolUse_run_command.json" "PreCommand" 2
run_test "Antigravity toolCall clean (Allow)"      "$ROOT_DIR/examples/payloads/antigravity_PreToolUse_clean.json"       "PreCommand" 0
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
run_test "Key in written content, post event (Warn via 2)" "$ROOT_DIR/examples/payloads/claude_PostToolUse_write_with_key.json" "PostToolUse" 2
run_test "Key in written content, pre event (Block)" "$ROOT_DIR/examples/payloads/claude_PostToolUse_write_with_key.json" "PreToolUse" 2
run_test "Unknown event still guards (Block)" "$ROOT_DIR/examples/payloads/claude_PreToolUse_bash.json" "SomeFutureEvent" 2
run_test "Force push on a post event (Allow)" "$ROOT_DIR/examples/payloads/windsurf_pre_run_command_secret.json" "post_run_command" 0
run_symlink_tests

# Overrides are repo-scoped, so these run inside a throwaway repo with its own
# .captain-hook.json. The malformed-config case is the important one: a config
# that will not parse must never turn the guards off.
run_override_tests() {
  local tmp key
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN
  mkdir -p "$tmp/.git" "$tmp/fixtures"
  key="AKIAAAAAAAAAAAAAAAAA"

  printf '{"tool_name":"Write","tool_input":{"file_path":"fixtures/a.json","content":"%s"}}' "$key" > "$tmp/p_fixture.json"
  printf '{"tool_name":"Write","tool_input":{"file_path":"src/a.json","content":"%s"}}' "$key" > "$tmp/p_src.json"

  echo '{"allow_secrets_in": ["fixtures/*.json"]}' > "$tmp/.captain-hook.json"
  run_test "Secret in allow_secrets_in path (Allow)" "$tmp/p_fixture.json" "PreToolUse" 0 "$tmp"
  run_test "Secret in unlisted path (Block)"         "$tmp/p_src.json"     "PreToolUse" 2 "$tmp"

  # A single-level glob must not reach into a subdirectory: `*` stops at `/`,
  # so an exemption for one directory cannot silently cover a whole subtree.
  printf '{"tool_name":"Write","tool_input":{"file_path":"fixtures/deep/a.json","content":"%s"}}' "$key" > "$tmp/p_deep.json"
  run_test "Secret one level below the glob (Block)" "$tmp/p_deep.json" "PreToolUse" 2 "$tmp"

  echo '{"allow_secrets_in": ["fixtures/**"]}' > "$tmp/.captain-hook.json"
  run_test "Secret under an explicit ** glob (Allow)" "$tmp/p_deep.json" "PreToolUse" 0 "$tmp"

  echo '{"ignore_paths": ["fixtures/*"]}' > "$tmp/.captain-hook.json"
  run_test "Path in ignore_paths (Allow)" "$tmp/p_fixture.json" "PreToolUse" 0 "$tmp"

  echo '{not json' > "$tmp/.captain-hook.json"
  run_test "Malformed config still guards (Block)" "$tmp/p_src.json" "PreToolUse" 2 "$tmp"

  # A string where a list belongs is iterable, so it used to be walked
  # character by character — and one of those characters is `*`.
  echo '{"ignore_paths": "fixtures/**"}' > "$tmp/.captain-hook.json"
  run_test "Wrong-typed config value still guards (Block)" "$tmp/p_src.json" "PreToolUse" 2 "$tmp"

  # An allow_commands entry exempts the pattern it matched, not the denylist.
  printf '{"tool_name":"Bash","tool_input":{"command":"git push origin main --force && rm -rf ~/"}}' > "$tmp/p_chain.json"
  printf '{"tool_name":"Bash","tool_input":{"command":"git push origin main --force"}}' > "$tmp/p_push.json"
  echo '{"allow_commands": ["git push .*--force"]}' > "$tmp/.captain-hook.json"
  run_test "Allowlisted force push (Allow)"                 "$tmp/p_push.json"  "PreToolUse" 0 "$tmp"
  run_test "Allowlist does not cover a chained rm (Block)"  "$tmp/p_chain.json" "PreToolUse" 2 "$tmp"
}
run_override_tests

# Containment: the repository root comes from the payload when the host gives
# one, because a hook is not guaranteed to run with the repo as its cwd.
run_containment_tests() {
  local tmp
  tmp="$(mktemp -d)"
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
  tmp="$(mktemp -d)"
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

echo ""
echo "Verification Summary: $TEST_PASSED Passed, $TEST_FAILED Failed."
if [ "$TEST_FAILED" -ne 0 ]; then
  exit 1
fi
exit 0

# Known uncovered: the post-write auto-format guard. Asserting it requires npx
# or ruff to be installed on the machine running the suite, which would break
# the zero-dependency constraint. Left explicit rather than silently missing.
