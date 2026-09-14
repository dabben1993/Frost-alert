---
title: 'Persist state and ping the watchdog'
type: 'feature'
created: '2026-09-14'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '1a14b0bf0c9fea0f9e49d22819499278d28ed4ca'
context:
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A successful `frost-alert check` writes `data/state.json` only on the runner. The next checkout loses season, windows, and offset, and healthchecks.io never hears that the job ran.

**Approach:** After StateStore writes, Watchdog pings `HEALTHCHECKS_PING_URL` from `frost-alert check`. The workflow then commits `data/state.json`. Dual-API miss or crash: no ping, exit non-zero. Telegram send failure: window unmarked, still ping.

## Boundaries & Constraints

**Always:**
- Stay on branch `3-3-persist-state-and-ping-the-watchdog`. No story work on `master`.
- Order: write `data/state.json` → Watchdog ping inside `frost-alert check` → workflow git commit of that file only. YAML must not `curl` the ping URL. Commit message is `chore: persist frost-alert state` (no `[skip ci]`). A failed `git push` can look healthy on healthchecks.io; Actions failure email still fires.
- Ping after a monitoring tick that obtained a series and finished classify. Dual-API miss or crash before classify finishes: no ping, exit 1 (FR17). Notifier failure: do not mark the window; still ping (AD-6).
- `Watchdog.ping()` on the empty port. Adapter reads `HEALTHCHECKS_PING_URL`. Blank or missing URL: skip ping, still write, exit 0. Ping HTTP failure after a successful tick: still exit 0. Stdlib HTTP GET, 15s, identifying User-Agent. Tests fake `urlopen`; no sockets.
- Present `data/state.json` must have AD-3 keys/types. Invalid present file: exit 1, no write, no ping. Missing file still defaults.
- Do not hardcode period 6h or grace ~6h (AD-10). Miss copy and operator README are 3.5; healthchecks.io sends the miss warning.
- Commit with `GITHUB_TOKEN` as `github-actions[bot]`. Never commit secrets, `.env`, or `config/user.json`.

**Never:**
- Do not do operator README, MET/forecast edits, or Story 3.4 suspended ACs (`/out` on suspended). Suspended already polls+writes.
- Do not change `classify.py`, Telegram, setup, `check_tick.py`, or `user.json` keys.
- Do not add `requests`/`httpx`, use cache/artifacts as the store, or treat a watchdog miss as a frost alert.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Monitoring persist | series obtained, classify done | write `data/state.json`; Watchdog GET-pings `HEALTHCHECKS_PING_URL`; workflow then commits the file | N/A |
| Dual-API miss | monitoring; forecast raises | no write, no commit, no ping, exit 1 | existing `except` |
| Crash before classify | fetch/classify exception | no ping, exit 1 | same |
| Notifier fail | classify ok; send raises | window unmarked; write; ping | swallowed send |
| Invalid present state | on-disk file missing keys / bad types | exit 1; no write; no ping | fail closed |
| Workflow YAML | after successful check | `git add`/`commit`/`push` only `data/state.json` with message `chore: persist frost-alert state`; no ping-URL `curl` | skipped if check failed |

</frozen-after-approval>

## Code Map

- `src/frost_alert/ports/__init__.py` -- `Watchdog` is `pass` (L27–28). Add `ping(self) -> None`.
- `src/frost_alert/entrypoints/check.py` -- Telegram env L29–32; load L36–40; tick L58–66; `except: return 1` L67–68 (no write). Write L73–78. Wire injectable `watchdog=`; default from env URL.
- `src/frost_alert/check_tick.py` -- no I/O. Reuse; do not edit.
- `src/frost_alert/adapters/json_state_store.py` -- present-file `load` L12–22 is raw JSON. Validate AD-3 keys. `write` already stamps `updated_at`.
- `src/frost_alert/adapters/http.py` -- `get_json` only; do not JSON-parse the ping. Adapter-local `urlopen` or a GET-status helper.
- `src/frost_alert/adapters/healthchecks_watchdog.py` -- **new.** `HealthchecksWatchdog(url)` + `ping()`. `adapters/__init__.py` stays empty.
- `.github/workflows/check.yml` -- check last (L26); `contents: write` L5–6; ping URL in env L16. Add commit+push of `data/state.json`. No curl.
- `tests/test_check_tick.py` -- `_run_check` L160–199 has no Watchdog. Add ping/no-ping rows. Keep `test_matrix_forecast_raise_no_write` (L380). Notifier-fail row must ping.
- `tests/test_check_workflow.py` -- L201–207 forbids commit/push; flip to require commit of `data/state.json` and no curl.
- `tests/test_state_store.py` -- missing-file defaults L30–48. Add present-file invalid rows.
- `tests/test_package.py` -- `FakeWatchdog` L68–69 must grow `ping`.
- `src/frost_alert/entrypoints/cli.py` -- `setup|check` only. No ping command.
- Reuse, do not edit: domain, forecast adapters, Telegram, setup, `send_frost_alert.py`, `apply_season.py`.

## Tasks & Acceptance

**Execution:**
- [x] `tests/test_state_store.py` -- present-file invalid rows -- red first -- FR22
- [x] `src/frost_alert/adapters/json_state_store.py` -- validate present AD-3 keys -- epic-2 retro
- [x] `tests/test_healthchecks_watchdog.py` -- GET ping URL, UA, 15s; fake `urlopen` -- red first -- FR17
- [x] `src/frost_alert/adapters/healthchecks_watchdog.py` -- Watchdog adapter -- CAP-7, AD-6
- [x] `tests/test_check_tick.py` -- ping after write; no ping on dual-miss/crash/bad state; ping on notifier fail -- FR17
- [x] `src/frost_alert/entrypoints/check.py` -- wire Watchdog after write -- FR17, AD-13
- [x] `tests/test_check_workflow.py` -- commit/push `data/state.json` after check; no curl -- FR19
- [x] `.github/workflows/check.yml` -- git commit+push that file -- FR19, AD-3

**Acceptance Criteria:**
- Given a monitoring tick that obtained a forecast and finished classification, when persist runs, then StateStore writes `data/state.json`, Watchdog pings `HEALTHCHECKS_PING_URL` from that same check process, and the workflow then commits the file with `contents: write` (FR19, AD-13 order traded: ping-in-check so unit tests own ping-vs-no-ping).
- Given dual-API miss or a crash before classification finishes, when the tick ends, then it does not ping and exit is non-zero (FR17).
- Given classification succeeded but Telegram send failed, when the tick ends, then the window is not marked and the watchdog still pings (FR17, AD-6).
- Given the check does not report in within the documented 6h period plus ~6h grace, when healthchecks.io notices, then the owner gets a separate warning that is not a frost alert; period and grace are not hardcoded (FR18, AD-10).
- Given `uv run pytest`, when tests finish, then all pass, including every matrix row; no test opens a socket.

## Implementation Notes

`JsonStateStore.load` validates present AD-3 keys (`set` equality). `HealthchecksWatchdog.ping` GET+UA+15s; blank URL no-ops. `check.py` writes then `try/except` ping (exit 0). Default watchdog from env; tests inject `RecordingWatchdog`. `check.yml` commit+push after check; no curl. `uv run pytest` — 241 passed.

## Spec Change Log

## Review Triage Log

- `false` — Blind: ping-before-commit vs AD-13. Frozen Always records write → ping-in-check → YAML commit; lost-push looks healthy on healthchecks.io with Actions email as backstop.
- `false` — Blind: unguarded `git commit` if nothing staged. Successful check always stamps a new `updated_at`, so `git add data/state.json` has a diff; failed check skips the step.
- `low` — Blind: ping skip/failure silent vs stdout logs. Frozen does not require ping logs; a log protocol is more than a deletion. Reject.
- `false` — Blind: extra 2.5 rows omit ping asserts. Spec matrix rows that require ping/no-ping already assert; other rows are not this story’s I/O matrix.
- `false` — Blind: missing `HEALTHCHECKS_PING_URL` untested. `os.environ.get(..., "")` is the same path as blank; `HealthchecksWatchdog` no-ops on empty strip.
- `low` — Blind: `test_ping_does_not_parse_response_as_json` asserts nothing. Cosmetic. Reject.
- `low` — Blind: parametrize omits some missing keys; `write` skips `_validated`. `check.py` write always emits AD-3 keys; extra schema on write is new surface. Reject.
- `false` — Blind: workflow test allows `git add .` beside the path. YAML only `git add data/state.json`.
- `false` — Blind: FR18 period/grace undocumented. Frozen Always assigns miss copy and operator README to 3.5.
- `false` — Blind: default-wiring test omits GET/UA. `tests/test_healthchecks_watchdog.py` asserts GET, UA, 15s; entrypoint test covers env URL.
- `low` — Blind: Design Notes say FakeWatchdog; suite uses RecordingWatchdog. Naming only. Reject.
- `low` — Blind: ping shares `TIMEOUT_S` with forecast. Both are specified 15s. Reject.
- `false` — Blind: `ValueError` catch also wraps config load. Config is still raw `json.loads`; the new `ValueError` is present-state validation.
- `false` — Edge: list/object `season` TypeError. `payload["season"] not in _SEASONS` is True for a list; raises `ValueError`, caught by `check.py`.
- `low` — Edge: `date.fromisoformat` accepts `YYYYMMDD` and ISO week dates, not only `YYYY-MM-DD`. Disposition: patch.
- `low` — Edge: negative `telegram_offset`. Extra bound, undemonstrated input. Reject.
- `low` — Edge: `event_date` null with nonempty windows. Extra invariant, undemonstrated. Reject.
- `low` — Edge: non-http ping URL scheme. Secret is an https ping URL; transport failure already exits 0. Reject.
- `low` — Edge: unbounded `response.read()`. healthchecks.io body is `OK`. Reject.
- `false` — Edge: job cancelled after ping before `git push`. Same accepted ping-then-commit trade as Blind row 1.
## Design Notes

Success ping is GET of the UUID URL (no JSON). Adapter owns HTTP; YAML owns `git add data/state.json` then commit/push with `chore: persist frost-alert state`. `updated_at` changes every write, so each successful tick diffs (schedule activity, no dummy keep-alive file). Invalid present state fails closed like corrupt JSON. Golden notifier-fail: send raises, `alerted_windows` stays `[]`, FakeWatchdog `ping` called once. Blank ping URL skips ping. Ping transport errors do not change exit 0.

## Verification

**Commands:**
- `uv run pytest` -- expected: all pass including present-state, watchdog GET, ping/no-ping matrix, workflow commit-without-curl; isolation green; no sockets
