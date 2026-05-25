"""`ratchet add` — register one or more work items."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ratchet_cli.state import (
    FileLock,
    LOCK_FILENAME,
    STATE_FILENAME,
    State,
    append_history,
    now_iso,
    require_ratchet_dir,
)


def _read_lines_from_file(spec: str) -> list[str]:
    if spec == "-":
        text = sys.stdin.read()
    else:
        text = Path(spec).read_text(encoding="utf-8")
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def run(args: argparse.Namespace) -> int:
    ratchet_dir = require_ratchet_dir()
    state_path = ratchet_dir / STATE_FILENAME

    items: list[str] = list(args.items or [])
    if args.file:
        items += _read_lines_from_file(args.file)

    if not items:
        sys.stderr.write(
            "error: no items provided. pass them as args, with --file PATH, or via --file -.\n"
        )
        return 2

    with FileLock(ratchet_dir / LOCK_FILENAME):
        state = State.load(state_path)
        added_ids: list[int] = []
        for text in items:
            new_id = state.next_id()
            state.items.append(
                {
                    "id": new_id,
                    "text": text,
                    "status": "pending",
                    "added_at": now_iso(),
                    "completed_at": None,
                    "attempts": 0,
                }
            )
            added_ids.append(new_id)
        state.save(state_path)
        append_history(
            ratchet_dir,
            {"cmd": "add", "count": len(added_ids), "ids": added_ids},
        )

    counts = state.counts()
    print(f"added {len(added_ids)} item(s). total pending: {counts['pending']}")
    print("next: `ratchet next`")
    return 0
