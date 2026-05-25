"""`ratchet validate` — run all validators without consuming an item.

Park Jun-woo's bar: 0 error 0 warning. We return exit 0 only when every
validator actually ran AND passed — fail/warn/skip/error all zero. A "skip"
counts against the bar because nothing was verified.
"""
from __future__ import annotations

import argparse
import sys

from ratchet_cli.state import VALIDATORS_DIRNAME, require_ratchet_dir
from ratchet_cli.validators import run_all, summarize

TAGS = {"pass": "PASS", "fail": "FAIL", "warn": "WARN", "skip": "SKIP", "error": "ERROR"}


def run(args: argparse.Namespace) -> int:
    ratchet_dir = require_ratchet_dir()
    validators_dir = ratchet_dir / VALIDATORS_DIRNAME
    results = run_all(validators_dir, item=None, cwd=ratchet_dir.parent, phase="validate")

    if not results:
        sys.stderr.write(
            "WARN: no validators registered in .ratchet/validators/ — "
            "submit will pass trivially.\n"
        )
        return 1

    for r in results:
        suffix = f"  ({r.skip_reason})" if r.skipped and r.skip_reason else ""
        print(f"[{TAGS[r.status]}] {r.name}  exit={r.exit_code}  {r.duration_ms}ms{suffix}")

    s = summarize(results)
    print(
        f"\n{s['pass']} pass, {s['fail']} fail, {s['warn']} warn, "
        f"{s['skip']} skip, {s['error']} error"
    )

    # 0err 0warn 0fail 0skip = true verified pass
    return 0 if (s["fail"] == 0 and s["warn"] == 0 and s["skip"] == 0 and s["error"] == 0) else 1
