"""`ratchet submit` — close the current item if validators pass."""
from __future__ import annotations

import argparse
import sys

from ratchet_cli.state import (
    Config,
    CONFIG_FILENAME,
    FileLock,
    LOCK_FILENAME,
    STATE_FILENAME,
    VALIDATORS_DIRNAME,
    State,
    append_history,
    now_iso,
    require_ratchet_dir,
)
from ratchet_cli.validators import run_all, summarize


STATUS_TAGS = {
    "pass": "PASS",
    "fail": "FAIL",
    "warn": "WARN",
    "skip": "SKIP",
    "error": "ERROR",
}


def _format_results(results) -> str:
    lines = []
    for r in results:
        tag = STATUS_TAGS[r.status]
        suffix = f"  ({r.skip_reason})" if r.skipped and r.skip_reason else ""
        lines.append(f"  [{tag}] {r.name}  exit={r.exit_code}  {r.duration_ms}ms{suffix}")
    return "\n".join(lines)


def _print_failure_excerpts(results, max_lines: int = 12) -> None:
    for r in results:
        if r.status not in ("fail", "warn", "skip", "error"):
            continue
        body = (r.stdout + r.stderr).strip()
        if not body:
            continue
        lines = body.splitlines()
        head = lines[:max_lines]
        sys.stderr.write(f"\n--- {r.name} ({r.status}) ---\n")
        sys.stderr.write("\n".join(head) + "\n")
        if len(lines) > max_lines:
            sys.stderr.write(f"... ({len(lines) - max_lines} more line(s) truncated)\n")


def run(args: argparse.Namespace) -> int:
    ratchet_dir = require_ratchet_dir()
    state_path = ratchet_dir / STATE_FILENAME
    config_path = ratchet_dir / CONFIG_FILENAME
    validators_dir = ratchet_dir / VALIDATORS_DIRNAME

    with FileLock(ratchet_dir / LOCK_FILENAME):
        state = State.load(state_path)
        config = Config.load(config_path)

        if state.current is None:
            sys.stderr.write(
                "error: no item is locked. run `ratchet next` first.\n"
            )
            return 2

        item = state.find_item(state.current)
        if item is None:
            sys.stderr.write(
                f"error: state.current points to id {state.current} but item is missing. "
                f"run `ratchet reset` to recover.\n"
            )
            return 2

        item["attempts"] = int(item.get("attempts", 0)) + 1

        if args.skip_validators:
            results = []
            sys.stderr.write(
                "warning: --skip-validators given. this defeats the ratchet and is recorded.\n"
            )
        else:
            results = run_all(validators_dir, item, cwd=ratchet_dir.parent)

        summary = summarize(results)
        if results:
            print(_format_results(results))
        else:
            print("  (no validators present — submit will pass trivially; add some to .ratchet/validators/)")
        print(
            f"summary: {summary['pass']} pass, {summary['fail']} fail, "
            f"{summary['warn']} warn, {summary['skip']} skip, {summary['error']} error"
        )

        blocking_fail = summary["fail"] > 0
        blocking_error = summary["error"] > 0
        blocking_skip = (
            summary["skip"] > 0
            and config.require_all_pass
            and not config.allow_skipped
        )
        blocking_warn = config.warning_blocks and summary["warn"] > 0
        passed = not (blocking_fail or blocking_error or blocking_skip or blocking_warn)

        history_payload = {
            "cmd": "submit",
            "id": item["id"],
            "text": item["text"],
            "passed": passed,
            "skipped_validators": bool(args.skip_validators),
            "note": args.note,
            "summary": summary,
            "results": [
                {"name": r.name, "status": r.status, "exit": r.exit_code, "ms": r.duration_ms}
                for r in results
            ],
        }
        append_history(ratchet_dir, history_payload)

        if passed:
            item["status"] = "done"
            item["completed_at"] = now_iso()
            state.current = None
            # advance cursor to one past the freshly-done item
            for i, it in enumerate(state.items):
                if it["id"] == item["id"]:
                    state.cursor = i + 1
                    break
            state.save(state_path)
            print()
            print(f"[{item['id']}] locked. → `ratchet next` for the next item.")
            return 0

        # failure path — keep current locked so `next` returns the same item
        state.save(state_path)
        _print_failure_excerpts(results)

        reasons = []
        if blocking_fail:
            reasons.append(f"{summary['fail']} fail")
        if blocking_error:
            reasons.append(f"{summary['error']} error (validator broken?)")
        if blocking_skip:
            reasons.append(
                f"{summary['skip']} skip — validators could not verify "
                f"(install the missing tools, or set allow_skipped=true in config.json)"
            )
        if blocking_warn:
            reasons.append(f"{summary['warn']} warn (warning_blocks=true)")

        sys.stderr.write(
            "\nblocked: " + "; ".join(reasons) + "\n"
            "fix the issues above, then re-run `ratchet submit`.\n"
            "`ratchet next` will re-print the same item until it passes.\n"
        )
        return 1
