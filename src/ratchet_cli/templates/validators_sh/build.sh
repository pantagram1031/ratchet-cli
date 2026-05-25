#!/usr/bin/env bash
# ratchet validator: build
#
# Exit codes:
#   0  = pass (build succeeded)
#   1  = fail
#   2  = warning
#   78 = skipped (no build tool detected — could not verify)

set -u
cd "${RATCHET_PROJECT_ROOT:-$PWD}"

if [ -f "package.json" ] && grep -q '"build"' package.json 2>/dev/null; then
  exec npm run build --silent
fi

if [ -f "pyproject.toml" ] && command -v python >/dev/null 2>&1; then
  exec python -m compileall -q .
fi

if command -v go >/dev/null 2>&1 && [ -f "go.mod" ]; then
  exec go build ./...
fi

if [ -f "Cargo.toml" ] && command -v cargo >/dev/null 2>&1; then
  exec cargo build --quiet
fi

echo "SKIP: build: no build tool detected (npm-build/python/go/cargo)." >&2
echo "SKIP: install one or edit .ratchet/validators/build.sh to wire your build command." >&2
exit 78
