# Frost-alert

Single-user frost-warning automation for overwintering bonsai. A GitHub Actions job classifies the forecast, sends Telegram alerts, and pings a watchdog so a missed run is not a silent frost night.

Needs CPython 3.13 and [uv](https://docs.astral.sh/uv/). Host the watch on a GitHub repository you control. A local clone is not enough.

## Setup

```text
uv sync
uv run frost-alert setup
```

Setup prompts for temperature scale (`C` or `F`), frost threshold, and location (city, postal code, or coordinates). Confirm the resolved place. That writes `config/user.json`. Commit and push that file — scheduled checks never re-geocode.

## Operate the watch

Put `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `HEALTHCHECKS_PING_URL` in GitHub Secrets. Never commit those values, a `.env` file, or ping URLs.

Create a free [healthchecks.io](https://healthchecks.io) check. Set **period 6h** and **grace ~6h** on that check, store the ping URL in `HEALTHCHECKS_PING_URL`, and enable a notify channel so a miss warning can arrive. A healthchecks.io miss warning is not a frost alert.

Leave GitHub Actions workflow-failure email on. That is the $0 failure channel beside the watchdog.

After `config/user.json` is on the default branch and the secrets are set, run the **check** workflow once with `workflow_dispatch` to prove the job before the first frost night.

If you receive alerts on Android, whitelist Telegram from battery optimization.

The default path is a public repo on GitHub Free (or Pro if private). `schedule` runs only on the default branch. GitHub may disable a public-repo `schedule` after 60 days with no repository activity; successful `data/state.json` commits count as activity.
