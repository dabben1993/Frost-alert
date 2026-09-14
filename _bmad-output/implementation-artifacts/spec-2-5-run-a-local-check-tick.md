---
title: 'Run a local check tick'
type: 'feature'
created: '2026-09-14'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'e2a7319d5a01ff182a203cd6a026601fa5211619'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/_bmad-output/specs/spec-frost-alert/state-machines.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Classify, Open-Meteo, Telegram send, and in/out apply exist, but nothing runs that sequence on a laptop or writes `data/state.json`, so the owner cannot prove the loop before unattended scheduling.

**Approach:** Add `frost-alert check`: one local tick that loads config+state, fetches/classifies only while monitoring, sends an unmarked window, polls Telegram, then StateStore writes `data/state.json`.

## Boundaries & Constraints

**Always:**
- Stay on branch `2-5-run-a-local-check-tick`. No story work on `master`.
- Console script `frost-alert` dispatches `setup` (unchanged) and `check`. Entrypoints only wire. Composer returns state fields; only the check entrypoint calls `StateStore.write`.
- Tick order: load config+state → if `monitoring`, fetch+classify → `maybe_send_frost_alert` (mark only after success) → `apply_telegram_acks` → write `data/state.json`. Suspended: skip forecast and send; still poll and write.
- If monitoring classify returns a set `event_date` different from stored, start `alerted_windows` at `[]` before send. Absent risk: keep stored `event_date` and windows (do not write classify's `None`).
- Notifier raise: do not mark; still poll and write; exit 0. Forecast/classify raise or poll raise: no write; non-zero. Missing `config/user.json` or `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`: no Telegram, no write, non-zero.
- `ConfigStore.load() -> dict` (seven user.json keys; missing file raises). `StateStore.write(*, season, event_date, alerted_windows, telegram_offset)`; stamps `updated_at`. `Clock.now() ->` timezone-aware UTC datetime. Missing state.json still defaults without creating the file; write creates `data/`.
- Check entrypoint reads Telegram secrets from the environment and passes them to constructors. Reuse `classify`, `OpenMeteoForecast.fetch`, `maybe_send_frost_alert`, `apply_telegram_acks`. Tests fake ports; no sockets.

**Never:**
- Do not add `.github/workflows/check.yml`, git commit, Watchdog, MET Norway, `setWebhook`, setup season commands, or re-geocode.
- Do not change `classify.py`, Open-Meteo forecast, `send_frost_alert.py`, `apply_season.py`, Telegram HTTP adapters, setup prompts, or `user.json` / `state.json` keys.
- Do not add `requests`/`httpx`. Do not commit secrets, `.env`, `config/user.json`, or `data/state.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Monitoring send | valid user.json; monitoring; unmarked window 24; owner poll empty | fetch+classify+send; windows `[24]`; `data/state.json` written | N/A |
| Already marked / absent risk | same, windows `[24]` or no qualifying hour | no send; poll; write unchanged windows | N/A |
| Suspended | season `suspended`; inbox `/out` | no fetch/send; then monitoring, event/windows cleared; write | N/A |
| New event | stored event yesterday, windows `[24,12,6]`; classify today window 24 | windows reset then `[24]` after send; write new `event_date` | N/A |
| Notifier raise | send raises | windows unmarked; still poll+write; exit 0 | catch send, continue |
| Forecast raise | Open-Meteo raises | no poll; no write; non-zero | raise |
| Poll raise | send would mark; poll raises | no write; non-zero | raise |
| Missing config or secrets | no user.json, or env token/chat id unset | no Telegram; no write; non-zero | fail closed |

</frozen-after-approval>

## Code Map

- `src/frost_alert/ports/__init__.py` -- `ConfigStore` write-only (L30–41); add `load() -> dict`. `StateStore` load-only (L44–45); add `write(*, season, event_date, alerted_windows, telegram_offset)`. `Clock` empty (L48–49); add `now() -> datetime`.
- `src/frost_alert/adapters/json_config_store.py` -- `write` → `config/user.json` (L11–33). Add `load`; missing file raises. Do not change keys.
- `src/frost_alert/adapters/json_state_store.py` -- `load` defaults, no file create (L12–22). Add `write` under `data/state.json`; stamp `updated_at` via `_utc_now_iso`.
- `src/frost_alert/adapters/system_clock.py` -- new: `SystemClock.now()` UTC-aware. `adapters/__init__.py` stays empty.
- `src/frost_alert/check_tick.py` -- new composer: monitoring fetch/`classify`/`maybe_send_frost_alert` then always `apply_telegram_acks`; return season fields. No StateStore.
- `src/frost_alert/entrypoints/check.py` -- new: env secrets, wire adapters, load, composer, `StateStore.write`.
- `src/frost_alert/entrypoints/cli.py` -- new dispatcher `setup` → `setup.main`, `check` → `check.main`. Leave `setup.py` argv/`USAGE` as-is.
- `pyproject.toml` -- `[project.scripts]` currently `frost_alert.entrypoints.setup:main` (L9–10). Point at `cli:main`.
- Reuse, do not edit: `domain/classify.py`, `send_frost_alert.py`, `apply_season.py`, `open_meteo_forecast.py`, `telegram_notifier.py`, `telegram_ack_inbox.py`.
- `tests/test_package.py` -- entry point assert L213; Fake* stay constructible. `tests/test_setup_scale_threshold.py` -- `setup.main(["check"])` still usage. `tests/test_state_store.py` -- keep load-does-not-create; add write coverage here or in check tests.

## Tasks & Acceptance

**Execution:**
- [x] `tests/test_check_tick.py` -- failing tests for every I/O matrix row -- red first
- [x] `src/frost_alert/ports/__init__.py` -- `load` / `write` / `Clock.now` -- AD-1, AD-3, AD-5
- [x] `src/frost_alert/adapters/json_config_store.py` -- `load` -- AD-3
- [x] `src/frost_alert/adapters/json_state_store.py` -- `write` -- AD-3, AD-13
- [x] `src/frost_alert/adapters/system_clock.py` -- `now` UTC -- AD-5
- [x] `src/frost_alert/check_tick.py` -- tick order, new-event reset, notifier continue -- AD-13, AD-8
- [x] `src/frost_alert/entrypoints/check.py` -- env secrets, load, write -- NFR3, AD-3
- [x] `src/frost_alert/entrypoints/cli.py` + `pyproject.toml` -- `frost-alert check` -- CAP-2 local slice

**Acceptance Criteria:**
- Given valid `user.json` and StateStore defaults, when `frost-alert check` runs while monitoring, then it fetches, classifies, sends only an unmarked window, polls Telegram, and writes `data/state.json`.
- Given absent risk or `suspended`, when the check runs, then no frost alert is sent; suspended still polls and writes.
- Given `uv run pytest`, when tests finish, then all pass, including every matrix row; setup still cannot flip season; no test opens a socket.

## Implementation Notes

`frost-alert` now dispatches `setup` and `check`. The check entrypoint reads `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`, loads config+state, runs `run_check_tick`, then `StateStore.write`. Composer resets windows on a new `event_date`, catches notifier failures so poll+write still happen (exit 0), and lets forecast/poll errors abort before write. `uv run pytest` — 163 passed; sockets blocked.

## Spec Change Log

## Review Triage Log

- `false` — Blind: `.gitignore` omits `data/state.json`. AD-3 / structural seed: workflow commits that file in Epic 3. Spec Never is this story's commit hygiene, not a forever-ignore.
- `low` — Blind: check prints nothing. Frozen Always does not require stdout copy; proof is Telegram plus `data/state.json`. Reject (a log protocol is more than a deletion).
- `false` — Blind: `except Exception` around send. Frozen Always is notifier raise → do not mark, still poll+write, exit 0. Tests raise `RuntimeError` from the notifier.
- `medium` — Blind/Edge: `check.py:33-38` only catches `FileNotFoundError` on config load; `persist.load()` is unguarded. Corrupt `user.json` / `state.json` or `OSError` crash instead of fail-closed exit 1. Disposition: patch.
- `low` — Blind: `load` does not schema-check seven keys; `write_text` is non-atomic. Extra keys still classify; missing keys `KeyError` loudly. Reject (schema/atomic replace add surface the matrix never showed).
- `false` — Blind: `check_tick.py` outside `{domain,ports,adapters,entrypoints}`. Same package-root composer as `send_frost_alert.py` / `apply_season.py`. Code Map names that path.
- `false` — Blind: sprint-status `in-progress` vs spec `in-review`. Step-04 sets spec `in-review`; sprint `review` sync is a later step.
- `medium` — Blind: production CLI/`sys.argv`/USAGE untested. Same gaps as verification-gap rows below. Disposition: patch.
- `false` — Blind: missing-config/secrets tests inject fakes so they miss real Telegram construction. Secrets and missing-file returns are before `TelegramNotifier` / `TelegramAckInbox` (`check.py:26-36` then 39–47). Same-tick send-then-`/in` is Design Notes next-tick. Classify raise shares `check.main`'s composer `except`.
- `false` — Blind: Clock vs `_utc_now_iso` for `updated_at`. Frozen Always: Clock is classify `now`; write stamps `updated_at`. `test_state_store.py` already asserts the stamp on `write`.
- `medium` — Edge: `user.json` exists but is not valid JSON (`check.py:33-36`). `JSONDecodeError` bypasses fail-closed. Disposition: patch.
- `medium` — Edge: existing `state.json` invalid/unreadable (`check.py:38`). Uncaught abort before poll/write. Disposition: patch.
- `low` — Edge: `StateStore.write` after a successful poll raises. Spec already leaves poll-raise unpersisted; disk-full is not everyday. Reject (extra `except` around write).
- `medium` — Edge: whitespace-only `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` (`check.py:26-29`). `if not token` is true for `"   "`; adapters constructed with blanks. Disposition: patch.
- `medium` — Verification-gap: `cli.main()` with `argv is None` never runs; dropping `[1:]` still passes explicit-argv tests. Disposition: patch.
- `medium` — Verification-gap: `cli_main([])` / unknown argv never assert `Usage: frost-alert setup|check`. Disposition: patch.
- `medium` — Verification-gap: `check.main` defaults to cwd `JsonConfigStore`/`JsonStateStore` but every test injects stores. Disposition: patch.
- `medium` — Verification-gap: monitoring send never asserts notifier kwargs from `user.json`. Disposition: patch.
- `medium` — Verification-gap: missing-secrets test clears both env vars; `if not token or not chat_id` can degrade to `and`. Disposition: patch.

## Design Notes

AD-13 local slice stops before git and watchdog. Notifier failure still completes poll+write (AD-6 still-ping analogue, exit 0). Forecast or poll failure does not persist (one write after a completed poll). New-event reset lives in the composer so yesterday's `[24,12,6]` cannot suppress today's 24h.

Golden: monitoring, empty windows, clock `2026-01-15T12:00:00Z`, first hour `2026-01-16T06:00:00Z` @ 2°C, threshold 3°C, `Europe/Stockholm` → send 24, write `event_date=2026-01-16`, `alerted_windows=[24]`. Then `/in` on the next tick → `suspended`, same event/windows.

## Verification

**Commands:**
- `uv run pytest` -- expected: all tests pass including every matrix row; `test_package.py` isolation green; setup does not write `data/state.json`; no sockets
