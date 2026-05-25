"""State persistence for ratchet.

All mutating operations write atomically (tmp + os.replace) so that a process
killed mid-write leaves the previous state intact. `ratchet next` is idempotent:
re-running it without an intervening `submit` returns the same item.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RATCHET_DIRNAME = ".ratchet"
STATE_FILENAME = "state.json"
CONFIG_FILENAME = "config.json"
HISTORY_FILENAME = "history.jsonl"
LOCK_FILENAME = ".lock"
VALIDATORS_DIRNAME = "validators"

STATE_VERSION = 1


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_ratchet_dir(start: Path | None = None) -> Path | None:
    """Walk up from `start` looking for a .ratchet/ directory. Return None if not found."""
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        candidate = p / RATCHET_DIRNAME
        if candidate.is_dir():
            return candidate
    return None


def require_ratchet_dir() -> Path:
    p = find_ratchet_dir()
    if p is None:
        sys.stderr.write(
            "error: no .ratchet/ found in cwd or any parent. run `ratchet init` first.\n"
        )
        sys.exit(2)
    return p


@dataclass
class Item:
    id: int
    text: str
    status: str = "pending"  # pending | in_progress | done
    added_at: str = field(default_factory=now_iso)
    completed_at: str | None = None
    attempts: int = 0


@dataclass
class State:
    version: int = STATE_VERSION
    items: list[dict[str, Any]] = field(default_factory=list)
    cursor: int = 0           # index hint; next() scans from here forward
    current: int | None = None  # id of locked in-progress item; cleared on submit

    @classmethod
    def load(cls, path: Path) -> "State":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            version=data.get("version", STATE_VERSION),
            items=data.get("items", []),
            cursor=data.get("cursor", 0),
            current=data.get("current"),
        )

    def save(self, path: Path) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def next_id(self) -> int:
        return (max((it["id"] for it in self.items), default=0)) + 1

    def find_item(self, item_id: int) -> dict[str, Any] | None:
        for it in self.items:
            if it["id"] == item_id:
                return it
        return None

    def first_pending_from_cursor(self) -> dict[str, Any] | None:
        for i in range(self.cursor, len(self.items)):
            if self.items[i]["status"] == "pending":
                return self.items[i]
        return None

    def counts(self) -> dict[str, int]:
        total = len(self.items)
        done = sum(1 for it in self.items if it["status"] == "done")
        in_progress = sum(1 for it in self.items if it["status"] == "in_progress")
        pending = total - done - in_progress
        return {"total": total, "done": done, "in_progress": in_progress, "pending": pending}


@dataclass
class Config:
    version: int = STATE_VERSION
    require_all_pass: bool = True   # all validators must pass to submit
    warning_blocks: bool = False    # exit=2 (warning) blocks submit?

    @classmethod
    def load(cls, path: Path) -> "Config":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            version=data.get("version", STATE_VERSION),
            require_all_pass=data.get("require_all_pass", True),
            warning_blocks=data.get("warning_blocks", False),
        )

    def save(self, path: Path) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        os.replace(tmp, path)


def append_history(ratchet_dir: Path, record: dict[str, Any]) -> None:
    """Append a JSONL record to history. Best-effort: history is an asset, not a lock."""
    record = {"ts": now_iso(), **record}
    path = ratchet_dir / HISTORY_FILENAME
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class FileLock:
    """Coarse mutex for mutating commands. Read-only commands do not need it."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def __enter__(self) -> "FileLock":
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                pid = self.path.read_text().strip()
            except OSError:
                pid = "?"
            sys.stderr.write(
                f"error: another ratchet appears to be running (pid {pid}).\n"
                f"if not, remove the stale lock: {self.path}\n"
            )
            sys.exit(75)
        try:
            os.write(fd, str(os.getpid()).encode())
        finally:
            os.close(fd)
        self.acquired = True
        return self

    def __exit__(self, *_exc: object) -> None:
        if self.acquired:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
