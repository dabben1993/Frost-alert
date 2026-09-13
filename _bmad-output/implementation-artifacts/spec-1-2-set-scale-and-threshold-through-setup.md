---
title: 'Set scale and threshold through setup'
type: 'feature'
created: '2026-09-13'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '8097539aa3e41ca36d0817e109ad1daaed951757'
context:
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 1.1 left an installable package with empty entrypoints. The owner still cannot set temperature scale or frost threshold without editing source, so later checks have no stored `threshold_c`.

**Approach:** Add a local `frost-alert setup` CLI that prompts for scale and threshold, converts Fahrenheit to Celsius in domain, and writes `scale` and `threshold_c` to `config/user.json` through ConfigStore.

## Boundaries & Constraints

**Always:**
- Work on branch `1-2-set-scale-and-threshold-through-setup` from current `master`, not on `master`.
- Invoke as `frost-alert setup` via `[project.scripts]`. Interactive stdin prompts; no flags for scale or threshold.
- Empty scale → `C`. Empty threshold when scale is `C` → `threshold_c` `3`. Scale is stored uppercase `C` or `F` (input case-insensitive). When scale is `F`, threshold must be an explicit number — do not treat empty as 3.
- Domain converts display threshold to Celsius with `(F - 32) * 5 / 9` when scale is `F`. Domain and `config/user.json` store Celsius; `scale` is for setup and later display only.
- This story’s file contains only `scale` and `threshold_c`. Path is `config/user.json` relative to CWD; create `config/` if needed. Re-run overwrites those keys.
- Invalid scale (not `C`/`F`) or non-numeric threshold: do not write the file (existing file unchanged), print what to enter (`C` or `F`; a number in the chosen scale), exit non-zero.
- Domain has no I/O. ConfigStore gains the write method this story needs; a JSON adapter implements it. Unit tests use a fake ConfigStore and must not open a network connection.
- Keep the seven port **names**. Add a method only on `ConfigStore`.

**Never:**
- Do not geocode, prompt for location, or write `place_name`, `lat`, `lon`, `elevation_m`, or `timezone` (Story 1.3).
- Do not implement StateStore, check entrypoint, classification, Telegram, failover, or `.github/workflows/check.yml`.
- Do not add `requests`, `httpx`, or a web framework.
- Do not invent methods on ForecastSource, Notifier, AckInbox, Watchdog, StateStore, or Clock.
- Do not commit secrets, `.env`, or `.venv`.
- Do not change `_bmad/`, `.agents/`, planning artifacts, or `scripts/poc-telegram-getupdates.py`.
- Do not weaken `tests/test_package.py` isolation or banned-dep checks.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Celsius defaults | `frost-alert setup`; empty scale; empty threshold | `config/user.json` has `scale` `"C"` and `threshold_c` `3` | N/A |
| Fahrenheit convert | scale `F`; threshold `32` | `scale` `"F"`; `threshold_c` `0` | N/A |
| Re-run | file already has scale/threshold; enter new valid values | file updated to the new scale and Celsius threshold | N/A |
| Bad scale | scale `K` (or other non-C/F) | no write; existing file untouched | explain `C` or `F`; exit ≠ 0 |
| Bad threshold | non-numeric threshold | no write; existing file untouched | explain a numeric threshold; exit ≠ 0 |
| F without number | scale `F`; empty threshold | no write | empty is not a number when scale is `F` |

</frozen-after-approval>

## Code Map

- `src/frost_alert/entrypoints/` -- empty; add `setup.py` `main`. No check entrypoint.
- `src/frost_alert/ports/__init__.py` -- `ConfigStore` empty (L20-21); add write method only. Other six stay method-empty.
- `src/frost_alert/domain/` -- empty; validation + °F→°C live here, not in the CLI.
- `src/frost_alert/adapters/` -- empty; JSON ConfigStore for `config/user.json`. File I/O, no HTTP.
- `pyproject.toml` -- no scripts yet; register `frost-alert`. No runtime HTTP deps.
- `tests/test_package.py` -- keep isolation + banned-dep + `block_live_network` (L94-100). New setup tests go in a new module. Touch `FakeConfigStore` only if the new method breaks 1.1 tests.
- `config/` -- missing; setup creates it. Do not commit a placeholder `user.json`.

## Tasks & Acceptance

**Execution:**
- [x] `1-2-set-scale-and-threshold-through-setup` -- create this branch from `master` -- no story work on `master`
- [x] `tests/test_setup_scale_threshold.py` -- failing tests for every I/O matrix row (fake ConfigStore; tmp_path for JSON adapter) -- red first
- [x] `src/frost_alert/domain/` -- validate scale/threshold; convert `F` to Celsius -- AD-7 in domain
- [x] `src/frost_alert/ports/__init__.py` -- ConfigStore write method -- first port signature
- [x] `src/frost_alert/adapters/` -- JSON ConfigStore writes `config/user.json` under a given root -- setup-only writer
- [x] `src/frost_alert/entrypoints/setup.py` -- prompt scale then threshold; domain then ConfigStore; usage if argv ≠ `setup`
- [x] `pyproject.toml` -- `[project.scripts] frost-alert = "frost_alert.entrypoints.setup:main"`
- [x] `tests/test_package.py` -- keep 1.1 tests green if ConfigStore grows a method

**Acceptance Criteria:**
- Given a valid setup run, when it finishes, then only `config/user.json` changed — no source edits.
- Given a Fahrenheit threshold, when domain converts it, then `threshold_c` is Celsius and the CLI does not apply its own formula.

## Implementation Notes

- Branch `1-2-set-scale-and-threshold-through-setup` from `8097539`. ConfigStore method is `write_scale_and_threshold`. Domain uses `Decimal` so `F`+`37.4` is exactly `3`.
- `uv run pytest` — 27 passed after review patches (`sys.argv` `main()`, default CWD store, console-script entry, usage text). Live `frost-alert setup` with empty answers wrote `scale` `C` and `threshold_c` `3`.

## Spec Change Log

## Review Triage Log

- `false` — Blind: two-key replace wipes 1.3 location. `json_config_store.py:14` writes exactly `scale` and `threshold_c`. Location keys are unreachable this story (frozen Never). Specified document is those two keys.
- `low` — Blind: `write_text` can truncate then fail. Real on disk error; not everyday. Reject: atomic replace adds complexity for an undemonstrated I/O failure. Spec only requires unchanged file on validation errors.
- `medium` — Blind: production `main()` defaults untested. Every CLI test injects `config_store` and argv. Documented `frost-alert setup` path can break while pytest stays green.
- `low` — Blind: uncaught `EOFError` on `input()`. Closed stdin tracebacks; redirected empty answers are newlines, not EOF. Reject: everyday setup is interactive; guard is a new branch for undemonstrated EOF.
- `false` — Blind: silent success / wrong CWD. Frozen Always: path is CWD `config/user.json`. No success banner required.
- `false` — Blind: F+empty does not assert file bytes. `test_matrix_fahrenheit_empty_threshold_does_not_write` asserts no store write; `main` returns before `write_scale_and_threshold` on `InvalidSetupInput`.
- `false` — Blind: `F`+`37.4` not JSON-round-tripped. Domain returns `int` `3`; `_json_number(3)` writes JSON integer `3`. Claimed non-integer persist does not occur.
- `false` — Blind: empty `FakeConfigStore` vs `RecordingConfigStore`. `test_fake_ports_cover_all_ports_without_network` only constructs fakes; it never calls the new method.
- `false` — Blind: comma decimals. Frozen examples and matrix use `.` (`32`, `37.4`). `3,5` is non-numeric under specified `Decimal` validation.
- `false` — Blind: sprint `in-progress` vs spec `in-review`; stale Code Map. Workflow owns sprint status; Code Map is a planning snapshot. Fix would edit this spec — rejected.
- `low` — Edge: `setup.py:23-24` EOF on prompts. Same as Blind EOF. Reject: not everyday.
- `low` — Edge: `json_config_store.py:11-15` OSError after truncate. Same as Blind atomic write. Reject: not everyday.
- `low` — Edge: Decimal Overflow on huge `F`. Extreme exponent, not everyday threshold. Reject: fix is a new overflow branch for undemonstrated input.
- `maybe-false` — Edge: `int()` digit limit on huge integral threshold. Reproduction hung on a huge `Decimal` first. If true, still `low` (not everyday) — reject.
- `medium` — Verification-gap: `argv is None` / `sys.argv[1:]` never runs. All tests pass an argv list; `frost-alert setup` calls `main()` with no argv. Disposition: patch.
- `medium` — Verification-gap: default `JsonConfigStore()` CWD write never runs. All `main(...)` calls inject `config_store`. Disposition: patch.
- `medium` — Verification-gap: `[project.scripts] frost-alert` never loaded via `importlib.metadata`. Disposition: patch.
- `low` — Verification-gap: `test_usage_when_argv_is_not_setup` never asserts `USAGE`. Deleting the print still passes. Direct `capsys` check. Disposition: patch.

## Design Notes

Story 1.3 owns location keys (AD-3’s full document). 1.2 writes only `scale` and `threshold_c`. Collect both prompts, validate, then write once so a bad value cannot clobber an existing file. Extra golden: `F` + `37.4` → `threshold_c` `3`.

## Verification

**Commands:**
- `uv sync` -- expected: `frost-alert` console script installed
- `uv run pytest` -- expected: all tests pass, including the I/O matrix module
- `uv run frost-alert setup` with redirected empty answers -- expected: `config/user.json` contains `"scale": "C"` and `"threshold_c": 3`
