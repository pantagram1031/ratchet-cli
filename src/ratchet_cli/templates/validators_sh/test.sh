#!/usr/bin/env bash
# ratchet validator: test
#
# Exit codes:  0 = pass, 2 = warning, anything else = fail
#
# Auto-detects common test runners. Replace with your project's exact command
# for fastest feedback (e.g. `pytest -x tests/auth/` instead of full suite).

set -u
cd "${RATCHET_CWD:-$PWD}"

if [ -f "package.json" ] && grep -q '"test"' package.json 2>/dev/null; then
  exec npm test --silent
fi

if command -v pytest >/dev/null 2>&1 && ls tests test 2>/dev/null | head -1 >/dev/null; then
  exec pytest -q
fi

if command -v go >/dev/null 2>&1 && [ -f "go.mod" ]; then
  exec go test ./...
fi

if [ -f "Cargo.toml" ] && command -v cargo >/dev/null 2>&1; then
  exec cargo test --quiet
fi

echo "test: no known test runner detected — treating as pass." >&2
echo "edit .ratchet/validators/test.sh to wire your test command." >&2
exit 0
