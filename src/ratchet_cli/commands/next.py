"""`ratchet next` — print the next pending item.

Idempotency contract (load-bearing for crash recovery):
    * If `state.current` is set, re-print that same item. No state mutation.
    * Otherwise, find the first pending item from `cursor`, mark it in_progress,
      set `current = item.id`, and print it. Mutation is atomic.
    * `submit` is the only command that advances the cursor and clears `current`.

This means: a process killed between `next` and `submit` resumes by re-running
`ratchet next` — same item, no duplicate work.
"""
from __future__ import annotations

import argparse
import sys

from ratchet_cli.state import (
    FileLock,
    LOCK_FILENAME,
    STATE_FILENAME,
    VALIDATORS_DIRNAME,
    State,
    append_history,
    require_ratchet_dir,
)
from ratchet_cli.validators import discover


def run(args: argparse.Namespace) -> int:
    ratchet_dir = require_ratchet_dir()
    state_path = ratchet_dir / STATE_FILENAME

    if not discover(ratchet_dir / VALIDATORS_DIRNAME):
        sys.stderr.write(
            "WARN: no validators registered in .ratchet/validators/ — "
            "submit will pass trivially.\n"
        )

    with FileLock(ratchet_dir / LOCK_FILENAME):
        state = State.load(state_path)

        # idempotent path: a current item is already locked
        if state.current is not None:
            item = state.find_item(state.current)
            if item is not None:
                _print_item(item, resumed=True)
                return 0
            # current points to a missing id — heal by clearing.
            state.current = None

        item = state.first_pending_from_cursor()
        if item is None:
            # advance cursor past any non-pending stragglers for hygiene
            state.cursor = len(state.items)
            state.save(state_path)
            print("DONE")
            return 0

        item["status"] = "in_progress"
        state.current = item["id"]
        state.save(state_path)
        append_history(ratchet_dir, {"cmd": "next", "id": item["id"], "text": item["text"]})
        _print_item(item, resumed=False)
        return 0


def _print_item(item: dict, *, resumed: bool) -> None:
    tag = " (resumed)" if resumed else ""
    print(f"[{item['id']}] {item['text']}{tag}")
    print("→ run: ratchet submit  (after you finish this item; validators run automatically)")
