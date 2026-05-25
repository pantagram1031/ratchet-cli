# ratchet-cli

A deterministic ratchet for AI coding agents — implements Park Jun-woo's
**Reins Engineering** and **Ratchet Pattern** as a reusable CLI you can drop
into any existing project.

> Inspired by 박준우 (@park-jun-woo)'s *Reins Engineering* and *Ratchet
> Pattern*. Original sources:
> <https://www.parkjunwoo.com/ko/opinion/reins-engineering/> ·
> <https://www.parkjunwoo.com/ko/tech/ratchet-pattern/>

---

## The idea, in one paragraph

LLMs generate well but cannot reliably judge whether work is done. So don't
let them. Register the work you want done as discrete items, gate progression
on **deterministic validators** (lint, tests, build, Hurl, …), and let the
ratchet hand items out one at a time. An item only advances when validators
return exit 0. There is no "I think it's done" path. The CLI is the gate.

## Install

```bash
pipx install git+https://github.com/pantagram1031/ratchet-cli
```

Requires Python 3.10+. Zero runtime dependencies — pure standard library.

## Five-second tour

```bash
cd my-existing-project
ratchet init                      # creates .ratchet/ — does not touch your code
ratchet add "implement /login"
ratchet add "implement /logout"
ratchet next                      # → [1] implement /login
# do the work...
ratchet submit                    # runs all validators; locks the item if they pass
ratchet status                    # counts and recent outcomes
```

## How the loop works

```
loop:
  out = $(ratchet next)
  if out == "DONE": exit
  perform the work (you, or your LLM)
  ratchet submit
  if submit blocked:
    read validator output → fix → re-submit
```

The next item is not handed out until the previous one passes validators.
`ratchet next` is **idempotent**: re-running it before `submit` returns the
same item — crash-recovery safe.

## Exit code regime for validators

| code | meaning | blocks submit? |
|---:|---|---|
| 0 | pass — actually verified | no |
| 1 | fail | **yes** |
| 2 | warning — counted, advisory | only if `warning_blocks=true` |
| 78 | skipped — could not verify (e.g. tool missing) | **yes** (unless `allow_skipped=true`) |
| any other | error — validator itself broken | **yes** |

A validator that returns exit 0 when it didn't actually run anything is a
**false ratchet**. Use exit 78 to say "I couldn't verify this." Full contract
in [`docs/VALIDATORS.md`](docs/VALIDATORS.md).

## Where this fits in Park Jun-woo's tooling

`ratchet-cli` is the `next`-command pattern that Park Jun-woo uses across
**filefunc** (one-file-one-function discipline), **tsma** (auto-writing tests
for legacy code), and **yongol** (SaaS backend codegen) — extracted into a
language- and domain-neutral CLI. Those domain-specific tools stay put. We
take only the shared mechanism: a state machine that drives large batches of
work to completion under mechanical validation. The validators you write
fill in the domain — `.ratchet/validators/` is where your project's specifics
live. ratchet-cli itself stays small on purpose.

This tool sits between codegen (e.g., yongol) and post-implementation review.
For artifact-level inspection of AI-produced code, see also
[NEKOWORK](https://github.com/Ps-Neko/NEKOWORK), an independently developed
quality-gate tool that Park Jun-woo (@park_jun_woo) himself called
"a textbook example of Reins Engineering."

## Drop into an existing project — three scenarios

### Python project (pytest + ruff)

```bash
ratchet init                                           # 1. seed .ratchet/
$EDITOR .ratchet/validators/lint.sh                    # 2. replace with: exec ruff check .
$EDITOR .ratchet/validators/test.sh                    # 3. replace with: exec pytest -q
ratchet validate                                       # 4. confirm both pass
ratchet add "rewrite User model to use Pydantic v2"    # 5. ready
```

### Node / TypeScript project (npm + eslint)

```bash
ratchet init                                           # 1.
$EDITOR .ratchet/validators/lint.sh                    # 2. exec npx eslint .
$EDITOR .ratchet/validators/test.sh                    # 3. exec npm test --silent
ratchet validate                                       # 4.
ratchet add "migrate /api/users to App Router"         # 5.
```

### Go project (go test + golangci-lint)

```bash
ratchet init                                           # 1.
$EDITOR .ratchet/validators/lint.sh                    # 2. exec golangci-lint run
$EDITOR .ratchet/validators/test.sh                    # 3. exec go test ./...
ratchet validate                                       # 4.
ratchet add "extract auth middleware into internal/auth"  # 5.
```

The built-in templates already auto-detect these toolchains, so on a
well-configured project step 2/3 may be optional. Customize them when you
want a narrower or faster check (`pytest tests/auth/` over the full suite).

## Commands

| command | purpose |
|---|---|
| `ratchet init`       | create `.ratchet/` in cwd (safe in existing projects) |
| `ratchet add <…>`    | register work items (args, `--file PATH`, or stdin via `--file -`) |
| `ratchet next`       | print the next pending item; idempotent until `submit` |
| `ratchet submit`     | run validators against the current item; lock on pass |
| `ratchet status`     | counts, current item, recent submit history |
| `ratchet validate`   | run all validators without consuming an item |
| `ratchet reset`      | wipe items/cursor (keeps `history.jsonl` and validators) |
| `ratchet skill`      | print `SKILL.md` for Claude Code consumption |

`ratchet <cmd> --help` shows flags.

## What gets written under `.ratchet/`

```
.ratchet/
├── state.json        # items + cursor + current (gitignored — per-dev)
├── config.json       # toggles (require_all_pass, warning_blocks, allow_skipped)
├── history.jsonl     # append-only log (committed — team asset)
├── validators/       # drop-in validators (committed)
└── .gitignore        # auto-generated; controls what travels with the team
```

History is intentionally committed: the record of what passed and when is
worth more than re-deriving it. State (cursor, current) is per-developer,
so it's ignored to avoid merge conflicts.

## Use with Claude Code

```bash
ratchet skill > .claude/skills/ratchet/SKILL.md
```

The bundled SKILL.md teaches Claude Code the contract: ask `ratchet next`,
do exactly one item, run `ratchet submit`, read validator output on
failure, never declare done yourself, never bypass with `reset`. See
`ratchet skill | less` for the full text.

## Documentation

- [`docs/VALIDATORS.md`](docs/VALIDATORS.md) — the validator plugin contract:
  exit codes, env vars, naming convention, writing rules, recipes.
- [`CHANGELOG.md`](CHANGELOG.md)

## Sources and credit

The mechanism, philosophy, and demonstrative examples are entirely
박준우 (@park-jun-woo)'s. This package extracts a thin CLI from his
ecosystem; the original tools and writing are where the substance lives:

- *Reins Engineering*: <https://www.parkjunwoo.com/ko/opinion/reins-engineering/>
- *The Ratchet Pattern*: <https://www.parkjunwoo.com/ko/tech/ratchet-pattern/>
- *IFEval × Ratchet*: <https://www.parkjunwoo.com/ko/tech/ifeval-ratchet/>
- *Hurl & vibe-coding drift*: <https://www.parkjunwoo.com/ko/tech/hurl-vibe-coding-drift/>
- Reference implementations: <https://github.com/park-jun-woo/tsma> ·
  <https://github.com/park-jun-woo/filefunc>

## License

MIT — see [LICENSE](LICENSE).
