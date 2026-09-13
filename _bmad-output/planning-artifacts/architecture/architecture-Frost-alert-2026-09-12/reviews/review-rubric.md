# Rubric-walker review — Architecture Spine Finalize

- **Spine:** `_bmad-output/planning-artifacts/architecture/architecture-Frost-alert-2026-09-12/ARCHITECTURE-SPINE.md`
- **Lens:** good-spine checklist only (feature altitude; level below = epics / stories / coding agents)
- **Date:** 2026-09-13
- **Repo context:** greenfield + `scripts/poc-telegram-getupdates.py` (Python stdlib HTTP Telegram probe)
- **Parent spine:** none

## Verdict

**PASS WITH GAPS.** The spine is a real build-substrate: ports-and-adapters, CAP-1..7 mapped, v1 host/schedule/watchdog/secrets decided, and most AD Rules would stop the obvious forks. It is not yet safe to split independent units: four parallel-build seams are still unbounded (AD-8 keep-alerting vs already-alerted windows, `/out` vs `alerted_windows`, ForecastSource series shape, and git write-back / ping-vs-commit). Those are autofix-or-discuss items, not a rewrite.

Disposition legend: **autofix** (tighten the spine) · **discuss** (needs a product call) · **defer** (name it under Deferred) · **ignore**.

---

## Checklist

### 1. Fixes the real divergence points for the level below, and misses none

**Partial pass.** Independently built setup / check / Telegram / forecast-adapter units would otherwise fork on paradigm, runtime, file store, single-writer tick, remaining-time windows, watchdog ping-on-success, Celsius-on-disk, event-date identity, Telegram-only season flip, 6h cadence, Open-Meteo-then-MET failover, and package layout. Those are bound (AD-1..12 + conventions).

Missed forks that two coding agents *would* choose incompatibly:

| Seam | Why it is a real fork |
| --- | --- |
| ForecastSource return shape | CAP-6 is two adapters feeding one domain; “one hourly series” does not pin `(utc_instant, temp_c)` |
| `check.yml` persist | Who commits `data/state.json`, with which token/permissions, and whether a failed commit still pings |
| Monitoring after `/out` | Whether `alerted_windows` / `event_date` reset when season returns to monitoring |
| AD-8 vs AD-5 | “Keeps alerting until `/in`” vs already-alerted windows / spec “no further steps” after 6h |
| Ack poll filter | Commands `/in` `/out` plus callbacks; the PoC filters `callback_query` only |

Smaller misses (cron IANA vs UTC, MET `compact` vs `complete`, Open-Meteo `temperature_2m`, Clock-only `now`, CI workflow, `pyproject` build backend) are real but can be Deferred if not bound. They are currently **silent**, which fails the “named under Deferred” half of the altitude test.

### 2. Every AD’s Rule is enforceable and actually prevents its stated divergence

| AD | Enforceable? | Prevents the stated divergence? |
| --- | --- | --- |
| AD-1 | Yes (import/layout) | Yes |
| AD-2 | Yes (`.python-version`, no framework) | Yes. The `requests`/`httpx` “unless a later port cannot work without them” escape is slightly soft against MET docs that sample `requests`. |
| AD-3 | Yes | Yes (config vs state vs secrets vs cache) |
| AD-4 | Mostly | Single workflow + `concurrency` cancel-in-progress stops two jobs. Sequence omits ping and persist-success, so it does not fully prevent a “healthy” tick that lost the in/out write. |
| AD-5 | Yes (formula + mapping + event+window key) | Yes for late GHA sending the wrong 24/12/6 step |
| AD-6 | Yes for dual-API miss vs Telegram outage | Does not say ping is after **state persist**; a crash after ping + failed `git commit` still looks healthy |
| AD-7 | Yes | Yes |
| AD-8 | **No** | Prevents “cold snap goes silent after first 6h” but the Rule (“Monitoring keeps alerting until `/in`”) can be read as re-send 6h every tick. That neither matches AD-5 already-alerted keys nor the spec’s “no further steps.” |
| AD-9 | Yes for channel/commands/no-webhook | Does not require `deleteWebhook` (PoC does). `allowed_updates` unbounded. |
| AD-10 | Mostly | 6h schedule + dispatch + documented HC period/grace. “Leave Actions failure email on” is an account setting, not a repo rule. |
| AD-11 | Mostly | Failover set is clear. “No fallback on 4xx-bad-request” is ambiguous vs other 4xx (408/403) given 429 *does* fallback. MET `compact`/`complete`/`classic` unbound. |
| AD-12 | Yes | Yes for script-pile vs package |

### 3. Nothing under Deferred could let two units diverge

**Pass for the listed items; fail for the silent ones.**

Listed Deferred is safe to leave down:

- Exact frost-alert sentences — `alert-copy.md` owns the split; unlocked strings will not break wiring.
- Extra pytest plugins — not a product seam.
- `data/state.json` commit *message* — cosmetic.
- ntfy / email / Pushover — AD-9 already makes Telegram the season flip; “not required for v1” is close enough to “don’t build,” though “must not add a second Notifier in v1” would be sharper.
- Open-Meteo `models=` pin — spec already forbids; duplicating as Deferred is fine.
- AWS EventBridge + Lambda — explicit non-default, not built.

**Not in Deferred, not decided** (these *can* let two units diverge): ForecastSource DTO; git write-back; `/out` vs `alerted_windows`; ping vs commit order; cron timezone; MET 2.0 flavor; CI vs `check.yml`; Clock as the only `now`.

### 4. Named tech is verified-current (or dated)

**Pass.** Spot-checked 2026-09-13:

| Named | Spine | Check |
| --- | --- | --- |
| CPython 3.13 | 3.13, patch floats | Latest *feature* series is 3.14.7 (2026-08-05); 3.13.15 is still bugfix (EoL 2029-10). `actions/setup-python@v7` README still examples `3.13`. Intentional lag; should be treated as a pin, not “latest.” Low. |
| uv 0.12 | 0.12 | Current line 0.12.13 (2026-09-10). |
| actions/checkout | v7 | Current major (v7.0.1, 2026-07-20). |
| actions/setup-python | v7 | Current major (v7.0.0, 2026-07-20). |
| ubuntu-latest | floating runner | Acceptable seed. |
| Open-Meteo Forecast + Geocoding | public no-key 2026-09 | Still no-key non-commercial JSON APIs. |
| MET Norway Locationforecast | 2.0 | Current; identifying User-Agent still 403-enforced. Elevation + 4-decimal lat/lon match current HowTO. Flavor (`compact` vs `complete`) unnamed. |
| Telegram Bot API | 2026-09 | Latest is **10.3** (2026-08-24). Month-dated is allowed; stdlib HTTP does not need a client-lib pin. |
| healthchecks.io ping API | 2026-09 | Current (`hc-ping.com` UUID/slug). |

No unverifiable product names. No undated “latest” claims except the CPython 3.13 pin (still a maintained line).

### 5. Ratifies rather than contradicts brownfield

**Pass, with one PoC trap.** This is greenfield. The only code to ratify is `scripts/poc-telegram-getupdates.py`.

Ratified: CPython, stdlib `urllib` HTTP, Bot API `getUpdates` (no always-on webhook), `answerCallbackQuery`, JSON state, process-exit between send and poll.

Intentionally superseded (acceptable for a probe, not a product): callback_data `ack_overwinter` → `plants_in` / `plants_out`; temp PoC state path vs `data/state.json`.

Trap: PoC `getUpdates(..., allowed_updates=["callback_query"])` would drop `/in` `/out` messages. AD-9 requires both and does not forbid copying that filter. Also PoC `deleteWebhook` is not in the Rule.

### 6. Covers the spec’s CAP-1..7

**Pass.** Frontmatter `binds` and the capability map cover all seven. Placement is right: setup+ConfigStore, domain+ForecastSource, Notifier+copy companion, AckInbox+season, `check.yml`, failover adapters, Watchdog.

Known spec drift (any-hour classification vs SPEC “overnight low”; ping-after-success vs `state-machines.md` ping-first) is a product decision already in the spine, not a dropped capability. CAP-2/3/7 still land.

Residual coverage holes are the same unbounded seams as §1 (resume after `/out`, persist/ping, forecast DTO), not missing CAPs.

### 7. No parent spine

**Pass.** Feature-altitude first spine. No Inherited Invariants. No AD that could weaken a parent.

### 8. Every owned dimension is decided, deferred, or an open question

**Partial pass — operational envelope is mostly present, not fully closed.**

| Dimension | Status |
| --- | --- |
| Paradigm / boundaries / deps | Decided (AD-1, diagram) |
| Runtime / HTTP / no server | Decided (AD-2) |
| Shared data / secrets | Decided (AD-3, conventions) |
| State mutation / single writer | Decided in intent (AD-4); persist *mechanism* silent |
| Classification / windows / season | Decided (AD-5, 7, 8, 9) with AD-8 wording hole |
| Deployment | Decided: GHA only, default-branch schedule, public Free (or Pro if private), no personal host, `ubuntu-latest` |
| Environments | Implicit (local setup CLI vs scheduled check). Not named; acceptable if Deferred as “no staging env in v1.” Currently silent. |
| Infra / providers | Decided: Open-Meteo, MET Norway 2.0, Telegram, healthchecks.io; AWS host Deferred |
| Operations | Mostly decided: 6h tick, dispatch, concurrency, HC 6h+~6h (documented, not hardcoded), Actions failure email, stdout logs, Android-battery README. Git write-back, CI, cron timezone silent. |
| Open questions | None listed. Gaps were omitted rather than queued. |

A whole dimension is **not** missing. The failure is leftover operational seams treated as “seed the code will own” while two agents still have to invent them.

---

## Findings

### High

1. **AD-8 Rule does not prevent its stated divergence (and fights AD-5).**
   - **Evidence:** AD-8 Prevents “a cold snap going silent after the first 6h”; Rule says “Monitoring keeps alerting until Telegram `/in`.” AD-5 keys already-alerted by event+window; spec companion says no steps after 6h.
   - **Fork:** Agent A re-sends window-6 every tick until ack. Agent B stays silent until the next local date’s crossing (memlog intent).
   - **Disposition: autofix.** Spell the Rule: same `event_date` fires each of 24/12/6 at most once; after 6h on that date, no more frost alerts until a **new** local-date crossing (new event). `/in` is what stops *future* events, not what authorizes 6h spam.

2. **`/out` / `plants_out` vs `alerted_windows` / `event_date` is unbound.**
   - **Evidence:** AD-9 allows repeat in/out in one autumn. Conventions list the keys; no Rule says what resume does to them.
   - **Fork:** Same-day `/out` either re-fires 24/12/6 or stays quiet because windows already fired.
   - **Disposition: discuss** (product: re-alert on resume vs wait for next date), then **autofix** the Rule. Until then it is not Deferred either.

3. **ForecastSource series shape is the CAP-6 seam and is not pinned.**
   - **Evidence:** AD-11 “Domain sees one hourly series.” No port contract (UTC instants, °C, field).
   - **Fork:** Open-Meteo adapter and MET adapter (or domain) invent different dicts/timezones/`temperature_2m` vs apparent.
   - **Disposition: autofix.** Bind: adapters normalize to a UTC `(instant, temp_c)` sequence; domain never sees vendor JSON.

4. **State persist + watchdog ping order and git write-back are operationally silent.**
   - **Evidence:** AD-4 sequence is classify → maybe alert → poll → write state once (no ping, no git). AD-3/seed say the workflow commits `data/state.json`. AD-6 pings after forecast+classification; notifier failure still pings. No `permissions` / `GITHUB_TOKEN` vs PAT.
   - **Fork:** ping-then-failed-commit looks healthy (CAP-7 false negative) and drops in/out; two `check.yml` stories pick PAT vs `contents: write`.
   - **Disposition: autofix.** One writer: `check.yml` commits only `data/state.json` with `GITHUB_TOKEN` + `permissions: contents: write` (no PAT). Ping only after classification **and** successful persist; persist/commit failure → non-zero, no ping. Telegram send failure still pings if persist succeeded.

### Medium

5. **Ack intake can copy the PoC and drop commands.**
   - PoC uses `allowed_updates=["callback_query"]`. AD-9 requires `/in` `/out` **and** callbacks, and “a webhook must not be set,” but does not require `deleteWebhook` or both update types.
   - **Disposition: autofix.** Poll `message` + `callback_query`; setup or first check `deleteWebhook` if a URL is set.

6. **AD-11 “4xx-bad-request” and MET 2.0 flavor are fuzzy.**
   - 429 fallbacks; other 4xx unclear. `compact` vs `complete` vs `classic` unbound.
   - **Disposition: autofix** (fallback on timeout/connect/5xx/429/empty-malformed only; no fallback on any other 4xx) **and defer** endpoint flavor if you will not pin `compact`.

7. **Schedule timezone is an owned ops detail left silent.**
   - AD-10 “every 6 hours” vs spec IANA-on-`schedule:`. Remaining-time mapping makes the exact offset non-load-bearing.
   - **Disposition: defer** (“cron offset/timezone is not load-bearing; remaining-time mapping owns the window”).

### Low

8. **CPython 3.13 is a maintained pin, not the current feature series (3.14.7).** Safe if left as-is; date or note “not 3.14” in Stack if you want the checklist’s “or dated” clause explicit. **ignore** or one-line Stack note.

9. **AD-2 `requests`/`httpx` escape** vs MET samples. **autofix:** delete the escape; stdlib HTTP is the Rule.

10. **v1 second Notifier** (“not required” vs “must not”). **autofix** wording in Deferred.

11. **CI workflow, pyproject backend, Clock-only `now`, Open-Meteo hourly variable name** — silent. **defer** each in one line.

12. **Actions failure-email** is not enforceable in-repo. **ignore** as operator README (already have a docs convention).

13. **PoC callback_data `ack_overwinter`** superseded by `plants_in`/`plants_out`. **ignore** (probe, not brownfield lock).

---

## Gate summary (for parent)

- **Verdict:** PASS WITH GAPS
- **Critical:** none
- **High (4):** AD-8 keep-alerting vs already-alerted; `/out` vs `alerted_windows`; ForecastSource DTO; git persist + ping-after-persist
- **Plus 9 more** (medium/low) in this file
- **Do not hand to parallel coding agents** until the four highs are bound or explicitly Deferred with a revisit condition
