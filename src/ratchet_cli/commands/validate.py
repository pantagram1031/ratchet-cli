"""`ratchet validate` — run all validators without consuming an item.

Park Jun-woo's bar: 0 error 0 warning. We return exit 0 only when there are
zero fails AND zero warns. Skips do not affect the exit code.
"""
from __future__ import annotations

import argparse

from ratchet_cli.state import VALIDATORS_DIRNAME, require_ratchet_dir
from ratchet_cli.validators import run_all, summarize


def run(args: argparse.Namespace) -> int:
    ratchet_dir = require_ratchet_dir()
    validators_dir = ratchet_dir / VALIDATORS_DIRNAME
    results = run_all(validators_dir, item=None, cwd=ratchet_dir.parent)

    if not results:
        print("(no validators present in .ratchet/validators/)")
        return 0

    for r in results:
        tag = {"pass": "PASS", "fail": "FAIL", "warn": "WARN", "skip": "SKIP"}[r.status]
        suffix = f"  ({r.skip_reason})" if r.skipped and r.skip_reason else ""
        print(f"[{tag}] {r.name}  exit={r.exit_code}  {r.duration_ms}ms{suffix}")

    s = summarize(results)
    print(f"\n{s['pass']} pass, {s['fail']} fail, {s['warn']} warn, {s['skip']} skip")

    # 0 error 0 warning bar
    return 0 if (s["fail"] == 0 and s["warn"] == 0) else 1
