# Epic 3 Context: Trust the watch while the laptop is off

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Run the same classify → alert → in/out → state loop unattended on GitHub Actions so frost warnings still go out with the laptop off. This epic adds MET Norway availability failover, a repo commit of `data/state.json`, and a healthchecks.io dead-man switch that warns if the job itself missed — never treating that warning as a frost alert.

## Stories

- Story 3.1: Schedule the check on GitHub Actions
- Story 3.2: Fail over to MET Norway when Open-Meteo is down
- Story 3.3: Persist state and ping the watchdog
- Story 3.4: Keep the job healthy while the season is suspended
- Story 3.5: Document how to operate the watch

## Requirements & Constraints

- Default host is a public GitHub Free repo (GitHub Pro if it must stay private). No personally-owned always-on device. Primary path stays $0 — no credit card for default weather, notify, or hosting. `schedule:` fires only on the default branch.
- One workflow every 6 hours plus `workflow_dispatch`. A late run is still a useful check; window identity comes from remaining time, not the cron name. The last (6h) window must not assume on-the-hour delivery. The host must survive months of seasonal idle without pausing or a keep-alive write.
- Secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `HEALTHCHECKS_PING_URL` live in GitHub Secrets only. Leave Actions workflow-failure email on as the $0 failure channel beside the watchdog.
- Open-Meteo first, 15s timeout. Fail over to MET Norway Locationforecast 2.0 `compact` on timeout, connect error, 5xx, 429, or empty/malformed hourly data. Do not fail over on 4xx-bad-request. Domain sees one series (UTC `t` + `temp_c`); never blend sources. Missing, unsorted, or non-hourly data is malformed. Both sources fail while monitoring: non-zero exit, not a successful check.
- MET Norway calls must send `altitude` = stored `elevation_m`, lat/lon to 4 decimals, and an identifying User-Agent (`Frost-alert` plus repo URL). Omitting elevation uses a coarse topography set and skews temperatures. Open-Meteo must not pass GMT hours through as local.
- Watchdog pings only after a forecast series was obtained (primary or fallback) and classification finished. Dual-API miss or crash: no ping, non-zero exit. Notifier failure still pings (and still does not mark the window). If the check does not report in within the documented 6h period plus ~6h grace, the user gets a separate warning that is not a frost alert. Period and grace are documented beside the ping-URL secret, not hardcoded.
- Full tick order: load config+state → if `monitoring`, fetch+classify → send a frost alert only if that window is not in `alerted_windows` and mark it only after a successful send → poll Telegram and apply in/out → write state → `git` commit `data/state.json` → watchdog ping.
- Suspended ticks skip the forecast, send no frost alerts, and still poll Telegram, write state, commit `data/state.json`, and ping. `/out` on a suspended tick becomes `monitoring` with cleared `event_date` and `alerted_windows` so the following tick can alert the same local day.
- Runtime stays CPython 3.13 (`.python-version` and `actions/setup-python@v7`; patch floats) + uv + stdlib HTTP. Unit tests use fake ports; no live network. Logs to stdout. Scheduled checks never re-geocode.

## Technical Decisions

- `.github/workflows/check.yml` is this epic (Story 3.1), not Epic 1. Install the real scheduled job here: `ubuntu-latest`, `actions/checkout@v7`, `actions/setup-python@v7` pinned to Python 3.13, `concurrency` one in-flight run cancel-in-progress, `permissions: contents: write` so the job can commit `data/state.json`. Do not use Actions cache or artifacts as the store. Setup remains a local CLI and never a concurrent writer.
- One workflow per tick. The git commit of `data/state.json` belongs to the workflow after StateStore writes; do not split that write across two owners. Commit-message wording is deferred.
- Adding MET Norway is a new ForecastSource adapter, not new domain rules. Failover is availability only — not a second opinion. Open-Meteo stays the default multi-model blend (no locale `models=` pin).
- healthchecks.io is a dead-man switch, not a second scheduler. Ping URL comes from the environment. User creates the free check and stores the URL in host secrets.
- GitHub Actions delay is chronic (hours, not minutes); design for degradation of precision, not silent total miss. Community reports (official docs silent) say Free `schedule` does not fire on private repos. A billing lock on a Free account can stop workflows with no pipeline-looking error — the watchdog is the detection path.
- v1 host is GitHub Actions only. AWS EventBridge Scheduler + Lambda is a documented non-default, not built. Do not use as primary: Supabase Cron (free projects pause after ~7 days idle), Vercel Hobby, Fly.io scheduled machines, cron-job.org/EasyCron as the only runner, Render Cron.
- Do not add `requests`/`httpx` or a MET/Open-Meteo SDK.

## UX & Interaction Patterns

No UX design contract exists. Surfaces here are the scheduled job, Telegram frost alerts already specified in Epic 2, a healthchecks.io miss warning (must not look like a frost alert), and operator README. README must cover: put the three secrets in GitHub Secrets; healthchecks.io period 6h and grace ~6h beside the ping-URL secret; leave Actions workflow-failure email on; whitelist Telegram from Android battery optimization; default path is a public GitHub Free repo (or Pro if private); `schedule` runs only on the default branch.

## Cross-Story Dependencies

- Epic 2 already wires the local tick (classify, Open-Meteo, Telegram, in/out, StateStore write). This epic reuses that loop; it does not re-specify classification, preview copy, or ack intake. Epic 1 supplies committed `config/user.json`; checks still must not geocode.
- 3.1 lands `check.yml` and runs the existing check entrypoint unattended. 3.2 adds MET Norway on Open-Meteo availability failure (Open-Meteo adapter is Epic 2). 3.3 adds the git commit then the watchdog ping, including ping-vs-no-ping rules. 3.4 extends the suspended path so skip-forecast still poll/write/commit/ping. 3.5 is operator README for secrets, watchdog, hosting, and Android delivery.
- 3.3’s no-ping path depends on 3.2’s dual-API miss. 3.4 depends on 3.1’s schedule and 3.3’s persist/ping. 3.5 documents the secrets and watchdog window those stories introduce.
