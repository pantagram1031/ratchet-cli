"""ratchet validator: test (Python fallback)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

cwd = Path(os.environ.get("RATCHET_CWD", os.getcwd()))


def _run(argv: list[str]) -> int:
    return subprocess.run(argv, cwd=str(cwd)).returncode


def main() -> int:
    pkg = cwd / "package.json"
    if pkg.exists() and '"test"' in pkg.read_text(encoding="utf-8", errors="replace"):
        npm = shutil.which("npm")
        if npm:
            return _run([npm, "test", "--silent"])

    if shutil.which("pytest") and (any((cwd / "tests").glob("**/*")) if (cwd / "tests").exists() else False):
        return _run(["pytest", "-q"])

    if shutil.which("go") and (cwd / "go.mod").exists():
        return _run(["go", "test", "./..."])

    if (cwd / "Cargo.toml").exists() and shutil.which("cargo"):
        return _run(["cargo", "test", "--quiet"])

    print("test: no known test runner detected — treating as pass.", file=sys.stderr)
    print("edit .ratchet/validators/test.py to wire your test command.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
