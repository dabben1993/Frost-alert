---
title: 'Send a preview-first Telegram frost alert'
type: 'feature'
created: '2026-09-14'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '83aeadf421c070d2259b894c3e986f88f2e2f9f1'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/_bmad-output/specs/spec-frost-alert/alert-copy.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Classification can name a 24/12/6 window, but nothing sends a lock-screen-readable Telegram frost warning or records that window only after a successful send.

**Approach:** Add `Notifier.send_frost_alert`, a Telegram adapter, and a composer that marks `alerted_windows` only after send succeeds. Persist stays Story 2.5.

## Boundaries & Constraints

**Always:**
- Stay on branch `2-3-send-a-preview-first-telegram-frost-alert`. No story work on `master`.
- `maybe_send_frost_alert` skips when risk is absent, `window` is missing, or that int is already in `alerted_windows`. Else `Notifier.send_frost_alert`, then append. On raise, return the original list.
- Window values are ints `{24, 12, 6}`. Domain marks; Notifier does not persist or self-dedupe. No `StateStore` write.
- Preview = first line of `sendMessage` `text`: emoji, frost risk coming, roughly 24h/12h/6h. That line has no table, place, temps, threshold, `/in`, or `plants_in`.
- Body after that line: `place_name`, first-crossing temp and threshold in user `scale` (disk stays °C; convert when `F`), crossing time in the configured IANA zone. Ack is an inline button with `callback_data` `plants_in`.
- Exact strings unlocked; keep the preview-vs-opened split. No `parse_mode`.
- `POST https://api.telegram.org/bot{token}/sendMessage` JSON `chat_id`, `text`, `reply_markup`. UA `Frost-alert (https://github.com/dabben1993/Frost-alert)`. Timeout 15s. Stdlib HTTP. Token and chat id are constructor args.
- HTTP 4xx/5xx/429, timeout, connect, bad JSON, or `ok: false` → raise. Tests monkeypatch `urlopen`; no sockets.

**Never:**
- Do not implement `getUpdates`, `answerCallbackQuery`, `/in` `/out`, `plants_out`, season flip, check entrypoint, ConfigStore read, StateStore write, `check.yml`, or `os.getenv` for secrets.
- Do not change classify, forecast/geocoder, setup CLI, or `user.json` / `state.json` keys.
- Do not add `requests`/`httpx`, set a webhook, or send live Telegram in tests.
- Do not commit secrets, `.env`, `config/user.json`, or `data/state.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | window 24, windows `[]`; place `Stockholm`; 2°C at 2026-01-16 06:00 UTC; `Europe/Stockholm`; scale `C`; threshold 3°C | preview ~24h + emoji; body has place, 2°C, local `2026-01-16 07:00`, 3°C; `plants_in`; windows `[24]` | N/A |
| Already marked | same, windows `[24]` | no HTTP; still `[24]` | N/A |
| Absent risk | `risk_present` false | no HTTP; windows unchanged | N/A |
| Scale F | same crossing; scale `F` | body uses °F for crossing and threshold | N/A |
| Preview hygiene | any send | first line has no place, temps, `/in`, or `plants_in` | N/A |
| HTTP / `ok: false` | 5xx/429/timeout/connect or `ok: false` | no mark | raise |
| Composer failure | notifier raises | windows equal input | raise, do not append |

</frozen-after-approval>

## Code Map

- `src/frost_alert/ports/__init__.py` -- `Notifier` empty (L10–11). Add `send_frost_alert(*, classification, place_name, threshold_c, scale, timezone) -> None`.
- `src/frost_alert/domain/classify.py` -- `Classification` (L16–21). Reuse; do not edit.
- `src/frost_alert/domain/alert_windows.py` -- new: skip/mark window ints, no I/O.
- `src/frost_alert/send_frost_alert.py` -- new: `maybe_send_frost_alert` (send then mark).
- `src/frost_alert/adapters/telegram_notifier.py` -- new. `adapters/__init__.py` stays empty.
- `src/frost_alert/adapters/open_meteo_forecast.py` -- copy `urlopen`/UA/15s/raise (L11–47); do not edit.
- `src/frost_alert/adapters/json_state_store.py` -- `load` only. Do not add write. Setup CLI: do not touch.
- `tests/test_open_meteo_forecast.py` -- copy `_FakeHTTPResponse` + `urlopen` monkeypatch.
- `tests/test_package.py` -- `FakeNotifier` stays constructible; domain isolation still forbids HTTP.

## Tasks & Acceptance

**Execution:**
- [x] `tests/test_frost_alert_send.py` -- failing tests for every I/O matrix row -- red first
- [x] `src/frost_alert/ports/__init__.py` -- `Notifier.send_frost_alert` -- AD-1 / CAP-3
- [x] `src/frost_alert/domain/alert_windows.py` -- skip/mark window ints -- FR19
- [x] `src/frost_alert/adapters/telegram_notifier.py` -- `sendMessage`, preview-first text + `plants_in` -- FR10
- [x] `src/frost_alert/send_frost_alert.py` -- send then mark; raise leaves windows unchanged -- FR19

**Acceptance Criteria:**
- Given present risk and an unmarked window, when `maybe_send_frost_alert` runs, then Telegram gets a preview-first message with opened facts and a `plants_in` control, and that window int is appended only after send returns.
- Given absent risk, an already-marked window, or a notifier/HTTP failure, when the composer runs, then no new window is marked.
- Given `uv run pytest`, when tests finish, then all pass, fixtures fake `urlopen`, and no test opens a socket.

## Implementation Notes

`Notifier.send_frost_alert(*, classification, place_name, threshold_c, scale, timezone)`. Domain `should_send` / `mark_window` are pure ints. `maybe_send_frost_alert` sends then appends; absent risk, missing window, already-marked, or a notifier raise leaves the caller's list unchanged. `TelegramNotifier` POSTs JSON `sendMessage` (preview first line, opened facts after, `plants_in` inline button, no `parse_mode`); HTTP 4xx/5xx/429, timeout, connect, bad JSON, or `ok: false` raise `TelegramNotifierError` without chaining the token-bearing URL. Display-only F = C × 9/5 + 32. Happy-path / already-marked / preview tests parametrize windows 24, 12, and 6. `uv run pytest` — 113 passed; sockets blocked.

## Spec Change Log

## Review Triage Log

- `medium` — Blind: tests and matrix happy path only use window 24; preview interpolates `classification.window` at `telegram_notifier.py:87` and mark appends that int at `send_frost_alert.py:30-33`. Hardcoding `~24h` / mark 24 would still pass. Disposition: patch.
- `false` — Blind: skip could treat any non-empty `alerted_windows` as done. `should_send` is `window not in alerted_windows` (`alert_windows.py:17`). `test_notifier_raise_leaves_windows_unchanged` already sends window 24 when `[12]` is marked.
- `false` — Blind: Fahrenheit facts leak onto the preview line. Preview is `❄️ Frost risk in ~{window}h`; `_format_temp` is only used in the body after the newline (`telegram_notifier.py:87-92`).
- `false` — Blind: local stamp is a fixed +1h offset. `_local_stamp` uses `ZoneInfo(timezone)` (`telegram_notifier.py:95-96`); January CET is not a hardcoded hour.
- `false` — Blind: Always says return the original list on raise, code propagates. Matrix Error Handling is `raise`. Composer copies then marks only after send (`send_frost_alert.py:20-33`); the caller's list is unchanged and the exception propagates.
- `false` — Blind: preview hygiene omits the crossing stamp. First line interpolates only `window`; date/time are in the body (`telegram_notifier.py:87-92`).
- `false` — Blind: naive `t` uses the host zone. `Classification.t` from `classify` is UTC-aware; this story does not construct naive `t`.
- `false` — Blind: invalid IANA raises `ZoneInfoNotFoundError` unwrapped. Setup stores a geocoder IANA name; loud fail on bad config, same as `classify`. Spec wrap list is HTTP/parse, not `ZoneInfo`.
- `false` — Blind: `test_already_marked` aliasing assert cannot fail. Composer always copies (`pending = list(alerted_windows)`); skip returns the copy, not the caller's list.
- `medium` — Blind: `raise TelegramNotifierError(...) from err` at `telegram_notifier.py:72` chains `HTTPError`/`URLError` whose URL contains `/bot{token}/`. CI traces can leak the secret. Disposition: patch.
- `low` — Blind: display F uses binary float vs setup `Decimal`. Spec formula is `F = C × 9/5 + 32`; switching to Decimal adds conversion surface the matrix never showed. Reject.
- `false` — Blind: matrix omits 4xx/bad JSON rows. Fix would be editing this spec; Always already names those failures. Tests cover them. Reject (spec edit).
- `false` — Blind: `plants_in` spinner until 2.4 and no real lock-screen client. Intent Never forbids `answerCallbackQuery` / `getUpdates` this story; unit tests cannot open Telegram.
- `false` — Edge: unknown IANA at `_local_stamp`. Same as Blind invalid IANA: geocoder-persisted zone; loud fail, not a silent wrong clock.
- `false` — Edge: naive `t` at `_local_stamp`. Same as Blind naive `t`; classify emits aware UTC.
- `false` — Edge: `send_frost_alert` with `t` set and `window` None interpolates `~Noneh`. `maybe_send_frost_alert` returns before send when `window is None` (`alert_windows.py:15-16`, `send_frost_alert.py:21-22`).
- `false` — Edge: window int outside `{24, 12, 6}` is sent and appended. `classify` only returns 24, 12, or 6; this story consumes that output.
- `false` — Edge: `IncompleteRead`/`BadStatusLine` bypass `TelegramNotifierError`. Truncation still raises before `mark_window`; spec requires raise, not a specific type. Same except-tuple as the forecast adapter.
- `medium` — Verification-gap: 12h/6h send, preview, and mark only exercised as 24. Hardcode preview `~24h`, `mark_window(..., 24)`, and `24 not in alerted_windows` and `uv run pytest` stays green. Disposition: patch — parametrize `_send` / already-marked for 12 and 6.

## Design Notes

Lock-screen preview is the start of `text`: one-glance line, newline, then facts. Inline button is the ack control — do not print `/in` how-to. C→F display-only: `F = C × 9/5 + 32`. Token/chat id via constructor; 2.5 reads env.

Golden: `2026-01-16 06:00 UTC` @ 2°C, `Europe/Stockholm`, threshold 3°C, place `Stockholm`, scale `C` → window 24, local `2026-01-16 07:00`. Starting copy (unlocked): `❄️ Frost risk in ~24h`; button `Plants are in overwintering`.

## Verification

**Commands:**
- `uv run pytest` -- expected: all tests pass, including every send matrix row; `test_package.py` isolation still green; no test opens a socket
