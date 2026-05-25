"""argparse dispatcher for the `ratchet` command."""
from __future__ import annotations

import argparse
import sys

from ratchet_cli import __version__
from ratchet_cli.commands import (
    init as cmd_init,
    add as cmd_add,
    next as cmd_next,
    submit as cmd_submit,
    status as cmd_status,
    validate as cmd_validate,
    reset as cmd_reset,
    skill as cmd_skill,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ratchet",
        description="Deterministic ratchet for AI coding agents (Reins Engineering CLI).",
    )
    p.add_argument("--version", action="version", version=f"ratchet-cli {__version__}")
    sub = p.add_subparsers(dest="command", required=True, metavar="<command>")

    pi = sub.add_parser("init", help="create .ratchet/ in the current directory")
    pi.add_argument("--force", action="store_true", help="overwrite existing .ratchet/")
    pi.add_argument(
        "--shell",
        choices=["sh", "py", "both", "auto"],
        default="auto",
        help="which validator templates to seed (default: auto-detect by bash availability)",
    )
    pi.set_defaults(func=cmd_init.run)

    pa = sub.add_parser("add", help="register one or more work items")
    pa.add_argument("items", nargs="*", help="one or more items as positional args")
    pa.add_argument("--file", "-f", help="read items from a file (one per line). Use '-' for stdin.")
    pa.set_defaults(func=cmd_add.run)

    pn = sub.add_parser("next", help="print the next pending item (idempotent)")
    pn.set_defaults(func=cmd_next.run)

    ps = sub.add_parser("submit", help="mark the current item done after running validators")
    ps.add_argument("--note", help="free-form note recorded in history.jsonl")
    ps.add_argument(
        "--skip-validators",
        action="store_true",
        help="skip validators (recorded; use sparingly — defeats the ratchet)",
    )
    ps.set_defaults(func=cmd_submit.run)

    pst = sub.add_parser("status", help="show counts and recent validator outcomes")
    pst.set_defaults(func=cmd_status.run)

    pv = sub.add_parser("validate", help="run all validators without consuming an item")
    pv.set_defaults(func=cmd_validate.run)

    pr = sub.add_parser("reset", help="clear items/cursor (keeps history.jsonl and validators/)")
    pr.add_argument("--yes", action="store_true", help="skip confirmation prompt")
    pr.set_defaults(func=cmd_reset.run)

    psk = sub.add_parser("skill", help="print SKILL.md for Claude Code")
    psk.add_argument("--write", metavar="PATH", help="write to PATH instead of stdout")
    psk.set_defaults(func=cmd_skill.run)

    return p


def _force_utf8_stdio() -> None:
    """Reconfigure stdout/stderr to UTF-8 so non-ASCII output (em-dashes,
    Korean item text, etc.) does not crash on Windows consoles whose code
    page is cp949 / cp1252. Errors are replaced rather than raised — a
    garbled glyph beats a UnicodeEncodeError mid-command."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        rc = args.func(args)
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted.\n")
        return 130
    return int(rc or 0)


if __name__ == "__main__":
    sys.exit(main())
