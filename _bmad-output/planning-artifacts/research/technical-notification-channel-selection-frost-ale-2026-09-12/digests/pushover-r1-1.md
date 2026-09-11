# Digest: Pushover (round 1)

## Findings

1. **[pricing]** Individual Pushover license is a one-time $4.99 USD purchase per platform (iPhone/iPad, Android, Desktop), no subscription fee; 30-day free trial via the apps. — Pushover, LLC, live pricing page, accessed 2026-09-12, confidence: high. https://pushover.net/pricing
2. **[pricing]** Sending via API/e-mail gateway is free up to 10,000 messages/month per account (25,000/month for Teams); as of 2026-05-01 the limit became per-account (was per-application). — Pushover, LLC (API docs 2026-04-08 blog), accessed 2026-09-12, confidence: high. https://pushover.net/api ; https://blog.pushover.net/posts/2026/4/app-limits
3. **[pricing]** Independent blogger corroborates one-time license cost and the May 2026 quota change; "always felt more than fair," no subscription creep. — Deuts Log (independent blog), 2026-04-29, accessed 2026-09-12, confidence: medium. https://deuts.org/p/pushover-api-limit/
4. **[mechanism]** "Emergency Priority" (priority=2) messages repeat (sound+vibration) at a configurable `retry` interval (min 30s) until acknowledged or `expire` elapses (max 10800s, capped 50 retries). Returns a `receipt` ID; an optional `callback` URL parameter lets Pushover POST to the sender's own endpoint the instant the user acknowledges — directly usable to flip a remote "plants moved" toggle. — Pushover, LLC official API docs, accessed 2026-09-12, confidence: high. https://pushover.net/api
5. **[mechanism]** A simpler `url` parameter renders as a tappable link in the notification — usable for a "click to silence" pattern without receipt polling, but lacks retry/re-alert semantics. — same source, confidence: high.
6. **[mechanism]** Sending is a single HTTPS POST (form-urlencoded/JSON) to `api.pushover.net/1/messages.json` with `token`, `user`, `message`; no OAuth. Setup: register a free "application" for a token, install Android app, get user key. — same source, confidence: high.
7. **[reliability]** Pushover's own support KB: normal delivery "within a second or so, often within a few hundred milliseconds"; known delay causes enumerated (broken IPv6 path → 30-60s fallback, Android battery optimization, DND, e-mail gateway latency) with fixes; public status page exists. — Pushover support KB, accessed 2026-09-12, confidence: high. https://support.pushover.net/i281-notifications-are-received-but-after-significant-delay
8. **[reliability]** Recent (2026) multi-minute delay reports via Home Assistant's Pushover integration traced to broken/misconfigured IPv6 on the sending host/ISP, not a Pushover-side outage; fixing/disabling IPv6 restored instant delivery; maintainer closed the GitHub issue confirming root cause. — Reddit r/homeassistant (2026-06-25), GitHub home-assistant/core#173003 (2026-06), accessed 2026-09-12, confidence: medium.
9. **[reliability]** Same IPv6-delay pattern documented as far back as 2021 on the Home Assistant community forum — a known environmental gotcha, not a Pushover service defect. — Home Assistant Community Forum, accessed 2026-09-12, confidence: medium.
10. **[ecosystem/GDPR]** Privacy policy (updated 2026-05-01) explicitly addresses EEA/GDPR: legal bases, named sub-processors (Apple, Google, Cloudflare, FastMail, PayPal, Stripe, rsync.net, Vultr, Postmark), US data transfers under SCCs, EEA-style data subject rights. — Pushover, LLC, accessed 2026-09-12, confidence: high. https://pushover.net/privacy
11. **[pricing]** Payment via PayPal/Stripe or Google Play in-app purchase — all routinely support Sweden/EU billing; no Sweden-specific restriction found. — same source, confidence: medium.
12. **[ecosystem]** Pushover, LLC (formerly Superblock LLC) is a solo-developer venture (Joshua Stein — not "Greg Kromer", which could not be verified), Chicago-based, independently financed, operating since March 2012. — Pushover support KB / blog 10-year retrospective (2022-03-07), accessed 2026-09-12, confidence: high.
13. **[ecosystem]** Active 2026 development: native Webhooks (2026-02-04), API sending-limit overhaul (announced 2026-04-08), legacy GitHub endpoint deprecation (2026-06-23) — service is actively maintained. — Pushover blog, accessed 2026-09-12, confidence: high.
14. **[ecosystem]** 2022 retrospective: 3B+ notifications delivered to 750k+ users — scale/longevity signal, but figure is ~4yr stale and not re-verified for 2025-2026. — Pushover blog (2022-03-07), confidence: medium.

## Leads (not chased)
- "Greg Kromer" appears to be a misattribution — no connection to Pushover found; actual owner is Joshua Stein.
- Independent uptime/incident history (status.pushover.net) not retrievable (JS-rendered widget) — would need rendered-DOM fetch.
- No 2025-2026 App/Play Store review-sentiment check performed.
- No direct Sweden-specific payment confirmation (only inferred from PayPal/Stripe/Google Play universality).
- `cancel_by_tag` behavior (cancel all pending emergency-priority retries by tag) not fully explored for edge cases — relevant to "silence for rest of season."

## Not found
- No source confirms/denies "Greg Kromer" in connection with Pushover — treat as incorrect.
- No human-readable uptime % or incident list retrieved from the live status page.
- No independent reliability benchmark for stock-Android delivery outside the Home-Assistant-integration-specific IPv6 reports.
- No explicit Sweden-specific statement anywhere (GDPR/privacy policy treats EEA uniformly).

## Verdict
Well-suited with high confidence on the core requirements: no custom app needed (Android app is a $4.99 one-time install), the Emergency Priority mechanism (priority=2, retry/expire, optional server-side `callback` on acknowledgment) is a documented, purpose-built fit for "escalate until confirmed, then silence," and the plain HTTP POST API is trivial to integrate. Medium-high confidence on delivery reliability (sub-second per official docs; the only recent complaints trace to client-side IPv6 misconfig, not a Pushover defect) and EU/GDPR fitness (May-2026 privacy policy explicitly covers EEA, no Sweden-specific restriction surfaced). Medium confidence on long-term company stability: single-founder, no outside funding, no employees found — a single-point-of-failure risk, offset by 14 years of continuous operation and clearly active 2026 development.
