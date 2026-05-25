#!/usr/bin/env bash
# ratchet validator: build
#
# Exit codes:  0 = pass, 2 = warning, anything else = fail
#
# Detects common build tools. Replace with your exact build invocation.

set -u
cd "${RATCHET_CWD:-$PWD}"

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

echo "build: no known build tool detected — treating as pass." >&2
echo "edit .ratchet/validators/build.sh to wire your build command." >&2
exit 0
