# Digest: ntfy.sh (round 1)

## Findings

1. **[mechanism]** `http` action button type fires a POST/GET/PUT to an arbitrary URL on tap, via `Actions`/`X-Actions` header or JSON `actions` array; executed client-side by the app, not proxied by the server. — ntfy official docs, accessed 2026-09-12, confidence: high. https://docs.ntfy.sh/publish/
2. **[mechanism]** Server-side source confirms exactly 4 action types: `view`, `broadcast`, `http`, `copy`; `label`+`url` required for URL actions. — GitHub binwiederhier/ntfy (server/actions.go), confidence: high.
3. **[mechanism]** Comma-separated header shortcut breaks if `body` contains a comma — documented workaround is to use full JSON publish syntax instead (GitHub issue #1334, reported/closed May 2025). Confidence: high.
4. **[pricing]** Public ntfy.sh server stated free indefinitely for personal, non-abusive use; paid tiers add limits/support, don't gate basic use. — ntfy official FAQ, confidence: high.
5. **[pricing]** Free/anonymous tier caps: 250 msgs/day, 5 emails/day, 0 phone calls, 20MB attachment total, 2MB/file, ~200MB attachment bandwidth/day; anonymous burst bucket 60 requests refilled 1/5s. — GitHub issue #1173 (2024, quoting live `/v1/account`), confidence: medium (numbers could have shifted since; worth a live re-check).
6. **[pricing]** For a hobbyist sending a handful of text alerts/night, well under 250/day — comfortably sufficient. — inference, confidence: medium.
7. **[pricing]** Self-hosting officially supported/open-source (Apache 2.0/GPLv2) as the trust/data-control alternative to the public server. — ntfy FAQ, confidence: high.
8. **[mechanism]** Self-hosting is low-complexity: single Docker container, SQLite-based (no external DB), ~20-50MB RAM idle, port 80 + reverse proxy for HTTPS in production. — ntfy docs + Jacar.es blog (2026), confidence: medium.
9. **[mechanism]** Official Android app (`io.heckel.ntfy`) on Google Play, F-Droid, and raw APK; subscribing to a topic is the only setup step. — ntfy docs/Play/F-Droid, confidence: high.
10. **[mechanism]** Publishing is a plain `curl -d "..." ntfy.sh/<topic>` (PUT/POST) — no SDK/API key/account required for base flow, trivially cron-callable. — ntfy docs/Play description, confidence: high.
11. **[reliability]** Play-Store-flavored app uses Firebase Cloud Messaging (FCM) by default — maintainer himself says "Firebase is overall pretty bad at delivering messages in time." An "instant delivery" mode (foreground service, persistent connection) trades battery for lower latency; F-Droid builds (no Firebase) always use instant delivery. — ntfy official docs, confidence: high.
12. **[reliability]** Instant delivery / persistent connection can be killed by Doze/OEM battery optimization, delaying notifications minutes-to-hours; maintainer-recommended fix is disabling battery optimization (cites dontkillmyapp.com for OEM quirks). — GitHub issue #757 (multi-year ongoing), confidence: high.
13. **[reliability]** Independent (non-ntfy) blog corroborates Doze delaying even "normal" notifications generally, with instant-delivery-via-foreground-service as the standard mitigation; some OEMs need ADB-level workarounds. — Nelson's log, 2024-07-19, confidence: medium.
14. **[reliability]** Open GitHub issue reports elevated battery use (>10%) from keep-alive/WebSocket pings, especially over VPN/mobile data on some devices (GrapheneOS, Pixel 8a); no complete server-side fix yet, workarounds are per-user. Single-source only — per the two-source bar for reliability-problem claims, stays medium confidence, not high. — GitHub issue #1195, confidence: medium.
15. **[reliability]** Android app v1.25.2 (Jul 23-26 2026) added graceful "no network" handling (stop retrying offline, auto-resume) — active remediation in this exact area within the last ~2 months of the research date. — F-Droid/ntfy release docs, confidence: medium.
16. **[regional]** ntfy.sh ToS: governed by laws of Connecticut, USA — US-based jurisdiction, not EU. — ntfy official ToS, confidence: high.
17. **[regional]** Privacy policy discloses minimal data collection (IP for rate limiting, optional tokens/web push endpoints), short retention (messages 12h, attachments 3h default); does NOT claim EU data residency or GDPR-specific guarantees for the hosted public server. — ntfy official privacy policy, confidence: high.
18. **[regional]** Maintainer states the public server "currently runs on a single DigitalOcean droplet, without any scale out strategy or redundancies"; no notable outages since inception per a Dec'22 note retained in the live FAQ (aside from short blips/HTTP 500 spikes); no server region disclosed. — ntfy FAQ, confidence: medium.
19. **[regional]** Third-party (non-ntfy-endorsed) commercial self-host offerings exist in EU/German datacenters for users wanting explicit EU data residency — a paid vendor marketing page, not verified further. — Serverdiscounter.com, confidence: low.
20. **[ecosystem]** GitHub repo ~33.6k stars, 1551 forks, 358 open issues; one dominant maintainer (binwiederhier/Philipp C. Heckel) plus a supporting contributor base. — GitHub, confidence: high.
21. **[ecosystem]** Steady mid-2026 release cadence: server v2.25.0 (Jun 24) → v2.27.0 (Aug 4); Android app v1.25.2 (Jul 23); iOS v1.7.0 (May 30) — active maintenance within ~1-2 months of research date. — ntfy docs/GitHub releases, confidence: high.
22. **[ecosystem]** Project accepts GitHub Sponsors for the maintainer — single-maintainer-led, donation-supplemented model, paid tiers are supplementary revenue. — GitHub, confidence: medium.

## Leads (not chased)
- Exact DigitalOcean droplet region (affects EU latency/residency) not disclosed anywhere fetched.
- No zero-cost endpoint researched for what the `http` action's URL should point at to flip an "acknowledged" toggle — that's a hosting-dimension question, not ntfy's own scope.
- Free-tier numeric limits (#5) sourced from 2023-2024 GitHub threads — a live `curl https://ntfy.sh/v1/account` check would give current authoritative numbers.
- No 2026 GDPR/EU regulator commentary specifically flagging ntfy.sh's US jurisdiction.
- No "bus factor"/succession discussion located for the single-maintainer risk.

## Not found
- No physical datacenter region (EU vs US) for the public server.
- No GDPR adequacy statement or EU representative designation (ToS/privacy policy read as generic/US-oriented).
- No second independent source confirming the VPN/keep-alive battery-drain issue as widespread vs. device-specific.
- No official SLA/uptime numbers beyond the informal, 2022-dated FAQ note.

## Verdict
Strong, low-effort fit on the criteria that matter most: no custom app needed (official app on Play/F-Droid), the `http` action button is a documented, server-validated mechanism for firing an arbitrary webhook on tap (high confidence, with one known workaround-able parsing quirk), publishing is a one-line cron-callable `curl` (high confidence), and the free tier's 250 msgs/day ceiling comfortably covers a few alerts/night (medium-high confidence, numbers slightly dated). Main honest risk is delivery timing: default FCM path is admittedly "not great" per the maintainer, and the low-latency "instant delivery" alternative needs battery-optimization exemption and has one open (single-source) battery-drain complaint — a real but manageable trade-off, especially given active July/August 2026 reliability fixes. Sweden/EU angle is mildly unfavorable but not a functional blocker: the hosted server is US/Connecticut-governed with no stated EU data residency, fully mitigated by ntfy's well-documented, low-complexity self-hosting option. Ecosystem health is strong (active releases, thousands of stars), tempered by the typical solo-maintainer sustainability risk of most open-source infra projects.
