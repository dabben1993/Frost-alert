# Stack

Vendor and platform choices that implement the SPEC. Downstream treats these as locked unless an open question in SPEC.md forces a swap. File keys, tick order, and port layout live on the adopted architecture spine (AD-1..13).

## Hosting and scheduling

- **Primary:** GitHub Actions scheduled workflows on the default branch, every 6 hours, plus `workflow_dispatch`. One in-flight run; cancel-in-progress.
- **Repo visibility:** public on GitHub Free, or GitHub Pro if the repo must stay private. Community reports (not official docs) say Free `schedule` events do not fire on private repos.
- **Secrets:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `HEALTHCHECKS_PING_URL` live in GitHub Secrets, never in source.
- **Timezone:** IANA timezone on `schedule:` entries is supported; still design for multi-hour delay (see `failure-modes.md`).
- **Failure mail:** leave Actions' built-in workflow-failure email on; it is the $0 failure channel beside the watchdog.
- **Watchdog:** healthchecks.io dead-man switch. Period 6h, grace ~6h — document beside the ping-URL secret, do not hardcode. Ping only after a forecast series was obtained (primary or fallback) and classification finished. Dual-API miss or crash: no ping. Notifier failure still pings. A missed ping notifies the user (not a frost alert). Not a second scheduler.
- **Documented fallback host (not default):** AWS EventBridge Scheduler + Lambda — capable, Stockholm `eu-north-1` usable, but requires a credit card and the 2025 Free-plan auto-close gotcha.

**Do not use as primary scheduler:** Supabase Cron (free project auto-pauses after ~7 days of low DB activity — fights the seasonal-off design); Vercel Hobby (once/day, ±59 min); Fly.io scheduled machines (no free tier for new accounts; fixed cadences only); cron-job.org or EasyCron as the *only* runner (trigger-only; EasyCron free plan needs monthly manual renewal); Render Cron ($1/mo minimum).

## Weather

- **Primary:** Open-Meteo Forecast API, **default multi-model blend** (no Sweden-only `models=` pin). No key, no card. Hourly data out to 16 days. Free-tier headroom (600/min, 10k/day, 300k/month) far exceeds single-location hobby volume. No SLA; documented multi-hour 502 outages in 2026. Any configured location must get a forecast; v1 is validated in Sweden/Nordics. Accuracy is the tunable safety-margin threshold, not a Nordic-only model pin.
- **Geocoding:** Open-Meteo Geocoding API (same no-key path). Setup accepts city name or postal code (coordinates optional), shows the resolved place, caches lat/long plus elevation. Checks never re-geocode.
- **Fallback:** MET Norway Locationforecast 2.0 when Open-Meteo is unreachable (timeout, connect error, 5xx, 429, or empty/malformed hourly — not 4xx-bad-request). No key. Lat/long only. **Must pass elevation explicitly** — omitting it falls back to a coarse 1 km topography set and has produced measurably wrong temperatures in the field. Rate ceiling 20 req/s per app. Sweden is in MET's Nordic priority region. Identifying User-Agent required (`Frost-alert` plus repo URL).
- **Out:** OpenWeatherMap (no-card tier is 3-hour steps; hourly needs One Call 3.0 + a card). SMHI not primary or sole source (pmp3g retired 2026-03-31; no official SDK; lat/long only).

## Notifications

- **Primary:** Telegram Bot API. $0 at hobby volume (~1 msg/s/chat). Season flip: commands `/in` `/out` and inline-keyboard callback data `plants_in` / `plants_out`. Bot must call `answerCallbackQuery`. Secrets: bot token + chat id. Ignore updates whose chat id is not `TELEGRAM_CHAT_ID`.
- **Ack intake:** cron-polled `getUpdates` (no always-on webhook). Verified 2026-09-12: a later process received `callback_query` after the sender had exited. Telegram retains updates up to 24h; a webhook must not be set or polling is disabled.
- **Runner-up:** Pushover. $4.99 one-time per platform; 10k msgs/month free per account. Emergency Priority (`priority=2`) + `callback` URL is server-mediated ack (Pushover POSTs your endpoint when the user acknowledges).
- **Optional secondary (not required for v1 success):** ntfy.sh (`http` action button; public server 250 msgs/day free; FCM timing caveat on the Play build) or email + magic link (GET renders confirm page, POST flips state — never consume the token on GET).
- **Out as primary:** WhatsApp Business/Cloud API — ToS forbids personal, family, or household use; template gating; ~90-day test-number churn; per-message cost from 2026-10-01.

## Language / runtime

- **Locked:** CPython 3.13 (`.python-version` and `actions/setup-python@v7`; patch floats) + uv + stdlib HTTP. No `requests`/`httpx` unless a later port cannot work without them. No web framework.
- Cloudflare/Deno-only runtimes are not required and would force a rewrite of trigger plumbing if hosting later moves.
