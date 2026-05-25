# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Phase 0: methodology absorbed from Park Jun-woo's writing on Reins
  Engineering, the Ratchet Pattern, IFEval × Ratchet, and Hurl vs. vibe-coding
  drift.
- Phase 1: package design — Python 3.10+, stdlib-only, PEP 621 layout,
  `ratchet-cli` on PyPI / `ratchet` as CLI entry point.
- Phase 2: eight CLI commands — `init`, `add`, `next`, `submit`, `status`,
  `validate`, `reset`, `skill`.
- Phase 2: atomic state writes (`tmp + os.replace`); `FileLock` for mutating
  commands; idempotent `next` (same item until `submit` clears it) for
  crash-recovery.
- Phase 2: OS-aware validator seeding via `--shell={sh,py,both,auto}` — on
  Windows without bash/WSL, `.py` templates are seeded automatically with a
  stderr explanation.
- Phase 2: `.ratchet/.gitignore` auto-generated — `state.json` ignored,
  `history.jsonl` committed as team asset.
- Phase 2: built-in validator templates (`lint`, `test`, `build`, `hurl`) in
  both `.sh` and `.py` flavours.
- Phase 2: bundled `SKILL.md` for Claude Code consumption (`ratchet skill`).
- Phase 3: validator plugin contract — `RATCHET_PROJECT_ROOT`, `RATCHET_PHASE`,
  `RATCHET_ITEM`, `RATCHET_ITEM_ID`, `RATCHET_ITEM_INDEX` env vars; lexicographic
  ordering by filename (use `NN-name` prefixes for dependencies).
- Phase 3: `docs/VALIDATORS.md` — full writing guide with recipes for the
  five yongol SoTs (OpenAPI, sqlc, OPA Rego, Mermaid states, manifest.yaml)
  that intentionally do not ship as built-ins.
- Phase 4: README with three drop-in scenarios (Python / Node / Go), source
  attribution to Park Jun-woo, and a prose paragraph on this package's
  relationship to filefunc / tsma / yongol.
- Phase 4: `.gitattributes` enforcing LF line endings.
- Phase 4: GitHub Actions CI matrix — Ubuntu / Windows / macOS × Python
  3.10 / 3.11 / 3.12 — running `compileall` and the unit tests.
- Phase 4: `tests/test_basic.py` — unit tests for `state`, `validators`,
  and discovery rules.

### Changed

- **Phase 3 (breaking, pre-1.0):** exit code regime tightened. `78` is now
  reserved for "skipped — validator ran but could not verify (e.g. tool
  missing)". Built-in validators that previously returned exit 0 when their
  underlying tool was missing now return exit 78 with a `SKIP:` stderr
  prefix. `submit` blocks on `skip` by default; opt in to `allow_skipped`
  in `config.json` to relax that.
- **Phase 3 (breaking, pre-1.0):** validator environment variables renamed
  for clarity:
  - `RATCHET_CWD` → `RATCHET_PROJECT_ROOT`
  - `RATCHET_ITEM_TEXT` → `RATCHET_ITEM`
  - new: `RATCHET_PHASE` (`submit` | `validate`), `RATCHET_ITEM_INDEX`.
- Phase 3: `ratchet validate` "0err 0warn" pass bar tightened. Exit 0 now
  requires **0 fail AND 0 warn AND 0 skip AND 0 error**. A skip means
  nothing was verified — it is not a pass.
- Phase 3: `Config` gained `allow_skipped: bool = False`.
- Phase 3: `summarize()` returns five buckets (`pass`, `fail`, `warn`,
  `skip`, `error`); `status` and recent-submit lines render all five.
- Phase 4: SKILL.md rewritten to teach the Phase 3 exit code regime, the
  diagnostic order for a blocked submit, and the `RATCHET_PHASE` distinction.

[Unreleased]: https://github.com/pantagram1031/ratchet-cli/commits/main
