---
title: 'technical research: weather forecast API for frost alert'
type: 'technical'
topic: 'weather forecast API for frost alert'
decision: 'Select a weather forecast API/data source for the Frost Alert bonsai automation (Sweden-first, location-agnostic under the hood)'
source: 'native run'
status: complete
preset: 'deep'
validation: 'normal'
created: '2026-09-12'
updated: '2026-09-12'
---

# technical research: weather forecast API for frost alert

**Decision this research serves:** Select a weather forecast API/data source for the Frost Alert bonsai automation (Sweden-first, location-agnostic under the hood)

## Executive summary

**Pick Open-Meteo as the primary forecast source, with MET Norway's Locationforecast API as a cheap, easy fallback if Open-Meteo is unreachable.** Open-Meteo is genuinely free with no key, gives hourly data out to 16 days, blends 30+ models including a 1 km-resolution Nordic model that covers Sweden, and ships a free companion geocoding API so a friend can type a city name instead of coordinates — the best combination of accuracy signal, integration ease, and location-agnostic setup of any candidate [10][11][12][13][14][15]. Its one real weakness is reliability: three documented multi-hour 502 outages in 2026 on the free tier, with no SLA [14]. MET Norway/Yr costs nothing extra to add as a fallback, uses the same lat/long input, is Sweden's next-door national-institute-grade service with a long, drama-free operating history, and needs no API key [16][17][18][19] — pairing the two hedges Open-Meteo's biggest weakness for close to zero extra integration cost.

**The most important finding of this whole research run is a negative one: nobody — not SMHI, not MET Norway, not any commercial vendor, not academia — publishes a Sweden-specific, overnight-minimum-temperature-specific accuracy benchmark.** Two full research rounds, in English and Swedish, across institutional, academic, and commercial sources, could not close this gap (see Open Questions below). This is not a research failure; it is itself a finding, and it directly validates the forged-idea.md decision to use a non-zero, tunable safety margin (e.g. ~3°C) rather than trusting any single provider's raw forecast down to the degree — radiative-cooling (clear, calm) nights are structurally the hardest case for every model family, including the one MET Norway itself documents failing by 14°C in a real 2024 case study [21][36].

**SMHI, despite being Sweden's own national service, is not the recommendation.** It is free and well-documented in principle, but it retired its old forecast API on 2026-03-31 with roughly 6.5 months' advance notice (verified independently via SMHI's own announcements plus two unrelated GitHub issues) [1][2][3][39], breaking real integrations anyway, has no official SDK, and offers no location input beyond raw lat/long. For a "set up once and forget it" hobby automation, that operational churn risk outweighs the nationalistic appeal of using Sweden's own service — especially since independent (if dated) academic comparisons found SMHI and MET Norway roughly equivalent on general temperature accuracy [8][9].

**OpenWeatherMap is cut outright**: its no-card free tier only offers 3-hour-step forecasts, not hourly; true hourly data requires the paid "One Call 3.0" tier, which requires a credit card on file even to use its free call allotment [22][23] — a hard-gate failure against the "no cost, no card" requirement.

## Requirements frame

Sourced from the project brief, not from web research (per the research firewall, requirements are set by the project and the user, never by search results).

**Hard gates:**
- Free or near-$0, with no credit card required for the free tier
- Hourly (or near-hourly) forecast data at least 24h out, ideally further
- Accepts arbitrary locations — directly, or via a free/low-friction geocoding pairing — so a friend elsewhere can configure their own location without editing code
- Usable for frost-risk: must expose overnight low / minimum temperature, not just a daily high

**Weighted preferences (in priority order for this decision):**
1. Accuracy signal for Sweden specifically, and for overnight lows in particular (evidence permitting)
2. Long-term free-tier sustainability for an unattended, low-volume hobby workload
3. Ease of integration, especially how painlessly a non-technical friend's location gets turned into what the API needs

## Candidate screen

Seven candidates were researched in round 1: SMHI, Open-Meteo, MET Norway/Yr, OpenWeatherMap, WeatherAPI.com, Tomorrow.io, and Visual Crossing.

**Cut for failing a hard gate:**
- **OpenWeatherMap** — the no-card free tier caps forecast resolution at 3-hour steps; genuine hourly data requires the "One Call API 3.0" subscription, which mandates a credit card on file even though it includes a free daily call allowance [22][23]. This directly violates the "no credit card, no cost" hard gate.

**Screened through as finalists (3-5, per the decision shape's screening step):**
- **Open-Meteo** — strongest technical fit; screened through as primary candidate.
- **MET Norway / Yr.no (Locationforecast 2.0)** — Nordic-native, institutionally stable; screened through.
- **SMHI** — Sweden's own national service; screened through despite the API-churn flag, since "the national service" deserves a fair hearing on its home turf.
- **Visual Crossing** — wildcard; screened through for its best-in-class free-text location handling (any address, automatic geocoding, no separate call needed) [31][32][33] and generous effective daily quota [32].
- **WeatherAPI.com** — weak finalist; screened through because its free tier does meet the letter of the hard gates (hourly, no card, accepts city names directly), but its 3-day forecast horizon is the shortest of any finalist [25], and the one independent (US-based, non-Nordic) accuracy scoreboard found placed it tied for last among five providers compared, well behind MET Norway [26].

**Cut to a footnote (did not fail a hard gate, but dominated by a finalist on every criterion that matters here):**
- **Tomorrow.io** — free tier is only 500 requests/day with a 5-day horizon and a single monitored location [29][30], and its own documentation pages disagree with each other on the actual rate limit (a separate, older page says 1,000/day/30,000/month, marked "updated over 5 years ago") [41], it has no confirmed EU data region [34], and no accuracy evidence for Sweden or even Europe generally was found beyond a single German-language review noting Germany's own DWD tends to beat it on precipitation [34]. Visual Crossing beats it on every axis relevant here (horizon, quota-per-forecast-call, location handling), so Tomorrow.io does not carry forward as an independent finalist.

## Evidence per criterion

### Integration & location input

This dimension matters unusually much for this decision: the brief requires that a friend elsewhere can configure their own location without touching code, which puts real weight on how painlessly each API turns "a place a human would type" into "what the forecast call needs."

- **Visual Crossing** and **WeatherAPI.com** are the most friend-friendly: both accept a free-text address, city name, or postal code directly on the forecast call itself, with the API doing geocoding internally — Visual Crossing even returns a `resolvedAddress` field confirming what it matched [33]. WeatherAPI additionally exposes a dedicated autocomplete/search endpoint for building a location picker [27].
- **Open-Meteo** and **OpenWeatherMap** require a separate (but free, no-extra-key) geocoding call: Open-Meteo ships its own companion Geocoding API resolving city/postal-code to lat/long [13]; OpenWeatherMap's Geocoding API works the same way and shares the same free-tier quota as the main API [24].
- **SMHI** and **MET Norway** take latitude/longitude *only*, with no bundled geocoding — both point developers to third-party options (OpenStreetMap Nominatim is the common recommendation for both) [19][38]. Nominatim's usage policy caps traffic at 1 request/second and explicitly discourages periodic background geocoding [38] — not a problem for this use case, since a location only needs to be geocoded once at setup time and then cached as coordinates, never re-geocoded on every scheduled check.
- **MET Norway carries a specific accuracy trap**: forecast temperature is adjusted using a lapse-rate correction based on the elevation you supply; omitting it falls back to a coarse 1 km global topography dataset, and real Home Assistant users have hit measurably wrong forecasts from getting this wrong [20]. Any integration against MET Norway needs to explicitly pass elevation, not just lat/long.
- **SMHI has no official SDK**; every client library found was community-maintained, and the healthiest ones were only rewritten in the days/weeks after the March 2026 breaking change — they haven't accumulated a track record yet (per the SMHI candidate digest). Open-Meteo, by contrast, has official, actively maintained Python and TypeScript SDKs with binary (FlatBuffers) transport for efficient time-series pulls [12].

### Accuracy for overnight lows (the central, unresolved question)

No independently verified, Sweden-specific, minimum-temperature-specific accuracy benchmark exists for any candidate. This was the single most heavily researched question in this run (round 1 across all candidates, then a dedicated round-2 pass specifically chasing it in English and Swedish, academic and institutional sources) — and it came back empty on the head-to-head number every time.

What *does* exist, and is directly relevant:

- **SMHI** runs a public, continuous verification program (±2°C "hit rate" against ~180 stations, published monthly by county) [5][6], but this is a general temperature metric, not broken out by minimum-temperature or overnight performance, and it evaluates SMHI against itself, not against competitors. SMHI stopped issuing agricultural frost warnings in 2009 [7] — there is no current SMHI product aimed specifically at this use case.
- **MET Norway** publishes periodic "METinfo" verification reports for its MEPS model (the shared Nordic ensemble covering Norway, Sweden, Finland, and the Baltics). Its 2024 report documents, as a *named recurring problem*, a positive-bias failure mode on cold, radiatively-cooled nights — one worked case (Dagali, 15–16 January) shows the model forecasting a low of roughly −20°C against an observed −34°C, attributed to the model failing to reproduce rapid near-surface cooling despite a correct cloud forecast [21]. This is a single case study, not an aggregate skill score, but it is the most concrete, Nordic-domain evidence found anywhere in this research of exactly the failure mode a frost-alert tool most needs to worry about.
- Two dated (2017-2018) but mutually corroborating **independent Swedish academic comparisons** found SMHI and MET Norway/Yr roughly equivalent on general 0-24h temperature accuracy, with differences "generally small and rarely statistically significant" [8][9] — consistent with a low-confidence, older hobbyist blog analysis reaching the same conclusion for Stockholm specifically. None of these isolate overnight minimums or postdate the SMHI API migration.
- It is well-established meteorological science, not specific to any provider, that **radiatively-cooled (clear, calm) nights are structurally harder for every NWP model to forecast** than wind-driven ("advective") nights, because the outcome depends on hyper-local factors (cloud-cover timing, boundary-layer decoupling, soil moisture, terrain) that models at typical grid resolution cannot fully resolve [36]. A 2025/2026 preprint on machine-learning post-processing for next-day minimum temperatures across Western Europe explicitly cites this same limitation as its motivation, and shows ML correction can meaningfully improve on raw model output — a possible future enhancement, not something this decision needs to build now [37].
- **Design implication:** this evidence gap is itself the strongest argument for the forged-idea.md decision to use a tunable safety margin above the literal freezing point rather than trusting any provider's raw forecast to the degree, and to let the user tighten the margin down once they've learned their own microclimate's behavior against real outcomes.

### Cost & free-tier sustainability

| Candidate | Free tier limits | Card required? | Notable risk |
|---|---|---|---|
| Open-Meteo | 600/min, 10k/day, 300k/month [11] | No [10] | 3 documented multi-hour 502 outages in 2026; no SLA [14] |
| MET Norway | 20 req/s per app, no hard daily/monthly cap [17] | No [16] | None found beyond generic public-service caveats; no SLA offered to anyone, free or paid [16] |
| SMHI | No published numeric limit, fair-use only [4] | No | Retired its main forecast API in March 2026 with ~6.5 months' advance notice — but broke real integrations anyway; a further API (Mesan2gv2) may already be scheduled for retirement in Nov 2026 (unverified lead), which would confirm a recurring churn pattern |
| Visual Crossing | 1,000 records/day (a full 15-day forecast for one location = 1 record) [31][32] | No, for the free allotment [31] | All accuracy/reliability claims found are vendor-sourced only; no independent verification located |
| WeatherAPI.com | 100,000 calls/month [25] | No [40] | Only 95.5% advertised uptime on Free [25]; free-tier call cap has shrunk before (1M → 100K calls/month per historical forum reports) and briefly appeared to vanish in 2022 before returning [28] |

For a single-user, once- or twice-daily forecast check, every finalist's quota is far more headroom than the workload needs — quota size is not a differentiator here. The differentiator is **operational stability**: SMHI's recent breaking change and WeatherAPI's shrinking-limits history are yellow flags for a "configure once, forget it" automation; MET Norway's long, boring, drama-free public-service operating history is a green flag; Open-Meteo's documented outages are a real but manageable risk (the maintainer responds quickly, and a fallback source neutralizes it).

## Cross-dimension insights

- The accuracy gap and the cost/sustainability dimension point the same direction together: since no provider can be shown to be more *accurate* than another for this exact use case, the tie-breaker should be operational stability and integration ease — which is exactly where Open-Meteo and MET Norway pull ahead of SMHI, despite SMHI's home-turf appeal.
- The "arbitrary locations for a friend" requirement and the "no always-on device" hosting constraint (from the third, separate research area) compound: a geocode-once-and-cache pattern (needed for SMHI/MET Norway's lat/long-only input) fits naturally with a scheduled, stateless job that stores a resolved location once at setup rather than re-geocoding on every run — this should be carried into the hosting/architecture research and the setup-wizard design, not treated as a weather-API-only concern.
- MET Norway's elevation-parameter pitfall and the universal "radiative cooling is hard" finding both point to the same mitigation: whatever provider is chosen, the safety-margin design (already locked in forged-idea.md) is doing real, evidence-backed work, not just being conservative for its own sake.

## Contrary evidence

Red-team pass was not run for this session (`{workflow.red_team}` = `off`, not raised at the plan gate). No dedicated adversarial pass was performed; the "Could not find" sections within each candidate digest serve as the honest-gap record instead.

## Recommendations

1. **Use Open-Meteo as the primary forecast source.** No key, no cost, hourly data to 16 days, includes a free geocoding companion API, and has the best-documented integration surface of any candidate [10][11][12][13][14][15]. *Confidence: high on integration/cost facts (primary docs); medium on "best accuracy signal for Sweden," since no independent Sweden-specific benchmark exists — this is an inference from model diversity/resolution, not a verified ranking.*
2. **Add MET Norway's Locationforecast API as an automatic fallback** when Open-Meteo is unreachable (e.g. during one of its documented 502 incidents). Same lat/long input shape, no key, no added cost, long operating history [16][17][18][19], and it is the default weather source for roughly 83% of Home Assistant installations [20]. Remember to pass the elevation parameter explicitly to avoid the documented accuracy pitfall [20]. *Confidence: high on availability/terms; low-medium on whether it will actually out-accuracy Open-Meteo on any given night, given the documented cold-bias case [21].*
3. **Do not build against SMHI as the primary or sole source**, despite it being "Sweden's own" service. Its March 2026 breaking API change is verified from two independent sources [1][2][3][39]; a second API (Mesan2gv2) may already be scheduled for its own retirement in November 2026, which — if it holds — would suggest a recurring deprecation cadence, but that second data point is an unconfirmed lead, not a verified pattern (see Open Questions). For a "configure once" hobby automation with no maintainer actively watching it, even one confirmed unannounced-to-the-integrator breaking change is enough churn risk to outweigh the nationalistic appeal, especially since SMHI offers no accuracy advantage over MET Norway per the (dated) academic evidence [8][9]. It remains a reasonable secondary cross-check if the user wants a third opinion.
4. **Cut OpenWeatherMap entirely** — its free, no-card tier cannot deliver hourly resolution; the tier that can requires a credit card [22][23], violating the project's hard cost/no-card gate.
5. **Feed the unresolved accuracy question directly into the escalation-cadence and threshold design** (open items in forged-idea.md): since no provider can be shown to nail overnight lows precisely, the design should keep the safety margin user-tunable and treat the 24h-out check as a coarse early warning rather than a precise prediction, tightening only as the shorter-window checks approach.

## Open questions

- **No Sweden/Nordic-specific, overnight-minimum-temperature accuracy benchmark exists for any candidate.** Closing this for real would require a DIY approach: Open-Meteo's own "Previous Runs" and "Historical Forecast" APIs are explicitly designed to let a developer reconstruct past forecasts and compare them to later observations (per the round-2 accuracy-gap digest) — building a small personal accuracy log (predicted vs. actual overnight low, for the user's own garden, over one winter) would be a more useful answer than any published study, and doubles as the data needed to eventually tune the safety-margin threshold per the forged-idea.md design.
- **SMHI's own SNOW1gv1 documentation could not be read directly this session** (it is a JavaScript-rendered SPA that a plain page fetch could not render) — all structural claims about it were sourced secondhand via a GitHub issue that quotes the docs. If SMHI is ever revisited, verify field names against the live docs with a JS-capable browser fetch before writing an integration.
- **An unverified lead suggests SMHI's Mesan2gv2 analysis API may already be scheduled for retirement around November 2026** — not independently confirmed this session. If true, this would be SMHI's second breaking API change within a year and would upgrade "one confirmed churn event" to "a genuine pattern" — worth a quick check of SMHI's "Uppdateringar öppna data" page before committing to any SMHI-based fallback, and worth revisiting this report's SMHI verdict if it's confirmed.
- **Open-Meteo's exact `models=` parameter value for forcing its Nordic (MET Norway-sourced) model** was not confirmed — the documented model-selector list didn't clearly list it even though the data-sources table confirms it's ingested. Worth a direct check against the live API before final implementation.

## Source appendix

| # | Claim/finding it supports | Publisher | Pub. date | Accessed | Confidence |
|---|---|---|---|---|---|
| [1] | SMHI retired the pmp3g forecast API on 2026-03-31, replaced by SNOW1gv1 | [SMHI — "API för PMP3 avvecklas 31 mars"](https://www.smhi.se/data/om-smhis-data/uppdateringar-oppna-data/uppdateringar-i-smhis-oppna-data/2026-03-16-api-for-pmp3-avvecklas-31-mars) | 2026-03-16 | 2026-09-12 | high |
| [2] | Home Assistant's SMHI integration broke on 2026-03-31 from this migration | [GitHub — home-assistant/core #166935](https://github.com/home-assistant/core/issues/166935) | 2026-03-31 | 2026-09-12 | high |
| [3] | MagicMirror's SMHI provider independently broke the same day (404s) | [GitHub — MagicMirrorOrg/MagicMirror #4081](https://github.com/MagicMirrorOrg/MagicMirror/issues/4081) | 2026-03-31 | 2026-09-12 | high |
| [4] | SMHI publishes no numeric rate limit, fair-use terms only; CC BY 4.0 SE license | [SMHI — "Villkor för användning av SMHIs öppna data"](https://www.smhi.se/data/om-smhis-data/villkor-for-anvandning) | undated (updated 2026-06-15) | 2026-09-12 | high |
| [5] | SMHI's public ±2°C temperature verification, by county/month, ~180 stations | [SMHI — "Uppföljning av prognoser"](https://www.smhi.se/data/temperatur-och-vind/temperatur/uppfoljning-av-prognoser) | 2025-02-05 (updated 2025-09-23) | 2026-09-12 | high |
| [6] | SMHI's verification methodology dates to 2017; no min-temp-specific breakdown | [SMHI — "Hur mäts prognosers träffsäkerhet?"](https://www.smhi.se/kunskapsbanken/meteorologi/vaderprognoser/hur-mats-prognosers-traffsakerhet) | undated | 2026-09-12 | high |
| [7] | SMHI stopped issuing agricultural frost warnings after the 2009 season | [SMHI — "Frost och markfrost"](https://www.smhi.se/kunskapsbanken/meteorologi/sno--och-isfenomen/frost-och-markfrost) | undated | 2026-09-12 | high |
| [8] | SMHI vs. MET Norway 0-24h temperature forecasts roughly comparable (2018 data) | [Uppsala University thesis, DiVA](http://urn.kb.se/resolve?urn=urn%3Anbn%3Ase%3Auu%3Adiva-383449) | undated (2018 data) | 2026-09-12 | low |
| [9] | SMHI vs. YR 24h forecasts: differences small, rarely significant | [Uppsala University thesis, DiVA](http://urn.kb.se/resolve?urn=urn%3Anbn%3Ase%3Auu%3Adiva-577046) | undated | 2026-09-12 | low |
| [10] | Open-Meteo requires no API key/sign-up/card for non-commercial use | [Open-Meteo homepage](https://open-meteo.com/) | undated | 2026-09-12 | high |
| [11] | Open-Meteo free limits: 600/min, 5k/hr, 10k/day, 300k/month per IP | [Open-Meteo Terms of Use](https://open-meteo.com/en/terms) | undated | 2026-09-12 | high |
| [12] | Open-Meteo hourly data to 16 days; official Python/TS SDKs | [Open-Meteo API Docs](https://open-meteo.com/en/docs) | undated | 2026-09-12 | high |
| [13] | Open-Meteo free companion Geocoding API resolves city/postal to lat/long | [Open-Meteo Geocoding API docs](https://open-meteo.com/en/docs/geocoding-api) | undated | 2026-09-12 | high |
| [14] | Open-Meteo had 3 documented multi-hour 502 outages in 2026; no SLA | [GitHub — open-meteo/open-meteo #1801, #1870, #1866](https://github.com/open-meteo/open-meteo/issues/1801) | 2026 | 2026-09-12 | high |
| [15] | MET Nordic (1 km, MET Norway) is one of 30+ models Open-Meteo blends | [Open-Meteo API Docs](https://open-meteo.com/en/docs) | undated | 2026-09-12 | high |
| [16] | MET Norway Locationforecast is free, no key, no pricing tier | [MET Weather API FAQ](https://docs.api.met.no/doc/FAQ.html) | undated | 2026-09-12 | high |
| [17] | MET Norway rate ceiling: 20 req/s per app before special agreement needed | [MET Weather API Terms of Service](https://api.met.no/doc/TermsOfService) | 2020-06-26 | 2026-09-12 | high |
| [18] | Sweden is in MET's "Nordic priority" region (higher-res, more frequent updates) | [MET Locationforecast data model docs](https://docs.api.met.no/doc/locationforecast/datamodel.html) | undated | 2026-09-12 | high |
| [19] | Locationforecast takes lat/long only; MET recommends Nominatim/GeoNames | [Locationforecast HOWTO](https://docs.api.met.no/doc/locationforecast/HowTO.html) | undated | 2026-09-12 | high |
| [20] | MET Norway is the default weather source for ~83% of Home Assistant installs; elevation misconfiguration degrades accuracy | [Home Assistant Met.no integration docs](https://www.home-assistant.io/integrations/met) | undated | 2026-09-12 | medium |
| [21] | MEPS documented cold-bias case: forecast −20°C vs. observed −34°C (Dagali) | [MET-info 31-2024 verification report](https://www.met.no/publikasjoner/met-info/met-info-2024/_/attachment/inline/00476eb6-c021-4601-beb5-87e29c8f96f9:8de05906dd220c52fa401e7c2f16491b569a6907/MET-info-31-2024.pdf) | 2024 | 2026-09-12 | medium |
| [22] | OpenWeatherMap no-card free tier: 3-hour-step forecast only, 60 calls/min | [OpenWeatherMap Pricing](https://openweathermap.org/price) | undated | 2026-09-12 | high |
| [23] | True hourly forecast requires One Call 3.0, which requires a credit card | [OpenWeather FAQ](https://docs.openweather.co.uk/faq) | undated | 2026-09-12 | high |
| [24] | OpenWeatherMap Geocoding API (city/zip to lat/long) is in the free tier | [OpenWeatherMap Geocoding API docs](https://openweathermap.org/api/geocoding-api) | undated | 2026-09-12 | high |
| [25] | WeatherAPI.com Free: 100,000 calls/month, 3-day forecast, 95.5% SLA | [WeatherAPI.com Pricing](https://www.weatherapi.com/pricing.aspx) | undated | 2026-09-12 | high |
| [26] | US (Boone, NC) scoreboard: WeatherAPI 85.4/100, MET Norway 94.8, Visual Crossing 91.1 | [Dave's Sweater — "Right Ray / Wrong Ray"](https://davessweater.com/right-wrong-ray) | undated (rolling) | 2026-09-12 | medium |
| [27] | WeatherAPI.com accepts city name directly; dedicated Search/Autocomplete API | [WeatherAPI.com API docs](https://www.weatherapi.com/docs/) | undated | 2026-09-12 | high |
| [28] | WeatherAPI.com free tier shrank over time (1M → 100K calls/month); briefly appeared to vanish in 2022 | [GitHub — monicahq/monica #6288](https://github.com/monicahq/monica/issues/6288) | 2022-08-27 (updated 2024-06-29) | 2026-09-12 | medium |
| [29] | Tomorrow.io free tier: 500 req/day, conflicting older docs say 1,000/day | [Tomorrow.io Support — Free API Plan Rate Limits](https://support.tomorrow.io/hc/en-us/articles/20273728362644-Free-API-Plan-Rate-Limits) | undated | 2026-09-12 | high |
| [30] | Tomorrow.io Free plan: 5-day forecast, 1 monitored location | [Tomorrow.io Weather API pricing page](https://www.tomorrow.io/weather-api/) | undated | 2026-09-12 | high |
| [31] | Visual Crossing Free: 1,000 records/day, no credit card for free allotment | [Visual Crossing Free Plan docs](https://www.visualcrossing.com/resources/documentation/weather-data/visual-crossing-weather-free-plan-free-weather-data-for-analysts-and-api-developers/) | undated | 2026-09-12 | high |
| [32] | A full 15-day hourly+daily forecast for one location costs 1 record | [Visual Crossing — "What exactly is a weather record?"](https://www.visualcrossing.com/resources/documentation/weather-data/what-exactly-is-a-weather-record/) | undated | 2026-09-12 | high |
| [33] | Visual Crossing accepts address/city/postal directly, auto-geocodes | [Visual Crossing Timeline Weather API docs](https://www.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/) | undated | 2026-09-12 | high |
| [34] | Tomorrow.io: no confirmed EU data region; DWD often beats it on precipitation in Central Europe | [KI-Syndikat — "Tomorrow.io im Überblick"](https://www.ki-syndikat.de/tools/tomorrow-io/) | undated (refs June 2026) | 2026-09-12 | low |
| [35] | Seasonal (weeks-months) Fennoscandian time-to-freeze prediction skill, not short-lead overnight lows | [Roksvåg et al., QJRMS](https://doi.org/10.1002/qj.4403) | 2022 | 2026-09-12 | medium |
| [36] | Radiatively-cooled nights are structurally harder to forecast than advective nights | [NWS — "Atmospheric Controllers of Local Nighttime Temperature"](https://www.weather.gov/source/zhu/ZHU_Training_Page/winds/nighttime_influences/Nighttime_Influences.htm) | undated | 2026-09-12 | medium |
| [37] | ML post-processing can improve next-day Tmin forecasts 35-64% over baselines (Western Europe) | [EarthArXiv preprint](https://doi.org/10.31223/x55758) | 2025/2026 | 2026-09-12 | low |
| [38] | OSM Nominatim usage policy: 1 req/sec cap, discourages periodic bulk geocoding | [OSM Foundation — Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) | undated | 2026-09-12 | high |
| [39] | SMHI pre-announced the SNOW1gv1/Mesan2gv2 replacement APIs on 2025-09-12, ~6.5 months before retiring the old ones | [SMHI — "Nya API:er för meteorologiska prognoser och analyser"](https://www.smhi.se/data/om-smhis-data/uppdateringar-oppna-data/uppdateringar-i-smhis-oppna-data/2025-09-12-nya-apier-for-meteorologiska-prognoser-och-analyser) | 2025-09-12 (updated 2026-02-04) | 2026-09-12 | high |
| [40] | WeatherAPI.com Free plan requires no credit card at signup | [WeatherAPI.com — Signup page](https://www.weatherapi.com/signup.aspx/) | undated | 2026-09-12 | high |
| [41] | An older Tomorrow.io docs page describes a "Developer" plan at 1,000/day, 30,000/month — conflicts with the current 500/day figure; page marked "updated over 5 years ago" | [Tomorrow.io Docs — "Plan and API Keys"](https://docs.developer.tomorrow.io/docs/your-account) | stale (5+ years old) | 2026-09-12 | low |

## Staleness map

Computed via `recon_kit.py staleness`, using the technical pack's freshness bars (version/compatibility ≤ 1 month, ecosystem signals ≤ 6 months, landscape ≤ 12 months) plus the selection shape's pricing bar (≤ 3 months):

- **Re-check first:** the SMHI API-stability claims [1][2][3][4] and all five finalists' live pricing/rate-limit pages [4][11][17][25][31] — pricing and version-compatibility facts are the fastest-decaying claims in this report, and SMHI in particular has already shown it will change its API again, even with several months' advance notice.
- **Re-check within 6 months:** ecosystem/reliability signals — Open-Meteo's outage history [14], WeatherAPI's SLA/quota-shrinkage pattern [25][28], and MET Norway's Home Assistant adoption/reputation signal [20].
- **Re-check within 12 months:** the general landscape claims (which model families exist, who blends what) [10][12][15][18].
- **Effectively evergreen for this report's purposes:** the meteorological-principle claim about radiative cooling being hard to forecast [36] and the seasonal-frost academic literature [35] — these describe stable physical/scientific facts, not a vendor's current offering.

**Earliest re-check date: 2026-12-12** (3 months out, driven by the pricing/API-stability claims). A Refresh run before committing to final implementation is recommended given how recently SMHI's API changed.
