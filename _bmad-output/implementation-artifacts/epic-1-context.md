# Epic 1 Context: Configure frost watch without editing source

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

A clone-and-run setup path so a bonsai owner (or a friend who cloned) can install one Python package, set location, scale, and frost threshold through a local CLI, confirm the geocoded place, and commit `config/user.json`. Later checks use only that stored config — they never edit source and never re-geocode. This epic is the foundation every classify-and-alert story depends on.

## Stories

- Story 1.1: Installable Frost Alert package
- Story 1.2: Set scale and threshold through setup
- Story 1.3: Set location through geocode-once setup

## Requirements & Constraints

- Setup collects location (city, postal code, or optional coordinates), temperature scale (`C` or `F`), and alert threshold without editing source.
- Geocode once through Open-Meteo Geocoding. Show the resolved place and write location keys only after confirmation. Place name, elevation, and timezone come from the geocoder — never guessed. No match or rejected place: do not write a partial location.
- `config/user.json` has exactly `place_name`, `lat`, `lon`, `elevation_m`, `timezone`, `threshold_c`, and `scale`. Only setup writes that file. After setup, scheduled-check paths use stored config only and never re-geocode. Changing location, scale, or threshold means re-running setup or editing config, not source.
- Default `threshold_c` is 3. If the user chooses Fahrenheit, convert the entered threshold to Celsius before writing. Domain and both JSON files store Celsius; `scale` is setup and display only. Non-numeric threshold or a scale other than `C`/`F`: refuse those keys and explain what to enter.
- `data/state.json` keys are exactly `season` (`monitoring` or `suspended`), `event_date` (`YYYY-MM-DD` or `null`), `alerted_windows` (array of 24/12/6 for the current event), `telegram_offset` (last processed `update_id`, `0` if none), and `updated_at` (UTC ISO-8601). Only StateStore writes state, and only the check entrypoint calls it. Missing file returns defaults: `monitoring`, `null`, `[]`, `0`, and a current UTC timestamp.
- Runtime is CPython 3.13 + uv + stdlib HTTP. No web framework. No `requests` or `httpx`. Unit tests use fake ports and no live network. Logs go to stdout.
- Single-user, one location per clone. Internals stay location-agnostic — do not hardcode a locale or pin Open-Meteo `models=`. Secrets never live in source. The setup CLI does not flip season; that control is Telegram-only in a later epic.

## Technical Decisions

- Ports and adapters: domain contains no I/O; adapters implement ports; entrypoints only wire. Adding a vendor is a new adapter, not new domain rules. Ports: ForecastSource, Notifier, AckInbox, Watchdog, ConfigStore, StateStore, Clock.
- Package `frost_alert` under `src/frost_alert/{domain,ports,adapters,entrypoints}`. Domain must not import adapters or stdlib HTTP. Pin 3.13 in `.python-version`. Tooling is uv 0.12.
- Agreed tree this epic leaves in place: setup CLI and check entrypoint slots, `config/user.json` (setup writes; user commits), `data/state.json` (StateStore writes; the workflow commits later), `.github/workflows/check.yml` as a structural seed, `.python-version`. Do not use Actions cache or artifacts as the store. Setup is a local CLI and never a concurrent writer of state.
- JSON on disk. Instants as UTC ISO-8601. Open-Meteo Geocoding is public and keyless. Lat/lon are floats; `elevation_m` is a number; `timezone` is IANA.
- Ports for forecast, notify, ack, and watchdog are defined here so later epics plug in; this epic does not implement classification, Telegram season flip, failover, or the unattended tick.

## UX & Interaction Patterns

No UX design contract exists. The only UI in this epic is the local setup CLI: prompt for scale, threshold, and location; show the geocoder’s resolved place and wait for confirmation; on no match or reject, do not write guessed location keys; on invalid scale or threshold, refuse those keys and explain the expected input. Accepting defaults with Celsius yields `scale` `C` and `threshold_c` `3`.

## Cross-Story Dependencies

- 1.1 lands the installable package, layout, ports, and seed files. 1.2 adds scale/threshold on that CLI. 1.3 adds geocode-once location on the same CLI and StateStore defaults for a missing `data/state.json`.
- Epics 2 and 3 assume a committed `config/user.json` and must not add a geocode call on the check path. Season flip, frost classification, GitHub Actions scheduling, MET Norway failover, and watchdog ping are out of scope here.
