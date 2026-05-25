---
name: ratchet
description: |
  Deterministic ratchet for AI coding work. Use when the user has registered
  work items via `ratchet add` (or asks you to do so) and wants you to execute
  them one at a time under mechanical validation. Implements Park Jun-woo's
  Reins Engineering / Ratchet Pattern: validators decide "done", not the model.
---

# Skill: ratchet

You are operating under the **Ratchet Pattern**. The user does not trust your
judgment on whether work is complete. A `ratchet` CLI tool gates progression.
Your job is to do the work; the validators decide pass/fail.

## Core contract

1. **Ask `ratchet next` for what to do.** Never invent the next item.
2. **Do exactly one item at a time.** Do not batch.
3. **Run `ratchet submit` when you believe the item is done.**
4. If submit fails, **read the validator output**, fix the specific errors
   reported, and re-submit. Do not redesign or rescope.
5. When `ratchet next` prints `DONE`, stop.

## Loop

```
loop:
  out = $(ratchet next)
  if out == "DONE": exit
  # out is "[<id>] <text>", treat <text> as the user's instruction
  perform the work
  ratchet submit
  if submit exited non-zero:
    read stderr (validator output) — these are facts, not opinions
    fix the specific lines/files/errors named
    ratchet submit   # repeat until pass
```

## Rules — what NOT to do

- **Do not declare an item complete yourself.** Only `ratchet submit` returning
  exit 0 means done.
- **Do not modify `.ratchet/state.json` directly.** Use the CLI.
- **Do not bypass validators with `--skip-validators` unless the user explicitly
  asks.** It is recorded in history and defeats the ratchet.
- **Do not refactor, rename, or "clean up" code that isn't the current item.**
  This is exactly the drift behavior the ratchet exists to prevent.
- **Do not add new items via `ratchet add` unless the user asks.** You execute
  the queue; the user owns the queue.

## Reading validator output

Validators emit facts, not opinions:

```
[FAIL] lint.sh  exit=1  240ms
--- lint.sh (fail) ---
src/auth.py:41: undefined name 'user_id'
```

Treat each line as a concrete claim about a file and position. Fix that exact
location. If the validator output is empty or unclear, surface that to the user
— do not guess.

## Idempotency / crash recovery

`ratchet next` is idempotent: calling it twice without an intervening
`ratchet submit` returns the same item. If your previous session was killed,
just run `ratchet next` again — you will get the same item with `(resumed)`
appended.

## Useful commands

- `ratchet status` — counts, current item, recent pass/fail
- `ratchet validate` — run all validators without consuming an item
- `ratchet next` / `ratchet submit` — the main loop
- `ratchet add "<text>"` — only if the user asked

## Background — why this exists

The user has read Park Jun-woo's writing on **Reins Engineering** and the
**Ratchet Pattern**. The premise: LLMs generate well but cannot reliably judge
completeness; mechanical validators can. Stay inside the rails. Generate;
let the validators close the loop.
