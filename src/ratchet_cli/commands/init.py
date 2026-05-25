"""`ratchet init` — create .ratchet/ in cwd. Safe to run inside existing projects."""
from __future__ import annotations

import argparse
import shutil
import sys
from importlib import resources
from pathlib import Path

from ratchet_cli.state import (
    Config,
    RATCHET_DIRNAME,
    STATE_FILENAME,
    CONFIG_FILENAME,
    HISTORY_FILENAME,
    State,
    VALIDATORS_DIRNAME,
)
from ratchet_cli.validators import make_executable

GITIGNORE_BODY = """# managed by `ratchet init` — edit if your team prefers different defaults.
# state.json holds per-developer cursor/current; commit causes merge conflicts.
state.json
state.json.tmp
.lock
# config.json is per-developer in v0.1 (may move to commit-by-default later).
# history.jsonl is intentionally committed: it's a team asset (per Reins Engineering).
"""


def _resolve_shell_mode(requested: str) -> tuple[bool, bool, str | None]:
    """Decide which templates to seed.

    Returns (seed_sh, seed_py, warning).
    """
    bash_available = shutil.which("bash") is not None
    if requested == "sh":
        if not bash_available:
            return True, False, (
                "warning: --shell=sh requested but bash not detected. "
                ".sh validators will be skipped at run time until bash is installed."
            )
        return True, False, None
    if requested == "py":
        return False, True, None
    if requested == "both":
        warn = None if bash_available else (
            "note: --shell=both requested but bash not detected; .sh validators will be skipped at run time."
        )
        return True, True, warn
    # auto
    if bash_available:
        return True, False, None
    return False, True, (
        "shell validator seed skipped: bash not detected.\n"
        "  → seeded .py validator templates instead.\n"
        "  → install git-bash or WSL and re-run `ratchet init --force --shell=sh` for shell templates."
    )


def _copy_templates(subdir: str, dest: Path, make_exec: bool) -> list[str]:
    """Copy files from packaged templates/<subdir>/ into dest/. Return copied names."""
    copied: list[str] = []
    pkg_root = resources.files("ratchet_cli").joinpath("templates", subdir)
    for entry in pkg_root.iterdir():  # type: ignore[union-attr]
        if not entry.is_file():
            continue
        name = entry.name
        out = dest / name
        out.write_bytes(entry.read_bytes())
        if make_exec:
            make_executable(out)
        copied.append(name)
    return copied


def run(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    ratchet_dir = cwd / RATCHET_DIRNAME

    if ratchet_dir.exists():
        if not args.force:
            sys.stderr.write(
                f"error: {ratchet_dir} already exists. use --force to re-seed templates.\n"
            )
            return 1
        sys.stderr.write(f"note: --force given. re-seeding into existing {ratchet_dir}\n")

    ratchet_dir.mkdir(exist_ok=True)
    validators_dir = ratchet_dir / VALIDATORS_DIRNAME
    validators_dir.mkdir(exist_ok=True)

    # state.json: only create if missing — preserve cursor on --force re-seed
    state_path = ratchet_dir / STATE_FILENAME
    if not state_path.exists():
        State().save(state_path)

    config_path = ratchet_dir / CONFIG_FILENAME
    if not config_path.exists():
        Config().save(config_path)

    history_path = ratchet_dir / HISTORY_FILENAME
    history_path.touch(exist_ok=True)

    gitignore_path = ratchet_dir / ".gitignore"
    if not gitignore_path.exists() or args.force:
        gitignore_path.write_text(GITIGNORE_BODY, encoding="utf-8")

    seed_sh, seed_py, warning = _resolve_shell_mode(args.shell)
    seeded: list[str] = []
    if seed_sh:
        seeded += _copy_templates("validators_sh", validators_dir, make_exec=True)
    if seed_py:
        seeded += _copy_templates("validators_py", validators_dir, make_exec=True)

    if warning:
        sys.stderr.write(warning.rstrip() + "\n")

    print(f"initialized: {ratchet_dir}")
    if seeded:
        print(f"seeded {len(seeded)} validator(s): {', '.join(sorted(seeded))}")
    else:
        print("seeded 0 validators (drop your own into .ratchet/validators/)")
    print()
    print("next: `ratchet add <item>` to register work, then `ratchet next`.")
    return 0
