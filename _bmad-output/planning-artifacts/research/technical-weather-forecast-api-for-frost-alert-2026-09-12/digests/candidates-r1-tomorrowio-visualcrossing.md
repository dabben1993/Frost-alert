# Candidates R1: Tomorrow.io & Visual Crossing Weather API

Research firewall note: this digest was produced with no project context beyond the brief. Both candidates are treated as secondary/wildcard checks (lighter depth) for a hobby frost-alert automation with Sweden as the primary test location.

Accessed date for all sources below: 2026-09-12.

---

## Tomorrow.io

### Claims

- Free API plan rate limits are 500 requests/day, 25 requests/hour, 3 requests/second, with no separate weekly/monthly cap — source: Tomorrow.io Support, "Free API Plan Rate Limits", https://support.tomorrow.io/hc/en-us/articles/20273728362644-Free-API-Plan-Rate-Limits, published: undated, accessed: 2026-09-12, confidence: high, class: pricing
- The public-facing Free plan (via the marketing pricing page) includes a 5-day forecast, 24 hours of historical weather data, 1 automatically monitored location, and 1 weather-based alert — source: Tomorrow.io, "Weather API" pricing page, https://www.tomorrow.io/weather-api/, published: undated, accessed: 2026-09-12, confidence: high, class: pricing
- An older developer-docs page describes a separate "Developer" plan as "always free" with up to 1,000 daily / 30,000 monthly calls and core + sample Air Quality/Pollen data layers — this conflicts with the 500/day figure above and the page itself is flagged "Updated over 5 years ago," so it may be stale — source: Tomorrow.io Docs, "Plan and API Keys", https://docs.developer.tomorrow.io/docs/your-account, published: stated as "updated over 5 years ago" (stale), accessed: 2026-09-12, confidence: low, class: pricing
- The core weather-forecast endpoint documentation states hourly forecasts are available for the next 120 hours (5 days) and daily forecasts for the next 5 days, via `location` query parameter supporting lat/long, city name, US zip, UK postcode, or Canada postal code — source: Tomorrow.io Docs, "Weather Forecast" reference, https://docs.tomorrow.io/reference/weather-forecast, published: "updated about 1 year ago", accessed: 2026-09-12, confidence: medium, class: coverage
- Location can be specified directly as city name, US zip, UK postcode, Canadian postal code, or lat/long decimal degrees — no separate geocoding call is needed for these formats; Tomorrow.io resolves them internally — source: Tomorrow.io Docs, "api-formats" and "Weather Forecast" reference, https://docs.tomorrow.io/reference/api-formats and https://docs.tomorrow.io/reference/weather-forecast, published: undated, accessed: 2026-09-12, confidence: high, class: integration
- Authentication uses a simple API key passed as a query parameter (`apikey=YOUR_API_KEY`); no OAuth flow required — source: Tomorrow.io Docs, "Realtime Weather" reference (OpenAPI security scheme), https://docs.tomorrow.io/reference/realtime-weather, published: undated, accessed: 2026-09-12, confidence: high, class: integration
- A third-party German-language review (2026) states Tomorrow.io's accuracy in Central Europe is "solid," but that Germany's national weather service (DWD, ICON-D2 model) is often more precise specifically for precipitation forecasts in that region — source: KI-Syndikat, "Tomorrow.io im Überblick", https://www.ki-syndikat.de/tools/tomorrow-io/, published: undated (references "June 2026" state), accessed: 2026-09-12, confidence: low, class: accuracy
- No Europe-specific or Nordic-specific accuracy validation was found; the one independent accuracy study located (NASA Commercial Data Program) validated Tomorrow.io's spaceborne precipitation radar performance only over the continental United States (CONUS), not Europe — source: Tomorrow.io Blog citing NASA CSDA, https://www.tomorrow.io/blog/nasa-csda-validates-spaceborne-precipitation-radar-tomorrowio/, and NASA NTRS Quality Assessment Report PDF, https://ntrs.nasa.gov/api/citations/20260002099/downloads/Tomorrow_io_Radar_QA_SME_Report_Final_signed.pdf, published: undated (2026 NASA report), accessed: 2026-09-12, confidence: medium, class: accuracy
- Consumer app-store reviews aggregated on a third-party site are mixed: several users report temperatures and precipitation "way off" from other apps and slow/no support responses; others say it's comparable to other weather apps — source: JustUseApp, "Tomorrow io Reviews (2026)", https://justuseapp.com/en/app/1443325509/weather-by-tomorrow-io/reviews, published: undated (aggregates dated user reviews), accessed: 2026-09-12, confidence: low, class: accuracy
- A short (~8 hour) "degraded precipitation" incident affecting Classic and Next-Gen UP-Europe radar-covered areas was reported and resolved on 2026-08-07; a separate "global regions degraded, missing data" incident was also logged days later — source: IsDown status aggregator, "Tomorrow.io Degraded precipitation ... Aug 2026", https://isdown.app/status/tomorrow-io/incidents/635312-degraded-precipitation-on-classic-and-next-gen-up-europe-over-radar-covered-areas, published: 2026-08-07, accessed: 2026-09-12, confidence: medium, class: reliability
- Tomorrow.io is a US-hosted company with no advertised native EU data region as of the cited article's reference point (June 2026); this is a GDPR/data-residency consideration rather than a direct API-quality issue — source: KI-Syndikat, "Tomorrow.io im Überblick", https://www.ki-syndikat.de/tools/tomorrow-io/, published: undated (references June 2026), accessed: 2026-09-12, confidence: low, class: reliability

### Leads

- Verify at signup whether the Free plan requires a credit card (not confirmed in any source retrieved this session).
- The conflicting free-tier numbers (500/day vs. 1,000/day-30,000/month) should be resolved by creating a live account and checking the current dashboard limits, since one source is 5+ years old.
- KI-Syndikat article names Meteomatics (Switzerland) and MeteoBlue as EU-hosted competitors actively marketing against Tomorrow.io's lack of an EU region — worth a look if GDPR/data residency matters for this hobby project.
- No source specifically addressed overnight/minimum-temperature accuracy (as opposed to precipitation) for any region — worth a targeted follow-up search if this candidate advances past the wildcard stage.

### Could not find

- Any accuracy benchmark specific to Sweden/Nordic locations (temperature or precipitation).
- Any accuracy benchmark specific to overnight/minimum temperature forecasts (most located evidence concerns precipitation).
- Confirmation of current, non-conflicting free-tier rate limits from a single authoritative page (two different numbers found on two different Tomorrow.io–owned pages).
- Explicit statement on whether a credit card is required to activate the free tier.

---

## Visual Crossing Weather API

### Claims

- The free plan provides 1,000 weather records/day, usable for historical, forecast, and current-conditions data, with global coverage and no credit card required to receive the daily free allotment (credit card is only needed to enable metered overage billing) — source: Visual Crossing, "Visual Crossing Weather Free Plan" documentation, https://www.visualcrossing.com/resources/documentation/weather-data/visual-crossing-weather-free-plan-free-weather-data-for-analysts-and-api-developers/, published: undated, accessed: 2026-09-12, confidence: high, class: pricing
- A single request for a full 15-day forecast for one location (including hourly data) counts as only 1 "record" against the daily quota, regardless of hourly granularity, meaning up to 1,000 forecast lookups/day are possible on the free tier — source: Visual Crossing, "What exactly is a weather record?", https://www.visualcrossing.com/resources/documentation/weather-data/what-exactly-is-a-weather-record/, published: undated, accessed: 2026-09-12, confidence: high, class: pricing
- Beyond the free 1,000 records/day, overage on the Metered plan costs $0.0001 per additional record — source: Visual Crossing, "What will my weather data cost?", https://www.visualcrossing.com/resources/blog/what-will-my-weather-data-cost/, published: undated, accessed: 2026-09-12, confidence: high, class: pricing
- The Timeline Weather API supports hourly and daily forecast data out to 15 days, plus alerts and astronomical data (sunrise/sunset, moon phase); a newer "Timeline LLX" low-latency endpoint (public beta) offers the same forecast horizon with typical sub-40ms response times and is available to free-tier accounts — source: Visual Crossing, "Weather API Documentation" and "Timeline Low Latency LLX Weather API", https://www.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/ and https://www.visualcrossing.com/resources/documentation/weather-api/timeline-llx-weather-api/, published: undated, accessed: 2026-09-12, confidence: high, class: coverage
- Location can be specified as a full/partial address, city + country, city + state, postal/ZIP code, or lat/long; the API performs internal geocoding automatically and returns a `resolvedAddress` field showing what it matched — source: Visual Crossing, "Weather Data FAQ" and "Timeline Weather API Documentation", https://www.visualcrossing.com/resources/documentation/weather-data/frequently-asked-questions-faq-for-visual-crossing-weather-data/ and https://www.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/, published: undated, accessed: 2026-09-12, confidence: high, class: integration
- Visual Crossing explicitly recommends passing lat/long directly rather than an address string when possible, noting that address geocoding "can make mistakes" and this is "especially true in remote countries" — relevant caution for northern Sweden — source: Visual Crossing, "Tutorial: How to Build a Weather Dataset...", https://www.visualcrossing.com/resources/documentation/weather-data/how-to-build-a-weather-dataset-for-download-bulk-import-or-scheduling/, published: undated, accessed: 2026-09-12, confidence: medium, class: integration
- Authentication is a simple API key passed as a query/path parameter (`key=YOUR_API_KEY`); requests are plain HTTP GET returning JSON or CSV — source: Visual Crossing, "Timeline Low Latency LLX Weather API" docs, https://www.visualcrossing.com/resources/documentation/weather-api/timeline-llx-weather-api/, published: undated, accessed: 2026-09-12, confidence: high, class: integration
- Visual Crossing's own FAQ states weather-data accuracy "depends on many factors" (station density, distance from requested location, model resolution, etc.) and that "no weather data source is perfect for every location and time" — this is a general accuracy disclaimer, not a specific performance number, and no Nordic/Sweden-specific accuracy claim was found from Visual Crossing or any third party in this session — source: Visual Crossing, "Weather Data FAQ", https://www.visualcrossing.com/resources/documentation/weather-data/frequently-asked-questions-faq-for-visual-crossing-weather-data/, published: undated, accessed: 2026-09-12, confidence: medium, class: accuracy
- Exceeding assigned request/concurrency/usage limits returns HTTP 429; in "very rare" extreme fair-use violations, Visual Crossing states it may temporarily suspend an account (with prior email notice) rather than just throttle — source: Visual Crossing, "Weather Data FAQ" and "Understanding the 'fair use' system in Visual Crossing Weather", https://www.visualcrossing.com/resources/documentation/weather-data/frequently-asked-questions-faq-for-visual-crossing-weather-data/ and https://dev.visualcrossing.com/resources/documentation/weather-api/understanding-the-fair-use-system-in-visual-crossing-weather/, published: undated, accessed: 2026-09-12, confidence: medium, class: reliability
- Visual Crossing's own documentation recommends segmenting large queries to avoid timeouts, noting a ~120-second server-side timeout ceiling exists in their load-balancing stack — mainly relevant for bulk/historical queries, less so for a single-location daily forecast check — source: Visual Crossing, "Best practices for segmenting your weather queries", https://www.visualcrossing.com/resources/documentation/weather-api/best-practices-for-segmenting-your-weather-queries/, published: undated, accessed: 2026-09-12, confidence: medium, class: reliability

### Leads

- Visual Crossing's "Weather Ambassador" program offers additional free credits for public, non-commercial projects — could be relevant if this hobby project's usage ever exceeds 1,000 records/day (very unlikely for a single-location frost check).
- The Timeline LLX endpoint is in public beta; worth checking its current GA status and whether it changes rate limits before relying on it.
- No independent (non-vendor) accuracy or reliability commentary on Visual Crossing was found in this session — all retrieved sources were Visual Crossing's own documentation/blog. A follow-up search on independent review sites or forums (e.g., Reddit, HN, comparison blogs) would strengthen confidence on accuracy/reliability claims.

### Could not find

- Any third-party (non-vendor) source discussing Visual Crossing's accuracy, reliability, or user complaints — all reliability/accuracy claims above are vendor-sourced self-disclosure, not independently verified.
- Any accuracy benchmark specific to Sweden/Nordic locations or to overnight/minimum-temperature forecasts specifically.
- Any reports of "aggressive upsell" or sudden pricing/plan changes for Visual Crossing (none surfaced in searches this session — absence of evidence, not evidence of absence).
- Confirmation of whether a credit card must be added at signup even to use the free 1,000 records/day (docs suggest no, since "free plan" and "metered plan without billing enabled" are described as the same underlying tier, capped at 1,000/day without a card).

---

## Cross-candidate note

Neither candidate has independently verified, Nordic-specific accuracy data for overnight/minimum-temperature forecasts. Both free tiers are usable for a single-location, low-frequency hobby check (Tomorrow.io: 500 requests/day; Visual Crossing: effectively up to 1,000 forecast lookups/day since a full 15-day multi-hour forecast costs 1 record). Visual Crossing's forecast horizon (15 days) exceeds Tomorrow.io's free-tier horizon (5 days), which matters less for a next-night frost check but could matter for early-warning use cases.
