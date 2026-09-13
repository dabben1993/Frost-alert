---
title: 'Fetch hourly forecast from Open-Meteo'
type: 'feature'
created: '2026-09-13'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '35ba425c5924fef1b48179542c88d39ec10c789a'
context:
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Classification already maps an in-memory hourly series to frost risk, but nothing loads that series from Open-Meteo for the stored place, so a check cannot use a real forecast.

**Approach:** Implement the Open-Meteo Forecast adapter as `ForecastSource`: stored lat/lon in, one ascending UTC `{t, temp_c}` series out. Availability failover stays Story 3.2.

## Boundaries & Constraints

**Always:**
- Stay on branch `2-2-fetch-hourly-forecast-from-open-meteo`. No story work on `master`.
- `ForecastSource.fetch(*, lat, lon)` returns `list[ForecastHour]` (`t` timezone-aware UTC, `temp_c` Celsius). Callers pass stored coordinates; this story does not read `user.json` or re-geocode.
- `GET https://api.open-meteo.com/v1/forecast` with `latitude`, `longitude`, `hourly=temperature_2m`, `timezone=UTC`. Identifying User-Agent `Frost-alert (https://github.com/dabben1993/Frost-alert)`. Timeout 15s. Stdlib HTTP only. Default multi-model blend — query must not include `models=`.
- Parse `hourly.time` as UTC (attach UTC when the string has no offset). Never treat those clock hours as the configured IANA zone. Domain never sees vendor JSON.
- A valid series is complete, strictly ascending, and hourly (adjacent `t` differ by exactly 1h). Empty, missing keys, length mismatch, null temps, unsorted, or non-hourly → malformed.
- On timeout, connect error, HTTP 4xx/5xx/429, JSON error, or malformed hourly data: raise. Do not return `[]` or a partial/blended series (empty would look like no frost to `classify`).
- Unit tests monkeypatch `urlopen` / use fixtures; sockets stay blocked. No live API.

**Never:**
- Do not implement MET Norway, Telegram, classify changes, season in/out, check entrypoint, ConfigStore `read`, or `.github/workflows/check.yml`.
- Do not add `requests`/`httpx`. Do not pin `models=`. Do not request `current_weather` / live temperature.
- Do not change setup, geocoder, ConfigStore write, StateStore, or `classify.py`.
- Do not commit secrets, `.env`, `config/user.json`, or `data/state.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | lat/lon; hourly times `12:00`,`13:00`,`14:00` UTC and matching `temperature_2m` | three `ForecastHour`; `t` UTC-aware; temps in Celsius; ascending | N/A |
| Query shape | any fetch | URL host `api.open-meteo.com`, path `/v1/forecast`; params `hourly=temperature_2m`, `timezone=UTC`; UA and timeout 15; no `models=` | N/A |
| GMT-as-local | times without offset under `timezone=UTC` | `t.tzinfo` is UTC, not naive and not the place's IANA zone | N/A |
| Missing hourly | no `hourly`, or missing `time` / `temperature_2m` | no series returned | raise |
| Empty arrays | `time` and `temperature_2m` both `[]` | no series | raise |
| Length mismatch | more times than temps (or the reverse) | no series | raise |
| Null temp | a `null` in `temperature_2m` | no series (do not drop the hour) | raise |
| Unsorted | a later ISO time before an earlier one | no series | raise |
| Non-hourly | adjacent times 3h apart | no series | raise |
| HTTP 5xx / 429 / timeout / connect | `urlopen` fails that way | no series | raise |
| HTTP 4xx | `HTTPError` 400 | no series (3.2 will not failover; 2.2 still raises) | raise |
| Bad JSON / `error: true` | non-JSON body or Open-Meteo error object | no series | raise |

</frozen-after-approval>

## Code Map

- `src/frost_alert/ports/__init__.py` -- `ForecastSource` empty (L4–5). Add `fetch(*, lat: float, lon: float) -> list[ForecastHour]`. Import `ForecastHour` from domain.
- `src/frost_alert/domain/classify.py` -- `ForecastHour(t, temp_c)` (L9–12). Reuse; do not edit.
- `src/frost_alert/adapters/open_meteo_geocoder.py` -- stdlib `urlopen`, UA, 15s (L9–34). Copy the pattern; do not edit.
- `src/frost_alert/adapters/open_meteo_forecast.py` -- new: `OpenMeteoForecast` + fetch error. `adapters/__init__.py` stays empty.
- `tests/test_setup_location.py` -- `_FakeHTTPResponse` + `urlopen` monkeypatch (L452–567). Copy into a new test module.
- `tests/test_package.py` -- `FakeForecastSource` stays constructible; domain isolation still forbids adapter/HTTP imports.

## Tasks & Acceptance

**Execution:**
- [x] `tests/test_open_meteo_forecast.py` -- failing tests for every I/O matrix row -- red first
- [x] `src/frost_alert/ports/__init__.py` -- `ForecastSource.fetch` returning `list[ForecastHour]` -- AD-1 / AD-11
- [x] `src/frost_alert/adapters/open_meteo_forecast.py` -- Open-Meteo Forecast adapter, stdlib HTTP, UTC series or raise -- FR15/FR16 adapter half, NFR6

**Acceptance Criteria:**
- Given stored lat/lon, when the adapter fetches a well-formed hourly payload, then domain receives one ascending `ForecastHour` list with UTC-aware `t` and Celsius `temp_c`, and the request used `timezone=UTC` with no `models=`.
- Given missing, unsorted, non-hourly, empty, or HTTP/parse failure, when the adapter runs, then it raises and does not return a partial, blended, or empty series.
- Given `uv run pytest`, when tests finish, then all pass, fixtures fake `urlopen`, and no test opens a socket.

## Implementation Notes

`ForecastSource.fetch(*, lat, lon)` returns `list[ForecastHour]`. `OpenMeteoForecast` GETs `api.open-meteo.com/v1/forecast` with `hourly=temperature_2m` and `timezone=UTC`; naive `hourly.time` gets `datetime.UTC`. All fetch/parse failures raise `OpenMeteoForecastError` (HTTPError is a URLError, so 4xx/5xx/429 wrap with `__cause__`). Empty hourly arrays raise. Review patch: null-temp test uses leading and trailing `None`. `uv run pytest` — 92 passed; sockets blocked.

## Spec Change Log

## Review Triage Log

- `false` — Blind: sprint-status `in-progress` while spec is `in-review`. Step-04 sets spec `in-review` before reviewers run; sprint sync to `review` is later in this workflow. Not a product defect.
- `medium` — Blind: `test_null_temp_raises_without_dropping_hour` only uses a middle `null`; dropping that hour still raises on the 2h gap. Leading/trailing `null` drop would return a shorter valid series. Disposition: patch.
- `false` — Blind: `OpenMeteoForecastError` has no status field; HTTP tests do not assert `__cause__`. Frozen Always requires raise, not a discriminator. HTTPError is chained with `from err`; 3.2 can read `.code`.
- `false` — Blind: `_is_number` accepts NaN/Inf. Open-Meteo JSON is RFC-compliant and does not emit those tokens. Same helper as the geocoder. `isfinite` would be a new guard for undemonstrated input.
- `false` — Blind: query test does not forbid extra params / pin `temperature_unit=celsius`. Adapter encodes only lat, lon, `hourly`, `timezone`. Open-Meteo default unit is Celsius. Spec does not require pinning `temperature_unit`.
- `false` — Blind: tests never `isinstance` the adapter as `ForecastSource`; `FakeForecastSource` has no `fetch`. Spec keeps the fake constructible. Ports are not `@runtime_checkable`; other fakes also omit methods.
- `false` — Blind: no non-string / unparseable `hourly.time` test. `_parse_utc` raises `OpenMeteoForecastError`. GMT-as-local is the offset-less ISO case, which is tested. Loud fail on junk time is correct.
- `false` — Blind: `error: true` fixture has no `hourly` block. Real Open-Meteo error objects omit hourly; missing-hourly already raises. Combined error+series is undemonstrated vendor shape.
- `low` — Edge: truncated body can raise `http.client.IncompleteRead` unwrapped at `open_meteo_forecast.py:36-47`. Loud fail, not a silent warm series. Same except tuple as the geocoder. Reject: extra `except` for a path tests never showed.
- `false` — Edge: NaN/Inf `temperature_2m` at `_is_number`. Same claim as Blind NaN. Vendor JSON does not emit those tokens.
- `medium` — Verification-gap: null-temp test only uses middle `None`; drop-hour still raises on the gap; leading/trailing `None` would return a shorter series. Disposition: patch (parametrize leading/trailing).


## Design Notes

Open-Meteo `hourly.time` with `timezone=UTC` has no `Z`. Attach `datetime.UTC` — naive subtract breaks classify, and treating the clock hour as `Europe/Stockholm` is the GMT-as-local trap.

Raise on every failure, including empty arrays. `classify([])` is absent risk; a down API must not look warm. 3.2 will branch 4xx vs availability on that raise.

Golden: `lat=59.33`, `lon=18.07`. `hourly.time` `["2026-01-15T12:00","2026-01-15T13:00","2026-01-15T14:00"]`, `temperature_2m` `[4.0, 3.0, 2.0]` → first `t` is `2026-01-15 12:00 UTC`, `temp_c` 4.0. Same times out of order raises.

## Verification

**Commands:**
- `uv run pytest` -- expected: all tests pass, including every forecast matrix row; `test_package.py` isolation still green; no test opens a socket
