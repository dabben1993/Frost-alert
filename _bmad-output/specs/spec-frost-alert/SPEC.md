---
id: SPEC-frost-alert
companions:
  - stack.md
  - failure-modes.md
  - state-machines.md
  - alert-copy.md
  - ../../planning-artifacts/architecture/architecture-Frost-alert-2026-09-12/ARCHITECTURE-SPINE.md
sources:
  - ../../forge/frost-alert/forged-idea.md
  - ../../planning-artifacts/research/technical-weather-forecast-api-for-frost-alert-2026-09-12/research.md
  - ../../planning-artifacts/research/technical-notification-channel-selection-frost-ale-2026-09-12/research.md
  - ../../planning-artifacts/research/technical-frost-alert-hosting-and-scheduling-platf-2026-09-12/research.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Frost Alert for overwintering bonsai

## Why

**A pain to solve.** Outdoor bonsai must be moved to overwintering *before* a frost night, not after a live thermometer crosses freezing. The owner is in Sweden (first build-and-test locale) and has no always-on home device; a friend elsewhere should be able to clone the repo and configure their own location without touching source. The work exists so that person gets enough lead time to move trees, on a zero-dollar unattended path, without building an app or running a multi-tenant service.

## Capabilities

- **CAP-1**
  - **intent:** A user can set location, temperature scale, and alert threshold through a setup flow so they (or a friend after cloning) never edit source.
  - **success:** After setup, scheduled checks use the stored location, scale, and threshold; changing any of those is done only by re-running setup or editing config, not source.

- **CAP-2**
  - **intent:** The system can detect that a forecast hour at the configured location will meet or fall below the user's threshold far enough ahead that plants can still be moved.
  - **success:** Given a forecast with any upcoming hour within the remaining-time lookahead at or below the configured threshold, the next check classifies frost risk as present; given all hours above threshold, it does not.

- **CAP-3**
  - **intent:** The user receives an early awareness alert and, if they have not confirmed overwintering, further alerts at shorter remaining windows as the cold approaches.
  - **success:** An unacknowledged frost-risk event produces alerts at ~24h, ~12h, and ~6h remaining; no alerts fire when risk is absent or the season is suspended; each frost alert is readable from the notification preview alone (see `alert-copy.md`).

- **CAP-4**
  - **intent:** The user can confirm plants are in overwintering and thereby stop all frost alerts until they turn the automation back on.
  - **success:** After a valid acknowledgment via the notification channel's two-way control, subsequent checks send no frost alerts until the user explicitly re-enables monitoring.

- **CAP-5**
  - **intent:** Checks and alerts continue whether or not the owner's laptop or phone is on.
  - **success:** With no personally-owned always-on device available, a scheduled check still fetches a forecast and can send an alert.

- **CAP-6**
  - **intent:** A temporary outage of the primary weather API does not skip a frost-risk check.
  - **success:** When the primary source errors or is unreachable, the same check obtains hourly data from the fallback source and continues classification.

- **CAP-7**
  - **intent:** The user learns if the scheduled checker failed to run, rather than discovering it after a frost night.
  - **success:** If the primary check does not report in within its expected window, the user receives a separate warning that is not itself a frost alert.

## Constraints

- Single-user personal automation: no accounts, no multi-tenant service, no custody of other people's keys; sharing is clone plus own config.
- Primary-path cost is zero dollars; no credit card required for the weather, notification, or hosting services used in the default build.
- Do not build or maintain a custom native app; installing an existing receiver app is allowed.
- Trigger on any forecast hour at or below the user's threshold, never on live current temperature, never on a night-only window.
- Lead-time window is remaining time to the first at-or-below hour, not the scheduler job name; each window fires at most once per frost event.
- Acknowledgment is a seasonal on/off, not a nightly snooze; in/out may repeat in one autumn and each flip is an explicit user action.
- Threshold is user-set and defaults above 0°C (starting default 3°C in the user's scale) because forecast error and radiative frost make pot/soil colder than official air temperature.
- Internals stay location-agnostic; Sweden is the first locale to build and test against, not a hardcoded location.
- Must not depend on a personally-owned always-on device.
- Primary scheduler must not be trusted alone for the last time-critical check; an independent healthchecks.io dead-man switch is required (ping only after forecast+classification succeeded; a missed ping warns the user). See `stack.md`, `failure-modes.md`, and the architecture spine (AD-6, AD-13).
- Secrets live in host secrets, never in source.
- Location is geocoded once at setup (city name or postal code; coordinates optional), confirmed as a resolved place, and cached as coordinates plus elevation; scheduled checks do not re-geocode.
- Free-tier schedulers have no SLA; the design must tolerate multi-hour delay and still treat a late run as a useful check.
- Document that the receiver app must be whitelisted from Android battery optimization.
- Build decisions AD-1..13 in the adopted architecture spine are binding; do not invent a second classification, season, or store.

## Non-goals

- Hosted multi-user product, accounts, or handling other people's data/keys.
- Custom Android or macOS app.
- Live-temperature triggering.
- Night-only (e.g. 20:00–08:00) classification that ignores daytime crossings.
- Nightly in/out or "snooze tonight" acknowledgment.
- Hardcoded 0°C threshold.
- WhatsApp Business/Cloud API as the primary or default channel.
- SMHI as the primary or sole forecast source.
- OpenWeatherMap (hourly data requires a credit card).
- Home server, Raspberry Pi, or any personal always-on host.
- SMS.
- Multi-location fleet or dashboard in one deployment (one location per clone).
- EU data-residency pinning as a hard requirement.
- A personal forecast-accuracy research log or ML post-processing (possible later; not this build).

## Success signal

A Sweden-configured instance, with the owner's laptop off, sends a Telegram frost warning when any forecast hour is at or below the user's threshold about 24 hours out — understandable from the notification preview alone, with detail in the opened message — offers an in-message acknowledgment that suspends all further frost alerts until re-enabled, re-alerts at ~12h and ~6h if unacknowledged, and separately warns the user if the checker itself did not run.

## Assumptions

- A public GitHub repo is acceptable provided secrets stay in GitHub Secrets.
- EU data residency is a nice-to-have, not a hard gate.
- GDPR household-use exemption applies to this single-hobbyist automation (not legally confirmed).
- The user will install Telegram (or the chosen receiver app) on the corporate Android phone and whitelist it from battery optimization.
- One configured location per clone/deployment.
- Default temperature scale is Celsius for the Sweden-first build; scale remains user-selectable.
- v1 requires Telegram only; ntfy and email are optional secondary paths, not required for first success.
- User will create a free healthchecks.io check and put the ping URL in host secrets.
