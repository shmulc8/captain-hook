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

  echo -n "  Testing [$name] ... "

  set +e
  python3 "$ROOT_DIR/scripts/captain_hook.py" dispatch "$event" < "$payload_file" > /dev/null 2>&1
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
run_test "GitLab Token (Block)" "$ROOT_DIR/examples/payloads/cursor_beforeSubmitPrompt_gitlab_token.json" "beforeSubmitPrompt" 2
run_test "OpenAI sk-proj Key (Block)" "$ROOT_DIR/examples/payloads/cursor_beforeSubmitPrompt_openai_proj.json" "beforeSubmitPrompt" 2
run_test "Prose containing 'ask-' (Allow)" "$ROOT_DIR/examples/payloads/cursor_beforeSubmitPrompt_clean_prose.json" "beforeSubmitPrompt" 0
run_test "Kebab-case sk- identifier (Allow)" "$ROOT_DIR/examples/payloads/cursor_beforeSubmitPrompt_kebab_case.json" "beforeSubmitPrompt" 0
run_test "Key in written content, post event (Allow+warn)" "$ROOT_DIR/examples/payloads/claude_PostToolUse_write_with_key.json" "PostToolUse" 0
run_test "Key in written content, pre event (Block)" "$ROOT_DIR/examples/payloads/claude_PostToolUse_write_with_key.json" "PreToolUse" 2
run_test "Unknown event still guards (Block)" "$ROOT_DIR/examples/payloads/claude_PreToolUse_bash.json" "SomeFutureEvent" 2
run_test "Force push on a post event (Allow)" "$ROOT_DIR/examples/payloads/windsurf_pre_run_command_secret.json" "post_run_command" 0
run_symlink_tests

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
