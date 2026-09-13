# Failure modes

Load-bearing risks that bend design. None of the $0 choices has an SLA suitable for a frost alert on its own.

## Scheduler

- **GitHub Actions delay is chronic and worsening.** Measured average delay rose from ~1h40m (2025) to over 4h30m (June 2026) across several UTC offsets; "pick an odd minute" does not reliably fix it. A late run still appears as ran — degradation of precision, not a silent total miss. Escalation (24h → 12h → 6h) is what makes this tolerable; the last window must not assume on-the-hour delivery. Healthchecks.io is the miss detector.
- **Private-repo `schedule` on Free** is reported disabled (community-corroborated; official docs silent). Default path is a public repo with secrets in GitHub Secrets.
- **Billing lock** on a Free account can stop workflows with no pipeline-looking error (stale $0 card-verification hold). Watchdog is the detection path.
- **Default-branch-only:** `schedule:` on a non-default branch never fires.
- **Supabase free auto-pause** (~7 days low DB activity) is why Supabase Cron is not the host: this project is designed to go quiet for months.

## Forecast accuracy

- **No Sweden-specific overnight-minimum benchmark exists** for any provider (two research rounds, EN/SV, institutional and academic). Do not paper over that by pinning a Nordic-only Open-Meteo model. Tie-breaker is operational stability plus the user-tunable safety margin.
- **Radiative (clear, calm) nights are structurally hard** for every NWP model; MET Norway documented a MEPS case (Dagali, 2024-01-15/16) forecasting about −20°C against an observed −34°C. This is why the threshold defaults above 0°C and stays user-tunable. The 24h check is a coarse early warning, not a degree-precise prediction; shorter windows tighten urgency, not claimed precision.
- **MET Norway elevation omission** produces wrong lapse-rate adjustment. Fallback calls must send elevation.

## Forecast availability

- **Open-Meteo** had three documented multi-hour 502 outages on the free tier in 2026, no SLA. CAP-6 fallback to MET Norway exists to cover this, not as a second opinion for accuracy.
- **Ping-before-success hides a dual-API miss.** Watchdog pings only after a forecast series was obtained and classification finished. A crash or both sources failing must not look healthy. A Telegram send failure still pings — that is not a missed job.

## Notification delivery

- **No candidate was end-to-end benchmarked** under Android Doze/OEM battery optimization. Delays attributed to generic Android, not Telegram-specific defects. Highest-leverage mitigation: unrestricted battery usage for the receiver app.
- **Telegram `getUpdates` for acks** works without a webhook (PoC 2026-09-12). Failure modes left: a webhook would disable polling; updates older than 24h are dropped; `answerCallbackQuery` is still required to clear the client spinner. Callback data is `plants_in` / `plants_out`; commands are `/in` / `/out`.
- **ntfy Play-store path uses FCM**; the maintainer calls timeliness "not great." Instant-delivery / F-Droid persistent connection can itself be killed by Doze. Reason ntfy is optional secondary, not primary.
- **Email** can lag up to ~15 minutes on Gmail Android sync; Outlook Safe Links can prefetch a naive magic-link GET and consume the token. If email is added, GET must render an inert confirm page and only POST may flip state.

## Seasonal idle

- Long off-season (trees in, or summer) is expected. The host must survive months of no frost-risk alerts without pausing or requiring a keep-alive write. GitHub Actions fits; Supabase Cron does not.
