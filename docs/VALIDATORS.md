# Validators

A validator is any executable file in `.ratchet/validators/`. The CLI runs each
one, reads its exit code, and reports the outcome. Validators are how the
ratchet decides "done" — not the LLM, not you.

The contract is small. The rules behind the contract are not.

---

## 1. Drop-in installation

Put a file in `.ratchet/validators/`. That's it.

```
.ratchet/validators/
├── 10-lint.sh         # runs first (alphabetical)
├── 20-test.py         # runs second
├── 30-hurl.sh         # runs third
└── _disabled.sh       # ignored (leading underscore)
```

The CLI discovers files on every run — no registry to maintain.

---

## 2. Exit code contract

| code | meaning | blocks submit? |
|---:|---|---|
| **0** | pass — validator ran and the check succeeded | no |
| **1** | fail | **yes** |
| **2** | warning — counted but advisory | only if `warning_blocks=true` |
| **78** | skipped — validator ran but could not verify (e.g. tool missing) | **yes** (unless `allow_skipped=true`) |
| any other | error — validator itself is broken or could not be invoked | **yes** |

Exit 78 is the most important rule. **Never return exit 0 when you did not
actually verify something.** A validator that says "no linter installed, so I'll
say pass" is a false ratchet — exactly the failure mode Reins Engineering
exists to prevent.

Example, the right way:

```bash
if ! command -v ruff >/dev/null 2>&1; then
  echo "SKIP: ruff not installed" >&2
  exit 78
fi
exec ruff check .
```

`ratchet validate` exits 0 only when every validator returns exit 0 — no fails,
no warns, no skips, no errors. Park Jun-woo's bar.

---

## 3. Discovery and run order

* Files in `.ratchet/validators/` are discovered on every run.
* Order is **lexicographic by filename**. Use numeric prefixes to enforce
  dependencies: `10-lint.sh`, `20-test.sh`, `30-hurl.sh`.
* Files whose name starts with `.` or `_` are ignored.
* `.tmp` files are ignored.
* Recognized handlers:
  * `*.py` → `python` (always)
  * `*.sh` → `bash` (skipped with exit 78 if `bash` not on `PATH`)
  * any other file → must be executable (`chmod +x` on POSIX); run directly
* Windows: `.bat` / `.cmd` / `.exe` work via the OS — no extra setup.

There is no "validator manifest." There is no priority field. The filename
*is* the contract.

---

## 4. Environment variables

The CLI sets these for every validator process. Treat them as the only
parameter passing channel.

| name | when set | meaning |
|---|---|---|
| `RATCHET_PROJECT_ROOT` | always | absolute path of the directory containing `.ratchet/` |
| `RATCHET_PHASE` | always | `"submit"` (during `ratchet submit`) or `"validate"` (during `ratchet validate`) |
| `RATCHET_ITEM` | submit only | raw text of the current item, exactly as the user added it |
| `RATCHET_ITEM_ID` | submit only | integer id (string-encoded) |
| `RATCHET_ITEM_INDEX` | submit only | 0-based position in `state.items` |

`cwd` of the validator process is `RATCHET_PROJECT_ROOT`. You can rely on
that for relative paths.

A validator can short-circuit based on `RATCHET_PHASE`. For example, a slow
end-to-end test might run only during `validate`, not on every `submit`:

```bash
if [ "$RATCHET_PHASE" = "submit" ]; then
  echo "SKIP: e2e runs only on manual \`ratchet validate\`" >&2
  exit 78
fi
```

---

## 5. Writing rules (Reins Engineering)

These are not style preferences. They are why the ratchet works.

### 5.1 Output facts, not opinions

The LLM consumes your stderr/stdout as a fact list to fix. Make every line
mechanically actionable.

| ✗ opinion (bad) | ✓ fact (good) |
|---|---|
| `code is messy` | `src/auth.py:41: E501 line too long (132 > 100)` |
| `tests look wrong` | `tests/test_login.py::test_logout FAILED at line 23: AssertionError` |
| `consider using X` | (don't say it — validators don't advise; they assert) |

Reference: include filename, line number, error code, and the asserted vs.
actual where applicable. The LLM will go to that exact location and fix it.

### 5.2 Be fast

Validators run on every `ratchet submit`. The ratchet loop is "do one thing,
prove it, do the next thing." If proving takes 30s, the loop dies.

* Target: **under 1 second per validator**.
* If a check is necessarily slow (full e2e, integration suite), gate it on
  `RATCHET_PHASE=validate` and run it manually.
* Prefer narrow checks: `pytest tests/auth/` over `pytest`.

### 5.3 No side effects

Validators must be **idempotent and observation-only**.

| forbidden | reason |
|---|---|
| writing files outside `.ratchet/cache/` | the validator is a witness, not an actor |
| network calls to mutable endpoints | non-deterministic; breaks the ratchet |
| auto-formatting (`black --in-place`, `prettier --write`) | hides what was wrong; LLM cannot learn |
| modifying git state | catastrophic and surprising |

A formatter check is fine — but invoke it in `--check` / `--diff` mode and let
the LLM apply the fix.

### 5.4 Be one thing

One validator file = one concern. Compose by adding more files, not by branching
inside one. This mirrors filefunc's "one file, one concept" — the LLM (and the
human running `ratchet status`) can reason about one signal at a time.

---

## 6. Mapping to Park Jun-woo's nine Sources of Truth

The yongol/Reins ecosystem cross-checks code against nine SoTs before
compilation. Four of them have built-in validator templates seeded by
`ratchet init`. The other five are easy to add — recipes below.

| SoT | built-in? | how to wire |
|---|---|---|
| **Hurl** (HTTP behavior) | ✅ `hurl.sh` | seeded — drop `*.hurl` files under `tests/` |
| **lint / style** (any linter) | ✅ `lint.sh` | seeded — auto-detects ruff/eslint/flake8/golangci-lint |
| **tests** (any runner) | ✅ `test.sh` | seeded — auto-detects pytest/npm-test/go-test/cargo-test |
| **build** (compilation success) | ✅ `build.sh` | seeded — auto-detects npm-build/python/go/cargo |
| **OpenAPI ↔ code** | ⛔ | recipe §6.1 |
| **DDL ↔ ORM** | ⛔ | recipe §6.2 |
| **OPA Rego** (authz policy) | ⛔ | recipe §6.3 |
| **Mermaid state diagram ↔ code** | ⛔ | recipe §6.4 |
| **manifest.yaml** (infra/config) | ⛔ | recipe §6.5 |

Built-ins stop at 4 by design. Adding more grows the dependency surface of
ratchet-cli itself. **Write your own** — it's a 10-line shell script.

### 6.1 OpenAPI ↔ code

Drop `40-openapi.sh`:

```bash
#!/usr/bin/env bash
set -u
cd "${RATCHET_PROJECT_ROOT:-$PWD}"
SPEC="${OPENAPI_SPEC:-openapi.yaml}"
if [ ! -f "$SPEC" ]; then
  echo "SKIP: $SPEC not found" >&2; exit 78
fi
if ! command -v redocly >/dev/null 2>&1; then
  echo "SKIP: @redocly/cli not installed" >&2; exit 78
fi
exec redocly lint "$SPEC"
```

For drift between spec and handlers, generate clients/servers via
`openapi-generator` or `oapi-codegen` and check the diff:

```bash
oapi-codegen -generate types,server -o /tmp/gen.go "$SPEC"
diff -q /tmp/gen.go internal/api/generated.go || { echo "FAIL: openapi/code drift"; exit 1; }
```

### 6.2 DDL ↔ ORM

```bash
#!/usr/bin/env bash
set -u
cd "${RATCHET_PROJECT_ROOT:-$PWD}"
if ! command -v sqlc >/dev/null 2>&1; then
  echo "SKIP: sqlc not installed" >&2; exit 78
fi
sqlc diff || { echo "FAIL: DDL/sqlc out of sync — run \`sqlc generate\`"; exit 1; }
```

### 6.3 OPA Rego

```bash
#!/usr/bin/env bash
set -u
cd "${RATCHET_PROJECT_ROOT:-$PWD}"
if ! command -v opa >/dev/null 2>&1; then
  echo "SKIP: opa not installed" >&2; exit 78
fi
opa test policy/ -v
```

### 6.4 Mermaid state diagram ↔ code

Author the spec as `docs/states/order.mmd`. Write a small extractor (`scripts/extract-states.py`)
that returns the set of states/transitions found in your code, and compare to the
parsed Mermaid. The validator just shells out:

```bash
python scripts/check-states.py docs/states/order.mmd internal/order/state.go
```

Return exit 1 on mismatch with concrete lines. (This is where filefunc's
`//ff:` annotations earn their keep.)

### 6.5 manifest.yaml

```bash
#!/usr/bin/env bash
set -u
cd "${RATCHET_PROJECT_ROOT:-$PWD}"
if ! command -v yq >/dev/null 2>&1; then
  echo "SKIP: yq not installed" >&2; exit 78
fi
# example: every service in manifest.yaml has a Dockerfile
for svc in $(yq '.services[].name' manifest.yaml); do
  [ -f "services/$svc/Dockerfile" ] || { echo "FAIL: services/$svc/Dockerfile missing"; exit 1; }
done
```

---

## 7. Testing your validator

Validators are scripts. Run them directly with the env vars set:

```bash
RATCHET_PROJECT_ROOT="$PWD" \
RATCHET_PHASE=submit \
RATCHET_ITEM="implement /login" \
RATCHET_ITEM_ID=1 \
RATCHET_ITEM_INDEX=0 \
bash .ratchet/validators/20-test.sh
echo "exit=$?"
```

Expected exit codes:

```bash
# unit-test your validator
bash my-validator.sh ; [ $? -eq 78 ] && echo OK   # when tool is missing
bash my-validator.sh ; [ $? -eq 0 ]  && echo OK   # when everything is wired
```

`ratchet validate` is the canonical "are all validators wired correctly" check.
Run it after editing.

---

## 8. Anti-patterns

* **A validator that emits a natural-language summary at the top.** Just dump
  the tool's raw output; the LLM is fine with stack traces.
* **A "smart" validator that calls an LLM to judge.** That is exactly what the
  ratchet exists to avoid. Validators are mechanical.
* **A validator that fixes the problem instead of reporting it.** The LLM has
  to learn from the fact list. Auto-fixing hides the fact.
* **Catch-all: `|| true` to keep exit 0.** Now the ratchet ratchets nothing.

If any of these feel useful in your project, you don't need a validator —
you need a script. Validators are a smaller thing.
