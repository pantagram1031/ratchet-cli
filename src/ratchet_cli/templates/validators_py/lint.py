"""ratchet validator: lint (Python fallback for systems without bash).

Exit codes:
    0  = pass (lint ran and passed)
    1  = fail
    2  = warning
    78 = skipped (no linter detected — could not verify)
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
    if pkg.exists() and '"lint"' in pkg.read_text(encoding="utf-8", errors="replace"):
        npm = shutil.which("npm")
        if npm:
            return _run([npm, "run", "lint", "--silent"])

    if (cwd / "pyproject.toml").exists() and shutil.which("ruff"):
        return _run(["ruff", "check", "."])

    if shutil.which("flake8") and any(cwd.glob("*.py")):
        return _run(["flake8", "."])

    if shutil.which("golangci-lint") and (cwd / "go.mod").exists():
        return _run(["golangci-lint", "run"])

    print("SKIP: lint: no linter detected (ruff/eslint/flake8/golangci-lint/npm-lint).", file=sys.stderr)
    print("SKIP: install one or edit .ratchet/validators/lint.py to wire your linter.", file=sys.stderr)
    return 78


if __name__ == "__main__":
    sys.exit(main())
