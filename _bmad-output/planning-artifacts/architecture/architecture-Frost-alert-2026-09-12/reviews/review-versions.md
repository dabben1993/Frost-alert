# Finalize-gate review — versions / reality-check

- **Artifact:** `ARCHITECTURE-SPINE.md` (status: draft, updated 2026-09-13)
- **Lens:** Verify every committed decision was web-researched or reality-checked rather than asserted from training data: current library/framework versions, that each named technology still exists and fits, and — greenfield — the live defaults of any starter it leans on. Flag anything that could be out of date and wasn't confirmed against the web, the existing project, or the current starter.
- **Spine not edited.** This file is gate scratch only.
- **Review date:** 2026-09-13

## Verdict

**Pass with findings.** Every named Stack row still exists and still fits a single-user GHA + stdlib-HTTP frost checker. The memlog's 2026-09-13 checks for CPython, uv, and MET Norway Locationforecast 2.0 hold. Additional live checks today confirm `actions/checkout@v7`, `actions/setup-python@v7`, `ubuntu-latest`, Open-Meteo Forecast + Geocoding, Telegram Bot API, and healthchecks.io ping.

The holes are not dead products. They are **imprecise pins and unbound live defaults**: Telegram is identified by a month stamp instead of Bot API **10.3**; MET Norway 2.0 is a family of endpoints (live HOWTO is `/compact`); GitHub Actions' new-repo `GITHUB_TOKEN` is `contents: read`; Open-Meteo timestamps default to **GMT**; uv 0.12 `uv init` now scaffolds a packaged `uv_build` app. Two units that obey every AD could still pick incompatible surfaces.

## Method

Checked against the web on 2026-09-13 (this review), plus the architecture memlog and the repo as it exists today.

| Source | What it settled |
| --- | --- |
| Architecture `.memlog.md` (2026-09-13) | CPython 3.14.7 latest / 3.13.15 current; setup-python@v7 README example uses 3.13; uv 0.12.x (0.12.13 reported 2026-09-10); MET Norway identifying User-Agent (missing UA → 403); lat/lon 4 decimals |
| python.org / Python Insider 2026-08-05 | Reconfirmed 3.14.7 latest stable, 3.13.15 current 3.13 |
| PyPI / uv releases | Reconfirmed uv 0.12.13 (2026-09-10) |
| github.com/actions/checkout | Current major **v7** (latest listed **v7.0.1**, 2026-07-20) |
| github.com/actions/setup-python | Current major **v7** (v7.0.0, 2026-07-20); README still examples `python-version: '3.13'` and `actions/checkout@v7` |
| actions/runner-images + GitHub-hosted runners docs | `ubuntu-latest` → Ubuntu **24.04**; `ubuntu-26.04` is public preview |
| open-meteo.com/en/docs + geocoding-api | Forecast `/v1/forecast` and Geocoding `geocoding-api.open-meteo.com/v1/search` still public no-key (non-commercial); live defaults below |
| core.telegram.org/bots/api | Bot API **10.3** (2026-08-24); getUpdates vs webhook still mutually exclusive; updates kept ≤ 24h |
| healthchecks.io/docs/http_api + apiv2 | Ping API at `hc-ping.com`; Management API create defaults period **86400s**, grace **3600s** |
| api.met.no Locationforecast 2.0 + ToS + HOWTO | 2.0 live; `/compact` recommended; `altitude` query param; UA + 4 decimals still 403 if missed |
| docs.astral.sh/uv/concepts/projects/init | uv 0.12 `uv init` default: packaged app, `src/<name>/`, `uv_build>=0.12.13,<0.13` |
| GitHub Docs: GITHUB_TOKEN / workflow permissions | New personal repos default `GITHUB_TOKEN` to **contents: read** (and packages: read) |
| Workspace scan | No product `.python-version` or `pyproject.toml`. Greenfield for the app. PoC `scripts/poc-telegram-getupdates.py` uses stdlib `urllib` — matches AD-2, is not a stack lock. |

No cookiecutter/Copier/template repo is named. The starter the spine leans on is **uv 0.12 + actions/setup-python@v7 + GitHub-hosted `ubuntu-latest`**.

## Stack table — row by row

| Spine pin | Live 2026-09-13 | Memlog web-check at distill? | Fit | Notes |
| --- | --- | --- | --- | --- |
| CPython **3.13** | 3.13.15 current in-series; **3.14.7** is latest stable (2026-08-05) | Yes | Fits | Intentional minor pin, patch floats. Matches setup-python@v7 README example. Not stale. |
| uv **0.12** | **0.12.13** (2026-09-10) | Yes | Fits | Minor-line pin is current. Repo already uses uv for BMAD scripts. |
| actions/checkout **v7** | **v7** current; patch **v7.0.1** (2026-07-20) | No (this review) | Fits | README uses `@v7`. v7 blocks fork PR checkout by default on `pull_request_target` / `workflow_run` — this workflow is `schedule` + `workflow_dispatch`, so the new default does not bind. |
| actions/setup-python **v7** | **v7.0.0** (2026-07-20) | Partial (cited with CPython) | Fits | `python-version` is optional: falls back to `.python-version`, then PATH. Action docs still say always set version explicitly. AD-2 already pins both. |
| GitHub-hosted runner **ubuntu-latest** | Alias currently **Ubuntu 24.04**; 26.04 is preview (`ubuntu-26.04`) | No (this review) | Fits | Moving alias. Fine for stdlib Python. Will retarget when GitHub moves `-latest`. Not wrong today. |
| Open-Meteo Forecast API **public no-key 2026-09** | Live; no numeric version; free non-commercial, no key | No (this review) | Fits | Date-stamp is a “checked as of”, not a vendor version. Live defaults: `forecast_days=7` (enough for 30h lookahead), `temperature_unit=celsius` (matches AD-7), **`timezone=GMT`** (see F4). |
| Open-Meteo Geocoding API **public no-key 2026-09** | Live `v1/search`; no key | No (this review) | Fits | Default `count=10`, `language=en`. Returns `latitude`, `longitude`, **`elevation`**, **`timezone`** — matches AD-3 cache of lat/lon/elevation/timezone. |
| MET Norway Locationforecast **2.0** | 2.0 current | Yes (UA, 4 decimals) | Fits, surface under-specified | See F2. `altitude` (whole metres) is the wire name; missing it uses coarse 1 km topography. |
| Telegram Bot API **Bot API 2026-09** | Official version is **10.3** (2026-08-24), not a month stamp | No (this review) | Fits | getUpdates / webhook still exclusive; 24h retention still documented. See F1. |
| healthchecks.io **ping API 2026-09** | Live (`https://hc-ping.com/<uuid>`); HEAD/GET/POST | No (this review) | Fits | No product version. Operator-created check is the intended path. Management/auto-provision **defaults are 1 day / 1 hour**, not AD-10’s 6h / ~6h — already “document beside the secret, do not hardcode.” |

## Starter and platform live defaults

Greenfield: there is no application package in the repo yet. Builders will `uv init` and author `.github/workflows/check.yml` against GitHub’s current workflow defaults.

### uv 0.12 `uv init` (current docs)

- Default is a **packaged application** with a build system (changed in **v0.12**; prior uv left apps unpackaged).
- Layout: `src/<project_name>/__init__.py` plus `[project.scripts]` → `package:main`.
- Build backend example: `uv_build>=0.12.13,<0.13`.
- `.python-version` is written from the **discovered interpreter** unless `--python` is passed. Docs examples show `requires-python = ">=3.11"`.
- `--no-package` still yields a flat `main.py`.

AD-12’s `src/frost_alert/{domain,ports,adapters,entrypoints}` is compatible with the packaged src layout, but the spine does not bind packaged vs `--no-package`, `uv_build` vs another backend, `requires-python`, or console-script names. Two scaffolds that both “use uv 0.12” can still disagree (F5).

### actions/setup-python@v7

Live README: pin `python-version` (example **3.13**) or `python-version-file`. AD-2 already does this. No extra finding.

### GitHub Actions host defaults that AD-4 depends on

- New personal repositories: `GITHUB_TOKEN` **contents: read** (F3). Committing `data/state.json` needs `permissions: contents: write` in the workflow (or a non-default repo setting).
- `concurrency.cancel-in-progress` defaults to **false** if omitted. AD-4 already requires cancel-in-progress — good.
- `on.schedule` default timezone is **UTC**; IANA `timezone:` on a schedule entry exists (since 2026). A 6h cadence does not need local wall-clock, so UTC is fine.
- Public repos: scheduled workflows are **auto-disabled after 60 days with no repository activity**. A successful state commit every 6h is activity — but only if the push is allowed (couples to F3). Watchdog (AD-6/AD-10) still fires if the schedule dies.

### Open-Meteo Forecast live defaults (adapters will inherit unless they override)

- `timezone`: **GMT** (not config IANA, not `auto`) — F4.
- `temperature_unit`: **celsius** — aligned with AD-7.
- `forecast_days`: **7** — enough for AD-5’s 30h lookahead; no need to pin 16.
- Hourly variables: none unless requested — implementation detail, not a spine pin.

### MET Norway 2.0 live surface

HOWTO: use **`/compact`** (GeoJSON). `/complete` is larger JSON; `/classic` is legacy **XML**. Root `/2.0/?lat=` was removed. Query param for height is **`altitude`**. ToS: identifying User-Agent; max **4** lat/lon decimals or **403**. AD-11 already binds UA, 4 decimals, and elevation-required; it does not bind compact vs classic or the wire name `altitude` (F2).

### stdlib HTTP (AD-2)

`urllib.request`’s default User-Agent is generic (`Python-urllib/3.13`). MET Norway 403s that. AD-11 already requires an identifying UA (`Frost-alert` plus repo URL). Confirmed, not a new hole.

### healthchecks.io

Ping URL is secret; period/grace are operator-configured. Live create defaults (1d / 1h) would miss a 6h job if someone auto-provisions. AD-10 already forbids hardcoding and tells the operator to document 6h + ~6h beside the secret. No extra spine pin required.

## Findings

### F1 — Telegram version pin is a month stamp; live identifier is Bot API 10.3

- **Location:** Stack table, “Telegram Bot API | Bot API 2026-09”
- **Trigger:** Official changelog (`core.telegram.org/bots/api`, fetched 2026-09-13) lists **Bot API 10.3** on **2026-08-24** (10.2 was 2026-07-14). There is no “Bot API 2026-09” product. The row was not web-checked in the architecture memlog.
- **Guard:** Pin `Telegram Bot API | 10.3` (or `10.3 as of 2026-09-13`). The methods AD-9 needs (`getUpdates`, `answerCallbackQuery`, inline keyboard, 24h retention, webhook disables polling) are unchanged in 10.3.
- **Consequence:** Two builders treat “2026-09” as a date check vs a version; one copies 10.2 blog posts, another 10.3. Unlikely to break getUpdates, but the Stack table claims a version it did not verify.

### F2 — MET Norway 2.0 live surface is `/compact` + `altitude`; spine only names “2.0”

- **Location:** Stack “MET Norway Locationforecast | 2.0”; AD-11
- **Trigger:** Current HOWTO: `/weatherapi/locationforecast/2.0/compact` (GeoJSON). `/classic` is XML. `/complete` is a larger JSON. Root `/2.0/?lat=` is gone. Height query parameter is **`altitude`** (integers, metres). AD-11 says “elevation required” and config stores `elevation_m` — concept is right; wire name and path are not bound. UA and 4 decimals **were** web-checked and match ToS.
- **Guard:** Bind compact (JSON) in AD-11 or the Stack row: path `/2.0/compact`, query `altitude` from `elevation_m`. Forbid `/classic` unless XML is an explicit later port.
- **Consequence:** One adapter parses GeoJSON compact; another follows old “2.0” examples into XML classic or a 404/403 root. Failover looks like an outage (AD-6 no-ping) even though MET is up.

### F3 — GitHub Actions live default cannot commit `data/state.json`

- **Location:** AD-4; Structural Seed `.github/workflows/check.yml`; host sentence “v1 host is GitHub Actions only”
- **Trigger:** GitHub Docs (2026): new personal repositories grant `GITHUB_TOKEN` **read** on `contents` (and packages). AD-4’s single writer **commits** `data/state.json`. The spine never pins `permissions: contents: write` (and a push token). Not in the distill memlog.
- **Guard:** In AD-4 or the check.yml seed: workflow `permissions: contents: write` (minimum needed to push state). Keep other scopes unset/none.
- **Consequence:** On a default-settings public clone, checkout works and the job can classify/alert/ping, then the state commit fails. Next tick re-reads stale `telegram_offset` / `alerted_windows` / season — the divergence AD-4 exists to prevent. Public-repo 60-day schedule auto-disable also stays in play if pushes never land.

### F4 — Open-Meteo live timezone default is GMT, not the config IANA zone

- **Location:** Stack Open-Meteo Forecast; AD-8 (frost event = local calendar date in config IANA zone); AD-11
- **Trigger:** Forecast docs, live default: `timezone` = **GMT**. `temperature_unit` default **celsius** matches AD-7 and needs no extra pin. Geocoding already returns `timezone` for AD-3. Distill memlog did not web-check Open-Meteo.
- **Guard:** Forecast adapter must request `timezone=auto` or the stored IANA zone, **or** parse UTC/GMT timestamps and convert with config timezone before the domain sees the series. Do not rely on the API default.
- **Consequence:** One adapter omits `timezone` (GMT hours); another uses `auto`. Same forecast, different local dates around midnight — AD-8 event keys split, duplicate 24h alerts or a skipped window.

### F5 — uv 0.12 `uv init` live defaults are unbound (packaging changed in 0.12)

- **Location:** AD-2, AD-12, Stack uv 0.12, Structural Seed
- **Trigger:** Current uv docs: default `uv init` is a **packaged** app with `src/`, `[project.scripts]`, and `uv_build>=0.12.13,<0.13`. “Prior to v0.12, uv did not define a build system for applications by default.” `.python-version` / `requires-python` follow the discovered interpreter unless `--python 3.13` is passed. Training-era “flat `main.py`” is now `--no-package`. No product `pyproject.toml` exists to ratify a convention.
- **Guard:** Bind the scaffold: `uv init` packaged src layout (already implied by AD-12), `requires-python = ">=3.13"`, `.python-version` `3.13`, and either accept `uv_build` (current default) or name hatchling. Name console scripts for setup vs check if both are entry points.
- **Consequence:** One unit ships an importable `frost_alert` package with `uv run setup`; another drops `main.py` at repo root and duplicates domain in the GHA step. AD-12’s “not a script pile” fails at cold start.

## Confirmed current — no spine change required

- **CPython 3.13** as a minor pin while 3.14.7 is latest: deliberate, documented, matches setup-python@v7’s own example. Not out of date.
- **uv 0.12** line matches 0.12.13.
- **actions/checkout@v7** and **actions/setup-python@v7** are the current majors.
- **ubuntu-latest** exists and currently means 24.04. Pinning the alias is the going GitHub example; 26.04 is still preview.
- **MET Norway UA + 4 decimals + elevation/altitude required:** ToS still 403s missing/generic UA and 5+ decimals. Memlog check stands.
- **Telegram getUpdates vs webhook + 24h retention:** still in the official Bot API notes. AD-9 matches live docs.
- **healthchecks.io ping API:** exists; AD-10 correctly refuses to hardcode period/grace (live create defaults are 1d/1h).
- **Open-Meteo no-key + geocoding elevation/timezone fields:** exist; default Celsius matches AD-7; default 7-day forecast covers 30h lookahead.
- **No brownfield app pin to contradict:** no `.python-version` / `pyproject.toml`. PoC stdlib HTTP is consistent with AD-2.
- **stdlib HTTP / no requests/httpx / no web framework:** still a coherent 3.13 choice; urllib remains in the stdlib.

## Suggested triage (for the parent gate; not applied here)

| ID | Suggested disposition |
| --- | --- |
| F1 | Autofix: Stack row `Telegram Bot API \| 10.3` |
| F2 | Autofix: AD-11 / Stack name `/2.0/compact` and query `altitude` |
| F3 | Autofix: AD-4 requires `permissions: contents: write` on `check.yml` |
| F4 | Autofix: AD-11 — ForecastSource timestamps in config IANA (or UTC with explicit conversion); do not use Open-Meteo GMT default |
| F5 | Discuss/autofix: bind `requires-python >=3.13` and packaged src (`uv_build` or named backend) |

## Compact summary

**Verdict:** Pass with findings

**Top findings:** F1 Telegram pin should be Bot API 10.3, not “2026-09”; F2 MET 2.0 live path is `/compact` + `altitude`; F3 GHA default `GITHUB_TOKEN` cannot commit state; F4 Open-Meteo timezone default is GMT; F5 uv 0.12 init packaging defaults unbound.

**File:** `_bmad-output/planning-artifacts/architecture/architecture-Frost-alert-2026-09-12/reviews/review-versions.md`
