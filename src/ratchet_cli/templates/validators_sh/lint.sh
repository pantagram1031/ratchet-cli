#!/usr/bin/env bash
# ratchet validator: lint
#
# Exit codes:  0 = pass, 2 = warning, anything else = fail
#
# Auto-detects common linters in the project root ($RATCHET_CWD) and runs
# the first one it finds. Edit or replace freely — your project may need a
# specific linter invocation.

set -u
cd "${RATCHET_CWD:-$PWD}"

if [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null; then
  exec npm run lint --silent
fi

if [ -f "pyproject.toml" ] && command -v ruff >/dev/null 2>&1; then
  exec ruff check .
fi

if command -v eslint >/dev/null 2>&1 && ls *.{js,ts,tsx,jsx} 2>/dev/null | head -1 >/dev/null; then
  exec eslint .
fi

if command -v flake8 >/dev/null 2>&1 && ls *.py 2>/dev/null | head -1 >/dev/null; then
  exec flake8 .
fi

if command -v golangci-lint >/dev/null 2>&1 && [ -f "go.mod" ]; then
  exec golangci-lint run
fi

echo "lint: no known linter detected — treating as pass." >&2
echo "edit .ratchet/validators/lint.sh to wire your linter." >&2
exit 0
