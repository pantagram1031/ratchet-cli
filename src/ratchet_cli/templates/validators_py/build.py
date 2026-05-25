"""ratchet validator: build (Python fallback)."""
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
    if pkg.exists() and '"build"' in pkg.read_text(encoding="utf-8", errors="replace"):
        npm = shutil.which("npm")
        if npm:
            return _run([npm, "run", "build", "--silent"])

    if (cwd / "pyproject.toml").exists():
        return _run([sys.executable, "-m", "compileall", "-q", "."])

    if shutil.which("go") and (cwd / "go.mod").exists():
        return _run(["go", "build", "./..."])

    if (cwd / "Cargo.toml").exists() and shutil.which("cargo"):
        return _run(["cargo", "build", "--quiet"])

    print("build: no known build tool detected — treating as pass.", file=sys.stderr)
    print("edit .ratchet/validators/build.py to wire your build command.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
