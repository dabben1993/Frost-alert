---
title: 'technical research: Frost Alert hosting and scheduling platform selection'
type: 'technical'
topic: 'Frost Alert hosting and scheduling platform selection'
decision: 'Pick a $0-or-cheapest scheduled-job platform to run the Frost Alert checks (multiple times/day, at specific hour-offsets before a forecast cold night) without any personally-owned always-on device.'
source: 'run'
status: complete
preset: 'standard'
validation: 'normal'
created: '2026-09-12'
updated: '2026-09-12'
claims_verified: 8
claims_unverified: 1
---

# technical research: Frost Alert hosting and scheduling platform selection

**Decision this research serves:** Pick a $0-or-cheapest scheduled-job platform to run the Frost Alert checks (multiple times/day, at specific hour-offsets before a forecast cold night) without any personally-owned always-on device.

## Executive summary

**Recommendation: GitHub Actions scheduled workflows**, made public (or paired with GitHub Pro at $4/mo) to avoid the private-repo scheduling restriction — paired with an independent, low-cost watchdog rather than trusted alone.

Four candidates screened clean on the hard requirements ($0, no personal-device dependency, precise multi-time-per-day scheduling): **GitHub Actions**, **Cloudflare Workers Cron Triggers**, **Deno Deploy Cron**, and **Supabase Cron**. The two biggest findings only emerged past that first pass:

1. **Every free scheduler has a real, dated reliability gap** — GitHub Actions' scheduled-workflow delay has been measured rising from ~1h40m to over 4h30m through 2026 (an open, unresolved issue); Cloudflare Workers Cron Triggers had an official status-page degradation incident 3 days before this research ran; Deno Deploy's cron requires manually configuring retries and sits on a young (~7-month-old) platform; and Supabase's `pg_net` trigger is fire-and-forget with no built-in retry. **No $0 option here comes with an SLA suitable for a safety-relevant alert on its own** — the design should assume this and add a cheap independent watchdog, not chase a mythical perfectly-reliable free scheduler.
2. **Supabase Cron has a structural mismatch with this specific project**: its free tier auto-pauses a project after ~7 days of low database activity, and Frost Alert's whole design is a seasonal on/off automation that goes quiet for months at a time — exactly the pattern that triggers a pause. This ruled Supabase out as the primary choice despite it otherwise being the strongest option for EU/Sweden data residency (an explicit Stockholm region, a self-serve DPA).

GitHub Actions is recommended as primary despite its own delay problem because that problem degrades precision rather than causing silent total failure (a late run still shows as "ran," just late), it has the widest language choice and easiest setup of the four, it's the only one with free built-in failure-email alerting, and its parent company (Microsoft) carries no platform-continuity risk. The single biggest caveat: **pair it with an independent trigger or a dead-man's-switch watchdog** for the final, most time-critical check in the escalation sequence, since none of the free options tested here should be trusted alone for that role.

_Sections are appended per the approved research plan._

## Dimension 1: Candidate screen

**Stopped after round 1 — coverage.** All three plan questions (map the credible field, cut hard-gate failures) were answered with load-bearing claims confirmed; a second round would only have deepened dimensions 2–3, which run separately.

**Hard gates applied:** (a) $0, or as close to it as realistically possible; (b) zero dependency on a personally-owned always-on device; (c) can plausibly fire multiple times/day at specific hour-offsets, within a free tier, at single-user volume.

### Screening result

| Candidate | $0 at this volume? | No personal-device dependency? | Multiple precise times/day on free tier? | Verdict |
|---|---|---|---|---|
| GitHub Actions (`schedule:`) | Yes [1] | Yes [4] | Yes — multiple `schedule:` entries per workflow, IANA timezone support [2] | **Finalist** — but see private-repo caveat below |
| Cloudflare Workers Cron Triggers | Yes, up to 5 triggers/account on Free [6] | Yes [7] | Yes — arbitrary cron, UTC only [7] | **Finalist** |
| Deno Deploy (`Deno.cron()`) | Yes, up to 10 jobs/deployment on Free, built-in retries [30] | Yes [30] | Yes — arbitrary cron [30] | **Finalist** |
| Supabase Cron (pg_cron + Edge Functions) | Yes, 500K Edge Function invocations/mo free [36][37] | Yes [36] | Yes — "every second to once a year" cron syntax [36] | **Finalist** |
| AWS Lambda + EventBridge Scheduler | Yes (Always Free: 1M req + 400K GB-s Lambda [10]; 14M invocations EventBridge [11]) | Yes [10][11] | Yes — 6-field cron, comma-list hours, per-schedule timezone [12] | Screened to background — passes gates but adds a credit-card requirement [13][19] and a 2025 free-tier restructuring risk (see below); EventBridge Scheduler was recently expanded to all AWS regions, a signal of active investment rather than sunset [15] |
| Google Cloud Scheduler + Functions | Marginal — $0 for ≤3 jobs/billing-account, then $0.10/job [16] | Yes [16][18] | Yes — 5-field cron with comma-list hours, one schedule per job [17] | Screened to background — same credit-card friction as AWS [19], plus per-job (not per-invocation) billing |
| cron-job.org | Yes, no published cap [20] | Yes | Yes, down to once/minute [20] | Cut as a **standalone** answer — it is trigger-only: it requires your check logic to already be hosted at a public HTTPS endpoint [22][23]; no SLA, deliberately delays repeatedly-failing jobs [20][21]; a low-confidence aggregator lists similar third-party alternatives (Cronhooks, Runhooks) [24], and one anecdote describes a user fleeing GitHub Actions' own delays for cron-job.org [25] |
| EasyCron | Yes, but free tier requires **manual monthly renewal** or it silently expires [26][27] | Yes | Yes, 200 executions/day, 20-min min interval [26] | Cut — same trigger-only limitation as cron-job.org, plus an ongoing manual-maintenance burden that fights the "set and forget" goal |
| healthchecks.io / UptimeRobot Heartbeat | N/A | N/A | N/A | Cut — not schedulers at all; both are dead-man's-switch monitors that require a *separate* real scheduler to already exist [28][29] |
| Vercel Cron Jobs (Hobby) | Yes | Yes | **No** — Hobby is hard-capped at once/day, and even that fires only "sometime within the hour," not at a precise minute [31][32][38][39][40] | **Cut — fails hard gate (c)** |
| Render Cron Jobs | No free tier for Cron specifically ($1/mo minimum per job) [33] | Yes | Yes | Cut for cost — cheap but not $0, and other finalists meet the same need for less |
| Fly.io scheduled machines | No free tier for new accounts as of Oct 2024 [35] | Yes | **No** — only fixed cadences (hourly/daily/weekly/monthly) from machine-creation time, no specific-time targeting [34] | **Cut — fails hard gates (a) and (c)** |

### Key findings and contradictions

**GitHub Actions' private-repository schedule restriction.** GitHub's own documentation states scheduled workflows run only from the default branch and can be delayed under high load [2][3], but is silent on any plan-tier restriction. However, three independent community write-ups — a GitHub Community Discussions thread summarized across two devActivity posts and mirrored on DEV Community — consistently and specifically report that on a **personal GitHub Free account, `schedule` events are effectively disabled on private repositories**; scheduled workflows only fire on private repos with GitHub Pro ($4/mo) or if the repo is made public [5]. This is corroborated across independent write-ups of the same underlying GitHub Community thread (still a single root incident, not fully independent confirmation, and official docs remain silent) — reported here as **medium confidence, unverified against an official GitHub statement**. This matters directly: a single-user hobby automation is very likely to live in a private repo, and this would either force making the repo public (fine if it contains no secrets — plausible for this project since API keys would live in repo secrets, not code) or force pairing GitHub Actions with an external trigger (e.g., cron-job.org calling `workflow_dispatch` via a Personal Access Token [5]) or paying $4/mo for Pro.

**Vercel Hobby's cron limitations are confirmed, not just alleged.** Vercel's own current pricing/limits docs state plainly: Hobby is capped at "Once per day" per cron job with "Per-hour (±59 min)" precision — a job set for 1:00am can fire any time up to 1:59am [31]. Three independent third-party write-ups corroborate this exactly, including the specific deployment-time error message [32][38][39][40]. This is a clean, verified elimination: Vercel Hobby cannot meet the "multiple times/day at specific hour-offsets" requirement at all, regardless of price.

**AWS's 2025 Free Tier restructuring is a real sustainability signal, not a rumor.** As of July 15, 2025, new AWS accounts choose between a "Free" plan (up to $200 credit, but the *account itself* auto-closes after 6 months or when credits run out) or a "Paid" plan (full, indefinite access); "Always Free" services like Lambda and EventBridge Scheduler remain available indefinitely under either program "as long as you are an AWS customer," but a hobbyist who doesn't realize this and stays on the default "Free" plan risks their account closing after 6 months [14]. This is a real, dated (2025) change to AWS's terms — not disqualifying, but a concrete maintenance/setup gotcha that GitHub Actions, Cloudflare Workers, Deno Deploy, and Supabase don't have (none require a credit card at all for the tiers in question).

**Cloudflare's production retry behavior on a failed scheduled run is not confirmed by official docs.** Cloudflare's own docs describe cron-trigger propagation delays (config changes can take up to 15 minutes to take effect) [7] but do not explicitly state whether a failed `scheduled()` handler is automatically retried. Two vendor blogs (with a commercial interest in selling alternative schedulers, so read with bias) assert there is no automatic retry [9] — this is reported as **low confidence, single-source-type (vendor blog), unverified against Cloudflare's own docs**.

### Finalists carried into Dimensions 2–3

**GitHub Actions**, **Cloudflare Workers Cron Triggers**, **Deno Deploy Cron**, and **Supabase Cron** — all genuinely $0 at this volume, all support precise multi-time-per-day scheduling, none require a credit card. **AWS EventBridge Scheduler + Lambda** and **Google Cloud Scheduler + Functions** are carried forward as credible but higher-friction background options (credit card required; AWS has the 2025 plan-structure gotcha; GCP bills per-job).

## Dimension 2: Timing precision, reliability & implementation reality

**Stopped after round 1 — coverage**, with one important caveat carried to the verdict as an open question (see below): the plan's questions (precision/reliability of finalists, setup/maintenance burden) were answered with load-bearing, dated evidence; a second round would mainly chase corroboration depth on already-identified findings.

This dimension surfaced the single most decision-relevant discovery of the whole research run: **all four $0 finalists have documented, dated reliability gaps** — this is not a case of "three solid options and one flawed one." The differences are in *what kind* of gap and how bad it is, not whether one exists.

### GitHub Actions

**Timing is worse than commonly assumed, and getting worse.** Beyond GitHub's own documented "can be delayed during high load" disclaimer [2][3], a real, open, actively-updated GitHub issue from a maintainer running a production nightly-build workflow shows *measured* average delay rising from ~1h40m in 2025 to over 4h30m by June 2026 — tested across three different UTC minute/hour offsets, all similarly delayed, meaning "pick an odd time to avoid the rush" does not reliably fix it [41]. A separate, independently measured account reports the *effective* fire rate can be throttled to a fraction of the declared cron rate, not just "occasionally late" [42]. This is corroborated (with different framing/severity) by two Stack Overflow threads from 2021 and March 2025 describing 10-30+ minute delays and explicit non-guarantees that a scheduled run fires at all [43][44]. **A cold-night frost alert that needs to reliably land at a specific hour-offset is exactly the workload this problem threatens most.**

**Setup is simple; ongoing maintenance has two silent-failure modes.** A minimal setup is one YAML file plus repo secrets, and workflows can only fire when the `schedule:` block is on the default branch — genuinely easy but with a documented gotcha [77][45][78]. But: (a) on a GitHub Free personal account, `schedule` triggers are — per consistent, if only community-corroborated, reports — effectively disabled on **private repositories** [5], meaning either the repo must be public (fine if secrets stay in repo Secrets, not code) or GitHub Pro ($4/mo) is needed; (b) multiple hobbyists report workflows silently stopped firing due to an account "billing lock" (e.g., a stale failed $0 card-verification hold) with zero warning and a failure mode indistinguishable from a broken pipeline [79][80][81]. On the plus side, GitHub Actions has genuinely free, built-in failure-email notifications requiring no extra setup [46] — the only one of the four finalists with this out of the box.

### Cloudflare Workers Cron Triggers

**An active incident during this very research window.** Cloudflare's own status page shows an official "Workers Cron Triggers degraded" incident that began 2026-09-09 — three days before this research ran — with triggers documented as possibly "not execute or be delayed" [47]. A separate resolved incident on 2026-03-24/25 similarly disrupted Cron Trigger changes [48]. A detailed Cloudflare Community report describes a production Cron Trigger that silently stopped dispatching for 5+ hours with zero log entries and no error, despite the underlying Worker being healthy — the poster states this "matches a recurring pattern reported across multiple prior Community threads" (unverified beyond that assertion) [49]. Cloudflare's own docs add up to 15 minutes of config-propagation delay and up to 30 minutes before new schedules even appear in the dashboard, complicating debugging [7].

**No confirmed automatic retry on failure.** Official docs are silent on production retry behavior for a failed `scheduled()` handler; vendor blogs (commercially motivated to sell alternatives, so read with that bias, but consistent with each other and with the `controller.noRetry()` field's mere existence) assert there is none — a failed run is simply lost until the next tick [9][50]. Setup itself is lightweight (2 files, `wrangler deploy` auto-registers the schedule) [82][83], secrets are straightforward [84][85], and outbound API calls are unrestricted at this volume [86][87] — but the code must be JS/TS/WASM, a real constraint if the developer prefers Python. (Cloudflare's own pricing page illustrates a heavier hourly-cron workload costing ~$7/month, but that example is on the paid Standard plan, not Free — at this project's volume the Free plan's Cron Triggers remain genuinely $0 [8].)

### Deno Deploy Cron

**"At-least-once," not "exactly-once," with no default retries.** Deno's own docs state invocation timing can vary by up to a minute and a handler may fire more than once for the same scheduled slot in failure scenarios [51]. Failed runs are not retried unless a `backoffSchedule` is explicitly configured (capped at 5 retries / 1hr max delay) [51] — this is more explicit and controllable than Cloudflare's undocumented behavior, a point in Deno's favor. Setup is minimal (no config file at all — cron is registered in code, deploy is the only step) [88][89], outbound calls to third-party APIs work with no documented default egress restriction [90], but registration is fragile: it must sit at literal module top level, and a specific, reproducible bug causing this detection to silently fail has been open for 18+ months across multiple confirmations (most recent 2026-03-09) [52][53][54]. The current "V2" platform only reached General Availability 2026-02-03 — about 7 months old at research time — and had a ~40-hour platform-wide outage in November 2025 (pre-GA) plus several shorter incidents [55][56][57]; mixed first-hand reports describe it as workable for small projects but still carrying "beta-quality" rough edges (poor error messages/logging) as of 2026 [58][59].

### Supabase Cron (pg_cron + Edge Functions)

**The most consequential finding for this specific project: the free tier auto-pauses on inactivity.** Supabase's own docs confirm a Free-tier project is automatically paused after ~7 days of low database activity, which halts pg_cron entirely because the database itself is suspended [72]. This is a long-standing, well-documented hobbyist pain point (Reddit threads from 2022 and 2025) requiring a keep-alive workaround — and some hobbyists report even a regular keep-alive ping still failed to prevent pausing if it hit the wrong (non-database-touching) endpoint [73][74][75]. **This interacts directly with Frost Alert's seasonal on/off design**: the whole point of the seasonal acknowledgment toggle is that the automation goes quiet for months at a time once trees are in overwintering, and again all summer when there's no frost risk to check for — exactly the low-activity pattern that triggers a Supabase free-project pause. Using Supabase Cron would require *deliberately* keeping the database "busy" (e.g., an unrelated periodic write) purely to prevent this — extra, non-obvious maintenance for a project whose whole premise is $0 and low-touch.

Beyond that: pg_net's HTTP trigger to an Edge Function is fire-and-forget with no automatic retry (must hand-build a retry table) [60][61][62][68]; a documented gotcha where `verify_jwt=true` silently 401s cron-triggered calls with zero logs [64]; and the pg_cron background worker itself can die and require a manual dashboard "fast reboot" on older Postgres/pg_cron versions [66]. One production account running 28 free-tier pg_cron jobs reported a data sync that "broke silently for 6 weeks" before anyone noticed [65], and another team hit Postgres connection-pool exhaustion from combining several long-running cron jobs with normal traffic [67]. No built-in failure alerting exists — documented workarounds range from a custom Postgres-trigger-to-Slack-webhook pattern [70] to a third-party paid monitor [71] to instrumenting with Sentry-style check-ins as Deno Deploy also requires [69]. Setup requires two Postgres extensions and raw SQL rather than a config file or CLI [91][92], and code must be TypeScript (Deno runtime) [91]. Keeping a free project alive long-term requires a genuine database-touching keep-alive job, not just a health-check ping [93].

### What this means for the verdict

None of the four is "reliable in the way a paid, SLA-backed scheduler would be." Ranked by risk for *this specific* use case (escalating, time-sensitive frost alerts with a months-long seasonal off-period):

1. **Supabase Cron is the weakest fit** specifically because of the free-project auto-pause interacting with the seasonal on/off design — a structural mismatch, not just a reliability nuisance.
2. **GitHub Actions' delay problem is the most severe and best-documented** (hours of delay, worsening trend in 2026) for a mechanism whose entire value proposition is precise hour-offset timing — but it has the best free built-in alerting and the widest language choice, and the delay mostly threatens precision, not complete silent failure (a workflow still shows as "ran late" in the Actions tab, it isn't invisible).
3. **Cloudflare's failure mode is more binary** (an incident window or a silent full stop) but appears less frequent/chronic than GitHub's measured drift, and — notably — Cloudflare had an active incident within the last 3 days at time of writing, which is itself informative about current health but should not be over-weighted as a permanent pattern (single data point).
4. **Deno Deploy's risks are the most idiosyncratic** (a specific registration bug, young V2 platform) but are the most controllable (explicit retry config) and the least tied to this project's specific usage pattern (unlike Supabase's auto-pause, nothing here is worsened by long idle stretches).

**Open question carried to the verdict:** none of this changes the $0/no-personal-device screening outcome, but it strongly argues for **layering a cheap independent reliability backstop** (e.g., a second, differently-timed trigger, or a dead-man's-switch monitor like healthchecks.io/UptimeRobot heartbeat — cut in Dimension 1 as *standalone* schedulers, but well-suited as a "did my real scheduler actually fire today" watchdog) rather than trusting any single free scheduler's on-time delivery for a safety-relevant alert. This is a design recommendation for `bmad-spec`/`bmad-prd`, not a further research question.

## Dimension 3: Cost, lock-in & EU/Sweden considerations

**Stopped after round 1 — coverage.** Both sub-questions (cost/lock-in/sustainability, and EU/Sweden regional fit) were answered with load-bearing evidence from official/primary sources for all four finalists plus the two background options.

### Cost and lock-in

All four finalists remain genuinely $0 for this workload with **no evidence of a prior cron-specific free-tier cut** for GitHub Actions or Cloudflare Workers [110][111][6][7]; Supabase Cron has likewise never charged separately for the feature [63][37]. The closest thing to a negative signal is Deno: the next-generation Deno Deploy platform briefly shipped in Early Access **without `Deno.cron()` support at all**, which the community explicitly called out as trust-damaging ("How can we build trust and invest in a language when things change in our disadvantage?") before support was restored [112][113]. Deno Deploy Classic (the older, more battle-tested implementation) is being sunset, forcing an eventual migration to the newer platform for all users [56][114].

**Portability if a migration is ever needed:** GitHub Actions' plain-YAML `schedule:` trigger is the most portable — the underlying script can be almost any language, and the trigger concept maps directly onto other CI systems [111]. Cloudflare's `scheduled()` handler and Deno's `Deno.cron()` are both runtime-specific APIs requiring a rewrite of the trigger plumbing (not just reconfiguration) to move elsewhere [7][51]. Supabase Cron is SQL against `pg_cron`/`pg_net` — portable in principle to any Postgres instance with those extensions installed, but that's a narrower requirement than "any host that can run a script" [36].

**Parent-company stability, as a multi-year hobby dependency:** Microsoft (GitHub) and Cloudflare are both large, financially unambiguous, public companies with no distress signals [115][116]. Supabase is well-funded (Series D + E totaling $500M+ through October 2025, at a $5B valuation [120][121]; a further $500M round reported for June 2026 by a single aggregator, unverified against a primary source [122]). **Deno Company is the outlier**: total disclosed funding is only ~$26M (last raised June 2022) [117], the company felt it necessary to publicly rebut "Deno is dying" criticism in May 2025 [118], and an independent (if adversarial) blog documented Deno Deploy's edge-region count shrinking from 35 to 6 between 2024 and January 2025 [119]. None of this means Deno Deploy will disappear, but among the four finalists it carries the most real platform-continuity risk over a multi-year "set and forget" horizon.

### EU/Sweden regional fit

| Finalist | Region pinning available? | Data-processing agreement for free/individual users? |
|---|---|---|
| GitHub Actions | No — GitHub places hosted runners on Azure VMs it controls; regional pinning (Azure private networking) is an org-level Enterprise feature, not available to a personal free repo [103] | A standard DPA exists but its published applicability language is framed around "Enterprise customers"; unclear if it self-serve-applies to personal/free accounts [104] |
| Cloudflare Workers Cron Triggers | No — runs on the global edge by default; Cloudflare's EU data-localization tooling (Regional Services, KV jurisdictions) explicitly does **not** cover Cron Triggers, and full data-localization control requires an Enterprise contract anyway [97][98][99] | Yes — DPA (with EU SCCs) is incorporated automatically into the Free/Pro/Business self-serve agreement, no signature needed [100] |
| Deno Deploy Cron | Yes — explicit `us` / `eu` / `global` region selection at deploy time (exact EU city/datacenter not confirmed) [101] | No — Deno's own pricing page lists "DPA: Not included" on Free/Pro/Builder tiers; only the custom Enterprise tier includes one [102] |
| Supabase Cron | Yes, and the most precise of the four — a project can be pinned specifically to "North EU (Stockholm)" (`eu-north-1`), not just a generic "Europe" grouping [94] | Yes — self-serve DPA (dated June 2026) is part of the Terms of Service on acceptance, including EU SCCs [95][96] |

For context, the two background options: **AWS** has a real Stockholm region (`eu-north-1`) confirmed usable for EventBridge+Lambda via a community tutorial (not an official region table specific to EventBridge Scheduler) [106], with a DPA automatically incorporated for all customers [105]. **Google Cloud Scheduler is notably *not available* in `europe-north1` (Finland)** — the nearest usable region would be Belgium or Frankfurt — even though other GCP compute services do support Finland [107][108]; GCP's DPA requires an explicit self-serve "accept" action in the console rather than being automatic [109].

**Practical read for this project:** the data involved (a location, a temperature threshold, a notification-bot token) is low-sensitivity and not the kind of personal data that typically drives strict EU-residency requirements for a single-user hobby tool — so this is a genuine "nice to have," not a hard gate. If EU data residency matters to the user regardless, **Supabase is the strongest fit** of the four (explicit Stockholm option, self-serve DPA) — though this cuts against Supabase's Dimension 2 weakness (free-tier auto-pause). None of the other three finalists offer real region control for the actual scheduling mechanism itself.

## Cross-dimension insights

**The screening dimension and the reliability dimension pull in opposite directions for Supabase.** Dimension 1 ranked Supabase Cron as a clean finalist — free, precise, self-contained (scheduler + compute in one platform, unlike cron-job.org). Only Dimension 2's deeper dig surfaced the free-project auto-pause, and only by connecting that finding back to the *specific* project brief (a seasonal on/off automation with months of planned inactivity) does it become clear this is a structural mismatch, not a generic nuisance that affects the other three candidates equally. A screening pass alone would have missed this; it only appears at the intersection of "what Supabase's free tier does" and "how this specific project behaves over a year."

**"$0 and reliable" turned out not to exist among the free options — the real choice is which failure mode to accept and how to backstop it.** Dimension 1 asked "is it free and does it support precise multi-time scheduling" and all four passed. Dimension 2 revealed that passing screening says nothing about actually firing on time; every finalist has a dated, evidenced reliability gap. Dimension 3 then showed that none of these gaps trace to a cost-cutting motive (no evidence of deliberate free-tier degradation) — they're just inherent to running a hobby workload on infrastructure whose SLAs don't extend to the free tier. This is the report's central cross-cutting conclusion: **the platform choice matters less than whether the design includes an independent watchdog**, because no $0 option here comes with a reliability guarantee suitable for a safety-relevant alert on its own.

**EU/Sweden fit and reliability fit anti-correlate for Supabase specifically.** Supabase is simultaneously the *best* finalist on EU data residency (explicit Stockholm pinning, self-serve DPA) and the *worst* finalist on reliability fit for this project (free-tier auto-pause). A user who weights EU residency heavily would be pulled toward the option Dimension 2 says fits this project's usage pattern worst — a genuine trade-off to flag explicitly rather than let a decision matrix average away.

## Recommendations

*Confidence basis noted per recommendation; feeds this project's forthcoming architecture/spec work (technical pack `Feeds`: architecture spine, feasibility brief, roadmap risk).*

1. **Primary recommendation: GitHub Actions scheduled workflows**, made public (or paired with GitHub Pro at $4/mo if privacy is preferred) to sidestep the private-repo scheduling restriction. Basis: highest confidence on cost ($0, verified, no historical cron-specific cuts [1][110][111]), on parent-company stability (high confidence [115]), on setup simplicity and language freedom (high confidence, real hobby examples found [76][77]), and on built-in failure alerting (high confidence, unique among the four [46]). Its timing-delay problem is real and well-evidenced (high confidence [41][42][43][44]) but is a *degradation* of precision, not a silent total failure — the workflow still visibly ran, just late — which is more tolerable for a system with an escalating, multi-checkpoint alert design (24h → 12h → shorter) than for a single-shot trigger.
2. **Do not trust any single free scheduler's on-time delivery for the final, most time-critical check.** Layer an independent watchdog — e.g., a second cheap/free trigger at a different time offset on a *different* platform, or a dead-man's-switch monitor (healthchecks.io/UptimeRobot Heartbeat, both cut in Dimension 1 as *standalone* schedulers but well-suited as "did my real scheduler actually fire" watchdogs) that alerts the user directly if the primary check hasn't reported in on schedule. Basis: medium-high confidence — every finalist's own documentation or dated incident history shows a real gap [7][9][47][49][51][60][68][72].
3. **If Supabase Cron is chosen instead (e.g., because the project already needs a Postgres database, or EU data residency is a hard requirement)**, budget for an explicit keep-alive mechanism (a genuine DB-touching ping, not a health-endpoint ping) to prevent the free-tier auto-pause during the project's long planned-idle stretches, and treat this as a known, accepted maintenance cost, not an edge case. Basis: high confidence, directly evidenced and long-standing [72][73][74][75].
4. **Avoid Vercel Hobby, Fly.io, cron-job.org/EasyCron as standalone, and healthchecks.io/UptimeRobot as standalone** — each fails a hard gate or requires infrastructure this project doesn't otherwise need (Dimension 1). Basis: high confidence, verified against live official docs/pricing [31][33][35][20][26][28][29].
5. **Keep AWS EventBridge Scheduler + Lambda as a documented fallback**, not the first choice — it is technically capable and has the best regional story for Sweden (`eu-north-1`/Stockholm confirmed usable [106]) but adds a credit-card requirement and the 2025 account-plan-structure gotcha [13][14] that fight the project's "as close to zero-touch as possible" goal.

## Open questions

- **Exact escalation-cadence timing (24h → 12h → ? → ?) and what "watchdog" mechanism to pair with the primary scheduler** were flagged in the forged idea as deferred to design and are not resolved by this research — they are implementation decisions for `bmad-spec`/`bmad-prd`, informed by but not answered by this report.
- **Whether GitHub's private-repo `schedule` restriction is truly absolute on Free**, or has any exception, remains only community-corroborated (medium confidence) — official GitHub documentation is silent either way [5]. A definitive test (creating a private repo and observing whether `schedule` fires) would resolve this in minutes if the team wants certainty before committing.
- **Cloudflare's actual retry behavior on a failed `scheduled()` invocation** is not confirmed by any primary Cloudflare source — only vendor blogs with a commercial interest in the answer [9][50]. Would need a direct test or a Cloudflare support/community-forum confirmation to move past medium/low confidence.
- **Which exact city/datacenter Deno Deploy's `eu` region flag resolves to**, and **Supabase Edge Functions' execution locality** (as distinct from the Postgres database's pinned region), were not confirmed this session [101][94] — relevant only if EU data residency becomes a hard requirement.
- **VAT/billing quirks for Swedish/EU customers** across all six platforms were not researched (out of budget this session) — low priority given all four finalists are free at this volume, but worth a quick check before ever crossing into a paid tier.

## Sources

| [n] | Finding it supports | Publisher | Pub date | Accessed | Confidence |
|---|---|---|---|---|---|
| [1] | Actions billing/free minutes | [GitHub Docs](https://docs.github.com/en/billing/concepts/product-billing/github-actions) | undated | 2026-09-12 | high |
| [2] | Schedule trigger mechanics, delay, 60-day disable | [GitHub Docs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) | undated | 2026-09-12 | high |
| [3] | Troubleshooting scheduled-workflow delay | [GitHub Docs](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows) | undated | 2026-09-12 | high |
| [4] | Runners have no personal-device dependency | [GitHub Docs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job) | undated | 2026-09-12 | high |
| [5] | Private-repo `schedule` disabled on Free | [devActivity / DEV Community](https://devactivity.com/posts/apps-tools/github-actions-cron-schedules-uncovering-the-hidden-free-tier-hurdle-for-private-repos/) | undated | 2026-09-12 | medium |
| [6] | Workers Free-plan limits | [Cloudflare Docs](https://developers.cloudflare.com/workers/platform/limits/) | undated | 2026-09-12 | high |
| [7] | Cron Triggers mechanics, propagation delay | [Cloudflare Docs](https://developers.cloudflare.com/workers/configuration/cron-triggers/) | 2026-09-04 | 2026-09-12 | high |
| [8] | Workers pricing example | [Cloudflare Docs](https://developers.cloudflare.com/workers/platform/pricing/) | undated | 2026-09-12 | high |
| [9] | No confirmed auto-retry on Cron Trigger failure | [Runhooks.app / CronAlert.com](https://runhooks.app/blog/cloudflare-workers-cron-triggers-limits/) | 2026 | 2026-09-12 | low |
| [10] | Lambda Always Free tier | [AWS](https://aws.amazon.com/lambda/pricing/) | undated | 2026-09-12 | high |
| [11] | EventBridge Scheduler free tier | [AWS](https://aws.amazon.com/eventbridge/pricing/) | undated | 2026-09-12 | high |
| [12] | EventBridge Scheduler cron/timezone support | [AWS Docs](https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html) | undated | 2026-09-12 | high |
| [13] | AWS card-verification requirement | [AWS](https://aws.amazon.com/free/registration-faqs/) | undated | 2026-09-12 | high |
| [14] | 2025 AWS Free Tier restructuring | [AWS News Blog](https://aws.amazon.com/blogs/aws/aws-free-tier-update-new-customers-can-get-started-and-explore-aws-with-up-to-200-in-credits/) | 2025 | 2026-09-12 | high |
| [15] | EventBridge Scheduler expanded to all regions | [AWS](https://aws.amazon.com/about-aws/whats-new/2025/07/amazon-eventbridge-scheduler-all-aws-regions/) | 2025-07-16 | 2026-09-12 | medium |
| [16] | Cloud Scheduler per-job pricing | [Google Cloud](https://cloud.google.com/scheduler/pricing) | undated | 2026-09-12 | high |
| [17] | Cloud Scheduler cron/comma-list support | [Google Cloud Docs (mirror)](https://docs.cloud.google.cn/scheduler/docs/configuring/cron-job-schedules) | undated | 2026-09-12 | medium-high |
| [18] | Cloud Functions 1st-gen free tier | [Google Cloud](https://cloud.google.com/functions/pricing-1stgen) | undated | 2026-09-12 | high |
| [19] | GCP billing account/card requirement | [Google Cloud](https://docs.cloud.google.com/free/docs/free-cloud-features) | undated | 2026-09-12 | high |
| [20] | cron-job.org free, no published cap | [cron-job.org](https://cron-job.org/en/faq/) | undated | 2026-09-12 | high |
| [21] | cron-job.org no SLA / can delay failing jobs | [cron-job.org](https://cron-job.org/en/tos/) | undated | 2026-09-12 | high |
| [22] | cron-job.org timeout/error behavior | [cron-job.org blog](https://blog.cron-job.org/service/2021/12/01/errors-explained-timeout.html) | 2021-12-01 | 2026-09-12 | high |
| [23] | cron-job.org is trigger-only, needs public endpoint | [DEV Community (arxeiss)](https://dev.to/arxeiss/cron-job-org-free-cron-service-2ge) | undated | 2026-09-12 | high |
| [24] | Cron-service landscape comparison (aggregator) | [DEV Community (ronency)](https://dev.to/ronency/best-external-cron-job-services-compared-2026-8a3) | 2026 | 2026-09-12 | low |
| [25] | Anecdote: fled GitHub Actions delay to cron-job.org | [lindsay.codes](https://lindsay.codes/posts/cron-job-dot-org/index.html) | undated | 2026-09-12 | low |
| [26] | EasyCron free-tier limits, real cheapest-paid price | [EasyCron](https://www.easycron.com/pricing) | undated | 2026-09-12 | high |
| [27] | EasyCron free plan needs manual monthly renewal | [EasyCron](https://www.easycron.com/faq/Will-my-free-plan-expire) | undated | 2026-09-12 | high |
| [28] | healthchecks.io is a monitor, not a scheduler | [Healthchecks.io](https://healthchecks.io/docs/monitoring_cron_jobs/) | undated | 2026-09-12 | high |
| [29] | UptimeRobot Heartbeat is a monitor, not a scheduler | [UptimeRobot](https://uptimerobot.com/cron-job-monitoring/) | undated | 2026-09-12 | high |
| [30] | Deno.cron cron syntax / classic docs | [Deno Docs](https://docs.deno.com/deploy/reference/cron/) | undated | 2026-09-12 | high |
| [31] | Vercel Hobby cron: once/day, ±59min precision | [Vercel Docs](https://vercel.com/docs/cron-jobs/usage-and-pricing) | undated | 2026-09-12 | high |
| [32] | Vercel plan limits | [Vercel Docs](https://vercel.com/docs/limits) | undated | 2026-09-12 | high |
| [33] | Render Cron Jobs: no free tier, $1/mo minimum | [Render Docs](https://render.com/docs/cronjobs) | undated | 2026-09-12 | high |
| [34] | Fly.io scheduled machines: fixed cadences only | [Fly.io Community](https://community.fly.io/t/new-feature-scheduled-machines/7398) | 2022 | 2026-09-12 | medium |
| [35] | Fly.io free-tier discontinued Oct 2024 | [Fly.io Docs](https://fly.io/docs/about/discontinued-plans/) | 2024-10-07 | 2026-09-12 | high |
| [36] | Supabase Cron / schedule-functions mechanics | [Supabase Docs](https://supabase.com/docs/guides/cron) | undated | 2026-09-12 | high |
| [37] | Supabase Edge Function invocation free tier | [Supabase](https://supabase.com/pricing) | undated | 2026-09-12 | high |
| [38] | Vercel Hobby cron limits corroboration | [Runhooks.app](https://runhooks.app/blog/vercel-hobby-cron-job-limits-explained/) | 2026 | 2026-09-12 | medium |
| [39] | Vercel Hobby vs Pro cron corroboration | [cronpreview.com](https://cronpreview.com/guides/vercel-cron-hobby-vs-pro) | undated | 2026-09-12 | medium |
| [40] | Vercel Hobby cron error message corroboration | [ZIDOOKA](https://www.zidooka.com/archives/2991) | undated | 2026-09-12 | medium |
| [41] | GH Actions delay measured 1h40m→4h30m+ in 2026 | [GitHub Issues (actions/runner#4468)](https://github.com/actions/runner/issues/4468) | 2026-06 | 2026-09-12 | high |
| [42] | GH Actions effective fire-rate throttling | [DEV Community (rulestack)](https://dev.to/rulestack/your-github-actions-cron-fires-less-often-than-you-declared-what-we-measured-and-how-to-design-for-80f) | undated | 2026-09-12 | medium |
| [43] | GH Actions delay reports, 2021 | [Stack Overflow](https://stackoverflow.com/questions/67077120/github-actions-cronjob-trigger-seems-to-trigger-an-hour-later) | 2021-04-13 | 2026-09-12 | medium |
| [44] | GH Actions delay/no-guarantee reports, 2025 | [Stack Overflow](https://stackoverflow.com/questions/79534419/reliability-issues-with-github-actions-with-cron-based-schedule) | 2025-03-25 | 2026-09-12 | medium |
| [45] | GH Actions default-branch-only gotcha | [Cronuru](https://cronuru.com/guides/github-actions-scheduled-workflows) | undated | 2026-09-12 | medium |
| [46] | GH Actions built-in failure email notifications | [GitHub Docs](https://docs.github.com/en/actions/concepts/workflows-and-actions/notifications-for-workflow-runs) | undated | 2026-09-12 | high |
| [47] | Cloudflare Cron Triggers degraded incident, Sep 2026 | [Cloudflare Status](https://www.cloudflarestatus.com/incidents/sjs8s0q2x4hw) | 2026-09-09 | 2026-09-12 | high |
| [48] | Cloudflare Cron Trigger delay incident, Mar 2026 | [Cloudflare Status](https://new.cloudflarestatus.com/incidents/sn641zvm39tz) | 2026-03-24 | 2026-09-12 | high |
| [49] | Cron Trigger silently stopped 5+ hours | [Cloudflare Community](https://community.cloudflare.com/t/cron-trigger-silently-stopped-dispatching/928936) | 2026-05-21 | 2026-09-12 | medium |
| [50] | No confirmed retry, corroborating vendor source | [crontap.com](https://crontap.com/blog/cloudflare-workers-cron-minute-limit) | undated | 2026-09-12 | medium |
| [51] | Deno.cron at-least-once, backoffSchedule, top-level | [Deno Docs](https://docs.deno.com/deploy/reference/cron/) | undated | 2026-09-12 | high |
| [52] | Deno.cron "unstable API" note | [Deno Docs](https://docs.deno.com/runtime/fundamentals/cron/) | undated | 2026-09-12 | high |
| [53] | Top-level cron detection bug, 18+ months open | [GitHub (denoland/deploy_feedback#699)](https://github.com/denoland/deploy_feedback/issues/699) | 2024-08-12 | 2026-09-12 | high |
| [54] | Silent cron registration failure bug | [GitHub (denoland/deploy_feedback#563)](https://github.com/denoland/deploy_feedback/issues/563) | undated | 2026-09-12 | medium |
| [55] | Deno Deploy 2025 incidents incl. ~40h outage | [Deno Status](https://denostatus.com/cmhqspm1p024m94xhj4tllutl) | 2025-11 | 2026-09-12 | high |
| [56] | Deno Deploy V2 reached GA Feb 2026 | [Deno (official blog)](https://deno.com/blog/deno-deploy-is-ga) | 2026-02-03 | 2026-09-12 | high |
| [57] | V1 vs V2 uptime comparison anecdote | [Reddit r/Deno](https://www.reddit.com/r/Deno/comments/1om4585/deploy_v2_do_we_get_a_better_service_if_we_pay/) | undated | 2026-09-12 | medium |
| [58] | 6-month Deno Deploy retrospective | [AgntWork blog](https://agntwork.com/deno-deploy-in-2026-5-things-after-6-months-of-use/) | 2026 | 2026-09-12 | low-medium |
| [59] | "Beta-quality" Deno Deploy experience, 2025 | [macchaffee.com](https://www.macchaffee.com/blog/2025/deno/) | 2025 | 2026-09-12 | medium |
| [60] | pg_net fire-and-forget HTTP semantics | [GitHub (supabase/pg_net)](https://github.com/supabase/pg_net/blob/a4bd5764/docs/api.md) | undated | 2026-09-12 | high |
| [61] | Manual retry-table workaround pattern | [GitHub (supabase/pg_net README)](https://github.com/supabase/pg_net) | undated | 2026-09-12 | high |
| [62] | pg_net lacks native retries, batching risk | [GitHub (supabase/pg_net#62)](https://github.com/supabase/pg_net/issues/62) | undated | 2026-09-12 | medium |
| [63] | Supabase Cron launch, Dec 2024 | [Supabase (changelog/blog)](https://supabase.com/blog/supabase-cron) | 2024-12-10 | 2026-09-12 | high |
| [64] | verify_jwt silent-401 gotcha | [DEV Community](https://dev.to/mike_clarke_50a95013f5c59/the-function-was-deployed-healthy-and-never-ran-once-1hgd) | undated | 2026-09-12 | medium |
| [65] | Silent 6-week data-sync break, free tier | [dashbuilds.dev](https://dashbuilds.dev/blog/28-cron-jobs-on-a-free-database) | 2026-era | 2026-09-12 | medium |
| [66] | pg_cron worker can die, needs manual reboot | [Supabase Docs](https://supabase.com/docs/guides/troubleshooting/pgcron-debugging-guide-n1KTaz) | undated | 2026-09-12 | high |
| [67] | Connection-pool exhaustion incident | [2muchcoffee.com](https://2muchcoffee.com/blog/postgres-pool-exhaustion-vercel-supabase-2026/) | 2026 | 2026-09-12 | medium |
| [68] | No retry/alerting, silent pause on incident | [crontap.com](https://crontap.com/guides/supabase-cron-jobs) | 2026 | 2026-09-12 | medium |
| [69] | Deno cron failure alerting requires Sentry add-on | [Sentry Docs](https://docs.sentry.io/platforms/javascript/guides/deno/crons/) | undated | 2026-09-12 | high |
| [70] | Supabase cron monitoring workaround patterns | [Coremity](https://coremity.com/supabase-how-to-monitor-cron-jobs/) | undated | 2026-09-12 | high |
| [71] | Third-party paid cron-monitor alternative | [CronJobPro](https://cronjobpro.com/blog/supabase-cron) | undated | 2026-09-12 | high |
| [72] | Free-tier project auto-pause after ~7 days | [Supabase Docs](https://supabase.com/docs/guides/platform/free-project-pausing) | undated | 2026-09-12 | high |
| [73] | Free-project pausing pain point, 2022 | [Reddit r/Supabase](https://www.reddit.com/r/Supabase/comments/zxfbg1/free_projects_are_paused_after_1_week_of/) | 2022-12-28 | 2026-09-12 | high |
| [74] | Free-project pausing pain point, 2025 | [Reddit r/Supabase](https://www.reddit.com/r/Supabase/comments/1mk881i/how_to_prevent_a_free_project_from_pausing/) | 2025 | 2026-09-12 | high |
| [75] | Keep-alive tool; wrong-endpoint-ping gotcha | [GitHub (Amo95/supawake)](https://github.com/amo95/supawake) | undated | 2026-09-12 | medium |
| [76] | Real hobby weather-bot repos on GH Actions | [GitHub (weather-sentinel et al.)](https://github.com/nipuna-lakruwan/weather-sentinel) | undated | 2026-09-12 | high |
| [77] | Minimal GH Actions YAML setup example | [nixx.dev](https://nixx.dev/blog/automating-blog-post-scheduling-with-github-actions-261f8f45) | undated | 2026-09-12 | high |
| [78] | GH Actions min interval/UTC/delay | [Earthly Blog](https://earthly.dev/blog/cronjobs-for-github-actions/) | undated | 2026-09-12 | high |
| [79] | Billing-lock silently stops free-tier Actions | [Reddit r/github](https://www.reddit.com/r/github/comments/1kmasu9/github_free_tier_actions_dont_run_anymore_because/) | undated | 2026-09-12 | medium |
| [80] | Billing-lock corroboration | [DEV Community](https://dev.to/devactivity/unexpected-roadblocks-github-actions-billing-locks-on-free-accounts-impacting-software-engineering-13i7) | undated | 2026-09-12 | medium |
| [81] | Minute-exhaustion silent-block incident | [Captain Random](https://captainrandom.co.uk/learning/github-shipping/actions-billing/) | undated ("mid-2026") | 2026-09-12 | medium |
| [82] | Minimal Cloudflare Cron Trigger setup (2 files) | [Cronuru](https://cronuru.com/guides/cloudflare-workers-cron-triggers) | 2026-07-03 | 2026-09-12 | high |
| [83] | Cloudflare Cron Trigger setup corroboration | [flaviocopes.com](https://flaviocopes.com/cloudflare-cron-triggers/) | undated | 2026-09-12 | high |
| [84] | Cloudflare Workers secrets mechanism | [Cloudflare Docs](https://developers.cloudflare.com/workers/configuration/secrets/) | undated | 2026-09-12 | high |
| [85] | Local-dev secrets corroboration | [Stack Overflow](https://stackoverflow.com/questions/71298357/local-development-with-secrets) | undated | 2026-09-12 | high |
| [86] | Free-tier CPU-time cap for Cron Triggers | [AltusLog](https://altuslog.io/cloudflare-workers-cost-optimization-7-patterns/) | undated | 2026-09-12 | high |
| [87] | Outbound fetch/subrequest limits | [Cloudflare Docs](https://developers.cloudflare.com/workers/configuration/integrations/apis/) | undated | 2026-09-12 | high |
| [88] | 24-line Deno.cron weather example | [Deno (official blog)](https://deno.com/blog/cron) | undated | 2026-09-12 | high |
| [89] | Deno Deploy env vars/secrets mechanism | [Deno Docs](https://docs.deno.com/deploy/reference/env_vars_and_contexts/) | undated | 2026-09-12 | high |
| [90] | Deno fetch() has no default egress restriction | [Deno Docs](https://docs.deno.com/api/deno/fetch/) | undated | 2026-09-12 | medium |
| [91] | Real hobby project: pg_cron + Edge Functions | [GitHub (TacticalReader/Routineforge)](https://github.com/TacticalReader/Routineforge) | undated | 2026-09-12 | high |
| [92] | Supabase pg_cron setup guide (SQL/extensions) | [dashbuilds.dev](https://dashbuilds.dev/blog/supabase-pg-cron-complete-guide) | undated | 2026-09-12 | high |
| [93] | Supabase free-project keep-alive guide | [DEV Community](https://dev.to/krishna-builds-dev/how-to-keep-your-supabase-free-project-active-no-cost-cron-with-github-actions-1nnd) | undated | 2026-09-12 | high |
| [94] | Supabase region options incl. Stockholm | [Supabase Docs](https://supabase.com/docs/guides/platform/regions) | undated | 2026-09-12 | high |
| [95] | Supabase GDPR region-choice guidance | [Supabase Docs](https://supabase.com/docs/guides/security/gdpr-compliance) | undated | 2026-09-12 | high |
| [96] | Supabase self-serve DPA | [Supabase Legal](https://supabase.com/legal/customer-resources/data-processing-addendum) | 2026-06-01 | 2026-09-12 | high |
| [97] | Cloudflare Regional Services excludes Cron Triggers | [Cloudflare Docs](https://developers.cloudflare.com/data-localization/how-to/workers/) | undated | 2026-09-12 | high |
| [98] | Full data-localization requires Enterprise | [Cloudflare Docs](https://developers.cloudflare.com/data-localization/regional-services/) | undated | 2026-09-12 | medium |
| [99] | KV EU jurisdictions in private beta | [Cloudflare Docs](https://developers.cloudflare.com/kv/reference/data-location/) | 2026-07-31 | 2026-09-12 | high |
| [100] | Cloudflare DPA auto-incorporated, self-serve plans | [Cloudflare](https://www.cloudflare.com/cloudflare-customer-dpa/) | undated | 2026-09-12 | high |
| [101] | Deno Deploy explicit us/eu/global region flag | [Deno Docs](https://docs.deno.com/deploy/migration_guide/) | undated | 2026-09-12 | high |
| [102] | Deno Deploy DPA not included below Enterprise | [Deno.com](https://deno.com/deploy/pricing) | undated | 2026-09-12 | high |
| [103] | GH Actions runners: no region control on free/personal | [GitHub Docs](https://docs.github.com/en/organizations/managing-organization-settings/about-azure-private-networking-for-github-hosted-runners-in-your-organization) | undated | 2026-09-12 | high |
| [104] | GitHub DPA framed around Enterprise customers | [GitHub](https://github.com/customer-terms/github-data-protection-agreement) | undated | 2026-09-12 | medium |
| [105] | AWS Global DPA auto-incorporated for all customers | [AWS](https://aws.amazon.com/service-terms/) | undated | 2026-09-12 | high |
| [106] | eu-north-1 (Stockholm) usable for EventBridge+Lambda | [AWS re:Post](https://repost.aws/articles/ARIw6q_ozaTmqqI25Eq4YIcQ/a-step-by-step-guide-to-cross-account-and-cross-region-events-with-eventbridge) | undated | 2026-09-12 | medium |
| [107] | Cloud Scheduler unavailable in europe-north1 | [Google Cloud Docs](https://docs.cloud.google.com/scheduler/docs/locations) | undated | 2026-09-12 | high |
| [108] | europe-north1 exists for other GCP compute services | [Google Cloud Docs](https://docs.cloud.google.com/batch/docs/locations) | undated | 2026-09-12 | medium |
| [109] | GCP CDPA requires explicit self-serve acceptance | [Google Cloud Console Help](https://support.google.com/cloud/answer/6329727) | undated | 2026-09-12 | high |
| [110] | No historical GH Actions cron-specific free-tier cut | [GitHub Changelog](https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/) | 2025-12-16 | 2026-09-12 | high |
| [111] | GH Actions 2026 pricing change scope/impact | [GitHub roadmap #1196](https://github.com/github/roadmap/issues/1196) | 2025-12 | 2026-09-12 | high |
| [112] | Deno Cron initially missing from next-gen Deploy | [Deno Docs GitHub repo diff](https://github.com/denoland/docs/blob/13edb904fa8c8d5548b40e265f04242a3f61f803/deploy/early-access/index.md) | undated (commit-dated) | 2026-09-12 | high |
| [113] | Community trust reaction to cron removal | [Reddit r/Deno](https://www.reddit.com/r/Deno/comments/1lg2bc7/the_next_deno_deploy_changes_number_of_regions_6/) | 2025 | 2026-09-12 | medium |
| [114] | Cron restored, Deploy Classic being sunset | [Deno Docs](https://docs.deno.com/deploy/migration_guide/) | undated | 2026-09-12 | high |
| [115] | Microsoft FY2025 financial results | [Microsoft Corp.](https://news.microsoft.com/source/2025/07/30/microsoft-cloud-and-ai-strength-fuels-fourth-quarter-results/) | 2025-07-30 | 2026-09-12 | high |
| [116] | Cloudflare FY2025 financial results | [Cloudflare, Inc.](https://www.cloudflare.com/press/press-releases/2026/cloudflare-announces-fourth-quarter-and-fiscal-year-2025-financial-results/) | 2026-02-10 | 2026-09-12 | high |
| [117] | Deno Company funding history (~$26M, 2022) | [Deno (official blog)](https://deno.com/blog/series-a) | 2022-06-21 | 2026-09-12 | high |
| [118] | Deno's own rebuttal to "is dying" criticism | [Deno (official blog)](https://deno.com/blog/greatly-exaggerated) | 2025-05-20 | 2026-09-12 | high |
| [119] | Independent critique: region count / KV decline | [David Bushell](https://dbushell.com/2025/04/28/denos-decline/) | 2025-04-28 | 2026-09-12 | medium |
| [120] | Supabase Series D/E funding (~$500M+) | [Supabase (official blog)](https://supabase.com/blog/series-e) | 2025-10-03 | 2026-09-12 | high |
| [121] | Supabase Series D press coverage | [Fortune](https://fortune.com/2025/04/22/exclusive-supabase-raises-200-million-series-d-at-2-billion-valuation/) | 2025-04-22 | 2026-09-12 | high |
| [122] | Unverified Supabase Series F (2026) | [Tracxn](https://tracxn.com/d/companies/supabase/__Eu-Qv0PGLlKKydFQbekQazgnqS4w5jeSDfFyg6oGPjg/funding-and-investors) | undated | 2026-09-12 | low |
