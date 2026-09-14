---
title: 'Schedule the check on GitHub Actions'
type: 'feature'
created: '2026-09-14'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '71b29f331349acdf8265d460bd2ca2f64df172ce'
context:
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `frost-alert check` only runs on a laptop. Without `.github/workflows/check.yml`, no forecast or frost alert can fire while the owner’s devices are off.

**Approach:** Install that workflow so GitHub Actions, on a 6-hour default-branch schedule plus `workflow_dispatch`, checks out the repo, sets up Python 3.13 and uv, injects the three GitHub Secrets as env, and runs the existing `frost-alert check` entrypoint.

## Boundaries & Constraints

**Always:**
- Stay on branch `3-1-schedule-the-check-on-github-actions`. No story work on `master`.
- Add `.github/workflows/check.yml` only. Runner `ubuntu-latest`. `actions/checkout@v7`. `actions/setup-python@v7` with Python `3.13` (patch floats). `astral-sh/setup-uv@v10` with uv `0.12`. Then `uv sync --frozen` and `uv run frost-alert check`.
- Triggers: `schedule` cron `0 */6 * * *` (UTC) and `workflow_dispatch`. Cron timezone is not load-bearing; window identity stays remaining time (AD-5), not the cron name. A late run is still a useful check.
- `concurrency`: one in-flight group (`${{ github.workflow }}`), `cancel-in-progress: true`.
- `permissions: contents: write` now so 3.3 can commit `data/state.json` with `GITHUB_TOKEN`. Do not add a git commit or push step in this story.
- Job `env` maps `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `HEALTHCHECKS_PING_URL` from `${{ secrets.* }}` only. Those names never appear as secret *values* in source. Python still ignores the ping URL (3.3).
- Reuse `frost-alert check` unchanged. Missing Telegram env or `config/user.json` already exits 1 (job fails). Tests read the YAML with the stdlib; no live Actions, no sockets, no PyYAML.

**Never:**
- Do not implement MET Norway, git commit of `data/state.json`, Watchdog ping, operator README, or a second pytest/CI workflow.
- Do not change `check.py`, `check_tick.py`, domain, adapters, setup, or JSON keys.
- Do not add `requests`/`httpx`. Do not commit secrets, `.env`, `config/user.json`, or `data/state.json`.
- Do not use Actions cache or artifacts as the state store. Do not geocode from the job. Do not treat a watchdog miss as a frost alert (no watchdog yet).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Scheduled job | no `.github/` yet | `check.yml` has `0 */6 * * *`, `workflow_dispatch`, cancel-in-progress concurrency, `ubuntu-latest`, checkout@v7, setup-python@v7 `3.13`, setup-uv@v10 uv `0.12`, `uv sync --frozen`, `uv run frost-alert check` | N/A |
| Secrets mapping | workflow YAML | env is `${{ secrets.TELEGRAM_BOT_TOKEN }}`, `TELEGRAM_CHAT_ID`, `HEALTHCHECKS_PING_URL`; file has no token-like values | fail the test if a secret value is committed |
| Persist permission only | workflow YAML | `permissions: contents: write`; no `git commit` / `git push` step | N/A |
| Late run | schedule fires hours late | still invokes `frost-alert check`; YAML does not name windows 24/12/6 | N/A |

</frozen-after-approval>

## Code Map

- `.github/workflows/check.yml` -- **new.** Only file that schedules the tick. Do not add other workflows.
- `src/frost_alert/entrypoints/cli.py` -- dispatcher `check` → `check.main` (L12–17). Reuse; do not edit.
- `src/frost_alert/entrypoints/check.py` -- already reads `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` (L27–30); does not read `HEALTHCHECKS_PING_URL`. Reuse; do not edit.
- `src/frost_alert/check_tick.py` -- local tick composer from 2.5. Reuse; do not edit.
- `pyproject.toml` -- console script `frost-alert` (L9–10); `requires-python = ">=3.13,<3.14"`. `.python-version` is `3.13`. `uv.lock` exists — `--frozen` is valid.
- `tests/test_check_tick.py` -- 2.5 CLI/tick coverage. Do not re-test the tick loop here.
- `tests/test_check_workflow.py` -- **new.** Stdlib read of `check.yml` for every matrix row.
- Reuse, do not edit: domain, Open-Meteo, Telegram adapters, JSON stores, `send_frost_alert.py`, `apply_season.py`.

## Tasks & Acceptance

**Execution:**
- [x] `tests/test_check_workflow.py` -- failing tests for every I/O matrix row -- red first
- [x] `.github/workflows/check.yml` -- schedule, dispatch, concurrency, pins, secrets env, `uv run frost-alert check` -- FR14, AD-4, AD-10, NFR3

**Acceptance Criteria:**
- Given the default branch of a public GitHub Free repo (or GitHub Pro if private), when `.github/workflows/check.yml` is installed, then it runs on `schedule` every 6 hours and on `workflow_dispatch`, concurrency allows one in-flight run and cancels in-progress, and the runner is `ubuntu-latest` with `actions/checkout@v7` and `actions/setup-python@v7` pinned to Python 3.13.
- Given laptop and phone are off, when the scheduled workflow runs, then it executes `frost-alert check` and can fetch a forecast and send an alert.
- Given workflow secrets, when the job starts, then it reads `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `HEALTHCHECKS_PING_URL` from GitHub Secrets, and those values never appear in source.
- Given a multi-hour Actions delay, when a late run still executes, then it is a useful check and window identity still comes from remaining time, not the cron name.
- Given `uv run pytest`, when tests finish, then all pass, including every matrix row; no test opens a socket.

## Implementation Notes

`.github/workflows/check.yml` schedules `uv run frost-alert check` every 6h UTC plus `workflow_dispatch`. Job env maps the three GitHub Secrets; `permissions: contents: write` is present with no git commit/push. `tests/test_check_workflow.py` covers all four matrix rows (stdlib YAML read, sockets blocked). `uv run pytest` — 175 passed. Tick loop unchanged.
## Spec Change Log

## Review Triage Log

- `low` — Blind: sprint-status `in-progress` vs spec `in-review`. Tracker comments say move to `review` here. Disposition: patch.
- `false` — Blind: no live test that the job fetches/sends. Frozen Always: stdlib YAML read, no live Actions. `frost-alert check` already covers fetch/send in `tests/test_check_tick.py`. Secrets/config fail-closed is 2.5; operator README is 3.5.
- `low` — Blind: Frozen Never (cache/artifacts, extra workflows, extra permissions) untested. Current tree has only `check.yml` with `contents: write` and no cache. Extra negative tests add surface the matrix never showed. Reject.
- `medium` — Blind: tests treat `run:` membership as enough and parse only single-line keys, so step order and block scalars can drift. Same root as verification-gap unscoped YAML. Disposition: patch.
- `low` — Blind: Design Notes golden YAML omits job env/pins; Implementation Notes sit against Spec Change Log. Fix is to edit this spec. Reject.
- `false` — Blind: `concurrency.group` is only `${{ github.workflow }}`. Frozen Always requires that group plus `cancel-in-progress`. Late-run usefulness is remaining-time mapping (AD-5), not “must not cancel.”
- `false` — Blind: no workflow `name:` / `timeout-minutes`. Frozen Always enumerates the job; HTTP adapters already pass `timeout=TIMEOUT_S`. GitHub’s default job timeout still bounds a hang. Failure email still fires on the filename (NFR14).
- `false` — Blind: `uv sync --frozen` installs the dev group. Frozen Always names that exact command. `--no-dev` would be a spec edit.
- `low` — Blind: GitHub may disable unused public `schedule` after 60 days. Not a code defect; 3.3’s state commit and 3.5 README own activity/docs. Disposition: defer.
- `false` — Blind: `version: "0.12"` vs 0.12.x; checkout `persist-credentials` default. Frozen Always pins uv `0.12`. Default credentials are what 3.3 needs.
- `medium` — Verification-gap: `test_check_workflow.py` matches unscoped substrings. First `env:` / any `run:` / commented cron still pass while job `check` could lack secrets or a live schedule. Disposition: patch.

## Design Notes

Architecture deferred cron IANA vs UTC as not load-bearing. Use UTC `0 */6 * * *`. `contents: write` lands with the file so 3.3 does not fork permissions; the commit step stays 3.3. Map `HEALTHCHECKS_PING_URL` now so NFR3’s three-secret contract is complete; do not ping. Pin uv `0.12` via `astral-sh/setup-uv@v10` to match the stack; do not add PyYAML.

Golden job shape:

```yaml
on:
  schedule:
    - cron: "0 */6 * * *"
  workflow_dispatch:
permissions:
  contents: write
concurrency:
  group: ${{ github.workflow }}
  cancel-in-progress: true
```

## Verification

**Commands:**
- `uv run pytest` -- expected: all tests pass including every matrix row; existing tick tests still green; no sockets
