# Forged Idea: Frost Alert for Overwintering Bonsai

## What it is

A personal automation that warns you (and, with easy reconfiguration, anyone else) before local temperature threatens outdoor plants, so trees get moved to overwintering in time.

## Context for this iteration

- **Primary user is based in Sweden.** First build-and-test locale. Internals stay location-agnostic so a friend elsewhere can set their own location — Sweden is the concrete case to validate against, not a hardcoded forecast mode.

## Locked decisions

- **Scope**: Single-user personal automation, not a hosted multi-tenant service. No accounts, no handling other people's keys/data. Sharing = cloning a repo/config, not signing up for a service.
- **Config, not code**: Location, temperature scale, and alert threshold are set through an intuitive setup flow (e.g. interactive CLI wizard or simple config UI). Never requires editing source code.
- **"No app" constraint, correctly scoped**: Rules out building/maintaining a custom native app (Android/macOS). Installing an existing third-party app (Telegram) to receive alerts is the path.
- **Trigger model**: Forecast-based, not live-current-temperature-based.
- **Escalating check cadence**: 24h (awareness) → 12h → 6h if still unacknowledged. No further steps.
- **Acknowledgment = seasonal toggle, not nightly snooze**: Confirming "plants are in overwintering" (Telegram inline button) suspends ALL frost alerts until the user manually turns it back on (e.g. in spring). Ack intake is cron-polled Telegram `getUpdates` — no always-on webhook (PoC 2026-09-12).
- **Alert threshold is user-set, not hardcoded to 0°C**: Default 3°C in the user's scale, tunable down once they learn their microclimate.
- **Alert copy**: Notification preview must be immediately understandable and uses emojis; the opened message carries location, forecast low, timing, threshold, and the ack control. Exact strings are not locked.
- **Location input**: City name or postal code (coordinates optional). Geocode once at setup, show the resolved place, cache lat/long plus elevation. Checks never re-geocode.
- **Hosting**: GitHub Actions scheduled workflows (public repo on Free, or Pro if private). Must not depend on a personal always-on device. Cost target $0; no credit card on the default path. Independent **healthchecks.io** dead-man switch is required.
- **Weather**: Open-Meteo default blend (primary); MET Norway Locationforecast fallback on outage (must pass elevation). Do not pin a Sweden-only model. Do not use SMHI as primary or OpenWeatherMap.
- **Notifications**: Telegram Bot API primary. WhatsApp Business/Cloud API is not the channel. Email/ntfy optional later, not v1.

## Rejected / narrowed options (and why)

- **Hosted multi-user product** — rejected. Would require accounts and handling other users' data/keys; explicitly not wanted.
- **Native Android/macOS app** — rejected as a delivery mechanism to build.
- **Trigger on live current temperature** — rejected. Gives no lead time to physically move trees.
- **Nightly snooze model for acknowledgment** — rejected; bonsai overwintering is one seasonal move, not nightly.
- **Hardcoded 0°C threshold** — rejected. Real risk is at/above 0°C forecast due to forecast error and radiative frost.

## Weak points that survived (carry forward, don't ignore)

- No Sweden-specific overnight-minimum accuracy benchmark exists for any provider. Reviewer-facing accuracy is the tunable safety-margin threshold, not a model pin.
- Free schedulers have no SLA; GitHub Actions can run hours late. Escalation (24h → 12h → 6h) plus the healthchecks.io watchdog are the mitigations.
- Android OEM battery optimization can delay Telegram. Document unrestricted battery usage for the app.

## Research (completed 2026-09-12)

Three technical research reports were run and absorbed into `_bmad-output/specs/spec-frost-alert/`:

- Weather API: `_bmad-output/planning-artifacts/research/technical-weather-forecast-api-for-frost-alert-2026-09-12/research.md`
- Notification channel: `_bmad-output/planning-artifacts/research/technical-notification-channel-selection-frost-ale-2026-09-12/research.md`
- Hosting / scheduling: `_bmad-output/planning-artifacts/research/technical-frost-alert-hosting-and-scheduling-platf-2026-09-12/research.md`

## Suggested next steps

- Spec is the build contract: `_bmad-output/specs/spec-frost-alert/`.
- Next planning step is architecture (`bmad-architecture`), not more research. A PRD is optional for this hobby/solo automation — it would largely restate the spec.
