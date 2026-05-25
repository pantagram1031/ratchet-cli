"""ratchet validator: test (Python fallback).

Exit codes:
    0  = pass (tests ran and passed)
    1  = fail
    2  = warning
    78 = skipped (no test runner detected — could not verify)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

cwd = Path(os.environ.get("RATCHET_PROJECT_ROOT", os.getcwd()))


def _run(argv: list[str]) -> int:
    return subprocess.run(argv, cwd=str(cwd)).returncode


def main() -> int:
    pkg = cwd / "package.json"
    if pkg.exists() and '"test"' in pkg.read_text(encoding="utf-8", errors="replace"):
        npm = shutil.which("npm")
        if npm:
            return _run([npm, "test", "--silent"])

    if shutil.which("pytest") and (cwd / "tests").exists():
        return _run(["pytest", "-q"])

    if shutil.which("go") and (cwd / "go.mod").exists():
        return _run(["go", "test", "./..."])

    if (cwd / "Cargo.toml").exists() and shutil.which("cargo"):
        return _run(["cargo", "test", "--quiet"])

    print("SKIP: test: no test runner detected (pytest/npm-test/go-test/cargo-test).", file=sys.stderr)
    print("SKIP: install one or edit .ratchet/validators/test.py to wire your test command.", file=sys.stderr)
    return 78


if __name__ == "__main__":
    sys.exit(main())
