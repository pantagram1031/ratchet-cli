"""Unit tests for ratchet_cli internals.

Pure-Python only — no shell-out, no subprocess. End-to-end CLI tests live
in Phase 5 (a dedicated smoke script).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ratchet_cli.state import Config, State, append_history, now_iso
from ratchet_cli.validators import (
    ValidatorResult,
    discover,
    summarize,
)


class TestState(unittest.TestCase):
    def test_load_missing_returns_default(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "state.json"
            s = State.load(p)
            self.assertEqual(s.items, [])
            self.assertEqual(s.cursor, 0)
            self.assertIsNone(s.current)

    def test_save_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "state.json"
            s = State(items=[{"id": 1, "text": "x", "status": "pending"}], cursor=0)
            s.save(p)
            loaded = State.load(p)
            self.assertEqual(loaded.items, s.items)
            self.assertEqual(loaded.cursor, 0)

    def test_save_is_atomic_no_tmp_leftover(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "state.json"
            State().save(p)
            self.assertTrue(p.exists())
            self.assertFalse((Path(d) / "state.json.tmp").exists())

    def test_next_id_starts_at_one(self) -> None:
        s = State()
        self.assertEqual(s.next_id(), 1)

    def test_next_id_after_items(self) -> None:
        s = State(items=[{"id": 1}, {"id": 5}, {"id": 3}])
        self.assertEqual(s.next_id(), 6)

    def test_find_item(self) -> None:
        s = State(items=[{"id": 2, "text": "a"}])
        self.assertEqual(s.find_item(2)["text"], "a")
        self.assertIsNone(s.find_item(99))

    def test_first_pending_from_cursor(self) -> None:
        s = State(
            items=[
                {"id": 1, "status": "done"},
                {"id": 2, "status": "done"},
                {"id": 3, "status": "pending"},
                {"id": 4, "status": "pending"},
            ],
            cursor=2,
        )
        self.assertEqual(s.first_pending_from_cursor()["id"], 3)

    def test_first_pending_returns_none_when_all_done(self) -> None:
        s = State(items=[{"id": 1, "status": "done"}], cursor=0)
        self.assertIsNone(s.first_pending_from_cursor())

    def test_counts(self) -> None:
        s = State(items=[
            {"id": 1, "status": "done"},
            {"id": 2, "status": "in_progress"},
            {"id": 3, "status": "pending"},
            {"id": 4, "status": "pending"},
        ])
        self.assertEqual(
            s.counts(),
            {"total": 4, "done": 1, "in_progress": 1, "pending": 2},
        )


class TestConfig(unittest.TestCase):
    def test_default_values(self) -> None:
        c = Config()
        self.assertTrue(c.require_all_pass)
        self.assertFalse(c.warning_blocks)
        self.assertFalse(c.allow_skipped)  # opt-in, never default

    def test_save_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            Config(allow_skipped=True, warning_blocks=True).save(p)
            loaded = Config.load(p)
            self.assertTrue(loaded.allow_skipped)
            self.assertTrue(loaded.warning_blocks)


class TestValidatorResultStatus(unittest.TestCase):
    def _r(self, exit_code: int = 0, skipped: bool = False) -> ValidatorResult:
        return ValidatorResult(
            name="x", exit_code=exit_code, stdout="", stderr="",
            duration_ms=0, skipped=skipped,
        )

    def test_pass(self) -> None:
        self.assertEqual(self._r(0).status, "pass")

    def test_fail(self) -> None:
        self.assertEqual(self._r(1).status, "fail")

    def test_warn(self) -> None:
        self.assertEqual(self._r(2).status, "warn")

    def test_skip_via_exit_78(self) -> None:
        self.assertEqual(self._r(78).status, "skip")

    def test_skip_via_skipped_flag(self) -> None:
        self.assertEqual(self._r(-1, skipped=True).status, "skip")

    def test_error_on_other_exit_codes(self) -> None:
        self.assertEqual(self._r(3).status, "error")
        self.assertEqual(self._r(127).status, "error")
        self.assertEqual(self._r(-9).status, "error")


class TestSummarize(unittest.TestCase):
    def test_all_five_buckets_present(self) -> None:
        results = [
            ValidatorResult("a", 0, "", "", 0),
            ValidatorResult("b", 1, "", "", 0),
            ValidatorResult("c", 2, "", "", 0),
            ValidatorResult("d", 78, "", "", 0),
            ValidatorResult("e", 99, "", "", 0),
        ]
        self.assertEqual(
            summarize(results),
            {"pass": 1, "fail": 1, "warn": 1, "skip": 1, "error": 1},
        )

    def test_empty(self) -> None:
        self.assertEqual(
            summarize([]),
            {"pass": 0, "fail": 0, "warn": 0, "skip": 0, "error": 0},
        )


class TestDiscover(unittest.TestCase):
    def test_returns_empty_for_missing_dir(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(discover(Path(d) / "nope"), [])

    def test_ignores_dotfiles_and_underscores(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            vd = Path(d)
            (vd / "real.sh").write_text("#!/bin/sh\nexit 0\n")
            (vd / ".hidden.sh").write_text("")
            (vd / "_disabled.sh").write_text("")
            (vd / "in_progress.sh.tmp").write_text("")
            names = [p.name for p in discover(vd)]
            self.assertEqual(names, ["real.sh"])

    def test_sorted_lexicographically(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            vd = Path(d)
            for name in ("30-c.sh", "10-a.sh", "20-b.sh"):
                (vd / name).write_text("")
            names = [p.name for p in discover(vd)]
            self.assertEqual(names, ["10-a.sh", "20-b.sh", "30-c.sh"])


class TestHistory(unittest.TestCase):
    def test_append_creates_one_jsonl_record(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ratchet_dir = Path(d)
            (ratchet_dir / "history.jsonl").touch()
            append_history(ratchet_dir, {"cmd": "test", "ok": True})
            lines = (ratchet_dir / "history.jsonl").read_text().strip().splitlines()
            self.assertEqual(len(lines), 1)
            rec = json.loads(lines[0])
            self.assertEqual(rec["cmd"], "test")
            self.assertTrue(rec["ok"])
            self.assertIn("ts", rec)


class TestNowIso(unittest.TestCase):
    def test_ends_with_z_and_no_microseconds(self) -> None:
        ts = now_iso()
        self.assertTrue(ts.endswith("Z"))
        self.assertNotIn(".", ts)


if __name__ == "__main__":
    unittest.main()
