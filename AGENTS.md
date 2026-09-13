<!-- bmad:context -->
<!-- Verified 2026-09-13 against 8344684. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## Frost-alert

Single-user frost-warning automation for overwintering bonsai. CPython 3.13, uv, stdlib HTTP, scheduled on GitHub Actions. Contract and stories live in `_bmad-output/specs/spec-frost-alert/` and `_bmad-output/planning-artifacts/`.

## Policy

- Never push story work to `master`. Branch from `master` as `{epic}-{story}-{slug}` (e.g. `1-1-story-stub`); when the story is done, open a PR to `master`.
- Never commit secrets, tokens, ping URLs, or `.env` files. `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `HEALTHCHECKS_PING_URL` live only in GitHub Secrets or the process environment.
- Do not add files, dependencies, or behavior the current story does not need. Leave the tree cleaner than you found it.

## Where things are

- Spec: `_bmad-output/specs/spec-frost-alert/SPEC.md` (companions beside it).
- Architecture decisions AD-1..13: `_bmad-output/planning-artifacts/architecture/architecture-Frost-alert-2026-09-12/ARCHITECTURE-SPINE.md`
- Stories: `_bmad-output/planning-artifacts/epics.md`
- Changing classification, season, or store shape? Read the spine first — do not invent a second contract.

## Running and verifying

- Runtime is CPython 3.13 + uv. Install and test commands are after this managed block.

## Conventions that differ from defaults

- Domain contains no I/O; adapters implement ports; entrypoints only wire. Adding a vendor is a new adapter, not new domain rules.
- HTTP is stdlib only. Do not add `requests` or `httpx` unless a later port cannot work without them.
- Unit tests use fake ports; no live network in unit tests.

<!-- /bmad:context -->

## Install and test

- Install: `uv sync`
- Tests: `uv run pytest`
