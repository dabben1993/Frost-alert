# Digest: Telegram Bot API (round 1)

## Findings

1. **[mechanism]** Two-way ack via inline keyboards: `InlineKeyboardMarkup.inline_keyboard` buttons; pressing one sends a `callback_query` update (`id`, `from`, `message`, `data`); bot must also call `answerCallbackQuery` to clear the client-side loading spinner. Plain replies/`ForceReply` also possible. — Telegram official Bot API docs (2026-08-24 changelog), accessed 2026-09-12, confidence: high. https://core.telegram.org/bots/api
2. **[mechanism]** `answerCallbackQuery` is required even with no user-visible message — client shows a progress bar until it's called. — same source, confidence: high.
3. **[mechanism]** Two mutually exclusive update-retrieval modes: `getUpdates` (long polling, up to 24h retention, `offset`/`limit`/`timeout`/`allowed_updates`) or `setWebhook` (Telegram POSTs to your HTTPS URL, retry-until-give-up, optional `secret_token`). Can't use both at once. — same source, confidence: high.
4. **[mechanism]** Because `allowed_updates` includes `callback_query`, a cron/serverless job periodically calling `getUpdates` can plausibly receive button-press acks without an always-on webhook receiver — this is an inference from the docs, not an explicit worked example, hence **medium** confidence; worth a quick proof-of-concept before committing.
5. **[mechanism/hosting]** Webhook setup requires a domain + HTTPS server reachable on ports 443/80/88/8443 with TLS; Telegram provides no hosting/domains itself. — Telegram's "Marvin's Guide to Webhooks", confidence: high. https://core.telegram.org/bots/webhooks
6. **[pricing/rate-limits]** Bot messaging is free; limits ~1 msg/sec/chat, ~20 msgs/min/group, ~30 msgs/sec global bulk ceiling (429 + `retry_after` if exceeded). Paid "Broadcasts via Stars" only relevant beyond 30 msg/sec and ≥100k MAU — irrelevant at hobby scale. — Telegram official Bots FAQ, confidence: high.
7. **[pricing/rate-limits]** Independently corroborated by `python-telegram-bot` library's `FloodLimit` constants matching the same numbers (second independent source, satisfying the two-source bar for a pricing/limits-decisive claim). — GitHub python-telegram-bot, confidence: high.
8. **[pricing/rate-limits]** At "a few messages/day" scale, none of these limits are remotely reachable. — inference from #6/#7, confidence: high.
9. **[reliability]** Telegram's own bug tracker/support copy attributes delayed Android notifications to generic Android/OEM battery-optimization, task-killers, or Play Services/Firebase issues — not Telegram-specific; guidance is to whitelist the app and check Play Services. — Telegram bug tracker (originally 2020-11, standing guidance) + Telegram X translation string (undated, current), confidence: medium (original post predates the 6-12mo freshness bar).
10. **[reliability]** Single unverified/undated Reddit r/GooglePixel anecdote reports 20min-to-a-day delays vs. WhatsApp on same device — anecdotal, low confidence, freshness unconfirmed (fetch timeout).
11. **[reliability]** Third-party blog (2025-09-29) gives the same standard remediation playbook (battery unrestricted, allow background data, disable Battery Saver, update Play Services) — consistent with Telegram's own guidance; low-confidence corroboration only (aggregator).
12. **[compliance/data-residency]** Telegram's EU privacy policy: EEA/UK user data stored in Netherlands (EU) data centers; EDPO appointed as Art. 27 GDPR representative; may share data with Telegram group entities (BVI, Dubai) under EU-approved SCCs. — Telegram official EU privacy policy, confidence: high. https://telegram.org/privacy/eu
13. **[compliance]** Telegram's "Standard Bot Privacy Policy" places GDPR-type obligations on the bot developer/operator, not just Telegram — the hobbyist would be the "operator" under this framework; GDPR's household exemption (Art 2(2)(c)) plausibly applies for pure single-user personal use, but this was **not** confirmed by a legal source this run — inference only, medium confidence.
14. **[ecosystem]** Bot API changelog shows monthly-cadence feature releases through August 2026 (v10.3, plus July/June/May 2026 entries); no deprecation/breaking-change language found in recent entries. — Telegram official docs/changelog, confidence: high.

## Leads (not chased)
- r/GooglePixel anecdote's exact date unconfirmed (fetch timeout) — re-fetch via old.reddit.com or cache.
- Did not check Bot API / `python-telegram-bot` / `node-telegram-bot-api` GitHub issues for `callback_query` delivery edge cases (missed updates between polling windows, offset/ack races).
- GDPR household-exemption applicability to a Swedish hobbyist's personal Telegram bot not confirmed against any legal/regulatory source.
- No check of Telegram's status/incident page for recent EU/Netherlands-region outages.
- No worked hobbyist tutorial confirming real-world minimal hosting cost/shape for a `getUpdates`-via-cron pattern (mechanism claim #4 stays an inference).

## Not found
- No quantitative/official push-latency benchmark (e.g. P95 delivery time) vs. WhatsApp/SMS/email.
- No primary-source confirmation of a current, Telegram-specific (not generic-Android) Doze-mode delay bug within the last 6-12 months.
- No legal-opinion source on GDPR household exemption for a personal bot.
- Reddit thread's freshness unverified.

## Verdict
Strong fit on core requirements with high confidence: native two-way ack via inline-keyboard `callback_query` (+`answerCallbackQuery`), genuinely free at hobby volume with limits nowhere near reachable, and — per docs — plausibly pollable via cron/serverless `getUpdates` without an always-on webhook receiver (medium-confidence inference, worth a quick PoC). EU/Swedish data residency is favorable (Netherlands data centers, Art. 27 EDPO representative), though the personal-use GDPR exemption isn't independently confirmed. The one real soft spot is Android delivery reliability: all evidence points to generic Android battery-optimization/Doze interference (addressable via whitelisting), not a Telegram-specific defect — but corroborating anecdotal evidence is low-confidence/unverified for freshness, so for a consequence-bearing alert it would be prudent to explicitly whitelist the app and consider a secondary channel as a safety net. Ecosystem health is strong (monthly releases, no deprecation signals).
