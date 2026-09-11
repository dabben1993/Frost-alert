# Forged Idea: Frost Alert for Overwintering Bonsai

## What it is

A personal automation that warns you (and, with easy reconfiguration, anyone else) before local temperature threatens outdoor plants, so trees get moved to overwintering in time.

## Context for this iteration

- **Primary user is based in Sweden.** This is the location the first build targets and should be assumed as the default context for research (e.g. weather data coverage/accuracy for Sweden, availability and cost of notification/hosting services there). The config must still stay location-agnostic under the hood so a friend elsewhere can set their own location — Sweden is the concrete case to build and test against first, not a hardcoded assumption in the design.

## Locked decisions

- **Scope**: Single-user personal automation, not a hosted multi-tenant service. No accounts, no handling other people's keys/data. Sharing = cloning a repo/config, not signing up for a service.
- **Config, not code**: Location, temperature scale, and alert threshold are set through an intuitive setup flow (e.g. interactive CLI wizard or simple config UI). Never requires editing source code. This is what makes it usable by a friend or by future-you after moving.
- **"No app" constraint, correctly scoped**: Rules out building/maintaining a custom native app (Android/macOS). Does NOT rule out installing an existing third-party app (WhatsApp, Telegram, Pushover, ntfy, etc.) to receive alerts — those are fine, pending confirming installability on the target device.
- **Trigger model**: Forecast-based, not live-current-temperature-based. A live reading crossing the threshold gives no time to act.
- **Escalating check cadence**: First check/alert at the ~24h-out forecast (awareness). If unacknowledged, re-check and re-alert at progressively shorter windows (12h, then shorter still — exact steps deferred to design). Purpose: multiple chances to notice, tightening urgency as the cold snap approaches.
- **Acknowledgment = seasonal toggle, not nightly snooze**: Overwintering is a one-time seasonal move. Confirming "plants are in overwintering" suspends ALL alerts until the user manually turns it back on (e.g. in spring). This was explicitly decided over a "snooze tonight only" model because bonsai overwintering isn't a nightly in/out cycle.
- **Alert threshold is user-set, not hardcoded to 0°C**: Forecast error and radiative frost mean the pot/soil can be colder than the official air-temperature forecast. Default should include a safety margin above literal freezing (e.g. ~3°C as a starting point), tunable down per user once they learn their own microclimate. Expressed in the user's chosen scale (°C or °F).
- **Hosting must not depend on a personal always-on device**: No Raspberry Pi/home server available. The automation must run on a scheduler that doesn't care whether a laptop is open or asleep. Cost preference: $0 if at all possible; cheapest viable option otherwise. Specific platform is a research decision, not a forge decision.

## Rejected / narrowed options (and why)

- **Hosted multi-user product** — rejected. Would require accounts and handling other users' data/keys; explicitly not wanted. "Customizable for anyone" means easy self-serve config, not a shared service.
- **Native Android/macOS app** — rejected as a delivery mechanism to build. Not a hard device restriction (the phone can install apps) — it's a "don't want to build and maintain a custom app" decision.
- **Trigger on live current temperature** — rejected. Gives no lead time to physically move trees.
- **Nightly snooze model for acknowledgment** — rejected in favor of a seasonal on/off toggle, because it doesn't match how bonsai overwintering actually works (one seasonal move, not nightly).
- **Hardcoded 0°C threshold** — rejected. Real risk is at/above 0°C forecast due to forecast error and radiative frost; threshold needs to be user-configurable with a sane non-zero default.

## Weak points that survived (carry forward, don't ignore)

- Exact escalation cadence steps (24h → 12h → ? → ?) are unresolved — "whatever makes sense" was deferred to design/research, not decided.
- The acknowledgment mechanism needs a channel that supports two-way interaction (reply, button, or link), which meaningfully narrows the notification channel shortlist — this constraint must carry into the channel research, not get lost.
- How a friend inputs "my location" (city name, postal code, coordinates) is unresolved and affects which weather API is workable.
- Actual notification wording/content ("what does the message say") was explicitly flagged by the user as unresolved and still needs fleshing out.

## Open research questions (ready for bmad-deep-recon / technical research)

Three separate research areas remain open. Run each as its **own** research session (separate `bmad-deep-recon` invocation) to keep context focused — each block below is self-contained and can be pasted on its own without the others.

---

### Research 1 of 3: Weather forecast API

**Research context: Frost Alert automation for overwintering bonsai — weather API selection**

Building a personal (not multi-tenant) automation that checks a weather forecast for a user-configured location and sends an escalating alert before temperatures threaten outdoor plants, so they can be moved to overwintering in time. Primary user is based in **Sweden** — treat this as the concrete location to validate against, though the eventual config must support arbitrary locations for other users.

Please research and compare free or very-low-cost weather forecast APIs that:

- Provide hourly (or near-hourly) forecast data at least 24h out, ideally further.
- Have strong coverage and accuracy for **Sweden** specifically (e.g. national meteorological services like SMHI, as well as general-purpose global providers) — compare a Sweden-specific/regional source against global options.
- Accept arbitrary locations — ideally via city name or postal code, or are easily paired with a free geocoding step if they require lat/long.
- Are reliable/accurate enough for a frost-risk use case (i.e. good at predicting overnight lows, not just daily highs).

Compare: free-tier limits/rate limits, accuracy reputation (especially for low-temperature/overnight forecasts), ease of integration, and whether the API is realistically free long-term for a single-user hobby automation.

Constraint: no cost is ideal, cheapest-viable is the fallback.

---

### Research 2 of 3: Notification channel

**Research context: Frost Alert automation for overwintering bonsai — notification channel selection**

Building a personal (not multi-tenant) automation that sends an escalating alert (24h out, then re-alerting at shorter windows as a cold night approaches) to warn a user before temperatures threaten outdoor plants. Primary user is based in **Sweden**, has a corporate Android phone that can install apps, but does not want a custom-built native app.

Please research and compare free or very-low-cost notification channels that:

- Can deliver push-style alerts reliably to a stock Android phone.
- Support **two-way acknowledgment** (a reply, an inline button, or a clickable link hitting a simple endpoint) — needed so the user can confirm "plants moved to overwintering" and stop further alerts for the rest of the season.
- Don't require building/maintaining a custom native app — installing an existing app (e.g. Telegram, WhatsApp, Pushover, ntfy) is acceptable.
- Work well for a user based in Sweden (e.g. check for any regional restrictions, costs, or reliability quirks — for example SMS costs/providers in Sweden if SMS is considered).

Candidates to evaluate include (but aren't limited to): a Telegram bot, WhatsApp (Business API or otherwise), Pushover, ntfy.sh, and email with an action link.

Compare: cost (ideally $0), setup complexity, reliability of delivery, and how well each supports the acknowledgment/interaction requirement above.

Constraint: no cost is ideal, cheapest-viable is the fallback; must not require a custom native app.

---

### Research 3 of 3: Hosting / scheduling

**Research context: Frost Alert automation for overwintering bonsai — hosting and scheduling selection**

Building a personal (not multi-tenant) automation that runs scheduled checks (e.g. at 24h, 12h, and shorter windows out from an upcoming cold night) against a weather forecast and sends alerts. No personal always-on device is available (no home server/Raspberry Pi) — the schedule must run independent of whether the user's own laptop/phone is on.

Please research and compare free or cheapest-viable ways to run a small scheduled job that:

- Fires reliably on a schedule (including multiple times per day, at potentially precise times like "X hours before a forecast cold night") without depending on a personally-owned always-on device.
- Stays within free tiers for a single-user hobby workload (very low request volume).
- Is straightforward enough to set up and maintain without heavy infra expertise.

Candidates to evaluate include (but aren't limited to): GitHub Actions scheduled workflows, serverless functions on a cron trigger (e.g. Cloudflare Workers, AWS Lambda + EventBridge), and any other $0-tier scheduler options. Note any availability/billing quirks relevant to a user based in Sweden/EU (e.g. data residency, regional pricing) if applicable.

Compare: reliability, free-tier limits, timing precision (can it hit specific hour-offsets reliably?), and long-term sustainability at $0 cost.

Constraint: no cost is ideal, cheapest-viable is the fallback; no dependency on a personal device staying powered on.

---

## Suggested next steps

- Run **bmad-deep-recon** (technical research type) three times — once per block above — each in its own session to avoid context rot.
- Once research narrows each shortlist, feed this file plus all three research outputs into **bmad-spec** or **bmad-prd** to define the concrete build.
