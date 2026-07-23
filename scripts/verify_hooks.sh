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

# Run tests
run_test "Clean Command (Allow)" "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_clean.json" "beforeShellExecution" 0
run_test "AWS Key Secret (Block)" "$ROOT_DIR/examples/payloads/cursor_beforeShellExecution_secret.json" "beforeShellExecution" 2
run_test "Git Force Push (Block)" "$ROOT_DIR/examples/payloads/claude_PreToolUse_bash.json" "PreToolUse" 2

echo ""
echo "Verification Summary: $TEST_PASSED Passed, $TEST_FAILED Failed."
if [ "$TEST_FAILED" -ne 0 ]; then
  exit 1
fi
exit 0
