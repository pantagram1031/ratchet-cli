#!/usr/bin/env bash
# ratchet validator: hurl
#
# Exit codes:  0 = pass, 2 = warning, anything else = fail
#
# Runs all *.hurl files in tests/ (or a HURL_DIR you set). Hurl is the
# behavioral contract layer in Park Jun-woo's Reins Engineering: once a
# Hurl test passes, that observable HTTP behavior is locked.
#
# Install hurl: https://hurl.dev/

set -u
cd "${RATCHET_CWD:-$PWD}"

HURL_DIR="${HURL_DIR:-tests}"

if ! command -v hurl >/dev/null 2>&1; then
  echo "hurl: not installed — skipping (install: https://hurl.dev)" >&2
  exit 0
fi

# find any .hurl files
mapfile -t files < <(find "$HURL_DIR" -name '*.hurl' 2>/dev/null)
if [ "${#files[@]}" -eq 0 ]; then
  echo "hurl: no *.hurl files under $HURL_DIR — treating as pass." >&2
  exit 0
fi

exec hurl --test "${files[@]}"
