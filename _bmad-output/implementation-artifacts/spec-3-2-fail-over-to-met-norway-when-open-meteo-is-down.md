---
title: 'Fail over to MET Norway when Open-Meteo is down'
type: 'feature'
created: '2026-09-14'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '4af824dc1879bf24766c4e12154dcaecd51b7109'
context:
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `frost-alert check` uses only Open-Meteo. Timeout, 5xx, 429, or malformed hourly data aborts the tick, so a primary outage skips frost classification.

**Approach:** Keep Open-Meteo first (15s). On availability failure, fetch MET Norway Locationforecast 2.0 `compact` and continue with that one series. Extract a shared stdlib HTTP GET helper first; treat NaN/Inf temps as malformed.

## Boundaries & Constraints

**Always:**
- Stay on branch `3-2-fail-over-to-met-norway-when-open-meteo-is-down`. No story work on `master`.
- Open-Meteo first, 15s. Fail over on timeout, connect error, 5xx, 429, or empty/malformed hourly data (including NaN/Inf). Domain sees one `ForecastHour` list; never blend sources.
- No failover on HTTP 4xx except 429 (`HTTPError.code` in 400–499 excluding 429). Still raise; do not call MET.
- New MET adapter: `GET https://api.met.no/weatherapi/locationforecast/2.0/compact` with `lat`/`lon` to 4 decimal places, `altitude` = stored `elevation_m`, User-Agent `Frost-alert (https://github.com/dabben1993/Frost-alert)`, timeout 15s. Stdlib HTTP only.
- MET `properties.timeseries`: `time` UTC, `data.instant.details.air_temperature` Celsius. Return the leading contiguous hourly prefix (adjacent `t` differ by exactly 1h); drop the later 6-hourly tail. Empty prefix, missing keys, null/NaN/Inf temps, unsorted → raise (malformed).
- `ForecastSource.fetch(*, lat, lon)` unchanged. MET takes `elevation_m` in its constructor. `check.py` default-wires a composing failover source after config load; `check_tick.py` still calls one `forecast.fetch`. Injected `forecast=` in tests stays a single source (no failover).
- Shared GET helper under `adapters/` used by Open-Meteo forecast and MET (still `urllib.request.urlopen` so existing monkeypatches work). Do not migrate Telegram or the geocoder.
- Both sources fail while monitoring: raise → existing `check.py` `except Exception: return 1`, no `StateStore.write`. Suspended ticks still skip fetch.
- Unit tests fake `urlopen`; sockets blocked. No live API.

**Never:**
- Do not implement Watchdog ping, git commit of `data/state.json`, operator README, or change `check.yml`.
- Do not change `classify.py`, alert copy, season in/out, Telegram adapters, setup, geocoder, or JSON keys.
- Do not add `requests`/`httpx` or a MET/Open-Meteo SDK. Do not pin Open-Meteo `models=`. Do not treat failover as a second opinion.
- Do not commit secrets, `.env`, `config/user.json`, or `data/state.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| OM success | well-formed OM hourly series | that series; MET not called | N/A |
| OM availability miss | timeout, connect `URLError`, HTTP 5xx, 429, empty/malformed/NaN/Inf | MET compact fetched; one MET series returned | failover |
| OM 4xx-bad-request | `HTTPError` 400 (also 401–418, 404, 403) | MET not called; raise | no failover |
| MET request shape | failover fetch with lat `59.32932`, lon `18.06857`, elevation `28.4` | URL host `api.met.no`, path `/weatherapi/locationforecast/2.0/compact`; query `lat=59.3293`, `lon=18.0686`, `altitude=28.4`; UA and timeout 15 | N/A |
| MET hourly then 6h tail | times 12:00, 13:00, 14:00, then 18:00 UTC with temps | three `ForecastHour`; 18:00 dropped | N/A |
| MET malformed after failover | missing `air_temperature`, empty prefix, HTTP/parse fail | no series; do not return OM leftovers | raise |
| Dual miss, monitoring | OM availability fail and MET fail | no poll; no `state.json` write; exit 1 | raise |
| Suspended | season `suspended` | no OM, no MET | N/A |

</frozen-after-approval>

## Code Map

- `src/frost_alert/ports/__init__.py` -- `ForecastSource.fetch(*, lat, lon) -> list[ForecastHour]` (L7–8). Do not add elevation to the port.
- `src/frost_alert/adapters/open_meteo_forecast.py` -- raise `OpenMeteoForecastError` wrapping `HTTPError` `from err` (L39–47). Switch GET to the helper; reject non-finite temps in `_is_number` (L94–95). Keep query shape (no `models=`).
- `src/frost_alert/adapters/http.py` -- **new.** Stdlib GET + JSON; `USER_AGENT` / `TIMEOUT_S=15`. Used only by OM forecast and MET this story.
- `src/frost_alert/adapters/met_norway_forecast.py` -- **new.** `MetNorwayForecast(elevation_m)` + fetch error. `adapters/__init__.py` stays empty.
- `src/frost_alert/adapters/forecast_failover.py` -- **new.** Try primary; on availability fail call fallback; on 4xx-except-429 re-raise without fallback.
- `src/frost_alert/entrypoints/check.py` -- L39 default `OpenMeteoForecast()` only. After `store.load()`, default `FailoverForecast(OpenMeteoForecast(), MetNorwayForecast(elevation_m=float(config["elevation_m"])))`.
- `src/frost_alert/check_tick.py` -- L26 `forecast.fetch(lat=..., lon=...)`. Reuse; do not edit.
- `tests/test_open_meteo_forecast.py` -- monkeypatch `urllib.request.urlopen` (L54–72); HTTP 400/429/500 already raise (L197–213). Add NaN/Inf rows; keep socket block.
- `tests/test_check_tick.py` -- `test_matrix_forecast_raise_no_write` (L380–397) still the dual-miss contract when the injected source raises. Default failover coverage belongs in failover tests, not by changing injected fakes.
- Reuse, do not edit: domain, Telegram adapters, geocoder, `check.yml`, JSON stores, `send_frost_alert.py`, `apply_season.py`.

## Tasks & Acceptance

**Execution:**
- [x] `src/frost_alert/adapters/http.py` -- shared GET helper -- epic-2 retro item 4
- [x] `tests/test_open_meteo_forecast.py` -- NaN/Inf malformed; helper still faked via `urlopen` -- epic-2 retro item 5
- [x] `tests/test_met_norway_forecast.py` -- MET matrix rows (shape, hourly prefix, malformed) -- red first -- FR16
- [x] `src/frost_alert/adapters/met_norway_forecast.py` -- compact adapter -- FR16, AD-11
- [x] `tests/test_forecast_failover.py` -- OM success / availability failover / 4xx no-call / dual miss -- red first -- FR15
- [x] `src/frost_alert/adapters/forecast_failover.py` -- compose two `ForecastSource` -- AD-11
- [x] `src/frost_alert/entrypoints/check.py` -- default-wire failover with stored `elevation_m` -- FR15

**Acceptance Criteria:**
- Given Open-Meteo is called first with a 15s timeout, when the result is timeout, connect error, 5xx, 429, or empty/malformed hourly data, then the same tick fetches MET Norway Locationforecast 2.0 `compact` and continues classification, and domain sees one series only — sources are never blended (FR15, AD-11).
- Given Open-Meteo returns 4xx-bad-request, when failover is considered, then MET Norway is not called (FR15).
- Given a MET Norway request, when the adapter calls the API, then it sends `altitude` = `elevation_m`, lat/lon to 4 decimals, and User-Agent `Frost-alert` plus the repo URL (FR16).
- Given both sources fail while `monitoring`, when the tick ends, then the process exits non-zero and does not treat the miss as a successful check (FR15).
- Given `uv run pytest`, when tests finish, then all pass, including every matrix row; no test opens a socket.

## Implementation Notes

`adapters/http.py` GET+JSON (`urlopen`, UA, 15s). `OpenMeteoForecast` uses it and rejects non-finite temps. `MetNorwayForecast(elevation_m)` requests compact with 4-decimal lat/lon and `altitude`; returns the leading 1h prefix. `FailoverForecast` retries MET on availability/`OpenMeteoForecastError` unless `__cause__` is HTTP 4xx except 429. `check.py` default-wires that pair after config load. `uv run pytest` — 212 passed; sockets blocked.

## Spec Change Log

## Review Triage Log

- `false` — Blind: `FailoverForecast` `except Exception` would fail over a parser `TypeError`. Wired primary wraps fetch/parse as `OpenMeteoForecastError`; 4xx is filtered via `__cause__`. A failed series that is not 4xx is the availability path.
- `false` — Blind: unwrapped `HTTPError` 400 would fail over. `OpenMeteoForecast` always `raise OpenMeteoForecastError(...) from err`; tests that omit `__cause__` are not the default primary.
- `low` — Blind/Edge: MET parses the whole `timeseries` before the 1h prefix, so a bad 6h-tail temp would raise. Compact `instant.details.air_temperature` is present on all points; fix would restructure parse order. Reject: not everyday, not a direct correction.
- `medium` — Blind: failover tests use identical `OM_SERIES`/`MET_SERIES` and `any()` on `hosts`, so MET-first or a blend would still pass. Disposition: patch.
- `false` — Blind: dual-miss/`check.main` classification not re-run through composed adapters. Frozen Code Map keeps `test_matrix_forecast_raise_no_write` as the process contract; `test_dual_miss_*` covers both adapters raising.
- `false` — Blind: suspended row untested against default `FailoverForecast`. `check_tick` does not `fetch` when `suspended`; constructors do not HTTP.
- `low` — Blind/Edge: `float(config["elevation_m"])` is outside the tick `except` so a missing key is an uncaught `KeyError`. Setup always writes `elevation_m`; Actions still fails the job. Reject: not everyday; wrapping adds a branch for undemonstrated keys.
- `false` — Blind: failover fetch does not re-assert 4-decimal query/`altitude=28.4`. `test_request_shape_*` covers `MetNorwayForecast`; matrix `altitude=28.4` forbids rounding to whole metres.
- `low` — Edge: non-finite lat/lon/`elevation_m` in the MET query. Stored coords come from setup/geocoder. Reject: extra guards, undemonstrated input.
- `low` — Edge: `math.isfinite` `OverflowError` on a huge JSON int in MET `_is_number`. Celsius payloads are small ints/floats. Reject: loud fail on undemonstrated input.
- `low` — Edge: same `OverflowError` in Open-Meteo `_is_number`. Same rejection.
- `medium` — Verification-gap: `test_availability_failure_fetches_met` does not assert fallback `fetch(lat, lon)`; `urlopen` fake ignores query, so `lat=0, lon=0` would still pass. Disposition: patch.
## Design Notes

Failover is an adapter, not domain and not `check_tick`. Distinguish 4xx via `OpenMeteoForecastError.__cause__` (`HTTPError.code`); transport `URLError` without a 4xx code is availability. MET compact is hourly then 6-hourly — keep the leading 1h run so a valid Nordic payload is not “malformed”. Elevation stays off the port so existing fakes keep `fetch(*, lat, lon)`. Helper is GET-only; Telegram POST copies stay until a later story.

Golden MET prefix: times `2026-01-15T12:00:00Z`, `13:00:00Z`, `14:00:00Z`, `18:00:00Z` with temps `4.0, 3.0, 2.0, 1.0` → three hours, first `t` `2026-01-15 12:00 UTC`, `temp_c` 4.0.

## Verification

**Commands:**
- `uv run pytest` -- expected: all tests pass including OM NaN/Inf, every MET and failover matrix row; `test_check_tick.py` and `test_package.py` isolation still green; no sockets
