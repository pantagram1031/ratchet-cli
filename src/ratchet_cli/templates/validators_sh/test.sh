#!/usr/bin/env bash
# ratchet validator: test
#
# Exit codes:
#   0  = pass (tests ran and passed)
#   1  = fail
#   2  = warning
#   78 = skipped (no test runner detected — could not verify)

set -u
cd "${RATCHET_PROJECT_ROOT:-$PWD}"

if [ -f "package.json" ] && grep -q '"test"' package.json 2>/dev/null; then
  exec npm test --silent
fi

if command -v pytest >/dev/null 2>&1 && { [ -d tests ] || [ -d test ]; }; then
  exec pytest -q
fi

if command -v go >/dev/null 2>&1 && [ -f "go.mod" ]; then
  exec go test ./...
fi

if [ -f "Cargo.toml" ] && command -v cargo >/dev/null 2>&1; then
  exec cargo test --quiet
fi

echo "SKIP: test: no test runner detected (pytest/npm-test/go-test/cargo-test)." >&2
echo "SKIP: install one or edit .ratchet/validators/test.sh to wire your test command." >&2
exit 78
