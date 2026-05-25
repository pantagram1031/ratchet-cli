"""`ratchet skill` — print bundled SKILL.md for Claude Code."""
from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path


def _read_skill() -> str:
    return resources.files("ratchet_cli").joinpath("templates", "SKILL.md").read_text(  # type: ignore[union-attr]
        encoding="utf-8"
    )


def run(args: argparse.Namespace) -> int:
    body = _read_skill()
    if args.write:
        out = Path(args.write)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
        sys.stderr.write(f"wrote SKILL.md to {out}\n")
        return 0
    sys.stdout.write(body)
    if not body.endswith("\n"):
        sys.stdout.write("\n")
    return 0
