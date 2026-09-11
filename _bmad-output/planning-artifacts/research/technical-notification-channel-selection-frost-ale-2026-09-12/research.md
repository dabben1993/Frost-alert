---
title: 'technical research: Notification channel selection for Frost Alert'
type: 'technical'
topic: 'Notification channel selection for Frost Alert'
decision: 'Pick the notification channel for Frost Alert''s escalating frost alerts, requiring two-way acknowledgment (seasonal on/off), reliable delivery to a stock Android phone for a Sweden-based user, no custom native app, cost target $0.'
source: 'run'
status: complete
preset: 'standard'
validation: 'normal'
created: '2026-09-12'
updated: '2026-09-12'
claims_verified: 3
claims_unverified: 0
---

# technical research: Notification channel selection for Frost Alert

**Decision this research serves:** Pick the notification channel for Frost Alert's escalating frost alerts, requiring two-way acknowledgment (seasonal on/off), reliable delivery to a stock Android phone for a Sweden-based user, no custom native app, cost target $0.

## Executive summary

**Pick Telegram Bot API**, with **Pushover** as the strongest runner-up. Both natively support two-way acknowledgment (Telegram's inline-keyboard `callback_query`; Pushover's Emergency-Priority `callback` on ack), are genuinely free or near-free at hobby volume, need no custom app, and show no Sweden/EU blocker. **ntfy.sh** is a close, fully free third option with a documented ack mechanism but a real (mitigable) Android delivery-timing caveat on its default build. **WhatsApp Business/Cloud API** is technically workable but sits in direct, current tension with its own Terms of Service ("not for personal, family, or household purposes") — a hard-gate-adjacent risk none of the other four candidates carry — plus real onboarding friction (template approval, test numbers expiring ~every 90 days) and a non-zero per-message cost from October 2026. **Email + action link** is viable as a cheap, dependency-light fallback or secondary channel, but its ack mechanism (a clickable magic link) is the least purpose-built of the five and carries a link-prefetch risk that's well-documented for Outlook but unconfirmed for Gmail specifically.

The two or three findings driving this: (1) only Telegram, Pushover, and ntfy.sh have an ack mechanism *designed for exactly this pattern* (button/priority-message + server-side callback on tap) rather than a repurposed general-purpose feature; (2) WhatsApp's ToS conflict is a primary-sourced, independently corroborated fact, not a risk inferred from silence; (3) all five candidates clear the Sweden/EU bar with no disqualifying regional restriction — this dimension didn't end up differentiating the field the way the plan anticipated.

**Biggest caveat:** no candidate's Android push-delivery reliability was independently benchmarked end-to-end (no source measured actual delivery latency under real-world Doze/battery-optimization conditions for any candidate) — every reliability claim rests on official docs, vendor troubleshooting copy, or anecdotal community reports, so this stays an open question with a same mitigation across all app-based candidates (Telegram, Pushover, ntfy, WhatsApp): explicitly whitelist the app from battery optimization.

## Requirements frame

Agreed at the plan gate, from `forged-idea.md` and confirmed by the user:

**Hard gates:**
1. No custom native app to build/maintain — installing an existing app is fine.
2. Must support two-way acknowledgment (reply, inline button, or clickable link hitting a simple endpoint).
3. Reliable push-style delivery to a stock Android phone.

**Weighted preferences:** cost (highest — $0 ideal, cheapest-viable fallback), delivery reliability (high), setup complexity (medium), Sweden/EU-specific quirks (medium).

## Candidate screen

Five candidates, all from the forged-idea.md shortlist — field was already narrow enough that no wildcard was added. All five clear the three hard gates in principle (each has *some* documented ack mechanism and *some* Android delivery path), so none are cut outright at screening; the differentiation happens in the evidence and cost sections below.

| Candidate | Hard gate 1 (no custom app) | Hard gate 2 (two-way ack) | Hard gate 3 (Android delivery) |
|---|---|---|---|
| Telegram Bot API | Pass — official app | Pass — inline-keyboard `callback_query` [1] | Pass, with generic-Android caveat [5][10] |
| Pushover | Pass — official app, $4.99 one-time | Pass — Emergency Priority + `callback` [16] | Pass [15] |
| ntfy.sh | Pass — official app (Play/F-Droid) | Pass — `http` action button [23] | Pass, with FCM-timing caveat [34] |
| WhatsApp Business/Cloud API | Pass — official app, but see ToS note | Pass — interactive reply buttons [42] | Pass, unverified benchmark [52][53] |
| Email + action link | Pass — Gmail app | Pass — magic link, weakest-purpose-built [55] | Pass, with sync-delay caveat [79] |

## Per-candidate evidence

### Telegram Bot API

**Mechanism.** Inline-keyboard buttons (`InlineKeyboardMarkup`) are the purpose-built ack path: a tap sends a `callback_query` update to the bot, which must call `answerCallbackQuery` to clear the client's loading spinner [1][2]. Two mutually exclusive retrieval modes exist: `getUpdates` (long polling, up to 24h retention) or `setWebhook` (Telegram pushes to your HTTPS endpoint) [1]. Because `allowed_updates` accepts `callback_query`, a cron-triggered job calling `getUpdates` on a schedule can plausibly receive button-press acks without an always-on webhook receiver — this is a **medium-confidence inference** from the docs, not an explicitly worked example, and is worth a quick proof-of-concept before committing [1]. A real webhook, if chosen instead, needs a domain + HTTPS-reachable server; Telegram provides neither [3].

**Cost.** Free at hobby scale: limits are ~1 msg/sec/chat and ~30 msg/sec global bulk, independently corroborated by the `python-telegram-bot` library's own rate-limit constants [4][6] — nowhere near "a few messages per day."

**Reliability.** All delivery-delay evidence found traces to generic Android OEM battery-optimization/Doze behavior, not a Telegram-specific defect [5][7][8][9] — addressable by whitelisting the app from battery optimization. No quantitative latency benchmark exists.

**Sweden/EU.** EEA data stored in Netherlands data centers, with EDPO as the Art. 27 GDPR representative [11]. The bot-operator's own GDPR obligations under Telegram's Standard Bot Privacy Policy [12] are plausibly sidestepped by the household-use exemption, but this specific application wasn't confirmed against a legal source.

**Ecosystem.** Monthly-cadence feature releases through August 2026, no deprecation language found [1].

### Pushover

**Mechanism.** "Emergency Priority" (`priority=2`) messages repeat (sound+vibration) at a configurable interval until acknowledged or expiry, and an optional `callback` URL parameter has Pushover's own servers POST to the sender's endpoint the instant the user acknowledges [16] — this is the most directly server-mediated ack mechanism of the five (Pushover itself confirms the ack and notifies your backend, vs. Telegram/ntfy where the client device fires the callback). A simpler `url` parameter gives a plain tappable link without retry/receipt semantics [16].

**Cost.** One-time $4.99/platform license (30-day free trial), independently corroborated [13][14]; sending is free up to 10,000 msgs/month/account (a 2026-05-01 rule change made this per-account rather than per-app) [13][15].

**Reliability.** Official docs claim sub-second typical delivery [17]; the only recent (2026) delay reports trace to client-side IPv6 misconfiguration, not a Pushover-side defect, and the same root cause has been documented since 2021 [18][19][20].

**Sweden/EU.** Privacy policy (updated 2026-05-01) explicitly covers EEA legal bases, sub-processors, US data transfers under SCCs, and EEA-style data-subject rights [21]; no Sweden-specific restriction found.

**Ecosystem.** Solo-developer venture (Joshua Stein, not "Greg Kromer" as the brief's premise assumed — no connection to that name was found), independently financed, operating since 2012 [22][23], with active 2026 development (webhooks Feb 2026, API-limit overhaul Apr/May 2026) [24][13]. This is a genuine single-point-of-failure risk, offset by 14 years of continuous operation.

### ntfy.sh

**Mechanism.** An `http` action button fires a client-side POST/GET/PUT to an arbitrary URL on tap [25][26]; one known parsing quirk (comma in a multi-field body breaks the shorthand header syntax) has a documented workaround (use JSON syntax instead) [27].

**Cost.** Public server free indefinitely for personal, non-abusive use [28]. **Live-verified** (2026-09-12) free-tier limits: 250 msgs/day, 5 emails/day, 0 calls, 20MB attachment total — comfortably covers a handful of alerts/night [41]. Fully open-source with a low-complexity self-hosting fallback (single Docker container, SQLite, no external DB) if the public server's trust/jurisdiction posture is a concern [32][33].

**Reliability.** This is ntfy's real trade-off: the default Play-Store app path uses Firebase Cloud Messaging, which the maintainer himself calls "not great" for timeliness; an "instant delivery" mode (persistent connection, F-Droid builds always use it) trades battery for lower latency, and can itself be killed by Doze/OEM battery optimization [34][35][36]. One open (single-source) issue reports elevated battery drain from keep-alive traffic on some devices [39]. Active fixes shipped as recently as July-August 2026 [40].

**Sweden/EU.** The public server is contractually governed by Connecticut, USA law [37], with no stated EU data residency in its privacy policy [38] — a mild, non-blocking flag, fully mitigated by self-hosting if desired.

**Ecosystem.** ~33.6k GitHub stars, steady mid-2026 release cadence, single lead maintainer plus contributors, donation-supported [42][43][44].

### WhatsApp Business/Cloud API

**Mechanism.** Interactive reply-button messages are a documented, primary-sourced ack mechanism: a tap fires a `messages` webhook with the button's ID/title [45]. Technically capable, but gated: any business-initiated "cold-start" message (i.e. the alert itself) must use a pre-approved template, since free-form messages only work inside a 24h window opened by an *inbound* message from the recipient [50] — a meaningfully heavier setup than the other four candidates' "just send a message" flow.

**Cost.** Sweden falls in Meta's "Rest of Western Europe" pricing tier; per-delivered utility-template rate is ~$0.018-0.020 (two independent BSP sources) [55][56] — a few dollars a year at hobby volume, not literally $0, and Meta's own roadmap ends the current utility-message-in-window fee exemption on **2026-10-01** [50][51].

**The decisive issue.** WhatsApp's Business Terms of Service explicitly state the service must be used "solely for business, commercial, and authorized purposes, and not for personal use," and separately prohibit use "for personal, family, or household purposes" [57] — a claim **independently verified this run** against a second primary source (`facebook.com/legal/business-broadcasts`'s "No Personal Use" clause) [61]. A third-party analysis usefully distinguishes the free consumer-facing WhatsApp *Business App* (where private use is an unenforced grey area) from the *Business Platform/API* researched here, which it describes as explicitly "not intended for private" use [61]. This is a pre-existing clause (documented since at least Feb 2024), not a new 2025-2026 crackdown, and enforcement against a near-zero-volume personal bot is undocumented and discretionary [57][58] — but it is a real, live tension none of the other four candidates carry.

**Setup friction.** The free auto-generated test number is capped at 5 recipients and is widely reported to expire roughly every 90 days, requiring manual recreation [48][49] — genuine recurring maintenance for a long-running seasonal automation.

**Reliability.** No credible independent benchmark found; the only figures retrieved were unsourced, promotional-register vendor-blog percentages [52][53] — low confidence either way.

### Email + action link

**Mechanism.** The standard secure pattern is a GET that renders an inert confirmation page and a separate, explicit POST that actually flips the state — never consuming the token on the initial GET [62]. This matters because Outlook/Office 365 "Safe Links" and similar corporate scanners prefetch links and can consume a naive single-step token before the user ever clicks, a recurring, well-documented issue across multiple auth libraries [63][64][65]. No comparable Gmail-side prefetch problem was found in this run, but it also wasn't explicitly ruled out for the target Gmail/Android recipient — flagged as an open question, not a confirmed non-issue.

**Cost.** Resend (3,000/mo, 100/day cap), Mailgun (100/day), and Brevo (300/day) all currently hold genuine, non-time-limited $0 tiers [66][67][71] — far more than Frost Alert needs. Gmail SMTP with an app password (500 msgs/rolling-24h) works as a zero-setup fallback [70]. **Avoid** SendGrid — its own support page confirms new direct accounts get only a 60-day trial capped at 100 emails/day from 2025-03-25 [68][69], which a secondary source frames as the end of a previously-permanent free tier [72] (that specific framing isn't stated by SendGrid itself) — and note Amazon SES's free tier is now a generic AWS-credit model, not an ongoing allowance [71].

**Deliverability.** Gmail's strict bulk-sender rules only bite above ~5,000 msgs/day [75]; a single, engaged recipient who never marks mail as spam structurally eliminates the complaint-rate risk factor [78]. Basic SPF/DKIM configuration is still recommended for baseline trust [75][76].

**Reliability.** Gmail's Android app depends on background sync, which Google's own docs say can take up to 15 minutes (longer if the device has been idle) [79] — mitigated the same way as the other app-based candidates: set battery usage to unrestricted [80][81].

**Sweden/EU.** GDPR's household-activity exemption (Art. 2(2)(c), Recital 18) very likely applies to a single hobbyist emailing themselves alerts via a US-based provider [82][83]; Sweden's IMY explicitly targets its email-security guidance at organizations, not private individuals [85].

## Cost & lock-in

| Candidate | Ongoing cost at hobby volume | One-time/setup cost | Exit cost if switching away |
|---|---|---|---|
| Telegram Bot API | $0 | $0 | Trivial — delete bot, no lock-in |
| Pushover | $0 (10k msgs/mo free) | $4.99 one-time per platform | Low — sunk $4.99, no data lock-in |
| ntfy.sh | $0 (250 msgs/day free) | $0 | Trivial — public server or self-host, fully open protocol |
| WhatsApp Business/Cloud API | ~$0.02/delivered template msg from Oct 2026; a few $/year at this volume | $0, but ~90-day test-number renewal churn | Low cost, but real ToS-compliance exit pressure |
| Email + action link | $0 (well within Resend/Mailgun/Brevo/Gmail free tiers) | $0 | Trivial — swap SMTP/API provider |

No candidate carries meaningful subscription or migration-away cost at this scale — cost differentiation is negligible except that WhatsApp is the only candidate with a *non-zero, scheduled-to-grow* per-message cost and recurring test-number maintenance.

## Cross-dimension insights

- **The Sweden/EU dimension didn't differentiate the field** the way the plan anticipated — all five candidates clear it with, at most, mild non-EU-residency flags (ntfy, ambiguously Telegram's bot-operator obligations) rather than any hard block. The real differentiator turned out to be **mechanism purpose-fit**: Telegram, Pushover, and ntfy.sh all have an ack feature *designed* for "alert until confirmed, then notify the backend," while WhatsApp's reply-buttons and email's magic-link are repurposed general-purpose features that work but weren't built for this pattern.
- **The two cheapest-looking options on paper (ntfy.sh, email) both carry the same underlying reliability dependency** — Android's background-sync/Doze behavior — that the more "native-feeling" push services (Telegram, Pushover) also depend on. There's no free lunch on reliability; whichever channel is chosen, the single highest-leverage mitigation across the board is disabling battery optimization for that one app.
- **WhatsApp is the only candidate where the cost dimension and the compliance dimension point the same direction** — it's simultaneously the only channel with a real (if tiny) recurring bill and the only one with a live ToS conflict. Both push away from it independently; combined, they're a clear signal to not need it as primary.

## Recommendations

1. **Primary: Telegram Bot API.** Free, purpose-built two-way ack via inline-keyboard `callback_query`, no company/verification friction, favorable EU data residency. Feeds directly into the architecture spine as the notification-channel choice and into the config-flow design (bot token + chat ID are the only two secrets needed). Confidence: high on mechanism/cost, medium on the specific claim that a cron-polled `getUpdates` call (rather than a webhook) can receive callback acks — validate with a short proof-of-concept before committing to the no-webhook hosting shape.
2. **Runner-up: Pushover.** Switch to this if the Telegram `getUpdates`-without-webhook proof-of-concept fails, or if the single-maintainer risk profile of either service becomes a concern (Pushover's is arguably lower — 14 years, still shipping features — but it's a paid $4.99 one-time entry vs. Telegram's $0). Its server-mediated `callback`-on-acknowledgment mechanism is, if anything, a slightly cleaner architectural fit than Telegram's client-fired callback.
3. **Do not select WhatsApp Business/Cloud API as primary.** The ToS conflict with personal/household use is verified against two independent primary sources, not a reach; combined with template-approval friction, ~90-day test-number churn, and a real (small) per-message cost, it's the weakest-fit candidate despite being technically capable. Reversibility hedge: if a future need arises for WhatsApp specifically (e.g. a friend who only wants WhatsApp), treat it as an explicit, informed risk acceptance rather than a default choice.
4. **ntfy.sh and email+action-link are solid secondary/fallback channels** — worth keeping in the design as a second notification path (defense in depth against any single channel's delivery-timing risk) rather than as the sole channel, given ntfy's FCM-timing caveat and email's less purpose-built ack mechanism.

## Open questions

- Does a cron-triggered `getUpdates` call actually receive `callback_query` updates in practice, avoiding the need for an always-on webhook receiver for Telegram? (Docs support it; no worked example found.) — resolve with a 10-minute proof-of-concept before finalizing the hosting design.
- Does Gmail perform any link-prefetch/scanning comparable to Outlook's Safe Links, which could prematurely consume an email action-link's token? — send a test email to the actual target Gmail account and observe.
- What is Meta's first-party (not BSP-republished) per-message rate for the "Rest of Western Europe" region? — Meta's own rate-card tool is JS-rendered and wasn't captured this run; low-priority given WhatsApp isn't the pick.
- No candidate's real-world Android push latency was independently benchmarked under Doze/battery-optimization conditions — if delivery-timing certainty matters more than this research can establish from docs and community reports alone, a short empirical test (send N messages via each shortlisted channel to the actual target phone, measure latency with battery optimization on vs. off) would close this gap directly and cheaply.

## Source appendix

| # | Claim / finding it supports | Publisher | Pub. date | Accessed | Confidence |
|---|---|---|---|---|---|
| [1] | Telegram inline-keyboard `callback_query` ack mechanism; getUpdates/webhook modes | [Telegram Bot API docs](https://core.telegram.org/bots/api) | 2026-08-24 | 2026-09-12 | high |
| [2] | `answerCallbackQuery` required to clear client spinner | [Telegram Bot API docs](https://core.telegram.org/bots/api) | 2026-08-24 | 2026-09-12 | high |
| [3] | Webhook requires own domain/HTTPS server | [Telegram webhooks guide](https://core.telegram.org/bots/webhooks) | undated | 2026-09-12 | high |
| [4] | Telegram rate limits (1/sec/chat, 30/sec bulk) | [Telegram Bots FAQ](https://core.telegram.org/bots/faq) | undated | 2026-09-12 | high |
| [5] | Telegram Android delay attributed to generic OEM battery optimization | [Telegram bug tracker](https://bugs.telegram.org/c/227) | 2020-11-13 | 2026-09-12 | medium |
| [6] | Rate limits corroborated independently | [python-telegram-bot constants.py](https://github.com/python-telegram-bot/python-telegram-bot/blob/5a41d2ba/src/telegram/constants.py) | current | 2026-09-12 | high |
| [7] | Firebase/Play Services troubleshooting copy | [Telegram translations platform](https://translations.telegram.org/stringnames/android_x/settings/NotificationsGuideFirebaseError) | undated | 2026-09-12 | medium |
| [8] | Anecdotal Pixel delay report (unverified date) | [Reddit r/GooglePixel](https://www.reddit.com/r/GooglePixel/comments/1iyuudf/please_google_fix_delayed_notifications/) | unverified | 2026-09-12 | low |
| [9] | Third-party remediation playbook, consistent with official guidance | [TechBabble](https://techbabble.co.uk/2025/09/29/how-do-i-fix-delayed-telegram-message-delivery/) | 2025-09-29 | 2026-09-12 | low |
| [10] | (generic Android battery-optimization interaction, cross-referenced) | [Telegram bug tracker](https://bugs.telegram.org/c/227) | 2020-11-13 | 2026-09-12 | medium |
| [11] | EEA data in Netherlands centers, EDPO Art.27 representative | [Telegram EU privacy policy](https://telegram.org/privacy/eu) | undated | 2026-09-12 | high |
| [12] | Bot-operator GDPR obligations framework | [Telegram Standard Bot Privacy Policy](https://telegram.org/privacy-tpa) | undated | 2026-09-12 | medium |
| [13] | Pushover pricing: $4.99 one-time; 10k free msgs/mo per-account (2026-05 rule) | [Pushover pricing](https://pushover.net/pricing) / [blog](https://blog.pushover.net/posts/2026/4/app-limits) | 2026-04-08 | 2026-09-12 | high |
| [14] | Independent pricing corroboration | [Deuts Log](https://deuts.org/p/pushover-api-limit/) | 2026-04-29 | 2026-09-12 | medium |
| [15] | Emergency Priority mechanism, `callback` on ack, HTTP POST API | [Pushover API docs](https://pushover.net/api) | undated | 2026-09-12 | high |
| [16] | (same — mechanism detail) | [Pushover API docs](https://pushover.net/api) | undated | 2026-09-12 | high |
| [17] | Sub-second delivery claim, delay causes enumerated | [Pushover support KB](https://support.pushover.net/i281-notifications-are-received-but-after-significant-delay) | undated | 2026-09-12 | high |
| [18] | 2026 delay reports traced to client IPv6 misconfig | [Reddit r/homeassistant](https://www.reddit.com/r/homeassistant/comments/1ufh9p9/pushover_delay/) | 2026-06-25 | 2026-09-12 | medium |
| [19] | Same, GitHub issue confirmation | [home-assistant/core#173003](https://github.com/home-assistant/core/issues/173003) | 2026-06 | 2026-09-12 | medium |
| [20] | Same root cause documented since 2021 | [Home Assistant Community](https://community.home-assistant.io/t/pushover-is-really-slow-lately/45900) | since 2021 | 2026-09-12 | medium |
| [21] | EEA/GDPR legal bases, sub-processors, SCCs | [Pushover privacy policy](https://pushover.net/privacy) | 2026-05-01 | 2026-09-12 | high |
| [22] | Solo-developer venture, Joshua Stein, since 2012 | [Pushover support KB](https://support.pushover.net/i45-who-runs-pushover/1000/newest) | undated | 2026-09-12 | high |
| [23] | 10-year retrospective, scale figures | [Pushover blog](https://blog.pushover.net/posts/2022/3/ten) | 2022-03-07 | 2026-09-12 | medium |
| [24] | Active 2026 development (webhooks, limit overhaul) | [Pushover blog](https://blog.pushover.net/posts/2026/2/webhooks) | 2026-02-04 | 2026-09-12 | high |
| [25] | ntfy `http` action button mechanism | [ntfy publish docs](https://docs.ntfy.sh/publish/) | undated | 2026-09-12 | high |
| [26] | Server-side action-type validation | [ntfy server actions.go](https://github.com/binwiederhier/ntfy/blob/main/server/actions.go) | current | 2026-09-12 | high |
| [27] | Comma-in-body parsing quirk + workaround | [ntfy issue #1334](https://github.com/binwiederhier/ntfy/issues/1334) | 2025-05-11 | 2026-09-12 | high |
| [28] | Public server free indefinitely for personal use | [ntfy FAQ](https://docs.ntfy.sh/faq/) | undated | 2026-09-12 | high |
| [32] | Self-hosting low-complexity (single container) | [ntfy install docs](https://docs.ntfy.sh/install/) | undated | 2026-09-12 | medium |
| [33] | Self-hosting install walkthrough | [Jacar.es blog](https://jacar.es/en/how-to-install-ntfy-with-docker/) | 2026 | 2026-09-12 | medium |
| [34] | FCM default path, maintainer's own "not great" assessment; instant-delivery alternative | [ntfy phone subscribe docs](https://docs.ntfy.sh/subscribe/phone/) | undated | 2026-09-12 | high |
| [35] | Doze/battery-optimization killing persistent connection | [ntfy issue #757](https://github.com/binwiederhier/ntfy/issues/757) | ongoing | 2026-09-12 | high |
| [36] | Independent corroboration of Doze delaying notifications | [Nelson's log](https://nelsonslog.wordpress.com/2024/07/19/android-doze-mode-vs-notifications/) | 2024-07-19 | 2026-09-12 | medium |
| [37] | US/Connecticut governing jurisdiction | [ntfy ToS](https://docs.ntfy.sh/terms/) | undated | 2026-09-12 | high |
| [38] | No stated EU data residency | [ntfy privacy policy](https://docs.ntfy.sh/privacy/) | undated | 2026-09-12 | high |
| [39] | Open issue: keep-alive battery drain on some devices | [ntfy issue #1195](https://github.com/binwiederhier/ntfy/issues/1195) | ongoing | 2026-09-12 | medium |
| [40] | Active Jul-Aug 2026 reliability fixes | [ntfy releases](https://docs.ntfy.sh/releases/) | 2026-07/08 | 2026-09-12 | medium |
| [41] | Free-tier limits — live-verified | [ntfy.sh/v1/account](https://ntfy.sh/v1/account) (own fetch) | live | 2026-09-12 | high |
| [42] | ~33.6k GitHub stars, release cadence | [ntfy GitHub repo](https://github.com/binwiederhier/ntfy) | live | 2026-09-12 | high |
| [43] | (same — ecosystem stats) | [ntfy GitHub repo](https://github.com/binwiederhier/ntfy) | live | 2026-09-12 | high |
| [44] | Donation-supported single-maintainer model | [ntfy GitHub repo](https://github.com/binwiederhier/ntfy) | live | 2026-09-12 | medium |
| [45] | WhatsApp interactive reply-button mechanism | [Meta Cloud API docs](https://developers.facebook.com/docs/whatsapp/cloud-api/messages/interactive-reply-buttons-messages/) | undated | 2026-09-12 | high |
| [48] | Free test number expires ~90 days | [n8n community](https://community.n8n.io/t/whatsapp-triggers-test-number-stopped-working/233535) | 2025-12/2026-01 | 2026-09-12 | medium |
| [49] | Same, sandbox guide | [Medium sandbox guide](https://medium.com/@adityadeepa634/the-developers-guide-to-the-whatsapp-cloud-api-sandbox-2026-edition-c967ce0bf671) | 2026 | 2026-09-12 | medium |
| [50] | Template gating for cold-start messages; Oct 2026 fee-exemption end | [Meta pricing docs](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing) | 2026-08-05 | 2026-09-12 | high |
| [51] | Free monthly service-message allowance from Oct 2026 | [Meta pricing docs](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing) | 2026-08-05 | 2026-09-12 | high |
| [55] | Sweden "Rest of Western Europe" rate ~$0.018-0.020/msg | [HighLevel support](https://help.gohighlevel.com/support/solutions/articles/155000001428-whatsapp-pricing-billing-and-rebilling-guide) | 2026 | 2026-09-12 | medium |
| [56] | Same, second BSP source | [SleekFlow pricing](https://help.sleekflow.io/en_US/whatsapp/pricing) | 2026 | 2026-09-12 | medium |
| [57] | WhatsApp ToS "not for personal use" / household-purposes prohibition | [WhatsApp Business ToS](https://www.whatsapp.com/legal/business-terms/) | 2024-02-16 | 2026-09-12 | high |
| [58] | Discretionary enforcement (limit/throttle/suspend/terminate) | [WhatsApp Business ToS](https://www.whatsapp.com/legal/business-terms/) | 2024-02-16 | 2026-09-12 | high |
| [61] | Independent corroboration of "No Personal Use" + App-vs-Platform distinction | [Facebook business-broadcasts terms](https://www.facebook.com/legal/business-broadcasts) / [Chatarmin analysis](https://chatarmin.com/en/blog/whatsapp-business-for-private) | live/2026 | 2026-09-12 | high |
| [52] | Unsourced vendor delivery-rate claims | [SMSGatewayCenter blog](https://www.smsgatewaycenter.com/blog/whatsapp-business-api-vs-sms-api-2025/) | 2025 | 2026-09-12 | low |
| [53] | "Fails silently" delivery claim | [SMSGatewayCenter blog](https://www.smsgatewaycenter.com/blog/sms-api-vs-whatsapp-business-api-when-to-use-each/) | 2025/2026 | 2026-09-12 | low |
| [62] | GET-renders/POST-flips magic-link pattern | [Medium (Obie Fernandez)](https://obie.medium.com/prefetching-breaks-magic-link-password-less-login-systems-unless-you-take-precautions-a4c011a3e165) | undated | 2026-09-12 | high |
| [63] | Outlook Safe Links prefetch invalidating tokens | [next-auth issue #1840](https://github.com/nextauthjs/next-auth/issues/1840) | 2020-2024 | 2026-09-12 | high |
| [64] | Same, second library | [FusionAuth issue #629](https://github.com/FusionAuth/fusionauth-issues/issues/629) | 2020-2024 | 2026-09-12 | high |
| [65] | Same, third library | [Supabase auth issue #1214](https://github.com/supabase/auth/issues/1214) | 2020-2024 | 2026-09-12 | high |
| [66] | Resend free tier: 3,000/mo, 100/day cap | [Resend pricing](https://resend.com/pricing) | current | 2026-09-12 | high |
| [67] | Mailgun free tier: 100/day | [Mailgun pricing](https://www.mailgun.com/pricing/) / [help center](https://help.mailgun.com/hc/en-us/articles/203068914-What-does-the-Free-plan-offer) | current | 2026-09-12 | high |
| [68] | SendGrid: new accounts get 60-day trial, 100/day cap, from 2025-03-25 (source doesn't itself frame this as a tier being "killed") | [Twilio/SendGrid support](https://support.sendgrid.com/hc/en-us/articles/35270136965403-Twilio-SendGrid-Trial-Account-Plan) | 2025-03-25 | 2026-09-12 | high |
| [69] | SendGrid current pricing | [Twilio pricing](https://www.twilio.com/en-us/products/email-api/pricing) | current | 2026-09-12 | high |
| [71] | Amazon SES free-tier restructure to AWS credits | [AWS blog](https://aws.amazon.com/blogs/messaging-and-targeting/introducing-amazon-simple-email-service-ses-pricing-plans/) / [pricing](https://aws.amazon.com/ses/pricing/) / [Emercury history](https://www.emercury.net/blog/email-marketing-tips/amazon-ses-pricing/) | 2025-2026 | 2026-09-12 | high |
| [72] | SendGrid free-tier retirement, secondary date corroboration | [Dreamlit blog](https://dreamlit.ai/blog/best-sendgrid-alternatives) | 2025 | 2026-09-12 | medium |
| [70] | Gmail SMTP: 500 msgs/rolling-24h via app password | [Nylas dev docs](https://developer.nylas.com/docs/cookbook/email/gmail-smtp-settings/) / [Smartlead help](https://helpcenter.smartlead.ai/en/articles/45-data-command-failed-550-545-daily-user-sending-quota-exceeded) | current | 2026-09-12 | medium |
| [75] | Gmail bulk-sender threshold ~5,000/day; SPF/DKIM/DMARC guidance | [Google admin help](https://support.google.com/a/answer/81126) / [Gmail help](https://support.google.com/mail/answer/14229414) | current | 2026-09-12 | high |
| [76] | Reputation/engagement/volume-consistency factors beyond auth | [Relaymetry](https://relaymetry.com/spf-dkim-dmarc-pass-but-gmail-spam) / [Suped](https://www.suped.com/learn/email-deliverability/why-is-gmail-rate-limiting-my-marketing-and-transactional-emails-after-a-period-of-low-sending-v) | current | 2026-09-12 | medium |
| [78] | Spam-complaint-rate guidance (<0.1%) | [Google Gmail help](https://support.google.com/mail/answer/14229414) | current | 2026-09-12 | high |
| [79] | Gmail Android sync delay up to 15 min | [Google Gmail help](https://support.google.com/mail/answer/4780745) / [help](https://support.google.com/mail/answer/6562) | current | 2026-09-12 | high |
| [80] | Battery-unrestricted mitigation | [iTechHacks](https://itechhacks.com/gmail-notifications-not-working-android/) | current | 2026-09-12 | medium |
| [81] | Same, second guide | [Technobezz](https://www.technobezz.com/how-to-fix-gmail-notifications-not-working-on-android) | current | 2026-09-12 | medium |
| [82] | GDPR household exemption (Art. 2(2)(c), Recital 18) | [DPO World](https://app.dpo-world.com/Factor/Personal%20and%20Domestic%20Use%20Exemption) | undated | 2026-09-12 | medium |
| [83] | Exemption limits per CJEU Ryneš case law | [LegalClarity](https://legalclarity.org/gdpr-fines-for-individuals-penalties-and-how-to-avoid-them/) | undated | 2026-09-12 | low |
| [85] | Sweden IMY email guidance targets organizations, not individuals | [IMY](https://www.imy.se/en/organisations/data-protection/vi-guidar-dig/security-of-personal-data-in-e-mail/) | current | 2026-09-12 | medium |

## Staleness map

Freshness windows applied (technical pack + selection-shape additions): pricing figures and any cell deciding between top-two finalists ≤ 3 months · version/compatibility claims ≤ 1 month · ecosystem signals ≤ 6 months · landscape/policy claims ≤ 12 months.

Claims aged against these windows (see `.memlog.md` ledger for the full claim list): the earliest re-check need is **pricing-class claims** — Pushover, ntfy, WhatsApp, and email-provider pricing/free-tier figures were all captured 2026-09-12 against a 3-month pricing window, so **re-check by ~2026-12-12**. WhatsApp's own roadmap already flags a scheduled pricing change on **2026-10-01** (utility-in-window messages become chargeable) — this is a known future change, not staleness, but should be re-confirmed once it lands if WhatsApp is ever reconsidered. Ecosystem-class claims (release cadence, maintainer activity) recheck by ~2027-03-12. Landscape/policy claims (WhatsApp ToS, GDPR exemption reasoning) recheck by ~2027-09-12.

This selection report should be refreshed before anyone acts on it if more than two quarters (~2027-03-12) have passed.
