"""`ratchet status` — counts and recent outcomes. Read-only, no lock needed."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ratchet_cli.state import (
    CONFIG_FILENAME,
    Config,
    HISTORY_FILENAME,
    STATE_FILENAME,
    VALIDATORS_DIRNAME,
    State,
    require_ratchet_dir,
)
from ratchet_cli.validators import discover


def _tail_jsonl(path: Path, n: int) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out[-n:]


def run(args: argparse.Namespace) -> int:
    ratchet_dir = require_ratchet_dir()
    state = State.load(ratchet_dir / STATE_FILENAME)
    config = Config.load(ratchet_dir / CONFIG_FILENAME)
    c = state.counts()

    print(f"ratchet @ {ratchet_dir}")
    print(f"  items:   {c['total']} total | {c['done']} done | "
          f"{c['in_progress']} in_progress | {c['pending']} pending")
    print(f"  cursor:  {state.cursor}")
    if state.current is not None:
        cur = state.find_item(state.current)
        text = cur["text"] if cur else "(missing)"
        print(f"  current: [{state.current}] {text}")
    else:
        print("  current: (none — run `ratchet next`)")
    print(f"  config:  require_all_pass={config.require_all_pass}, "
          f"warning_blocks={config.warning_blocks}, allow_skipped={config.allow_skipped}")

    discovered = discover(ratchet_dir / VALIDATORS_DIRNAME)
    print(f"  validators: {len(discovered)} discovered in .ratchet/validators/")
    if not discovered:
        sys.stderr.write(
            "WARN: no validators registered in .ratchet/validators/ — "
            "submit will pass trivially.\n"
        )

    submits = [r for r in _tail_jsonl(ratchet_dir / HISTORY_FILENAME, 500)
               if r.get("cmd") == "submit_done"]
    total = len(submits)
    passed = sum(1 for r in submits if r.get("passed"))
    failed = total - passed
    print(f"  submits: {total} recorded ({passed} pass, {failed} fail)")

    recent = submits[-5:]
    if recent:
        print("  recent submits:")
        for r in recent:
            mark = "✓" if r.get("passed") else "✗"
            s = r.get("summary", {})
            counts = (
                f"{s.get('pass',0)}p/{s.get('fail',0)}f/"
                f"{s.get('warn',0)}w/{s.get('skip',0)}s/{s.get('error',0)}e"
            )
            print(f"    {mark} [{r.get('item_id')}] {r.get('item','')[:60]}  ({counts})")
    return 0
