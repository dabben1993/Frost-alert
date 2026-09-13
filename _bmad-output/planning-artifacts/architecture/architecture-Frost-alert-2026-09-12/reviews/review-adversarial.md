# Adversarial review — Architecture Spine (Frost Alert)

- **Lens:** Finalize-gate adversarial — two units one level down, each obeys every AD to the letter, still incompatible
- **Content:** `ARCHITECTURE-SPINE.md` (status: draft, updated 2026-09-13)
- **Altitude / purpose:** feature / build-substrate for coding agents
- **Verdict:** **FAIL** — the spine is not yet a parallel-build contract. Independent epics or agents can satisfy every `AD-n` and still clash on shared-data shapes, entity ownership, and state-mutation paths.
- **Date:** 2026-09-13

## Stance

ADs are the only binding contract. Consistency Conventions, Structural Seed, and the Capability map are cold-start hints: a unit that never reads them still "obeys every AD." Every pair below is therefore a hole — close it with a **new AD** or a **tightened Rule**, not another convention row.

## Attack pairs

### AP-1 — Two `ForecastSource` DTOs, one domain

- **Units:** Open-Meteo adapter epic vs domain-classifier epic
- **ADs obeyed:** AD-1 (adapter implements port; domain has no I/O), AD-7 (Celsius), AD-11 ("domain sees one hourly series")
- **Clash:** Adapter A returns `{time: ["2026-09-14T18:00"], temperature_2m: [2.1]}` in the place's civil zone with naive datetimes (`timezone=auto`). Adapter B returns a list of `(unix_epoch, temp_c)` UTC. Domain C treats series order as chronological and `first_at_or_below` as `series[0]` among matches. Remaining time and local `event_date` diverge by hours; MET Norway's compact timeseries vs Open-Meteo's parallel arrays never meet.
- **Hole:** AD-11 names a series and does not type it. Timestamp zone, sort, hour completeness, and field names are free.

**Canonical**

- **location:** AD-11 Rule; AD-5 `first_at_or_below`; Design Paradigm ports
- **trigger_condition:** "One hourly series" has no DTO, timezone, or ordering contract.
- **guard_snippet:** Tighten AD-11 (or add AD-13): domain consumes only `HourlySeries = ordered list of {t: UTC-aware datetime, temp_c: float}`; adapters convert vendor JSON; never pass through Open-Meteo/MET shapes; missing/unsorted/non-hourly hours are malformed → failover.
- **potential_consequence:** Same forecast classifies as window 24 in one build and window 6 (or no event) in the other; MET fallback looks like a different night.

---

### AP-2 — Setup vs check invent different `config/user.json` keys

- **Units:** CAP-1 setup CLI vs CAP-2/5 check entrypoint
- **ADs obeyed:** AD-3 (setup writes `config/user.json`; checks never re-geocode), AD-7 (`threshold_c`, `scale` display-only, Celsius on disk)
- **Clash:** Setup writes `{city, latitude, longitude, elevation, tz, threshold_c, scale}`. Check reads convention keys `{place_name, lat, lon, elevation_m, timezone, ...}`. AD-7 names only `threshold_c` and `scale`. Place, coordinates, elevation, and timezone live solely in the convention table — optional for an AD-obedient agent.
- **Hole:** Shared config shape is not an AD. Two file owners of one entity (`user.json`).

**Canonical**

- **location:** AD-3 Rule; Consistency Conventions "Data & formats"; CAP-1 map
- **trigger_condition:** AD-3 names the file, not the schema; only `threshold_c`/`scale` appear in an AD.
- **guard_snippet:** Tighten AD-3: `config/user.json` keys are exactly `place_name` (string), `lat`/`lon` (float), `elevation_m` (number, required), `timezone` (IANA), `threshold_c` (number), `scale` (`C`|`F`). Setup is the only writer; ConfigStore is read-only on the check path. No alias keys.
- **potential_consequence:** First scheduled tick crashes or silently geocodes/classifies against missing/wrong fields; clone-and-configure CAP-1 success is not interoperable with CAP-2.

---

### AP-3 — `data/state.json` types are unenforceable

- **Units:** StateStore adapter vs domain tick
- **ADs obeyed:** AD-3 (StateStore is the only writer of the file), AD-4 (one write per tick), AD-5 (already-alerted keyed by event + window), AD-8 (frost event = local date)
- **Clash:** Agent A stores `alerted_windows: [24, 12]` (ints) scoped to sibling `event_date`. Agent B stores `{"2026-09-14": ["24h", "12h"]}` or `alerted: true` booleans. `telegram_offset` is last `update_id` in A and next `getUpdates` offset (`id+1`) in B. `event_date` is `null` vs omitted vs `""` when idle. AD-5/AD-8 describe identity, not JSON types. Key names themselves are convention-only.
- **Hole:** The runtime shared record has no AD-level schema, so both writers are "the" StateStore.

**Canonical**

- **location:** AD-3; AD-5 already-alerted; AD-8 event identity; convention state keys
- **trigger_condition:** State identity is specified; on-disk types and key names are not ADs.
- **guard_snippet:** New AD (shared state record): keys exactly `season` (`monitoring`|`suspended`), `event_date` (`YYYY-MM-DD` or JSON `null`), `alerted_windows` (array of ints from `{24,12,6}`, scoped to current `event_date`, cleared when `event_date` changes), `telegram_offset` (int, last processed `update_id`, `0` if none), `updated_at` (UTC ISO-8601). No parallel maps.
- **potential_consequence:** Duplicate 24h alerts, skipped 6h, or dropped `/in` after an offset off-by-one — while both modules claim AD-3/AD-4 compliance.

---

### AP-4 — Two owners of `season` (and the rest of the tuple) on `/in` `/out`

- **Units:** domain season module vs AckInbox/Telegram adapter
- **ADs obeyed:** AD-8 (keep alerting until `/in`/`plants_in`; Suspended: job runs, no frost alerts), AD-9 (Telegram is the flip; commands/callbacks named), AD-4 (one write at end of tick)
- **Clash:** Domain A applies `transition(cmd) -> season` and, on `/out`, **keeps** `event_date` + `alerted_windows` so the same local date does not restart 24h. Adapter B writes `season` directly into the dict and, on `/out`, **clears** windows (resume = re-alert today) and, on `/in`, nulls `event_date`. Both are legal: AD-9 specifies only the season enum, not the rest of the record. Both can "write once" at tick end.
- **Hole:** One entity (`season` + event/windows) has two mutators; flip side-effects are unspecified.

**Canonical**

- **location:** AD-9 Rule; AD-8 "until /in"; AD-4 write-once
- **trigger_condition:** Season flip names the channel and enum, not the owner or the adjacent fields.
- **guard_snippet:** Tighten AD-9: only domain applies `/in`|`plants_in` → `suspended` and `/out`|`plants_out` → `monitoring`. Adapters report intents, they do not assign `season`. On `/in`: `season=suspended`; `event_date` and `alerted_windows` unchanged. On `/out`: `season=monitoring`; `alerted_windows` unchanged for the current `event_date` (same-day resume does not restart windows). Repeat commands are idempotent.
- **potential_consequence:** Same-afternoon `/out` either storms the user with a fresh 24h or stays silent until a new `event_date` — two shipped behaviors, both "correct."

---

### AP-5 — `alerted_windows` marked before send vs after send vs twice

- **Units:** domain classifier vs Notifier adapter
- **ADs obeyed:** AD-5 (keyed by event + window, not job name), AD-4 (one state write), AD-6 (Notifier failure still pings)
- **Clash:** Domain A marks the window alerted, then Notifier.send; Telegram 5xx → AD-6 pings, window never retries. Notifier B records "sent" itself and skips if it thinks it already did, while domain also skips on `alerted_windows` — first 24h never leaves. Domain C marks only after `send()` returns; crash between send and StateStore write → duplicate next tick. AD-5 says how to key, not who commits the key relative to I/O.
- **Hole:** Two mutation paths for one field; success vs attempt is undefined.

**Canonical**

- **location:** AD-5 already-alerted; AD-6 Notifier-failure clause; CAP-3 map
- **trigger_condition:** Dedup key exists; the send/mark ordering and exclusive mutator do not.
- **guard_snippet:** Tighten AD-5: domain is the only writer of `alerted_windows`. Mark a window only after Notifier reports send success. Failed send: leave unmarked, still follow AD-6 ping. Notifier must not persist or self-dedupe.
- **potential_consequence:** A Telegram blip either burns the only 24h slot (plants stay out with no retry) or double-pages every remaining tick.

---

### AP-6 — Two failover orchestrators

- **Units:** composite `ForecastSource` facade vs check entrypoint
- **ADs obeyed:** AD-11 (Open-Meteo first, 15s, MET on timeout/connect/5xx/429/empty; no fallback on 4xx; domain sees one series), AD-1 (new vendor = new adapter)
- **Clash:** Facade A already returns MET Norway on Open-Meteo 502. Entrypoint B also catches failure and calls the MET adapter. Domain sees a blended or double-fetched series, or B never calls MET because A swallowed the error and returned empty-as-success. Inverse: A is a thin Open-Meteo adapter, B never orchestrates — CAP-6 is nobody's job. Both units can claim AD-11 as "their" rule.
- **Hole:** Failover is a policy without a single owner.

**Canonical**

- **location:** AD-11 Rule; Capability map CAP-6 vs CAP-2
- **trigger_condition:** AD-11 states the policy, not the unique module that may run it.
- **guard_snippet:** Tighten AD-11: exactly one composition root — a single `ForecastSource` facade adapter — owns Open-Meteo-then-MET. Entrypoint and domain call that port once. Open-Meteo and MET adapters must not call each other. 4xx-bad-request is a hard fail of the facade (no MET).
- **potential_consequence:** Dual fetch (rate/ToS + contradictory hours) or a dual-API miss that still pings because each layer thought the other succeeded.

---

### AP-7 — `Clock.now` timezone vs local `event_date`

- **Units:** Clock adapter vs domain (AD-5 remaining time + AD-8 local date)
- **ADs obeyed:** AD-5 (`first_at_or_below − Clock.now`), AD-8 (event = local calendar date in config IANA zone), convention "instants UTC ISO-8601" (on-disk only)
- **Clash:** Clock A returns UTC-aware `datetime`. Domain B assumes `Clock.now` is already local civil time and subtracts naive forecast hours. Midnight in `Europe/Stockholm` vs UTC flips `event_date` and the 12h/6h boundary. Convention UTC applies to JSON, not to the port.
- **Hole:** Clock's unit and zone are not an AD.

**Canonical**

- **location:** AD-5 Rule; AD-8 local date; Clock port in paradigm
- **trigger_condition:** Remaining time and event key depend on a Clock whose timezone is unnamed.
- **guard_snippet:** Tighten AD-5: `Clock.now` is a UTC-aware instant. Domain converts to local date **only** with `config.timezone` for `event_date`. Forecast hours (AP-1) are UTC-aware. Never interpret Clock or series as civil-local.
- **potential_consequence:** Event key off-by-one around local midnight; a late GHA tick sends the wrong window even though AD-5 exists to prevent that.

---

### AP-8 — Remaining ≤ 0 and lookahead boundaries

- **Units:** classifier vs alerter (both "AD-5 mapping")
- **ADs obeyed:** AD-5 (lookahead 30h; `>12` → 24; `>6` → 12; else 6; outside lookahead: no event), AD-7 (any forecast hour)
- **Clash:** Series includes the current hour already at −1°C (`remaining = −20 min`). Classifier A maps `else` → window 6 (plants still out). Classifier B treats `remaining <= 0` as outside / no event. `remaining == 12.0` is window 12 under `>` and window 24 under a `>=` reading. `remaining == 30.0` is in-lookahead vs "outside." Equality is unspecified.
- **Hole:** The mapping is a slogan, not a closed function.

**Canonical**

- **location:** AD-5 mapping sentence
- **trigger_condition:** Bounds and `remaining <= 0` are unstated; two closed readings both match the text.
- **guard_snippet:** Tighten AD-5: let `r = first_at_or_below − Clock.now` (AP-7). If no crossing with `0 < r <= 30h`, no event. If `r > 12h` → 24; elif `r > 6h` → 12; else → 6. Hours already at or below threshold (`r <= 0`) do not start or keep an event by themselves; the first **future** crossing inside the lookahead does.
- **potential_consequence:** Frost-already-on nights either spam 6h forever or go silent while plants are still out — the exact failure AD-8 claims to prevent.

---

### AP-9 — `telegram_offset` has two owners

- **Units:** AckInbox adapter vs StateStore
- **ADs obeyed:** AD-3 (only StateStore writes `data/state.json`), AD-4 (poll then write once), AD-9 (getUpdates only; no webhook)
- **Clash:** AckInbox A keeps offset in adapter memory / a side file and only returns intents. StateStore B writes `telegram_offset` from a stale snapshot taken before poll. Next tick re-delivers or skips `/in`. Off-by-one: A stores last `update_id`, B passes it as `getUpdates(offset=)` without `+1`. AD-9 forbids webhooks; it does not say the offset lives in the state record or who advances it.
- **Hole:** One entity, two stores, two increment rules.

**Canonical**

- **location:** AD-9 intake; AD-3 StateStore; convention `telegram_offset`
- **trigger_condition:** Polling is required; persistence and increment of the cursor are not.
- **guard_snippet:** Tighten AD-9: `telegram_offset` lives only in `data/state.json`. AckInbox is stateless across ticks: input = current offset, output = intents + `new_offset` (last processed `update_id`). Domain/StateStore persist it on the same write as season. Next poll uses `offset=telegram_offset+1`. No other offset file or memory.
- **potential_consequence:** `/in` processed twice (oscillating season) or dropped until Telegram expires the update (24h) — plants stay out with no suspend.

---

### AP-10 — Disk write vs git commit: two writers of the same entity

- **Units:** `StateStore` adapter vs `.github/workflows/check.yml`
- **ADs obeyed:** AD-3 (StateStore writes the file; not cache/artifacts), AD-4 (one in-flight run, write state once, cancel-in-progress)
- **Clash:** Store A shells out `git add && git commit && git push` after each `save()`. Workflow B also commits `data/state.json` at job end. Two git writers, lost updates, or fighting `[skip ci]` vs looping schedules. Inverse: A writes disk only; B never commits — in/out dies at runner teardown, which is the seasonal-idle failure AD-3 claims to prevent. AD-4's "write once" can mean one Python `save`, one git commit, or both.
- **Hole:** The durable mutation path for state is split across adapter and workflow with no exclusive owner.

**Canonical**

- **location:** AD-4 Rule; AD-3 store; Structural Seed `check.yml` → commit
- **trigger_condition:** "Write state once" does not name disk vs git or forbid a second commit path.
- **guard_snippet:** Tighten AD-4: StateStore writes the working-tree file only — no git. `check.yml` is the only git committer of `data/state.json` (that path only), once per run, after the entrypoint exits 0 or after a planned non-zero classify-fail path that must still persist offset/season. No other workflow may write or commit that file (closes an `ack.yml` loophole). Adapters must not invoke git.
- **potential_consequence:** The in/out flip AD-4 exists to protect is lost on cancel-in-progress, double-commit, or ephemeral-disk-only writes.

---

### AP-11 — Ports named, call shapes free

- **Units:** `ports/` author vs any adapter epic
- **ADs obeyed:** AD-1 (adapters implement ports; domain does not import adapters), AD-12 (layout `domain,ports,adapters,entrypoints`)
- **Clash:** ForecastSource is `get_hourly(config) -> HourlySeries` in A and `fetch(lat, lon) -> Path` in B. Notifier is `send_frost(alert)` vs `send(text, reply_markup)`. AckInbox is `poll(offset) -> list[Intent]` vs `drain() -> None` (mutates state — AP-4/AP-9). Domain types vs port-local DTOs: two `Alert` dataclasses, circular imports, or adapters that cannot satisfy the domain.
- **Hole:** Hexagonal without a port contract is two codebases sharing folder names.

**Canonical**

- **location:** AD-1; AD-12; Design Paradigm port list
- **trigger_condition:** Ports are named; methods, DTOs, and which layer owns those types are not.
- **guard_snippet:** New AD (port contract): ports are `typing.Protocol` under `src/frost_alert/ports`. Domain owns `HourlySeries`, `Alert` (event_date, window 24|12|6, first_crossing_temp_c, first_at UTC, threshold_c, place_name, scale), `SeasonIntent` (`plants_in`|`plants_out`). Ports import those types; adapters map vendors. Entrypoints only wire. Forbidden: adapter-defined domain duplicates; ports that return HTTP/JSON blobs.
- **potential_consequence:** Independently "compliant" modules cannot be composed; integration is a rewrite.

---

### AP-12 — Two ping owners (Watchdog port vs workflow `curl`)

- **Units:** Watchdog adapter vs `check.yml` last step
- **ADs obeyed:** AD-6 (ping only after series + classify; dual miss/crash no ping; Notifier failure still pings), AD-10 (period/grace documented, not hardcoded)
- **Clash:** YAML A `curl`s the ping URL if the job's last step runs — including after a Python crash that was `|| true`, or before classify if someone "healthchecks the job." Adapter B pings from Python after classify. Both ping (noise) or neither (each defers). AD-6 states when, not who exclusively.
- **Hole:** The ping is one entity with two mutation paths.

**Canonical**

- **location:** AD-6 Rule; CAP-7 map; Structural Seed healthchecks.io
- **trigger_condition:** Ping policy is stated; exclusive caller is not.
- **guard_snippet:** Tighten AD-6: only the Watchdog port adapter may HTTP-ping. `check.yml` must not curl the ping URL. Call ping after classify returns on an obtained series, even if Notifier failed; do not ping on facade forecast miss or unhandled exception (non-zero exit).
- **potential_consequence:** Dual-API miss looks healthy (CAP-7 false negative) or a fine check looks dead (false positive) — the watchdog the spec requires.

---

### AP-13 — AckInbox accepts any chat; Notifier uses the secret

- **Units:** Notifier vs AckInbox (same Telegram bot, public repo)
- **ADs obeyed:** AD-9 (Telegram is the season flip; getUpdates; answerCallbackQuery), convention "secrets: bot token, chat id"
- **Clash:** Notifier A sends only to `TELEGRAM_CHAT_ID`. AckInbox B applies `/in` from whoever messaged the bot. AD-9 does not require filtering by chat id. Secret **names** are also free (`BOT_TOKEN` vs `TELEGRAM_BOT_TOKEN`), so workflow and adapter miss each other even for the real owner.
- **Hole:** Season entity writable by a stranger; env contract not an AD.

**Canonical**

- **location:** AD-9; AD-3 secrets sentence; convention secret list
- **trigger_condition:** Intake is Telegram; authorized chat and env names are not ADs.
- **guard_snippet:** Tighten AD-9 + secrets: GitHub Secrets / env are exactly `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `WATCHDOG_PING_URL`. Notifier sends only to `TELEGRAM_CHAT_ID`. AckInbox ignores any update whose chat id differs (still `answerCallbackQuery` if it was a callback, then drop).
- **potential_consequence:** A probe of a public bot suspends frost alerts; or check.yml and Python disagree on env names and ship a silent no-op notifier.

---

### AP-14 — Elevation and timezone provenance (setup vs MET adapter)

- **Units:** CAP-1 geocoding vs CAP-6 MET Norway adapter
- **ADs obeyed:** AD-3 (geocode once; cache lat/lon/elevation/timezone), AD-11 (MET: elevation required, lat/lon 4 decimals, identifying User-Agent)
- **Clash:** Open-Meteo geocoding often has no elevation. Setup A omits `elevation_m` or writes `null` — AD-3 says "caches" it, not "fails closed without it." MET adapter B refuses without elevation (AD-11). Check then cannot fail over. Timezone: setup C uses the laptop's zone; domain D uses it for `event_date` (AD-8) — Sweden-configured clone run on a travel laptop gets the wrong local date.
- **Hole:** Cached fields have two sources; required-ness for failover is not on the setup writer.

**Canonical**

- **location:** AD-3 geocode/cache sentence; AD-11 MET elevation; AD-8 IANA zone
- **trigger_condition:** Setup must cache elevation/timezone; it need not obtain a MET-safe elevation or a place IANA zone.
- **guard_snippet:** Tighten AD-3: setup must persist a numeric `elevation_m` and the **place's** IANA `timezone` from geocoding (not the operator machine). If elevation is missing from geocode, fetch it before finishing (or fail setup). Checks never guess elevation or timezone. MET adapter does not geocode.
- **potential_consequence:** CAP-6 is dead on first Open-Meteo outage; event keys follow the laptop, not the trees.

---

### AP-15 — Missing `state.json` and `deleteWebhook` have two defaults

- **Units:** setup CLI vs first `check.yml` tick vs AckInbox
- **ADs obeyed:** AD-3 (setup writes **config only**; StateStore writes state), AD-8/AD-9 (monitoring vs suspended), AD-9 (webhook must not be set)
- **Clash:** First run: Store A defaults `season=monitoring`, offset `0`. Store B defaults `suspended` ("safer," no spam). Setup C also writes an initial `state.json` (violates spirit of AD-3, not the letter if C argues first-run isn't "StateStore"). Webhook: nobody calls `deleteWebhook` because AD-9 only forbids setting one. A leftover BotFather webhook makes getUpdates empty forever; both ADs still hold.
- **Hole:** Initial state and webhook enforcement are ownerless.

**Canonical**

- **location:** AD-3 setup-vs-state; AD-9 webhook sentence; first-run path
- **trigger_condition:** No initial record; no unit is required to clear webhooks.
- **guard_snippet:** Tighten AD-3/AD-9: setup never writes `data/state.json`. Missing file means `season=monitoring`, `event_date=null`, `alerted_windows=[]`, `telegram_offset=0`. Each check tick calls `deleteWebhook` before `getUpdates` (AckInbox).
- **potential_consequence:** First clone either never alerts or alerts after a default-suspended season; or polling is silently disabled and `/in` can never land.

---

### AP-16 — Who formats user-scale copy (domain vs Notifier)

- **Units:** domain vs Telegram Notifier
- **ADs obeyed:** AD-1 (domain no I/O), AD-7 (`scale` is setup and display only), convention "Notifier follows alert-copy.md"
- **Clash:** Domain A converts `threshold_c` and first-crossing to °F and returns display strings. Notifier B converts again (`*9/5+32` on already-F numbers) or always prints Celsius because AD-7 "domain stores Celsius." Preview vs opened split is a companion, not an AD, so a third unit puts location into the preview.
- **Hole:** Display conversion and copy split have two owners; convention is skippable.

**Canonical**

- **location:** AD-7 scale sentence; Frost alert copy convention; CAP-3
- **trigger_condition:** Celsius-on-disk is an AD; who converts for display, and the preview/opened split, are not.
- **guard_snippet:** Tighten AD-7: domain exposes only Celsius fields on `Alert`. Notifier is the only scale converter (`C` display as stored; `F` via `C*9/5+32`) and the only module that applies `alert-copy.md` (preview: emoji + risk + 24/12/6, no table/location/ack how-to; opened: place, first-crossing in user scale, when, threshold, ack control).
- **potential_consequence:** °F users get a doubled conversion or a C reading they do not understand from the lock screen — CAP-3 preview success fails while every AD still passes.

---

## Cross-cutting

These are the same three holes repeating:

1. **Shared-data shapes live in conventions/seed** (`user.json`, `state.json`, hourly series, `Alert`, env names).
2. **Entities have two owners** (`season`, `alerted_windows`, `telegram_offset`, forecast failover, watchdog ping, git commit of state).
3. **Mutation order is a slogan** (mark vs send, poll vs persist offset, disk vs git, remaining-time equalities).

Closing AP-1, AP-3, AP-4, AP-6, AP-10, and AP-11 would remove most of the blast radius; the rest are tightenings of existing AD-3/5/6/7/9.

## Findings array

```json
[
  {"lens":"adversarial","location":"AD-11 / AD-5 / ports","trigger_condition":"Hourly series DTO, timezone, and ordering are unnamed.","guard_snippet":"Type HourlySeries as UTC-aware (t, temp_c) lists; vendor JSON cannot leak; unsorted/non-hourly is malformed.","potential_consequence":"Same forecast maps to different windows or event dates across adapters."},
  {"lens":"adversarial","location":"AD-3 / config schema","trigger_condition":"config/user.json keys other than threshold_c and scale are not ADs.","guard_snippet":"Pin exact config keys and types; ConfigStore read-only on check; no aliases.","potential_consequence":"Setup and check cannot read the same committed file."},
  {"lens":"adversarial","location":"AD-3 / AD-5 / AD-8 / state schema","trigger_condition":"state.json key names and types are convention-only.","guard_snippet":"Pin season, event_date, alerted_windows ints, telegram_offset last update_id, updated_at UTC.","potential_consequence":"Dedup and ack cursor disagree; duplicates or dropped /in."},
  {"lens":"adversarial","location":"AD-9 / AD-8","trigger_condition":"Season flip does not name exclusive mutator or event/window side-effects.","guard_snippet":"Domain-only transitions; /out does not reset windows for the current event_date.","potential_consequence":"Same-day resume either re-alerts 24h or stays silent."},
  {"lens":"adversarial","location":"AD-5 / AD-6","trigger_condition":"Who marks alerted_windows relative to Notifier.send is free.","guard_snippet":"Domain-only; mark only after send success; Notifier does not persist.","potential_consequence":"Burned 24h slot on Telegram fail, or duplicate alerts."},
  {"lens":"adversarial","location":"AD-11 / CAP-6 map","trigger_condition":"Failover policy has no unique owner.","guard_snippet":"One ForecastSource facade; entrypoint calls it once; adapters do not recurse.","potential_consequence":"Double fetch, blend, or a miss that still pings."},
  {"lens":"adversarial","location":"AD-5 / AD-8 / Clock","trigger_condition":"Clock.now timezone is unnamed.","guard_snippet":"Clock.now is UTC-aware; local date uses config.timezone only.","potential_consequence":"Wrong event_date and window around local midnight."},
  {"lens":"adversarial","location":"AD-5 mapping","trigger_condition":"remaining <= 0 and inclusive 6/12/30h bounds have two closed readings.","guard_snippet":"Event only if 0 < r <= 30h; >12 → 24; >6 → 12; else 6.","potential_consequence":"Frost-already-on either spams 6h or goes silent."},
  {"lens":"adversarial","location":"AD-9 / telegram_offset","trigger_condition":"Ack cursor ownership and last-id vs next-offset are free.","guard_snippet":"Offset only in state.json; persist last update_id; next poll uses +1.","potential_consequence":"Dropped or double-applied /in."},
  {"lens":"adversarial","location":"AD-4 / git vs StateStore","trigger_condition":"Write-once does not exclusive-own disk vs git or forbid a second workflow.","guard_snippet":"StateStore writes the file; only check.yml commits it; no other workflow writers; no git from adapters.","potential_consequence":"Lost in/out on runner teardown or overlapping commits."},
  {"lens":"adversarial","location":"AD-1 / AD-12 ports","trigger_condition":"Ports have names, not methods or DTO owners.","guard_snippet":"Protocols + domain-owned HourlySeries/Alert/SeasonIntent; no vendor blobs through ports.","potential_consequence":"Compliant modules cannot compose."},
  {"lens":"adversarial","location":"AD-6 Watchdog","trigger_condition":"Ping when is stated; exclusive who is not.","guard_snippet":"Only Watchdog adapter pings; check.yml must not curl.","potential_consequence":"Missed job looks healthy or healthy job looks dead."},
  {"lens":"adversarial","location":"AD-9 / secrets","trigger_condition":"Chat-id filter and env names are not ADs.","guard_snippet":"Pin TELEGRAM_* and WATCHDOG_PING_URL; ignore other chats.","potential_consequence":"Stranger flips season, or notifier never sends."},
  {"lens":"adversarial","location":"AD-3 / AD-11 elevation and timezone","trigger_condition":"Setup can cache empty elevation and a laptop timezone.","guard_snippet":"Setup must persist numeric elevation_m and place IANA timezone or fail.","potential_consequence":"MET failover unusable; event keys follow the operator not the trees."},
  {"lens":"adversarial","location":"AD-3 first-run / AD-9 webhook","trigger_condition":"Missing state.json defaults and deleteWebhook have no owner.","guard_snippet":"Missing state = monitoring + empty windows + offset 0; each tick deleteWebhook first.","potential_consequence":"First clone never alerts or never receives /in."},
  {"lens":"adversarial","location":"AD-7 / alert copy","trigger_condition":"Display conversion and preview/opened split can sit in domain or Notifier.","guard_snippet":"Domain Celsius-only Alert; Notifier converts scale and owns alert-copy.md split.","potential_consequence":"Wrong scale on the lock screen or preview that violates CAP-3."}
]
```
