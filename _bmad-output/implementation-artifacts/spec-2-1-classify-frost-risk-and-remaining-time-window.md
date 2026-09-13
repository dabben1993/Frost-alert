---
title: 'Classify frost risk and remaining-time window'
type: 'feature'
created: '2026-09-13'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'b0022275c33b1e590dd9e557e1c7d99374f0b7bc'
context:
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Checks have a stored threshold and place but no domain rule that finds the first upcoming forecast hour at or below it, so later ticks cannot pick the 24h, 12h, or 6h warning without inventing classification.

**Approach:** Add a pure domain function: hourly series + `threshold_c` + `now` + IANA timezone → frost risk, remaining-time window, and frost-event date. No I/O.

## Boundaries & Constraints

**Always:**
- Stay on branch `2-1-classify-frost-risk-and-remaining-time-window`. No story work on `master`.
- Risk is present when any forecast hour with `0 < remaining ≤ 30h` has `temp_c ≤ threshold_c`; otherwise absent. Remaining is `first_at_or_below − now`. At-threshold counts. Daytime hours count.
- Window map (hours): remaining > 12 → 24; remaining > 6 → 12; remaining > 0 → 6. Absent risk: window and `event_date` are `None`.
- Frost event identity is the local calendar date (`YYYY-MM-DD`) of that first qualifying hour in the given IANA zone. Same local date → same event id.
- Series is an ascending list of UTC-aware `{t, temp_c}`. Domain uses the earliest qualifying `t` (order-independent). `now` is a timezone-aware datetime argument — do not call `Clock`.
- Unit tests construct series in memory; no live network, no ForecastSource.

**Never:**
- Do not read live current temperature. Do not ignore daytime crossings. Do not restrict to a night window.
- Do not implement Open-Meteo forecast, Telegram, season in/out, check entrypoint, `alerted_windows` read/write, or `.github/workflows/check.yml` as a runner.
- Do not add methods on Clock, ForecastSource, Notifier, AckInbox, or Watchdog.
- Do not change setup, geocode, ConfigStore, StateStore, `user.json` keys, or `state.json` keys.
- Do not add `requests`/`httpx`. Do not import adapters or stdlib HTTP from domain.
- Do not commit secrets, `.env`, `config/user.json`, or `data/state.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Present in lookahead | hour at 18h, `temp_c ≤ threshold_c` | risk present, window 24, `event_date` = that hour's local `YYYY-MM-DD`, lead time = that `t − now` | N/A |
| All above | every lookahead hour `temp_c > threshold_c` | absent; window `None`; `event_date` `None` | N/A |
| Empty series | `[]` | same as all-above | N/A |
| Daytime crossing | 14:00 local at/below, inside lookahead | present; not skipped | N/A |
| Window 12 / 6 | remaining exactly 12h / 6h | window 12 / 6 | N/A |
| Lookahead bounds | remaining 30h at/below; remaining > 30h at/below; remaining ≤ 0 at/below | 30h → present window 24; >30h ignored; ≤0 ignored (even if in the series) | N/A |
| At threshold | `temp_c == threshold_c` inside lookahead | present | N/A |
| Same-day revision | first qualifying hour moves, same local date | same `event_date` | N/A |
| New local date | `now` after the prior event's local date; new qualifying hour | new `event_date` | N/A |
| Two dates in lookahead | Monday evening above, Tuesday 02:00 at/below | `event_date` is Tuesday (first qualifying hour), not Monday | N/A |

</frozen-after-approval>

## Code Map

- `src/frost_alert/domain/` -- only `scale_threshold.py` today (`ScaleAndThreshold`, setup conversion). Add `classify.py`; do not fold classify into setup types.
- `src/frost_alert/domain/__init__.py` -- empty; leave empty (callers import `frost_alert.domain.classify`).
- `src/frost_alert/ports/__init__.py` -- `Clock` is an empty Protocol (L38–39). Leave it empty; classify takes `now`, not the port.
- `src/frost_alert/adapters/` -- JSON stores + Open-Meteo geocoder only. Do not add a forecast adapter.
- `src/frost_alert/entrypoints/setup.py` -- do not touch.
- `tests/test_package.py` -- domain isolation walks all `domain/**/*.py` (L172–180); new classify module must stay free of adapters/HTTP. Keep FakeClock empty.
- `tests/test_setup_scale_threshold.py`, `tests/test_setup_location.py`, `tests/test_state_store.py` -- do not change.
- `_bmad-output/implementation-artifacts/epic-2-context.md` -- 2.1 is domain-only: series + threshold + clock in, risk/window/event out.

## Tasks & Acceptance

**Execution:**
- [x] `tests/test_classify.py` -- failing tests for every I/O matrix row -- red first
- [x] `src/frost_alert/domain/classify.py` -- `ForecastHour`, `Classification`, `classify` -- FR5–FR8, AD-5/7/8

**Acceptance Criteria:**
- Given an in-memory hourly series and `threshold_c`, when `classify` runs, then it uses only forecast hours and `now` — no live-temperature argument, no night-only filter.
- Given existing setup, geocode, ConfigStore, StateStore, and empty Clock, when this story lands, then those modules are unchanged.
- Given `uv run pytest`, when tests finish, then all pass and no test opens a socket.

## Implementation Notes

`classify(series, threshold_c, now, timezone)` returns `Classification(risk_present, window, event_date, t, temp_c)`. Earliest qualifying `t` wins. `tzdata` added so `ZoneInfo("Europe/Stockholm")` works on Windows. Review patch: `test_matrix_event_date_is_iana_local_not_utc_date` (23:00 UTC → local next date). `uv run pytest` — 71 passed; sockets blocked; setup/geocode/stores/Clock unchanged.

## Spec Change Log

## Review Triage Log

- `medium` — Blind: no test where UTC calendar date ≠ local `event_date`; every fixture is January `Europe/Stockholm` with matching Y-M-D. Same claim as verification-gap. `classify.py:60` uses `ZoneInfo`; tests would still pass if replaced with `t.date()`. Disposition: patch.
- `false` — Blind: no 24→12→6 remap with a fixed crossing as `now` advances. Window mapping is already tested at remaining 18/12/6/30; remaining is always `t − now`, so a clock-advance case is the same branch.
- `false` — Blind: `remaining ≤ 0` not mixed with a later at-or-below hour. `test_matrix_remaining_zero_or_past_ignored` would be present if those hours counted; that is the live-thermometer trap. The 30h-at-5°C companion matches the Design Notes golden.
- `false` — Blind: lone 31h hour does not mix with in-range hours. Remaining > 30h is later than in-range hours; the lone 31h case already fails if the 30h cap is dropped.
- `false` — Blind: no naive/`now` tz-mix/invalid-zone tests. Spec series and `now` are UTC-aware; 2.2 constructs them. Naive subtract raises; bad `ZoneInfo` raises. Loud fail on input this story does not produce.
- `false` — Blind/Edge: `NaN > threshold_c` is false so NaN counts as frost. Forecast hours are adapter-owned; the matrix has no non-finite row. `isfinite` would be a new guard for undemonstrated input.
- `false` — Blind: `tzdata` unrecorded / empty Spec Change Log / `stack.md`. Implementation Notes already record `tzdata` for Windows `ZoneInfo`. Spec Change Log is for review loopbacks. `stack.md` is a planning artifact this story must not edit.
- `low` — Blind: `classify.py` has no docstring. Contract lives in the spec; later stories load that, not a module docstring. Reject: everyday callers are 2.2/2.5 from the spec; adding a docstring is noise, not a user-facing defect.
- `false` — Blind: some present-risk tests omit extra `Classification` fields. Each matrix row’s required output is asserted; unused fields on those rows are not a wrong result.
- `false` — Blind: epic-2 context still says “clock in, risk/window/event out.” That file is orientation; the frozen spec and `classify` signature are the contract 2.3 will copy.
- `false` — Edge: naive or mixed-tz `hour.t`/`now` at `classify.py:38-60`. `datetime` subtraction of naive vs aware raises `TypeError`. Not reachable from in-memory UTC fixtures or the 2.2 series contract.
- `false` — Edge: invalid IANA `timezone` at `classify.py:60`. Setup writes a geocoder IANA name; `ZoneInfoNotFoundError` is a loud fail on a bad config, not a silent wrong `event_date`.
- `false` — Edge: `series is None` at `classify.py:37`. Spec empty case is `[]`; iteration of `None` raises. Adapter will pass a list.
- `medium` — Verification-gap: `event_date` IANA conversion unobserved. All `event_date` asserts equal `t.date()` on UTC+1 January fixtures; `uv run pytest tests/test_classify.py` would still pass if line 60 used `first.t.date()`. Disposition: patch — named test where UTC date ≠ `Europe/Stockholm` date.
## Design Notes

Window edges follow the spec's strict `>`: remaining `== 12` is window 12, `== 6` is window 6, `== 30` is inside lookahead and window 24. Past and current hours (`remaining ≤ 0`) are skipped so a series that still contains "now" is not treated as a live thermometer.

`event_date` is `first_at_or_below.astimezone(ZoneInfo(timezone)).date().isoformat()`. Classify does not see `alerted_windows`; same-day identity is that string staying equal. Story 2.5 applies it to state.

Return the first qualifying hour's `t` and `temp_c` on `Classification` so 2.3 does not re-derive the crossing. Absent: those fields `None`.

Golden: `now` 2026-01-15 12:00 UTC, zone `Europe/Stockholm`, `threshold_c` 3. Hour 2026-01-16 06:00 UTC at 2°C → remaining 18h → window 24, `event_date` `2026-01-16`. Hour 2026-01-15 12:00 UTC at 0°C (remaining 0) plus 2026-01-16 18:00 UTC at 5°C → absent.

## Verification

**Commands:**
- `uv run pytest` -- expected: all tests pass, including every classify matrix row; `test_package.py` isolation still green; no test opens a socket
