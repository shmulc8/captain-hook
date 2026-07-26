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

# The symlink guard needs a real symlink, which cannot be committed portably,
# so this case builds its own fixture and cleans up after itself.
run_symlink_tests() {
  local tmp
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN

  echo "real" > "$tmp/real.txt"
  ln -s "$tmp/real.txt" "$tmp/link.txt"

  printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$tmp/link.txt" > "$tmp/link_payload.json"
  printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$tmp/real.txt" > "$tmp/real_payload.json"

  run_test "Symlink Target (Block)" "$tmp/link_payload.json" "PreToolUse" 2
  run_test "Regular File (Allow)"   "$tmp/real_payload.json" "PreToolUse" 0
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
run_symlink_tests

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
