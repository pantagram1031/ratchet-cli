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
    diagnose (see "When submit is blocked" below)
    fix the specific lines/files/tools named
    ratchet submit   # repeat until pass
```

## Exit code regime — what each validator outcome means

| code | name | what it means | what you do |
|---:|---|---|---|
| **0** | pass | validator ran and verified | move on |
| **1** | fail | validator ran and found a problem | read output, fix the code, re-submit |
| **2** | warn | advisory; usually does not block | ignore unless `warning_blocks=true` |
| **78** | skip | validator ran but could **not** verify (tool missing) | install the missing tool — **never report skip as pass** |
| any other | error | the validator itself is broken | tell the user; do not try to fix the validator silently |

### "0 error 0 warning" — real definition

`ratchet validate` exits 0 **only** when every validator returned exit 0.
That means **0 fail AND 0 warn AND 0 skip AND 0 error**. A skip is not a
pass. If you see "1 skip" in the summary line, the bar is not met.

## When `ratchet submit` is blocked — diagnose in this order

1. **Run `ratchet status`.** Look at the most recent submit line. The counts
   are formatted as `Np/Nf/Nw/Ns/Ne` (pass / fail / warn / skip / error).
2. **If `f > 0` (fail) or `e > 0` (error):** read the validator's stdout/stderr
   from the submit output. Each line names a file, line number, and concrete
   error. Go to that exact location and fix it. Re-submit.
3. **If `s > 0` (skip):** look at the stderr line of the form
   `SKIP: <tool> not found ...`. The validator could not verify because a tool
   isn't installed. **Tell the user which tool to install** (or install it if
   the user has authorized that). Do not retry submit until the skip is
   resolved — re-submitting will just block again.
4. **If `w > 0` (warn) and submit blocked:** the user has set
   `warning_blocks=true`. Either resolve the warning, or ask the user whether
   to toggle `warning_blocks=false` in `.ratchet/config.json`. Do not toggle
   it without permission.

## `RATCHET_PHASE` — submit vs. validate

Validators receive `RATCHET_PHASE=submit` during `ratchet submit` and
`RATCHET_PHASE=validate` during `ratchet validate`. Validators may
short-circuit (exit 78) when the phase doesn't match — for example, a slow
e2e test that only runs on manual `ratchet validate`.

* `ratchet submit` is the fast inner loop — run it after every item.
* `ratchet validate` is the broader sweep — run it when the user asks, or
  at the end of a session. Do not run it on every submit; it can be slow.

If you don't know which to use, use `submit`. It's the default loop.

## Rules — never do these

- **Never declare an item complete yourself.** Only `ratchet submit` returning
  exit 0 means done.
- **Never report a skip as a pass.** "1 skip" means nothing was verified.
  Treat it like a failure: surface the missing tool to the user.
- **Never bypass a blocked submit with `ratchet reset`.** Reset wipes state.
  Using it to escape a failing validator is the exact "lying to make it pass"
  pattern the ratchet exists to prevent.
- **Never ignore validator output and move to the next item.** If submit
  failed, the same item is still locked — `ratchet next` will keep returning
  it until you fix it.
- **Never use `--skip-validators` unless the user explicitly asks.** It is
  recorded in history and defeats the ratchet.
- **Never modify `.ratchet/state.json` directly.** Use the CLI.
- **Never refactor, rename, or "clean up" code that isn't the current item.**
  This is exactly the drift behavior the ratchet exists to prevent.
- **Never add new items via `ratchet add` unless the user asks.** You execute
  the queue; the user owns the queue.

## Reading validator output

Validators emit facts, not opinions:

```
[FAIL] lint.sh  exit=1  240ms
--- lint.sh (fail) ---
src/auth.py:41: undefined name 'user_id'
```

Treat each line as a concrete claim about a file and position. Fix that exact
location. If the validator output is empty or unclear, surface that to the
user — do not guess.

## Idempotency / crash recovery

`ratchet next` is idempotent: calling it twice without an intervening
`ratchet submit` returns the same item. If your previous session was killed,
just run `ratchet next` again — you will get the same item with `(resumed)`
appended.

## Useful commands

- `ratchet status` — counts, current item, recent submits with p/f/w/s/e
  breakdown
- `ratchet validate` — run all validators without consuming an item; the
  authoritative "is everything green?" check
- `ratchet next` / `ratchet submit` — the main loop
- `ratchet add "<text>"` — only if the user asked

## Background — why this exists

The user has read Park Jun-woo's writing on **Reins Engineering** and the
**Ratchet Pattern**. The premise: LLMs generate well but cannot reliably judge
completeness; mechanical validators can. Stay inside the rails. Generate;
let the validators close the loop.
