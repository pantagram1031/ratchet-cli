"""ratchet validator: hurl (Python fallback).

Runs all *.hurl files under tests/ (or $HURL_DIR). Hurl is the behavioral
contract layer in Park Jun-woo's Reins Engineering — once a Hurl test passes,
that observable HTTP behavior is locked.

Install hurl: https://hurl.dev/
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

cwd = Path(os.environ.get("RATCHET_CWD", os.getcwd()))
hurl_dir = Path(os.environ.get("HURL_DIR", "tests"))


def main() -> int:
    if not shutil.which("hurl"):
        print("hurl: not installed — skipping (install: https://hurl.dev)", file=sys.stderr)
        return 0

    search_root = cwd / hurl_dir if not hurl_dir.is_absolute() else hurl_dir
    if not search_root.exists():
        print(f"hurl: directory {search_root} not found — treating as pass.", file=sys.stderr)
        return 0

    files = sorted(search_root.rglob("*.hurl"))
    if not files:
        print(f"hurl: no *.hurl files under {search_root} — treating as pass.", file=sys.stderr)
        return 0

    return subprocess.run(["hurl", "--test", *[str(f) for f in files]], cwd=str(cwd)).returncode


if __name__ == "__main__":
    sys.exit(main())
