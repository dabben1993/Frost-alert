# Epic 2 Context: Get escalating frost warnings I can silence

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

A local check that classifies frost risk from any upcoming forecast hour, sends one 24h then 12h then 6h Telegram warning per frost event (readable from the lock-screen preview), and lets the owner suspend or resume the season from Telegram without editing `state.json` or using the setup CLI. This epic proves classify → alert → in/out → state write on a laptop; unattended schedule, MET Norway failover, git commit, and watchdog ping belong to Epic 3.

## Stories

- Story 2.1: Classify frost risk and remaining-time window
- Story 2.2: Fetch hourly forecast from Open-Meteo
- Story 2.3: Send a preview-first Telegram frost alert
- Story 2.4: Flip season from Telegram
- Story 2.5: Run a local check tick

## Requirements & Constraints

- Frost risk is present when any upcoming **forecast** hour with `0 < remaining ≤ 30h` is at or below stored `threshold_c`; absent when all such hours are above. Never use live current temperature. Never restrict to a night-only window — a daytime crossing counts.
- Lead time is `first_at_or_below − now`. Map remaining > 12h → window 24, remaining > 6h → window 12, remaining > 0 → window 6. Cadence is 24 then 12 then 6 with no further steps. Each window fires at most once per frost event. A crossing outside the 30h lookahead does not count.
- Frost event identity is the local calendar date (config IANA timezone) of that first at-or-below hour. Same-day forecast revision does not reset windows. When that local date ends, the next crossing is a new event. Monitoring keeps evaluating every tick until plants-in.
- No frost alerts when risk is absent or season is `suspended`. Mark a window in `alerted_windows` only after a successful send; a notifier failure must not mark it.
- Notification preview: one glance — emoji, frost risk coming, roughly 24h/12h/6h. No forecast table, location string, or ack how-to. Opened message adds configured place, first-crossing temperature in the user’s `scale`, when that crossing is expected, the user’s threshold, and an ack control (`/in` or `plants_in`). Exact sentence strings stay unlocked; keep the preview-vs-opened split.
- `/in` or `plants_in` sets season to `suspended` and leaves `event_date` and `alerted_windows` unchanged. `/out` or `plants_out` sets `monitoring` and clears both so a same-day resume can warn again. Repeat commands are idempotent. Domain has only `monitoring` and `suspended` — no snooze-until-tomorrow.
- Season flip is Telegram-only (commands `/in` `/out` and callback data `plants_in` / `plants_out`). Always `answerCallbackQuery`. Ignore updates whose chat id is not `TELEGRAM_CHAT_ID`. Setup CLI must not flip season.
- Ack intake is cron-polled `getUpdates` with `offset = telegram_offset + 1`. Do not set a webhook (`getUpdates` and webhook cannot be used together). Telegram drops updates older than 24h — do not design around older acks.
- Local tick order: load config+state → if `monitoring`, fetch+classify → send a frost alert only if that window is not already in `alerted_windows` (mark only after success) → poll Telegram and apply domain in/out → StateStore writes `data/state.json`. Suspended local ticks skip forecast, still may poll and write state, and send no frost alert. GitHub Actions, git commit, and watchdog ping are out of scope.
- Open-Meteo Forecast is the only weather source in this epic. Domain receives one ascending series of `{t, temp_c}` with `t` as UTC ISO-8601. Do not pass GMT hours through as local. Missing, unsorted, or non-hourly data is malformed — do not hand domain a blended or partial series. Use the default multi-model blend; do not pin `models=` to a locale. Forecast calls use stored lat/lon (and timezone as needed); never re-geocode.
- Domain and JSON store Celsius; `scale` is display only (convert first-crossing temp and threshold for the opened message). Bot token and chat id come from the environment, never source. HTTP is stdlib only. Unit tests use fake ports; no live network.

## Technical Decisions

- Domain owns classification, remaining-time windows, and season. Adapters implement ports; they report intents and never write `state.json`. Entrypoints only wire. Ports in play: ForecastSource, Notifier, AckInbox, ConfigStore, StateStore, Clock.
- Window identity is frost event + window number, not a cron or job name. A late run still maps from remaining time. “Keep alerting until /in” means new events, not re-sending an already-marked window every tick.
- Open-Meteo Forecast is public and keyless. Do not add `requests`/`httpx` or a vendor SDK. MET Norway failover is Epic 3; do not blend two sources as a second opinion.
- Telegram Bot API 10.3. Ack path is an inline-keyboard `callback_query`; the client spinner clears only after `answerCallbackQuery`. Polling is the chosen intake so this epic needs no always-on HTTPS receiver.
- JSON on disk. Instants UTC ISO-8601. Event key local `YYYY-MM-DD`. Logs to stdout. ntfy, email, and Pushover stay deferred.

## UX & Interaction Patterns

No UX design contract exists. Surfaces here are Telegram messages plus a local check command (no custom app). Preview must be understandable without opening the chat. The opened frost alert is where facts and the plants-in control live. Season resume is the same chat (`/out` or `plants_out`), not a laptop CLI and not a hand-edit of `state.json`. Watchdog-miss copy is not a frost alert and is out of scope.

## Cross-Story Dependencies

- Epic 1 must already supply committed `config/user.json` and StateStore defaults. Check paths must not geocode.
- 2.1 is domain-only (series + threshold + clock in, risk/window/event out). 2.2 is the Open-Meteo adapter that feeds that series. 2.3 sends and marks-after-success. 2.4 polls and applies in/out. 2.5 wires the local tick from those pieces.
- Epic 3 reuses this same loop unattended: schedule, MET Norway on availability failure, commit `data/state.json`, then watchdog ping. Do not implement those here.
