"""`ratchet reset` — wipe items/cursor. Keeps history.jsonl and validators/."""
from __future__ import annotations

import argparse
import sys

from ratchet_cli.state import (
    FileLock,
    LOCK_FILENAME,
    STATE_FILENAME,
    State,
    append_history,
    require_ratchet_dir,
)


def run(args: argparse.Namespace) -> int:
    ratchet_dir = require_ratchet_dir()
    state_path = ratchet_dir / STATE_FILENAME

    if not args.yes:
        sys.stderr.write(
            f"about to clear items/cursor in {state_path}\n"
            f"history.jsonl and validators/ will be kept.\n"
            f"type 'yes' to confirm: "
        )
        sys.stderr.flush()
        reply = sys.stdin.readline().strip().lower()
        if reply != "yes":
            sys.stderr.write("aborted.\n")
            return 1

    with FileLock(ratchet_dir / LOCK_FILENAME):
        old = State.load(state_path)
        State().save(state_path)
        append_history(
            ratchet_dir,
            {"cmd": "reset", "cleared_items": len(old.items), "cleared_cursor": old.cursor},
        )

    print("state cleared. validators and history preserved.")
    return 0
