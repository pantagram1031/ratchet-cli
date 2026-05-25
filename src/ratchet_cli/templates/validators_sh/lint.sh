#!/usr/bin/env bash
# ratchet validator: lint
#
# Exit codes:
#   0  = pass (lint ran and passed)
#   1  = fail
#   2  = warning
#   78 = skipped (no linter detected — could not verify)
#
# Auto-detects common linters in the project root ($RATCHET_CWD) and runs
# the first one it finds. Edit or replace freely.

set -u
cd "${RATCHET_PROJECT_ROOT:-$PWD}"

if [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null; then
  exec npm run lint --silent
fi

if [ -f "pyproject.toml" ] && command -v ruff >/dev/null 2>&1; then
  exec ruff check .
fi

if command -v eslint >/dev/null 2>&1 && { compgen -G "*.js" >/dev/null || compgen -G "*.ts" >/dev/null || compgen -G "*.tsx" >/dev/null || compgen -G "*.jsx" >/dev/null; }; then
  exec eslint .
fi

if command -v flake8 >/dev/null 2>&1 && compgen -G "*.py" >/dev/null; then
  exec flake8 .
fi

if command -v golangci-lint >/dev/null 2>&1 && [ -f "go.mod" ]; then
  exec golangci-lint run
fi

echo "SKIP: lint: no linter detected (ruff/eslint/flake8/golangci-lint/npm-lint)." >&2
echo "SKIP: install one or edit .ratchet/validators/lint.sh to wire your linter." >&2
exit 78
