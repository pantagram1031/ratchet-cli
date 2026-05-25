# Phase 5 — End-to-end verification report

Executed against `v0.1.0-rc1` source tree on Windows 11, Python 3.11.9,
Git Bash. `pipx` not available on the test host; substituted with
`python -m venv` + `pip install -e .` (functionally equivalent: isolated
environment with the same entry point on PATH).

```
ratchet --version
→ ratchet-cli 0.1.0
```

11 mandatory scenarios run; 1 optional scenario skipped. **4 real bugs
discovered during e2e and fixed before tagging v0.1.0.** Each fix landed
as its own commit so the v0.1.0-rc1 → v0.1.0 delta is bisectable.

---

## Scenarios

### 1 — Local install

```
$ python -m venv .venv && .venv/Scripts/python.exe -m pip install -e <src>
$ ratchet --version
ratchet-cli 0.1.0
$ ratchet --help
…shows 8 subcommands…
```

Result: **PASS**.

### 2 — `ratchet init` creates `.ratchet/`

Fresh `sandbox/`, ran `ratchet init`. Output:

```
initialized: …/sandbox/.ratchet
seeded 4 validator(s): build.sh, hurl.sh, lint.sh, test.sh
```

Tree:

```
.ratchet/
├── .gitignore       362 bytes — state.json ignored, history.jsonl committed
├── config.json      {require_all_pass: true, warning_blocks: false,
│                     allow_skipped: false, require_validators: true}
├── history.jsonl    (empty)
├── state.json       {items: [], cursor: 0, current: null}
└── validators/      build.sh hurl.sh lint.sh test.sh (all chmod +x)
```

Git Bash was detected on the host, so `.sh` templates were seeded. The
auto-detection path was exercised; `--shell=py` and `--shell=both` flags
remain available but were not used in this scenario.

Result: **PASS**.

### 3 — 5 items added; full next/submit loop completes

After `init`, replaced the four seeded validators with trivial
`#!/usr/bin/env bash\nexit 0` to demonstrate the loop without external
toolchains.

```
$ ratchet add "implement /login endpoint" "implement /logout endpoint" \
              "add password reset flow" "wire up session cookies" \
              "write integration tests"
added 5 item(s). total pending: 5

$ for i in 1..5: ratchet next; ratchet submit
[1] implement /login endpoint
  [PASS] build.sh exit=0 78ms
  [PASS] hurl.sh  exit=0 62ms
  [PASS] lint.sh  exit=0 62ms
  [PASS] test.sh  exit=0 62ms
summary: 4 pass, 0 fail, 0 warn, 0 skip, 0 error
[1] locked.
… (items 2 through 5) …

$ ratchet next
DONE

$ ratchet status
items: 5 total | 5 done | 0 in_progress | 0 pending
cursor: 5
submits: 5 recorded (5 pass, 0 fail)
recent submits:
  ✓ [1] implement /login endpoint (4p/0f/0w/0s/0e)
  ✓ [2] implement /logout endpoint (4p/0f/0w/0s/0e)
  ✓ [3] add password reset flow (4p/0f/0w/0s/0e)
  ✓ [4] wire up session cookies (4p/0f/0w/0s/0e)
  ✓ [5] write integration tests (4p/0f/0w/0s/0e)
```

Result: **PASS**.

> **Bug fix #1 (from this scenario):** `ratchet status` crashed with
> `UnicodeEncodeError: 'cp949' codec can't encode character '—'` because
> Windows console codepage is cp949. Fixed by reconfiguring `sys.stdout`
> and `sys.stderr` to UTF-8 with `errors="replace"` at CLI entry.
> Commit: `fix(cli): force UTF-8 stdio …`.

### 4 — Failing validator blocks submit

Fresh sandbox, replaced `test.sh` with one that prints a concrete failure
and exits 1:

```bash
#!/usr/bin/env bash
echo "src/auth.py:41: undefined name 'user_id'"
echo "tests/test_auth.py::test_login FAILED"
exit 1
```

```
$ ratchet submit
--- test.sh (fail) ---
src/auth.py:41: undefined name 'user_id'
tests/test_auth.py::test_login FAILED

blocked: 1 fail
  [PASS] build.sh exit=0 77ms
  [PASS] hurl.sh  exit=0 62ms
  [PASS] lint.sh  exit=0 78ms
  [FAIL] test.sh  exit=1 78ms
summary: 3 pass, 1 fail, 0 warn, 0 skip, 0 error
[exit=1]

$ ratchet status
items: 2 total | 0 done | 1 in_progress | 1 pending
current: [1] implement /login
recent submits:
  ✗ [1] implement /login (3p/1f/0w/0s/0e)

$ ratchet next
[1] implement /login (resumed)
```

Failure excerpt is surfaced verbatim (no LLM-style summarization). Cursor
does not advance. `next` re-prints the same item with `(resumed)` tag.

Result: **PASS**.

### 5 — Output legibility

All scenario outputs reproduce above. Format conventions observed:
- Per-validator lines: `[STATUS] <name>  exit=N  Nms`
- Summary: `N pass, N fail, N warn, N skip, N error`
- Blocking explanation: `blocked: <reason1>; <reason2>; …` with actionable
  prescription on the next line.
- "next action" hint appended to every state-changing command.

Result: **PASS**.

### 6 — Idempotent crash-recovery

Three back-to-back `ratchet next` calls in **three separate shells** (each
shell exited between calls — no in-memory state preserved):

```
shell-1: $ ratchet next
         [1] first task

shell-2: $ ratchet next
         [1] first task (resumed)

shell-3: $ ratchet next
         [1] first task (resumed)

         $ ratchet submit
         summary: 4 pass, 0 fail, 0 warn, 0 skip, 0 error
         [1] locked.

shell-4: $ ratchet next
         [2] second task         ← no (resumed) tag, cursor advanced
```

Implementation: `state.current` is the lock. `next` only mutates state
when it transitions an item to in_progress; if `current != null` it
re-prints. `submit` is the only command that clears `current`.

Result: **PASS**. The phase-1 idempotency contract holds across hard
shell boundaries.

### 7 — Skipped result blocks submit by default; togglable

Fresh sandbox with seeded validators (no npm/pytest/go/cargo/hurl
installed in the sandbox — all four return exit 78 with a `SKIP:` line).

```
$ ratchet submit
--- build.sh (skip) ---
SKIP: build: no build tool detected (npm-build/python/go/cargo).
SKIP: install one or edit .ratchet/validators/build.sh to wire your build command.
--- hurl.sh (skip) ---
SKIP: hurl: not installed (https://hurl.dev). …
--- lint.sh (skip) ---
SKIP: lint: no linter detected (ruff/eslint/flake8/golangci-lint/npm-lint). …
--- test.sh (skip) ---
SKIP: test: no test runner detected (pytest/npm-test/go-test/cargo-test). …

blocked: 4 skip — validators could not verify (install the missing tools,
or set allow_skipped=true in config.json)
summary: 0 pass, 0 fail, 0 warn, 4 skip, 0 error
[exit=1]

$ ratchet status
recent submits:
  ✗ [1] implement /health endpoint (0p/0f/0w/4s/0e)
```

Then toggled `allow_skipped: true` in `config.json` and re-ran:

```
$ ratchet submit
…same SKIP output…
summary: 0 pass, 0 fail, 0 warn, 4 skip, 0 error
[1] locked.
[exit=0]

$ ratchet status
items: 1 total | 1 done | 0 in_progress | 0 pending
```

Then reverted `allow_skipped: false` for cleanup.

Result: **PASS**. Skipped truly blocks by default; opt-in via
`allow_skipped: true` lets it through. Park Jun-woo's "no false pass"
contract is enforced.

> **Bug fix #2 (from this scenario):** `lint.sh` and `test.sh` used
> `ls dir1 dir2 2>/dev/null | head -1 >/dev/null` as an "existence test".
> `head -1` always exits 0 on empty stdin, so the gate was always open;
> `pytest` would run in a project with no `tests/` directory and return
> exit 5 (classified as `error`). Replaced with `compgen -G` for globs
> and `[ -d tests ]` for directory checks.
> Commit: `fix(template): correct existence checks …`.

### 8 — Zero-validator submit must not pass trivially

Fresh sandbox, disabled all four seeded validators by renaming with `_`
prefix (recognized as ignored by discovery rules).

```
$ ratchet next
WARN: no validators registered in .ratchet/validators/ — submit will pass trivially.
[1] trivially-pass test item

$ ratchet submit
blocked: 0 validators discovered — refusing to falsely pass. add a
validator under .ratchet/validators/, or set require_validators=false in
config.json
summary: 0 pass, 0 fail, 0 warn, 0 skip, 0 error
[exit=1]
```

Then toggled `require_validators: false` (explicit opt-out):

```
$ ratchet submit
…
[1] locked.
[exit=0]
```

Result: **PASS** (after fix).

> **Bug fix #3:** prior to this fix, zero-validator submits returned
> exit 0 with summary `0p/0f/0w/0s/0e` — a false pass. Added
> `Config.require_validators: bool = True` and a `blocking_empty` reason
> in `submit`. The user spec was explicit: "validator 0개일 때도 submit은
> require_validators 디폴트 옵션으로 잠금."
> Commit: `fix(submit): block when zero validators discovered …`.

### 9 — Lexicographic execution order

Installed three validators in deliberately reverse order (`30-c.sh`,
then `10-a.sh`, then `20-b.sh`), each echoing its name:

```
$ ratchet validate
[PASS] 10-a.sh  exit=0  62ms
[PASS] 20-b.sh  exit=0  62ms
[PASS] 30-c.sh  exit=0  62ms

3 pass, 0 fail, 0 warn, 0 skip, 0 error
```

Then added `90-z.sh` and re-validated:

```
[PASS] 10-a.sh  exit=0  78ms
[PASS] 20-b.sh  exit=0  62ms
[PASS] 30-c.sh  exit=0  62ms
[PASS] 90-z.sh  exit=0  78ms
```

Result: **PASS**. `discover()` returns `sorted(child for child in
iterdir())` so order is deterministic by filename. `NN-name` prefixes
work as documented in [`docs/VALIDATORS.md` §3](VALIDATORS.md).

### 10 — `history.jsonl` schema, integrity, append-only

Setup: 3 items, 3 successful submits with 4 validators each.
Expected line count: 1 (add) + 3 × (4 submit + 1 submit_done) + 3 (next) = **19**.

```
$ wc -l .ratchet/history.jsonl
19

$ python -c "import json; [json.loads(l) for l in open('.ratchet/history.jsonl') if l.strip()]"
(no exception — all lines parse as JSON)
```

Required-field check against the user spec (`ts, cmd, item, validator,
exit, stdout_tail` per submit record):

```
submit records: 12
missing fields: NONE — all submit records have required fields
```

Example record:

```json
{
  "ts": "2026-05-25T02:54:05Z",
  "cmd": "submit",
  "submit_id": "2026-05-25T02:54:05Z",
  "item": "task A",
  "item_id": 1,
  "item_index": 0,
  "validator": "build.sh",
  "exit": 0,
  "status": "pass",
  "duration_ms": 62,
  "stdout_tail": "ran build\n",
  "stderr_tail": ""
}
```

Append-only test: deleted line 8 manually (down to 18 lines), then ran
`ratchet add` + `next` + `submit`. After: 25 lines. First 18 lines
diff-identical to pre-submit snapshot — existing records untouched, new
records appended.

```
first 18 lines IDENTICAL — append-only verified
```

Result: **PASS** (after fix).

> **Bug fix #4:** prior schema stored one record per submit with a
> `results` array — did not match the user-specified per-validator
> schema (`validator` singular, `exit` singular, `stdout_tail` singular).
> Rewrote `submit` to emit N "submit" records + 1 "submit_done" record
> per ratchet submit, all sharing `submit_id`. `status` updated to
> aggregate from `submit_done` records.
> Commit: `fix(history): per-validator jsonl records …`.

### 11 — `ratchet skill` output integrity

```
$ ratchet skill > /tmp/test-skill.md
$ wc test-skill.md
141 lines, 6277 bytes

required keyword check (case-insensitive grep counts):
  [1] exit code         ← table heading
  [1] exit 78           ← skip semantic
  [1] 0 skip            ← "0 fail AND 0 warn AND 0 skip AND 0 error"
  [3] RATCHET_PHASE     ← submit vs validate distinction
  [1] ratchet reset     ← in "never bypass" section
  [11] never
  [9] skip   [11] fail   [7] warn   [7] error
```

Structural check: YAML frontmatter (`name`, `description`) present;
10 `## ` headers found. Valid markdown.

Result: **PASS**.

### 12 — Optional edge cases

Skipped per user authorization. Candidates filed for post-v0.1.0:
- `ratchet reset` while item locked → behavior under read-only `state.json`.
- Concurrent invocations (lock-contention surfacing).

---

## Bug fixes landed during Phase 5

| # | issue | severity | commit |
|---:|---|---|---|
| 1 | Windows cp949 console crash on `—` and other non-ASCII | high (data loss / silent abort) | `fix(cli): force UTF-8 stdio …` |
| 2 | `lint.sh` / `test.sh` existence checks always pass | medium (false-error from pytest exit 5) | `fix(template): correct existence checks …` |
| 3 | zero-validator submit returns exit 0 — false pass | **critical** (Reins philosophy violation) | `fix(submit): block when zero validators …` |
| 4 | `history.jsonl` schema didn't match spec (per-validator fields nested in array) | medium (team-asset usability) | `fix(history): per-validator jsonl records …` |

Plus the v0.1.0-rc1 baseline:
- 25 unit tests, all green
- `compileall` clean

---

## Decision: ready for `v0.1.0` annotated tag?

All 11 mandatory scenarios pass; 4 fixes committed. Pending the CI matrix
(ubuntu/windows/macos × py3.10/3.11/3.12) running green after `git push`.
Per the user's release checklist, `v0.1.0` is only tagged after CI is
green — "검증 안 한 거 pass 처리 = 거짓 pass."

Hand-off to the CI push step.
