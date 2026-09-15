---
title: 'Keep the job healthy while the season is suspended'
type: 'feature'
created: '2026-09-15'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'd43f3ccd7ad1b43fd43630ea0e2c6a73d23bbd24'
context:
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A suspended season must keep the scheduled job visible (Telegram `/out`, state commit, watchdog ping) without frost alerts. Live Actions currently dies at `astral-sh/setup-uv@v10` — that tag does not exist.

**Approach:** Lock the existing suspended tick (skip forecast, still poll/write/commit/ping; `/out` resumes and clears) and pin `setup-uv` to a resolvable immutable tag so the job can actually start.

## Boundaries & Constraints

**Always:**
- Stay on branch `3-4-keep-the-job-healthy-while-the-season-is-suspended`. No story work on `master`.
- Suspended tick: skip forecast; send no frost alert even if a risk series is injected; still poll Telegram, write `data/state.json`, ping Watchdog, exit 0. Workflow still commits that file after check (FR20).
- `/out` / `plants_out` on a suspended tick: `monitoring`, `event_date=None`, `alerted_windows=[]`. The following tick can send the same local day (FR12, FR20).
- Pin `.github/workflows/check.yml` to `astral-sh/setup-uv@v10.0.1` with uv `0.12`. Keep `checkout@v7`, `setup-python@v7` Python `3.13`, commit step, secrets env. Do not retarget `@v10` (major/minor tags were dropped at setup-uv v8).
- Unit tests fake ports; no sockets. Do not weaken FR17: monitoring dual-API miss / crash still no ping, exit 1.

**Never:**
- Do not write operator README (3.5), a dummy keep-alive file, or a second workflow.
- Do not change `classify.py`, forecast adapters, Telegram send, setup, `HealthchecksWatchdog` internals, or `user.json` keys.
- Do not require a forecast on suspended ticks (that would block FR20 ping). Do not add `requests`/`httpx`. Do not treat a watchdog miss as a frost alert.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Idle suspended | `season=suspended`; empty inbox; risk series available | no fetch; no send; poll; write stays suspended (event/windows kept); ping 1; exit 0 | N/A |
| Suspended + `/out` | suspended with event+windows; inbox `out` | no fetch; no send; write `monitoring` + cleared event/windows; ping 1; exit 0 | N/A |
| Same-day resume | tick 1: that `/out`; tick 2: stored monitoring + same-day risk | tick 2 fetches and can send window 24 | N/A |
| Workflow uv pin | `check.yml` | `uses: astral-sh/setup-uv@v10.0.1` with `version: "0.12"`; commit of `data/state.json` still after check; no curl | N/A |

</frozen-after-approval>

## Code Map

- `src/frost_alert/check_tick.py` -- `run_check_tick` L25–51 is `if season == "monitoring"` only. Suspended skips fetch/send. L53–59 always `apply_telegram_acks`. Reuse; edit only if a new FR20 test fails.
- `src/frost_alert/domain/season.py` -- `apply_intent` L15–16: `out` → `("monitoring", None, [])`. No suspended special case. Reuse.
- `src/frost_alert/apply_season.py` -- `apply_telegram_acks` L17–24 last-wins. Reuse.
- `src/frost_alert/entrypoints/check.py` -- write L89–94 then `dog.ping()` L100–103; no season gate. Reuse; edit only if idle-suspended ping is missing.
- `.github/workflows/check.yml` -- L22 is `astral-sh/setup-uv@v10` (unresolvable). Change to `@v10.0.1`. Keep L27–32 commit. Do not add curl.
- `tests/test_check_tick.py` -- `_run_check` already injects `RecordingWatchdog` (L186–213) but `test_matrix_suspended_polls_and_writes` (L321–347) never asserts `pings`. Add idle-suspended ping, ping on the `/out` row, and a two-tick same-day send. Keep FR17 no-ping rows.
- `tests/test_check_workflow.py` -- L184 asserts `astral-sh/setup-uv@v10`. Flip to `@v10.0.1`. `_uses_with` (L116) keys the full `uses` string. Leave commit/secrets tests.
- Reuse, do not edit: forecast adapters, Telegram notifier, `healthchecks_watchdog.py`, `json_state_store.py`, setup, `send_frost_alert.py`.

## Tasks & Acceptance

**Execution:**
- [x] `tests/test_check_tick.py` -- idle suspended ping; `/out` row ping; two-tick same-day send -- FR20 (lock-in; touch src only if red)
- [x] `tests/test_check_workflow.py` -- require `astral-sh/setup-uv@v10.0.1` + uv `0.12` -- red first
- [x] `.github/workflows/check.yml` -- pin `@v10.0.1`; leave runner, secrets, commit -- Actions resolve failure

**Acceptance Criteria:**
- Given `season` is `suspended`, when a tick runs, then it skips the forecast, sends no frost alert, still polls Telegram, writes state, pings the watchdog, and the workflow still commits `data/state.json` (FR20).
- Given `/out` arrives on a suspended tick, when poll applies it, then state is `monitoring` with cleared `event_date` and `alerted_windows`, and the following tick can alert the same local day (FR12, FR20).
- Given `.github/workflows/check.yml`, when Actions resolves `uses`, then `astral-sh/setup-uv@v10.0.1` with uv `0.12` is the pin (not `@v10`).
- Given `uv run pytest`, when tests finish, then all pass, including every matrix row; no test opens a socket.

## Implementation Notes

No `src/` edits. `test_matrix_idle_suspended_skips_forecast_and_pings`, ping assert on `/out` row, `test_suspended_out_then_same_day_can_send`. `check.yml` + workflow test pin `astral-sh/setup-uv@v10.0.1` uv `0.12`. `uv run pytest` — 245 passed.

## Spec Change Log

## Review Triage Log

- `false` — Blind: sprint `in-progress` vs spec `in-review`. Step-04 sets spec `in-review`; sprint `review` is the later tracker sync. Not a product defect.
- `false` — Blind: empty Spec Change Log / AD-6 vs FR20. Log is empty until a bad_spec loopback. Frozen Always and epic-3-context already require suspended ping without fetch. Spec-edit reject.
- `false` — Blind: tests inject `out` not `plants_out`. `FakeAckInbox` takes domain intents; `TelegramAckInbox` already maps `plants_out`→`out` (`test_out_or_plants_out_resumes_and_clears`). Same `apply_intent` path.
- `false` — Blind: all Error Handling N/A; missing poll/ping/FR17 rows. FR17 no-ping rows remain (`test_matrix_forecast_raise_no_write`). Ping skip/fail is 3.3. Poll-raise is existing `check.py` except. Spec-edit reject for matrix cells.
- `false` — Blind: two-tick test throwaway watchdogs, no ping/offset asserts. Same-day resume matrix is fetch+send window 24; tick-1 ping is `test_matrix_suspended_polls_and_writes`; unused kwargs are not a failing path.
- `false` — Blind: workflow test does not forbid leftover `@v10`. YAML has one `setup-uv` uses; `@v10.0.1` key fails if the pin is still `@v10`. Dual-uses undemonstrated.
- `false` — Blind: SHA pin vs tag. Frozen Always pins `@v10.0.1`. SHA is a different pin the intent did not ask for.
- `false` — Blind: suspended-tick YAML commit not locked. Commit step is season-agnostic after check; `test_contents_write_commits_state_without_curl` already locks add/commit/push of `data/state.json`.
- `false` — Blind: `context` omits epics/3.1/3.3/spine. Template: keep short; AGENTS.md is the listed load. Spec-edit reject.
- `false` — Blind: Code Map line numbers stale after idle-test insert. Navigation only; no runtime miss. Spec-edit reject.
- `false` — Blind: Verification omits node ids. `uv run pytest` collected 245 including the new rows. Spec-edit reject.

## Design Notes

`setup-uv` v8+ publishes only immutable `vMAJOR.MINOR.PATCH` tags. `@v10` / `@v10.0` 404. Pin `@v10.0.1`; keep uv `0.12`.

Idle-suspended golden: `FakeForecast(series=[risk])`, empty inbox, `RecordingWatchdog` → `forecast.calls==[]`, `notifier.calls==[]`, `watchdog.pings==1`, `season` still `suspended`.

Two-tick golden: tick 1 suspended + inbox `out` writes monitoring/cleared; tick 2 same `tmp_path` with risk hour → one send, window 24.

## Verification

**Commands:**
- `uv run pytest` -- expected: all pass including idle-suspended ping, `/out` ping, two-tick send, workflow `@v10.0.1`; isolation green; no sockets
