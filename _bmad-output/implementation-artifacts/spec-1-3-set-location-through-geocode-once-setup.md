---
title: 'Set location through geocode-once setup'
type: 'feature'
created: '2026-09-13'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'e3b29ee6f382e65569f5c7f0b0d5c2dc5f4e7007'
context:
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Setup writes only `scale` and `threshold_c`. Checks still have no cached place, so later stories cannot forecast without editing source or geocoding on every tick.

**Approach:** Extend `frost-alert setup` to geocode city, postal code, or optional coordinates through Open-Meteo, show one resolved place, and on confirm write the full seven-key `config/user.json`. Implement StateStore load defaults for a missing `data/state.json`.

## Boundaries & Constraints

**Always:**
- Branch `1-3-set-location-through-geocode-once-setup` from current `master`. No story work on `master`.
- Prompt order: existing scale, then threshold, then one location prompt, then confirm the single shown place. No flags for location.
- Confirm is `Y/n`: empty Enter, `y`, or `Y` means yes; `n` or `N` means reject.
- Location text (city, postal code, or optional coordinates) is sent unchanged to Open-Meteo `name=` like any other query. Do not parse lat/lon.
- Open-Meteo Geocoding only: `GET https://geocoding-api.open-meteo.com/v1/search`. Stdlib HTTP. Identifying User-Agent `Frost-alert (https://github.com/dabben1993/Frost-alert)`. Do not pin `countryCode` or `models=`.
- Show the first result as `name`, `admin1`, `country` (omit missing fields). `place_name`, `lat`, `lon`, `elevation_m`, `timezone` come from that result — never guessed, never from typed coordinates.
- One ConfigStore write after confirm, exactly the seven keys. Re-run overwrites the file. Invalid scale/threshold, no match, reject, or geocoder failure: no write; existing file unchanged; exit non-zero; explain.
- Geocoder is injected into `main` like ConfigStore. It is not an eighth name in `ports/__init__.py`. Domain still has no I/O.
- StateStore `load` returns defaults when `data/state.json` is missing: `season` `monitoring`, `event_date` `null`, `alerted_windows` `[]`, `telegram_offset` `0`, `updated_at` UTC ISO-8601. Those are the only state keys. Setup does not write state. Only StateStore writes state; only the check entrypoint will call a writer later.
- Unit tests fake the geocoder and stores; no live network. Keep `tests/test_package.py` isolation and banned-dep checks.

**Never:**
- Do not implement classification, Telegram, forecast/failover, check entrypoint, or `.github/workflows/check.yml` as a runner.
- Do not add `requests`, `httpx`, Nominatim, or a web framework.
- Do not geocode on a scheduled-check path. Do not add methods on ForecastSource, Notifier, AckInbox, Watchdog, or Clock.
- Do not commit secrets, `.env`, `config/user.json`, or `data/state.json`.
- Do not change `_bmad/`, `.agents/`, planning artifacts, or `scripts/poc-telegram-getupdates.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| City confirm | location `Berlin`; confirm yes | `user.json` has seven keys; location fields from geocoder result | N/A |
| Postal confirm | postal code that geocoder matches; confirm yes | same seven-key document from that result | N/A |
| Coordinates | typed `lat,lon` (or any other text) | sent to `name=` unchanged; on hit, location keys from that result | no-match if GeoNames has no such name |
| Confirm default | empty confirm after a hit | treated as yes; seven-key write | N/A |
| No match | empty results or empty location | no write; existing file unchanged | explain no match; exit ≠ 0 |
| Reject | geocoder returns a place; user rejects | no write; existing file unchanged | exit ≠ 0 |
| Geocoder failure | HTTP error / malformed JSON | same as no match | no guessed location |
| Bad scale/threshold | invalid scale or threshold | no geocode call; no write | keep 1.2 messages |
| Re-run | existing seven-key file; new confirmed place | file replaced with new seven keys | N/A |
| Missing state | `data/state.json` absent | `load` returns the five default keys only; no file created | N/A |

</frozen-after-approval>

## Code Map

- `src/frost_alert/entrypoints/setup.py` -- `main(argv=None, *, config_store=None)` prompts scale then threshold and writes two keys (L13–34). Add location + confirm; inject geocoder; write once after confirm.
- `src/frost_alert/ports/__init__.py` -- `ConfigStore.write_scale_and_threshold` (L20–21); `StateStore` empty (L24–25). Replace the write with a seven-key method; add `load` on StateStore. Do not add a Geocoder port name.
- `src/frost_alert/adapters/json_config_store.py` -- full-replace two-key `user.json` (L11–15). Must write all seven keys or a later scale-only write wipes location.
- `src/frost_alert/adapters/` -- no HTTP yet. Add Open-Meteo geocoding adapter (stdlib). Add JSON StateStore reader for missing-file defaults. Do not write `data/state.json` from setup.
- `src/frost_alert/domain/scale_threshold.py` -- reuse `resolve_scale_and_threshold`. No HTTP here.
- `tests/test_setup_scale_threshold.py` -- two `input()` answers; `RecordingConfigStore` two-key writes; adapter asserts exact `{scale, threshold_c}` (L160–166). Update CLI feeds and write assertions or 1.2 tests go red.
- `tests/test_package.py` -- keep fakes constructible; network block; banned deps. New tests in a new module.
- `pyproject.toml` -- `frost-alert` script stays; runtime deps stay empty.

## Tasks & Acceptance

**Execution:**
- [x] `tests/test_setup_location.py` -- failing tests for every I/O matrix row except StateStore (fake geocoder + fake/JSON ConfigStore) -- red first
- [x] `tests/test_state_store.py` -- failing tests for missing `data/state.json` defaults -- red first
- [x] `src/frost_alert/ports/__init__.py` -- seven-key ConfigStore write; StateStore `load` -- AD-1 methods this story needs
- [x] `src/frost_alert/adapters/json_config_store.py` -- write exactly the seven keys -- AD-3 document
- [x] `src/frost_alert/adapters/` -- Open-Meteo geocode adapter (stdlib HTTP, User-Agent, first result) -- FR2
- [x] `src/frost_alert/adapters/` -- JSON StateStore `load` defaults when file missing -- FR22
- [x] `src/frost_alert/entrypoints/setup.py` -- location prompt, show place, confirm, then one write -- geocode-once CLI
- [x] `tests/test_setup_scale_threshold.py` -- extra answers + seven-key writes -- keep 1.2 matrix green

**Acceptance Criteria:**
- Given a confirmed geocode, when setup writes `config/user.json`, then the file contains exactly `place_name`, `lat`, `lon`, `elevation_m`, `timezone`, `threshold_c`, and `scale`, and location fields match the geocoder result.
- Given no match or a rejected place, when setup handles the result, then it does not write a guessed or partial location and leaves an existing file unchanged.
- Given a missing `data/state.json`, when StateStore loads, then it returns the five default keys and does not create the file.

## Implementation Notes

ConfigStore method is `write` (keyword-only seven keys). Geocoder is a local `_Geocoder` protocol on `setup.py`, not a port. Open-Meteo adapter uses stdlib `urlopen`, `count=1`, 15s timeout; missing `elevation`/`timezone` on the first hit is no-match. Location is `.strip()`’d before `name=` so whitespace-only input is empty. Reject prints `Place rejected.` Review patches: default `OpenMeteoGeocoder` wiring test, incomplete first-hit no-match tests, golden `admin1`/`country`/timeout asserts, omit-missing display, whitespace location. `uv run pytest` — 55 passed; sockets blocked. Live `frost-alert setup` not run.

## Spec Change Log

## Review Triage Log

- `medium` — Blind: reject (`n`/`N`) returns 1 with no message. Frozen Always requires explain. `setup.py:56-57` returns without print. Disposition: patch.
- `medium` — Blind: omit-missing `admin1`/`country` display untested. `_shown_place` omits falsy fields; only Berlin-with-all-fields is asserted. Disposition: patch.
- `medium` — Blind: missing `elevation`/`timezone` as no-match untested. `_place_from_payload` KeyError returns None; no incomplete first-hit test. Disposition: patch.
- `medium` — Blind: golden test captures timeout and maps payload but never asserts `timeout == 15` or `admin1`/`country`. Disposition: patch.
- `false` — Blind: `_Geocoder` as `object` so missing attrs traceback. `OpenMeteoGeocoder` returns `GeocodePlace | None`; required fields are set or the result is None. AttributeError is not reachable with this adapter.
- `low` — Blind: empty-string `name`/`timezone` would be written. Open-Meteo omits empty fields (KeyError → None). Everyday GeoNames hits are not `""`. Reject: empty-string guard is a new branch for undemonstrated input.
- `low` — Blind: `JsonStateStore.load` present-file untested. This story’s AC is missing-file defaults; setup does not call StateStore. Reject: present-file validation is new complexity for an unused path.
- `medium` — Blind: whitespace-only location untested. Code `strip()`s then treats `""` as no-match; tests only feed `""`. Disposition: patch.
- `low` — Edge: NaN/Inf lat/lon/elevation. Python `json` may accept NaN; Open-Meteo JSON does not emit it in normal hits. Reject: `isfinite` is a new guard for undemonstrated input.
- `low` — Edge: empty `name`/`timezone` strings. Same as Blind empty-string. Reject.
- `false` — Edge: `http.client.HTTPException` on read escapes the adapter. `setup.py:46-49` `except Exception` sets `place = None` and prints no-match. User-facing outcome does not occur.
- `low` — Edge: corrupt `state.json` makes `load` raise. No caller this story. Reject: try/except is a new branch.
- `low` — Edge: `state.json` JSON that is not an object. Same unused path. Reject.
- `low` — Edge: TOCTOU between `is_file` and read. Single-user; StateStore unused by setup. Reject.
- `low` — Edge: `EOFError` on location/confirm `input()`. Everyday setup is interactive; redirected answers are newlines. Reject: same as 1.2 EOF.
- `false` — Edge: non-None geocode result missing attributes. Same as Blind `_Geocoder` object; production adapter does not return a partial object.
- `medium` — Verification-gap: `main` default `OpenMeteoGeocoder()` never constructed in tests. Every `setup` path injects a fake. Dropping the fallback would break live `frost-alert setup` while pytest stays green. Disposition: patch.
- `medium` — Verification-gap: incomplete first-hit payloads (missing `elevation`/`timezone`) untested. Disposition: patch.
- `medium` — Verification-gap: `OpenMeteoGeocoder` `admin1`/`country` never asserted; CLI display uses fakes. Disposition: patch.
- `medium` — Verification-gap: omit-missing confirm fields untested. Disposition: patch.
- `medium` — Verification-gap: `captured["timeout"]` never asserted. Disposition: patch.
- `medium` — Verification-gap: whitespace-only location not in tests. Disposition: patch.
- `medium` — Verification-gap other: reject has no explanation and tests do not assert stderr. Same as Blind reject. Disposition: patch.

## Design Notes

Open-Meteo returns a `results` array; AC says “a place” — take index 0, `count=1`. Confirmation copy is the geocoder’s `name` plus `admin1` and `country` so a wrong first hit is visible. Collect scale, threshold, location, and confirm, then write once (same reason as 1.2: a failed location must not clobber a complete file with two keys). Empty confirm is yes. Coordinate-looking text is still `name=`, not reverse geocode.

Adapter golden (Berlin sample from Open-Meteo docs): `place_name` `Berlin`, `lat` `52.52437`, `lon` `13.41053`, `elevation_m` `74`, `timezone` `Europe/Berlin`.

## Verification

**Commands:**
- `uv run pytest` -- expected: all tests pass, including location matrix and StateStore defaults; no test opens a socket
- `uv run frost-alert setup` -- expected: prompts scale, threshold, location, then shows a place and waits for confirm (do not need a live geocode in CI)
