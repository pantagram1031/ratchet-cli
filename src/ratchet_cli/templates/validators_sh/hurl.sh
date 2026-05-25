#!/usr/bin/env bash
# ratchet validator: hurl
#
# Exit codes:
#   0  = pass (all hurl tests passed)
#   1  = fail
#   2  = warning
#   78 = skipped (hurl not installed or no *.hurl files — could not verify)
#
# Hurl is the behavioral contract layer in Park Jun-woo's Reins Engineering:
# once a Hurl test passes, that observable HTTP behavior is locked.
# Install: https://hurl.dev/

set -u
cd "${RATCHET_CWD:-$PWD}"

HURL_DIR="${HURL_DIR:-tests}"

if ! command -v hurl >/dev/null 2>&1; then
  echo "SKIP: hurl: not installed (https://hurl.dev). Install to enable HTTP contract validation." >&2
  exit 78
fi

mapfile -t files < <(find "$HURL_DIR" -name '*.hurl' 2>/dev/null)
if [ "${#files[@]}" -eq 0 ]; then
  echo "SKIP: hurl: no *.hurl files under $HURL_DIR — could not verify." >&2
  echo "SKIP: write hurl tests under $HURL_DIR/ or set HURL_DIR=<path>." >&2
  exit 78
fi

exec hurl --test "${files[@]}"
