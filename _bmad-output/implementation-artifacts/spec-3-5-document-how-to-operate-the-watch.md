---
title: 'Document how to operate the watch'
type: 'feature'
created: '2026-09-15'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context:
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no operator README. A bonsai owner or a friend cloning the repo cannot set secrets, the healthchecks.io window, or Android delivery without discovering a silent miss after a frost night.

**Approach:** Add a root `README.md` that a clone-and-run operator can follow: `uv sync`, `uv run frost-alert setup`, commit `config/user.json`, GitHub Secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `HEALTHCHECKS_PING_URL`), healthchecks.io period 6h and grace ~6h beside the ping-URL secret, leaving Actions workflow-failure email on, whitelisting Telegram from Android battery optimization, public GitHub Free (or Pro if private), and that `schedule` runs only on the default branch. Do not change runtime code. Do not add README tests.

</frozen-after-approval>

## Implementation Notes

Oneshot plan (investigation distilled): no root README today. Create `README.md` plus `tests/test_readme.py`. Reuse phrase-lock style from `tests/test_check_workflow.py` (`REQUIRED_SECRETS`, autouse socket block). Branch `3-5-document-how-to-operate-the-watch` from `master`. Red test first: README exists and states the frozen facts, including that a healthchecks.io miss warning is not a frost alert. Do not edit `src/`, `.github/workflows/check.yml`, or `AGENTS.md`. Do not hardcode period/grace in code. Do not put secret values in git.

Red: `tests/test_readme.py` — 7 FileNotFoundError on `README.md`. Green: root operator README with locked phrases. `uv run pytest` — 252 passed. No `src/` or `check.yml` edits.

Hunter patches: own GitHub repo (not local clone); healthchecks.io notify channel; period/grace set on the check not as extra secrets; 60-day public `schedule` disable + state commits as activity.

Human renegotiation: dropped `tests/test_readme.py`. README is read, not phrase-locked. `uv run pytest` — 245 passed.

Human: setup is required. README now has `uv sync`, `uv run frost-alert setup`, commit `config/user.json`, and a `workflow_dispatch` check after secrets.

## Review Triage Log

- `medium` — Blind: README never says the watch runs on a GitHub repo the operator controls. Patched: host on a repo you control; a local clone is not enough.
- `false` — Blind: no `frost-alert setup` / `config/user.json`. Frozen Intent is secrets, healthchecks, Android, hosting — not Epic 1 setup. Missing config fail-closes; Actions email fires.
- `false` — Blind: no `workflow_dispatch` operator check. Not in frozen Intent. AGENTS.md already notes that live dispatch check.
- `low` — Blind: healthchecks.io defaults period 1d / grace 1h. Rejected: README already requires period 6h and grace ~6h. Extra default-warning is polish.
- `medium` — Blind: no healthchecks.io notify channel. Period/grace without notify never delivers the miss warning. Patched.
- `medium` — Blind: 60-day public-repo schedule auto-disable omitted. Spec 3.1 deferred that docs path here. Patched.
- `low` — Blind: hosting omits why Free private `schedule` may not fire. Rejected: the public-Free / Pro-if-private rule is already present.
- `medium` — Blind: “beside that ping-URL secret” reads as extra GitHub Secrets. Patched: set period/grace on the healthchecks.io check, store the ping URL in the secret.
- `low` — Blind: no Settings → Secrets path or notification-settings location. Rejected: “GitHub Secrets” and “leave workflow-failure email on” are enough for normal use.
- `medium` — Blind: `"schedule" in text` matches intro “scheduled”. Patched exact phrase `` `schedule` runs only on the default branch ``; intro no longer says “scheduled”.
- `low` — Blind: Android / “leave on” / Pro phrase-locks incomplete. Android assert patched (simple). Extra locks rejected as over-specification.
- `false` — Blind: no BotFather / chat-id how-to. AC is where to put the three secrets, not how to mint Telegram credentials.
- `false` — Blind: spec still `in-progress` without Boundaries/Verification. Oneshot form; Finalize sets `done`.
