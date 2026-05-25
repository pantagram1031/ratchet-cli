"""Validator discovery and execution.

A validator is any executable file in `.ratchet/validators/`. Exit code is the
only thing that matters:
    0 → pass
    2 → warning (does not block submit by default)
    other → fail

Discovery rules:
    * .py files run with `sys.executable` (always)
    * .sh files run with `bash` if available, else skipped with a stderr note
    * any other executable file (chmod +x) runs directly
    * dotfiles and files starting with `_` are ignored
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ValidatorResult:
    name: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    skipped: bool = False
    skip_reason: str = ""

    @property
    def status(self) -> str:
        if self.skipped:
            return "skip"
        if self.exit_code == 0:
            return "pass"
        if self.exit_code == 2:
            return "warn"
        return "fail"


def _is_ignored(name: str) -> bool:
    return name.startswith(".") or name.startswith("_") or name.endswith(".tmp")


def discover(validators_dir: Path) -> list[Path]:
    if not validators_dir.is_dir():
        return []
    out: list[Path] = []
    for child in sorted(validators_dir.iterdir()):
        if not child.is_file():
            continue
        if _is_ignored(child.name):
            continue
        out.append(child)
    return out


def _build_command(path: Path) -> tuple[list[str] | None, str]:
    """Return (argv, skip_reason). argv is None if validator should be skipped."""
    suffix = path.suffix.lower()
    if suffix == ".py":
        return [sys.executable, str(path)], ""
    if suffix == ".sh":
        bash = shutil.which("bash")
        if bash is None:
            return None, "bash not found on PATH"
        return [bash, str(path)], ""
    # any other file: must be executable
    if os.name == "nt":
        # Windows: trust the extension (.bat/.cmd/.exe handled by the shell)
        return [str(path)], ""
    if not os.access(path, os.X_OK):
        return None, "not executable (chmod +x to enable)"
    return [str(path)], ""


def run_one(path: Path, item: dict[str, Any] | None, cwd: Path) -> ValidatorResult:
    import time

    argv, skip_reason = _build_command(path)
    if argv is None:
        return ValidatorResult(
            name=path.name,
            exit_code=-1,
            stdout="",
            stderr="",
            duration_ms=0,
            skipped=True,
            skip_reason=skip_reason,
        )

    env = os.environ.copy()
    if item is not None:
        env["RATCHET_ITEM_ID"] = str(item.get("id", ""))
        env["RATCHET_ITEM_TEXT"] = str(item.get("text", ""))
    env["RATCHET_CWD"] = str(cwd)

    started = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(cwd),
            timeout=600,
        )
        return ValidatorResult(
            name=path.name,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
    except subprocess.TimeoutExpired:
        return ValidatorResult(
            name=path.name,
            exit_code=124,
            stdout="",
            stderr=f"validator timed out after 600s: {path.name}\n",
            duration_ms=int((time.monotonic() - started) * 1000),
        )
    except OSError as e:
        return ValidatorResult(
            name=path.name,
            exit_code=-1,
            stdout="",
            stderr=f"failed to execute {path.name}: {e}\n",
            duration_ms=0,
            skipped=True,
            skip_reason=str(e),
        )


def run_all(validators_dir: Path, item: dict[str, Any] | None, cwd: Path) -> list[ValidatorResult]:
    return [run_one(p, item, cwd) for p in discover(validators_dir)]


def summarize(results: list[ValidatorResult]) -> dict[str, int]:
    out = {"pass": 0, "fail": 0, "warn": 0, "skip": 0}
    for r in results:
        out[r.status] += 1
    return out


def make_executable(path: Path) -> None:
    """Best-effort chmod +x for seeded scripts on POSIX. No-op on Windows."""
    if os.name == "nt":
        return
    st = path.stat()
    path.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
