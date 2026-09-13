---
title: 'Installable Frost Alert package'
type: 'feature'
created: '2026-09-13'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '14d213d6fbb083419c38650f785627db035d8cda'
context:
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A fresh clone has no installable Python package. Setup and later checks have nowhere to live, so the repo is still a script pile plus planning docs.

**Approach:** Land a uv-managed CPython 3.13 `frost_alert` package with the agreed src layout, the seven named ports, and unit tests that prove install plus isolation using fake ports only.

## Boundaries & Constraints

**Always:**
- Package import name is `frost_alert` under `src/frost_alert/{domain,ports,adapters,entrypoints}`.
- `.python-version` is exactly `3.13`. Tooling is uv 0.12. Tests run via pytest.
- Ports exist as `typing.Protocol` types named `ForecastSource`, `Notifier`, `AckInbox`, `Watchdog`, `ConfigStore`, `StateStore`, and `Clock`.
- Domain contains no I/O: it must not import `frost_alert.adapters` or stdlib HTTP (`urllib`, `http.client`).
- Unit tests use fake ports only and must not open a network connection.
- Story work happens on branch `1-1-installable-frost-alert-package`, not `master`.

**Never:**
- Do not add `requests`, `httpx`, or a web framework.
- Do not implement setup CLI behavior, geocoding, classification, Telegram, failover, or a scheduled workflow (Stories 1.2, 1.3, Epic 2, Epic 3).
- Do not create `config/user.json`, `data/state.json`, or `.github/workflows/check.yml` — those seeds belong to later stories.
- Do not register console scripts yet; `entrypoints/` is an empty package slot.
- Do not invent port method signatures. Later stories add methods when they first implement a port.
- Do not change `_bmad/`, `.agents/`, planning artifacts, or `scripts/poc-telegram-getupdates.py`.
- Do not commit secrets, `.env`, or `.venv`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh sync | `pyproject.toml` + `.python-version` | `uv sync` + `import frost_alert` succeed | Fail if not importable |
| Layout | Import subpackages | `domain`, `ports`, `adapters`, `entrypoints` import | Fail if missing |
| Ports defined | Import `frost_alert.ports` | Seven Protocol names exist | Fail if a name is missing |
| Domain isolation | Scan `src/frost_alert/domain` | No adapters or stdlib HTTP imports | Fail on forbidden import |
| Fake-port tests | Fakes of the seven ports | Pass with no live network | Fail if a test opens a socket |
| Banned deps | `pyproject.toml` + lock | No `requests`, `httpx`, or web framework | Fail if listed |

</frozen-after-approval>

## Code Map

- `AGENTS.md` -- 3.13 + uv, stdlib HTTP, branch `{epic}-{story}-{slug}`. Replace the uv-command TODO after install works.
- `_bmad-output/planning-artifacts/epics.md` -- Story 1.1 ACs. Do not implement 1.2+.
- `_bmad-output/planning-artifacts/architecture/architecture-Frost-alert-2026-09-12/ARCHITECTURE-SPINE.md` -- AD-1, AD-2, AD-12. Full structural seed is project-wide; 1.1 lands package + `.python-version` only.
- `scripts/poc-telegram-getupdates.py` -- leave in place; do not move into the package.
- Missing today: `pyproject.toml`, `src/`, `tests/`, root `.gitignore`. Do not touch `_bmad/` or `.agents/`.

## Tasks & Acceptance

**Execution:**
- [x] `1-1-installable-frost-alert-package` -- create this branch from `master` -- policy forbids story work on `master`
- [x] `.python-version` -- write `3.13` -- AD-2 pin
- [x] `.gitignore` -- ignore `.venv/`, `__pycache__/`, `.pytest_cache/`, `dist/`, `*.egg-info/` -- keep build junk out of git
- [x] `pyproject.toml` -- hatchling, `src` layout, project name `frost-alert`, `requires-python = ">=3.13,<3.14"`, pytest in a `dev` dependency group, no runtime HTTP libs -- installable with uv
- [x] `src/frost_alert/__init__.py` -- empty package -- makes `frost_alert` importable
- [x] `src/frost_alert/domain/__init__.py` -- empty package -- domain slot with no I/O
- [x] `src/frost_alert/ports/__init__.py` -- export the seven empty `Protocol` types -- AD-1 names
- [x] `src/frost_alert/adapters/__init__.py` -- empty package -- adapter slot
- [x] `src/frost_alert/entrypoints/__init__.py` -- empty package -- setup/check slot, no scripts
- [x] `tests/test_package.py` -- cover the I/O matrix (import, layout, ports, domain isolation, fake ports, banned deps) -- AC proof
- [x] `uv.lock` -- produce via `uv lock` / `uv sync` -- reproducible install
- [x] `AGENTS.md` -- replace the uv-command TODO with `uv sync` and `uv run pytest` -- story close-out

**Acceptance Criteria:**
- Given a fresh clone, when I sync with uv, then package `frost_alert` is importable, `.python-version` is `3.13`, and there is no web framework and no `requests`/`httpx` dependency.
- Given the repository tree, when I inspect the package, then code lives under `src/frost_alert/{domain,ports,adapters,entrypoints}`, `domain` does not import `adapters` or stdlib HTTP, and the seven ports are defined.
- Given the package, when unit tests run, then they use fake ports only and make no live network calls.

## Implementation Notes

- Branch `1-1-installable-frost-alert-package` created from `master` at `14d213d`.
- Hatchling wheel target `packages = ["src/frost_alert"]`; editable `uv sync` imports `frost_alert`.
- Pytest 9.1.1 on CPython 3.13.13; 6 tests passed. Autouse fixture blocks `socket.socket` / `socket.create_connection`.
- `AGENTS.md` install/test lines live inside the managed `bmad:context` block (refresh can overwrite).

## Spec Change Log

## Review Triage Log

- `false` — Blind: sprint-status `in-progress` vs spec `in-review`. Step-03 required `in-progress`; this step sets spec `in-review`. Sprint `review` is a later workflow write, not a package defect.
- `false` — Blind: epic-context says 1.1 lands seed files. Frozen Never forbids those files; the tree matches. The compile line is not product behavior of this change.
- `false` — Blind: uv 0.12 unpinned. Always names the chosen toolchain already used for `uv sync`/`pytest`; tasks did not require `required-version`.
- `low` — Blind: `.gitignore` omits `.env` (Never) and `build/`. `.env` is committable if created; `build/` was not in the gitignore task. Harm is accidental secret add.
- `medium` — Blind: domain isolation ignores `ImportFrom.level` and allows `import http`. `_imported_modules` at `tests/test_package.py:130` uses `node.module` only; `from .. import adapters` is recorded as `adapters`.
- `false` — Blind: fakes not `isinstance` of Protocols. Empty Protocols (no signatures) make that check vacuous; tests do construct the seven fakes.
- `false` — Blind: socket fixture only in this module / misses urllib. Sole test file; empty packages do not open sockets.
- `false` — Blind: no console-script test; fresh sync not in pytest. `[project.scripts]` is absent as required; `uv sync` + import ran as Verification commands.
- `low` — Blind: `AGENTS.md` commands sit inside managed `bmad:context` markers that refresh overwrites.
- `false` — Blind: stale Code Map / empty logs. Code Map is a planning snapshot; those logs fill during review. Rejected: fix would edit this spec.
- `false` — Blind: banned-dep regex misses aiohttp/etc. Regex matches the frozen Never list.
- `false` — Blind: no `pythonpath` / README. AC is `uv sync` then import, which works; operator README is Story 3.5.
- `medium` — Edge: relative adapter import not resolved (`tests/test_package.py:130-140`). Same scanner hole as Blind isolation.
- `false` — Edge: `importlib`/`__import__` not scanned. Empty domain has no dynamic imports; the situation is not reachable in this tree.
- `medium` — Edge: `import http` then `http.client` (`tests/test_package.py:144-148`). Only `http.client` is banned; `import http` passes.
- `false` — Edge: `SocketType`/`_socket.socket` bypass. Empty packages and current tests do not construct sockets that way.
- `false` — Edge: import-time socket before autouse. `frost_alert` imports are empty packages with no I/O.
- `medium` — Verification-gap: `from .. import adapters` stays green. Pre-verified: helper returns `adapters`, which does not match `frost_alert.adapters`. Disposition filed as patch.

## Design Notes

Hatchling + `src` layout is the uv default. Port Protocols stay method-empty so 1.1 does not invent signatures; later stories add methods. Test fakes are simple stand-ins that prove the names exist without adapters or sockets.

## Verification

**Commands:**
- `uv sync` -- expected: environment created; `frost-alert` installed editable
- `uv run python -c "import frost_alert"` -- expected: exit 0
- `uv run pytest` -- expected: all tests pass
- `rg -n "requests|httpx|flask|django|fastapi|starlette" pyproject.toml uv.lock` -- expected: no dependency hits
