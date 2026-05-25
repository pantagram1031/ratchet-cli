"""ratchet validator: hurl (Python fallback).

Exit codes:
    0  = pass (all hurl tests passed)
    1  = fail
    2  = warning
    78 = skipped (hurl not installed or no *.hurl files — could not verify)

Hurl is the behavioral contract layer in Park Jun-woo's Reins Engineering —
once a Hurl test passes, that observable HTTP behavior is locked.
Install: https://hurl.dev/
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

cwd = Path(os.environ.get("RATCHET_PROJECT_ROOT", os.getcwd()))
hurl_dir = Path(os.environ.get("HURL_DIR", "tests"))


def main() -> int:
    if not shutil.which("hurl"):
        print("SKIP: hurl: not installed (https://hurl.dev). Install to enable HTTP contract validation.", file=sys.stderr)
        return 78

    search_root = cwd / hurl_dir if not hurl_dir.is_absolute() else hurl_dir
    if not search_root.exists():
        print(f"SKIP: hurl: directory {search_root} not found — could not verify.", file=sys.stderr)
        return 78

    files = sorted(search_root.rglob("*.hurl"))
    if not files:
        print(f"SKIP: hurl: no *.hurl files under {search_root} — could not verify.", file=sys.stderr)
        print("SKIP: write hurl tests under tests/ or set HURL_DIR=<path>.", file=sys.stderr)
        return 78

    return subprocess.run(["hurl", "--test", *[str(f) for f in files]], cwd=str(cwd)).returncode


if __name__ == "__main__":
    sys.exit(main())
