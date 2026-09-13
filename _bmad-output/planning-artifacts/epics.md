---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics, step-03-create-stories, step-04-final-validation]
inputDocuments:
  - _bmad-output/specs/spec-frost-alert/SPEC.md
  - _bmad-output/specs/spec-frost-alert/stack.md
  - _bmad-output/specs/spec-frost-alert/state-machines.md
  - _bmad-output/specs/spec-frost-alert/failure-modes.md
  - _bmad-output/specs/spec-frost-alert/alert-copy.md
  - _bmad-output/planning-artifacts/architecture/architecture-Frost-alert-2026-09-12/ARCHITECTURE-SPINE.md
---

# Frost-alert - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Frost-alert, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: A setup CLI lets the user set location (city name, postal code, or optional coordinates), temperature scale (`C`|`F`), and alert threshold without editing source.

FR2: Setup geocodes once via the Open-Meteo Geocoding API, shows the resolved place for confirmation, and writes `config/user.json` with exactly `place_name`, `lat`, `lon`, `elevation_m`, `timezone`, `threshold_c`, and `scale`. Place, elevation, and timezone come from the geocoder, not guessed values.

FR3: After setup, scheduled checks use only the stored config and never re-geocode. Changing location, scale, or threshold is done by re-running setup or editing config, not source.

FR4: Default `threshold_c` is 3. If the user chooses Fahrenheit, setup converts the entered threshold to Celsius before writing `threshold_c`. Domain and both JSON files store Celsius; `scale` is setup and display only.

FR5: Classify frost risk as present when any upcoming forecast hour with `0 < remaining ≤ 30h` is at or below `threshold_c`; classify absent when all such hours are above threshold.

FR6: Classification uses forecast hours only — never live current temperature, never a night-only (e.g. 20:00–08:00) window.

FR7: Lead time is `first_at_or_below − now`. Mapping: remaining > 12h → window 24; remaining > 6h → window 12; remaining > 0 → window 6. Each window fires at most once per frost event. Cadence is 24h then 12h then 6h with no further steps.

FR8: Frost event identity is the local calendar date (config IANA zone) of the first at-or-below hour. Same-day forecast revision does not reset windows. When that date ends, the next crossing is a new event. Monitoring keeps evaluating every tick until `/in`.

FR9: No frost alerts fire when risk is absent or season is `suspended`.

FR10: A frost-alert notification preview is understandable in one glance (emoji, frost risk coming, roughly 24h/12h/6h) without table, location, or ack instructions. The opened message adds configured place, first-crossing temperature in the user's scale, when that crossing is expected, the user's threshold, and an ack control (`/in` or `plants_in`).

FR11: `/in` or `plants_in` sets season to `suspended`. Subsequent ticks send no frost alerts until `/out` or `plants_out` sets `monitoring`.

FR12: `/in` leaves `event_date` and `alerted_windows` unchanged. `/out` clears both so a same-day resume can warn again. Repeat commands are idempotent. Domain has no snooze-until-tomorrow state.

FR13: Season flip is Telegram-only (commands `/in` `/out` and callback data `plants_in` / `plants_out`). Always `answerCallbackQuery`. Ignore updates whose chat id is not `TELEGRAM_CHAT_ID`. CLI is setup only and does not flip season.

FR14: A GitHub Actions scheduled workflow on the default branch (every 6 hours, plus `workflow_dispatch`) fetches a forecast and can send an alert with no personally-owned always-on device.

FR15: Open-Meteo is called first with a 15s timeout. On timeout, connect error, 5xx, 429, or empty/malformed hourly data, the same check obtains hourly data from MET Norway Locationforecast 2.0 and continues classification. No fallback on 4xx-bad-request. Domain sees one series (UTC `t` + `temp_c`); sources are never blended.

FR16: MET Norway calls pass `altitude` = `elevation_m`, lat/lon to 4 decimals, and an identifying User-Agent (`Frost-alert` plus repo URL). Open-Meteo must not pass GMT hours through as local. Missing, unsorted, or non-hourly data is malformed and triggers failover.

FR17: Watchdog pings healthchecks.io only after a forecast series was obtained (primary or fallback) and classification finished. Dual-API miss or crash: no ping and non-zero exit. Notifier failure still pings.

FR18: If the check does not report in within the documented 6h period plus ~6h grace, the user receives a separate warning that is not a frost alert.

FR19: One tick, this order: load config+state → if `monitoring`, fetch+classify → send a frost alert only if that window is not in `alerted_windows` and mark the window only after a successful send → poll Telegram and apply domain in/out → write state → `git` commit `data/state.json` → watchdog ping.

FR20: Suspended ticks skip forecast, still poll Telegram, write state, commit `data/state.json`, and ping the watchdog.

FR21: Ack intake is cron-polled `getUpdates` with `offset = telegram_offset + 1`. A webhook must not be set. Telegram drops updates older than 24h.

FR22: `config/user.json` is written only by setup. `data/state.json` keys are exactly `season` (`monitoring`|`suspended`), `event_date` (`YYYY-MM-DD` or `null`), `alerted_windows` (array of 24/12/6 for the current event), `telegram_offset` (last processed `update_id`, `0` if none), `updated_at` (UTC ISO-8601). Only StateStore writes state, and only the check entrypoint calls it.

### NonFunctional Requirements

NFR1: Primary-path cost is zero dollars; no credit card required for default weather, notification, or hosting services.

NFR2: Single-user personal automation: no accounts, no multi-tenant service, no custody of other people's keys; sharing is clone plus own config; one location per clone/deployment.

NFR3: Secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `HEALTHCHECKS_PING_URL` live in GitHub Secrets, never in source or committed files.

NFR4: Must not depend on a personally-owned always-on device (no home server, Raspberry Pi, or laptop-as-host).

NFR5: Design must tolerate multi-hour GitHub Actions delay; a late run still counts as a useful check. Last window must not assume on-the-hour delivery.

NFR6: Internals stay location-agnostic; Sweden is the first build-and-test locale, not a hardcoded location or Open-Meteo `models=` pin.

NFR7: Do not build or maintain a custom native app; installing an existing third-party receiver app is allowed.

NFR8: README documents that the Telegram receiver app must be whitelisted from Android battery optimization.

NFR9: Default host is a public repo on GitHub Free (or GitHub Pro if the repo must stay private). `schedule:` fires only on the default branch.

NFR10: Runtime is CPython 3.13 (`.python-version` and `actions/setup-python@v7`; patch floats) + uv + stdlib HTTP. No web framework. No `requests`/`httpx` unless a later port cannot work without them.

NFR11: Unit tests use fake ports; no live network in unit tests.

NFR12: Logs go to stdout.

NFR13: The host must survive months of seasonal idle (no frost-risk alerts) without pausing or requiring a keep-alive write.

NFR14: Leave GitHub Actions' built-in workflow-failure email on as the $0 failure channel beside the watchdog.

NFR15: Domain contains no I/O. Adapters implement ports. Entrypoints only wire. Adding a vendor means a new adapter, not a new domain.

### Additional Requirements

**Starter template (Epic 1 Story 1):** Greenfield Python 3.13 + uv + stdlib HTTP. Pin 3.13 in `.python-version` and `actions/setup-python@v7`. No web framework. Package layout `src/frost_alert/{domain,ports,adapters,entrypoints}`.

- Ports: ForecastSource, Notifier, AckInbox, Watchdog, ConfigStore, StateStore, Clock. No framework.
- Structural seed: `config/user.json` (setup writes; user commits), `data/state.json` (StateStore writes; workflow commits), `.github/workflows/check.yml`, `.python-version`.
- One workflow per tick; `concurrency`: one in-flight run, cancel-in-progress. Setup is a local CLI, never a concurrent writer.
- Workflow `permissions: contents: write` so the job can commit `data/state.json`. Do not use Actions cache or artifacts as the store.
- Stack pins: actions/checkout@v7, actions/setup-python@v7, GitHub-hosted `ubuntu-latest`, Open-Meteo Forecast + Geocoding (public no-key), MET Norway Locationforecast 2.0 `compact`, Telegram Bot API 10.3, healthchecks.io ping API, uv 0.12.
- JSON on disk. Instants UTC ISO-8601. Frost-event key is local `YYYY-MM-DD`.
- healthchecks.io period 6h, grace ~6h — document beside the ping-URL secret, do not hardcode.
- Open-Meteo uses the default multi-model blend (no Sweden-only `models=` pin).
- v1 required channel is Telegram only. ntfy, email, and Pushover are deferred.
- AWS EventBridge Scheduler + Lambda is a documented non-default host, not built in v1.
- Do not use as primary: SMHI, OpenWeatherMap, WhatsApp Business/Cloud API, SMS, Supabase Cron, Vercel Hobby, Fly.io scheduled machines, cron-job.org/EasyCron as the only runner, Render Cron.
- Deferred: exact frost-alert sentence strings, extra pytest plugins, `data/state.json` commit-message wording.

### UX Design Requirements

No UX design contract (`DESIGN.md` / `EXPERIENCE.md`) exists. This product has no custom UI beyond a local setup CLI and Telegram messages. Preview-vs-opened frost-alert copy is captured as FR10; operator README battery-optimization guidance is NFR8.

### FR Coverage Map

FR1: Epic 1 - Setup CLI for location, scale, and threshold without editing source
FR2: Epic 1 - Geocode once, confirm resolved place, write `config/user.json` keys
FR3: Epic 1 - Scheduled checks use stored config only; never re-geocode
FR4: Epic 1 - Default `threshold_c` 3; Fahrenheit converted to Celsius on disk
FR5: Epic 2 - Classify frost risk from any upcoming hour within the 30h lookahead
FR6: Epic 2 - Forecast hours only; never live temperature; never night-only window
FR7: Epic 2 - Remaining-time windows 24 / 12 / 6; each window once per event
FR8: Epic 2 - Frost event is local date of first crossing; same-day revision does not reset
FR9: Epic 2 - No frost alerts when risk is absent or season is suspended
FR10: Epic 2 - Preview-first frost-alert copy; opened message adds facts and ack control
FR11: Epic 2 - `/in` or `plants_in` suspends frost alerts until `/out` or `plants_out`
FR12: Epic 2 - `/out` clears event and windows; `/in` leaves them; no snooze state
FR13: Epic 2 - Telegram-only season flip; answer callbacks; ignore other chats
FR14: Epic 3 - GitHub Actions every 6 hours plus `workflow_dispatch`; no always-on device
FR15: Epic 3 - Open-Meteo first; MET Norway on availability failure; one series, never blend
FR16: Epic 3 - MET Norway elevation, 4-decimal lat/lon, identifying User-Agent; malformed → failover
FR17: Epic 3 - Watchdog ping only after forecast + classification; dual-API miss does not ping
FR18: Epic 3 - Missed check produces a separate non-frost warning
FR19: Epic 3 - Full tick order including state write, git commit, then ping
FR20: Epic 3 - Suspended ticks skip forecast; still poll, persist, and ping
FR21: Epic 2 - Cron-polled `getUpdates`; webhook must not be set
FR22: Epic 1 - Config and state key contracts; setup writes config only

## Epic List

### Epic 1: Configure frost watch without editing source
A user or friend can clone the repo, run setup, confirm a resolved place, and have a committed `config/user.json` so later checks never edit source or re-geocode.
**FRs covered:** FR1, FR2, FR3, FR4, FR22

### Epic 2: Get escalating frost warnings I can silence
A local check classifies any-hour frost risk, sends 24h / 12h / 6h Telegram alerts that are readable from the preview, and the user can suspend or resume the season from Telegram.
**FRs covered:** FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR21

### Epic 3: Trust the watch while the laptop is off
GitHub Actions runs the same loop unattended, fails over to MET Norway, commits state, and healthchecks.io warns if the job itself missed — without treating that warning as a frost alert.
**FRs covered:** FR14, FR15, FR16, FR17, FR18, FR19, FR20

## Epic 1: Configure frost watch without editing source

A user or friend can clone the repo, run setup, confirm a resolved place, and have a committed `config/user.json` so later checks never edit source or re-geocode.

### Story 1.1: Installable Frost Alert package

As a bonsai owner who cloned the repo,
I want an installable Python 3.13 project with the agreed package layout,
So that I can run setup and later checks from one place without a second runtime or a script pile.

**Acceptance Criteria:**

**Given** a fresh clone
**When** I sync the project with uv
**Then** package `frost_alert` is importable
**And** `.python-version` is `3.13`
**And** there is no web framework and no `requests`/`httpx` dependency (NFR10)

**Given** the repository tree
**When** I inspect the package
**Then** code lives under `src/frost_alert/{domain,ports,adapters,entrypoints}`
**And** `domain` does not import `adapters` or stdlib HTTP
**And** ports `ForecastSource`, `Notifier`, `AckInbox`, `Watchdog`, `ConfigStore`, `StateStore`, and `Clock` are defined (AD-1, AD-12)

**Given** the package
**When** unit tests run
**Then** they use fake ports only
**And** they make no live network calls (NFR11)

### Story 1.2: Set scale and threshold through setup

As a bonsai owner,
I want to set my temperature scale and frost threshold through a setup CLI,
So that I never edit source and the stored threshold defaults to a safety margin above 0°C.

**Acceptance Criteria:**

**Given** the installable package from Story 1.1
**When** I run the setup CLI and accept defaults with scale Celsius
**Then** `config/user.json` has `scale` `C` and `threshold_c` `3`
**And** I did not edit any source file (FR1, FR4)

**Given** I choose scale Fahrenheit and enter a threshold in °F
**When** setup writes config
**Then** `threshold_c` is that value converted to Celsius
**And** `scale` is `F`
**And** domain and the JSON file store Celsius only — `scale` is for setup and later display (FR4, AD-7)

**Given** I re-run setup and change scale or threshold
**When** setup completes
**Then** `config/user.json` is updated
**And** I still did not edit source (FR3)

**Given** I enter a non-numeric threshold or a scale other than `C`/`F`
**When** setup validates input
**Then** it refuses to write those keys
**And** it explains what to enter

### Story 1.3: Set location through geocode-once setup

As a bonsai owner or a friend after cloning,
I want to set my location by city, postal code, or optional coordinates and confirm the resolved place,
So that checks use cached coordinates and elevation and never re-geocode or edit source.

**Acceptance Criteria:**

**Given** setup can already write scale and threshold
**When** I enter a city name or postal code
**Then** the Open-Meteo Geocoding adapter resolves a place and setup shows it for confirmation
**And** on confirm, ConfigStore writes `place_name`, `lat`, `lon`, `elevation_m`, and `timezone` from the geocoder, not guessed values (FR2, AD-3)

**Given** I supply optional coordinates
**When** setup completes
**Then** place name, elevation, and timezone still come from the geocoder
**And** scheduled-check code paths have no geocode call (FR3)

**Given** I confirm a resolved place
**When** setup writes `config/user.json`
**Then** the file contains exactly `place_name`, `lat`, `lon`, `elevation_m`, `timezone`, `threshold_c`, and `scale`
**And** only setup wrote that file (FR1, FR22)

**Given** the geocoder returns no match or I reject the shown place
**When** setup handles the result
**Then** it does not write a guessed or partial location

**Given** `data/state.json` is missing
**When** StateStore loads state
**Then** it returns defaults `season` `monitoring`, `event_date` `null`, `alerted_windows` `[]`, `telegram_offset` `0`, and `updated_at` as UTC ISO-8601
**And** those are the only state keys (FR22)

## Epic 2: Get escalating frost warnings I can silence

A local check classifies any-hour frost risk, sends 24h / 12h / 6h Telegram alerts that are readable from the preview, and the user can suspend or resume the season from Telegram.

### Story 2.1: Classify frost risk and remaining-time window

As a bonsai owner,
I want the system to detect the first upcoming hour at or below my threshold and map how much time remains,
So that I get the right 24h, 12h, or 6h warning instead of a live-temperature surprise.

**Acceptance Criteria:**

**Given** an hourly forecast series and `threshold_c`
**When** any upcoming hour with `0 < remaining ≤ 30h` is at or below threshold
**Then** domain classifies frost risk as present
**And** lead time is `first_at_or_below − Clock.now` (FR5, AD-5)

**Given** all upcoming hours in that lookahead are above `threshold_c`
**When** domain classifies
**Then** frost risk is absent (FR5)

**Given** a forecast hour at or below threshold
**When** domain classifies
**Then** it uses forecast hours only
**And** it never reads live current temperature
**And** it never ignores a daytime crossing (FR6, AD-7)

**Given** remaining time to the first at-or-below hour
**When** domain maps the window
**Then** remaining > 12h → 24, remaining > 6h → 12, remaining > 0 → 6
**And** a crossing outside `0 < remaining ≤ 30h` does not count (FR7)

**Given** config IANA timezone
**When** risk is present
**Then** frost event identity is the local calendar date of that first at-or-below hour
**And** a same-day forecast revision does not create a new event or reset windows
**And** after that local date ends, the next crossing is a new event (FR8, AD-8)

### Story 2.2: Fetch hourly forecast from Open-Meteo

As a bonsai owner,
I want a check to load hourly temperatures for my stored location from Open-Meteo,
So that classification uses a real forecast series, not a hardcoded place or live thermometer.

**Acceptance Criteria:**

**Given** `config/user.json` with lat, lon, and timezone
**When** the Open-Meteo Forecast adapter fetches
**Then** domain receives one ascending list of `{t, temp_c}` with `t` as UTC ISO-8601
**And** GMT hours are not passed through as local (FR15 adapter contract, AD-11)
**And** the default multi-model blend is used — no Sweden-only `models=` pin (NFR6)

**Given** missing, unsorted, or non-hourly data
**When** the adapter parses the response
**Then** it treats the payload as malformed
**And** it does not hand domain a blended or partial series

**Given** unit tests for the adapter
**When** they run
**Then** they use fixtures or fakes, not the live API (NFR11)

**Does not include:** MET Norway failover (Story 3.2).

### Story 2.3: Send a preview-first Telegram frost alert

As a bonsai owner,
I want a frost warning I can understand on the lock screen, with facts and an ack control in the opened message,
So that I know plants must move without opening a table of forecast rows.

**Acceptance Criteria:**

**Given** risk is present and the window is not already in `alerted_windows`
**When** Notifier sends a frost alert
**Then** the notification preview is understandable in one glance: emoji, frost risk coming, and roughly 24h / 12h / 6h
**And** the preview does not include a forecast table, location string, or ack how-to (FR10)

**Given** the same send
**When** I open the Telegram message
**Then** it includes configured place, first-crossing temperature in my `scale`, when that crossing is expected, my threshold, and an ack control (`/in` or `plants_in`) (FR10)

**Given** a successful send
**When** the tick continues
**Then** that window is marked in `alerted_windows` only after success
**And** a notifier failure does not mark the window (FR19 mark-after-send)

**Given** exact sentence strings
**When** copy is implemented
**Then** the preview-vs-opened split is kept
**And** exact wording may follow `alert-copy.md` without being locked in this story

### Story 2.4: Flip season from Telegram

As a bonsai owner,
I want to tell the bot that plants are in or out from Telegram,
So that frost alerts stop for the season and can start again without editing `state.json` or using a laptop CLI.

**Acceptance Criteria:**

**Given** season is `monitoring`
**When** I send `/in` or tap `plants_in`
**Then** domain sets `season` to `suspended`
**And** `event_date` and `alerted_windows` are unchanged (FR11, FR12, AD-9)

**Given** season is `suspended`
**When** I send `/out` or tap `plants_out`
**Then** domain sets `season` to `monitoring`
**And** `event_date` and `alerted_windows` are cleared so a same-day resume can warn again (FR12)

**Given** I repeat the same in or out command
**When** AckInbox applies it
**Then** the result is idempotent
**And** domain still has only `monitoring` and `suspended` — no snooze-until-tomorrow (FR12)

**Given** Telegram updates
**When** the check polls `getUpdates` with `offset = telegram_offset + 1`
**Then** a webhook is not set
**And** updates whose chat id is not `TELEGRAM_CHAT_ID` are ignored
**And** every `callback_query` is answered with `answerCallbackQuery`
**And** the design does not rely on updates older than 24h — Telegram drops them (FR13, FR21)

**Given** the setup CLI
**When** I look for a season command
**Then** CLI cannot flip season — Telegram is the only control (FR13)

### Story 2.5: Run a local check tick

As a bonsai owner,
I want to run one check on my machine,
So that I can see classify → alert → in/out → state write work before the job is unattended.

**Acceptance Criteria:**

**Given** valid `config/user.json` and StateStore defaults or `data/state.json`
**When** I run the check entrypoint locally
**Then** it loads config and state, and if `season` is `monitoring` it fetches and classifies
**And** it sends a frost alert only if that window is not in `alerted_windows`
**And** it then polls Telegram and applies in/out
**And** StateStore writes `data/state.json` (FR9, FR19 local slice)

**Given** risk is absent or `season` is `suspended`
**When** the local check runs
**Then** no frost alert is sent (FR9)

**Given** `season` is `suspended` on this local tick
**When** the entrypoint runs
**Then** it may still poll Telegram and write state
**And** GitHub Actions, git commit, and watchdog ping are out of scope (Epic 3)

**Given** secrets
**When** the local check talks to Telegram
**Then** bot token and chat id come from the environment, not source (NFR3)

## Epic 3: Trust the watch while the laptop is off

GitHub Actions runs the same loop unattended, fails over to MET Norway, commits state, and healthchecks.io warns if the job itself missed — without treating that warning as a frost alert.

### Story 3.1: Schedule the check on GitHub Actions

As a bonsai owner without an always-on home device,
I want the check to run on GitHub Actions every 6 hours,
So that a forecast can still be fetched and an alert sent while my laptop is off.

**Acceptance Criteria:**

**Given** the default branch of a public GitHub Free repo (or GitHub Pro if private)
**When** `.github/workflows/check.yml` is installed
**Then** it runs on `schedule` every 6 hours and on `workflow_dispatch`
**And** `concurrency` allows one in-flight run and cancels in-progress
**And** the runner is `ubuntu-latest` with `actions/checkout@v7` and `actions/setup-python@v7` pinned to Python 3.13 (FR14, AD-4, AD-10)

**Given** my laptop and phone are off
**When** the scheduled workflow runs
**Then** it executes the check entrypoint and can fetch a forecast and send an alert (FR14, NFR4)

**Given** workflow secrets
**When** the job starts
**Then** it reads `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `HEALTHCHECKS_PING_URL` from GitHub Secrets
**And** those values never appear in source (NFR3)

**Given** a multi-hour Actions delay
**When** a late run still executes
**Then** it is treated as a useful check
**And** window identity still comes from remaining time, not the cron name (NFR5, AD-5)

### Story 3.2: Fail over to MET Norway when Open-Meteo is down

As a bonsai owner,
I want the same check to keep classifying if Open-Meteo is unreachable,
So that a temporary primary outage does not skip a frost-risk check.

**Acceptance Criteria:**

**Given** Open-Meteo is called first with a 15s timeout
**When** the result is timeout, connect error, 5xx, 429, or empty/malformed hourly data
**Then** the same tick fetches MET Norway Locationforecast 2.0 `compact` and continues classification
**And** domain sees one series only — sources are never blended (FR15, AD-11)

**Given** Open-Meteo returns 4xx-bad-request
**When** failover is considered
**Then** MET Norway is not called (FR15)

**Given** a MET Norway request
**When** the adapter calls the API
**Then** it sends `altitude` = `elevation_m`, lat/lon to 4 decimals, and User-Agent `Frost-alert` plus the repo URL (FR16)

**Given** both sources fail while `monitoring`
**When** the tick ends
**Then** the process exits non-zero
**And** it does not treat the miss as a successful check (FR15)

### Story 3.3: Persist state and ping the watchdog

As a bonsai owner,
I want each successful check to save season/windows on the repo and report in to healthchecks.io,
So that the next run does not lose an in/out flip and I am warned if the job itself missed.

**Acceptance Criteria:**

**Given** a monitoring tick that obtained a forecast and finished classification
**When** the tick reaches persist
**Then** StateStore writes `data/state.json`
**And** the workflow commits that file with `permissions: contents: write`
**And** only then does Watchdog ping `HEALTHCHECKS_PING_URL` (FR19, AD-13)

**Given** dual-API miss or a crash before classification finishes
**When** the tick ends
**Then** it does not ping
**And** exit is non-zero (FR17)

**Given** classification succeeded but Telegram send failed
**When** the tick ends
**Then** the window is not marked
**And** the watchdog still pings (FR17, AD-6)

**Given** the check does not report in within the documented 6h period plus ~6h grace
**When** healthchecks.io notices
**Then** I receive a separate warning that is not a frost alert (FR18)
**And** period and grace are documented beside the ping-URL secret, not hardcoded (AD-10)

### Story 3.4: Keep the job healthy while the season is suspended

As a bonsai owner with plants already in,
I want the scheduled job to keep running without frost alerts,
So that a missed check is still visible and I can press `/out` without a laptop.

**Acceptance Criteria:**

**Given** `season` is `suspended`
**When** a scheduled tick runs
**Then** it skips the forecast fetch
**And** it still polls Telegram, writes state, commits `data/state.json`, and pings the watchdog (FR20)

**Given** `season` is `suspended`
**When** frost risk would have been present
**Then** no frost alert is sent (FR9, FR20)

**Given** `/out` arrives on a suspended tick
**When** poll applies `plants_out`
**Then** state becomes `monitoring` with cleared `event_date` and `alerted_windows`
**And** the following tick can alert again the same local day (FR12, FR20)

### Story 3.5: Document how to operate the watch

As a bonsai owner or a friend cloning the repo,
I want README instructions for secrets, healthchecks, and Android delivery,
So that I can run the $0 path without discovering a silent miss after a frost night.

**Acceptance Criteria:**

**Given** the README
**When** I follow the operator section
**Then** it tells me to put `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `HEALTHCHECKS_PING_URL` in GitHub Secrets
**And** it documents healthchecks.io period 6h and grace ~6h beside the ping-URL secret
**And** it says to leave GitHub Actions workflow-failure email on (NFR3, NFR14, AD-10)

**Given** I receive alerts on Android
**When** I read the README
**Then** it tells me to whitelist Telegram from battery optimization (NFR8)

**Given** repo visibility
**When** I read hosting notes
**Then** the default path is a public repo on GitHub Free (or Pro if private)
**And** it states that `schedule` runs only on the default branch (NFR9)
