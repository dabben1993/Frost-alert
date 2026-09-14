---
title: 'Flip season from Telegram'
type: 'feature'
created: '2026-09-14'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '2fb2decacf40065f808910b855d4f57163ba13fb'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/_bmad-output/specs/spec-frost-alert/state-machines.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Frost alerts can send `plants_in`, but nothing polls Telegram or applies `/in` `/out`, so the owner cannot suspend or resume the season without editing `state.json` or using the setup CLI.

**Approach:** Add domain season apply, `AckInbox.poll`, a Telegram `getUpdates` adapter, and a composer that applies in/out and returns the new season fields plus `telegram_offset`. Persist stays Story 2.5.

## Boundaries & Constraints

**Always:**
- Stay on branch `2-4-flip-season-from-telegram`. No story work on `master`.
- Domain `apply_intent` only: `in` → `season=suspended`, `event_date` and `alerted_windows` unchanged. `out` → `season=monitoring` and clear both. Repeats idempotent. Only `monitoring`|`suspended`.
- `AckInbox.poll(*, telegram_offset) -> (intents, new_offset)`: `"in"`|`"out"` in `update_id` order. Adapter reports; no `state.json` write. Composer last-wins, returns `{season, event_date, alerted_windows, telegram_offset}`. `new_offset` = max `update_id`, else unchanged.
- `GET .../getUpdates` with `offset = telegram_offset + 1`, `timeout=0`. Never `setWebhook`. Ignore chat id ≠ constructor `chat_id` (str compare). Always `POST .../answerCallbackQuery` for every `callback_query` (including ignored chats). Commands: first token `/in`|`/out` with optional `@bot`. Callback data exact `plants_in`/`plants_out`. Unknown updates: no flip; still advance offset.
- HTTP 4xx/5xx/429, timeout, connect, bad JSON, or `ok: false` → raise `from None` (no token URL). UA `Frost-alert (https://github.com/dabben1993/Frost-alert)`. 15s, stdlib HTTP, token+chat_id via constructor. Tests monkeypatch `urlopen`; no sockets.
- Setup CLI still cannot flip season.

**Never:**
- Do not write `StateStore`, the check entrypoint, `check.yml`, `os.getenv` for secrets, a confirmation `sendMessage`, `setWebhook`, or a snooze state.
- Do not change classify, forecast, `send_frost_alert` / `alert_windows`, setup CLI, `user.json` keys, or `TelegramNotifier.send_frost_alert`.
- Do not add `requests`/`httpx` or send live Telegram in tests.
- Do not commit secrets, `.env`, `config/user.json`, or `data/state.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `/in` or `plants_in` | `monitoring`; event `2026-01-16`; windows `[24]`; offset 0; owner update_id 10 | `suspended`; event/windows unchanged; offset 10; callback answered if callback | N/A |
| `/out` or `plants_out` | `suspended`; event set; windows `[24, 12]` | `monitoring`; event `None`; windows `[]`; offset advanced; callback answered if callback | N/A |
| Idempotent in | already `suspended`; `/in` | still `suspended`; event/windows unchanged | N/A |
| Wrong chat | other chat_id; `/in` or `plants_in` | season unchanged; offset advanced; callback answered if callback | N/A |
| Empty poll | `ok: true` result `[]` | fields unchanged; offset unchanged | N/A |
| Last-wins | `/in` then `/out` in one batch | `monitoring`; event/windows cleared; offset = max `update_id` | N/A |
| HTTP / `ok: false` | 5xx/429/timeout/connect or `ok: false` on getUpdates or answerCallbackQuery | no apply | raise |

</frozen-after-approval>

## Code Map

- `src/frost_alert/ports/__init__.py` -- `AckInbox` empty (L22–23). Add `poll(*, telegram_offset: int) -> tuple[list[str], int]`.
- `src/frost_alert/domain/season.py` -- new: `apply_intent` pure; no I/O.
- `src/frost_alert/apply_season.py` -- new: `apply_telegram_acks` (poll then apply).
- `src/frost_alert/adapters/telegram_ack_inbox.py` -- new: `getUpdates` + `answerCallbackQuery`. `adapters/__init__.py` stays empty.
- `src/frost_alert/adapters/telegram_notifier.py` -- copy UA/15s/`from None` (L12–74). Do not edit send/`plants_in`.
- Leave alone: `send_frost_alert.py`, `alert_windows.py`, `json_state_store.py` (load-only), setup CLI.
- `tests/test_frost_alert_send.py` -- copy `_FakeHTTPResponse` + `urlopen` monkeypatch.
- `tests/test_package.py` -- `FakeAckInbox` constructible; domain still forbids HTTP. Setup still must not write `data/state.json`.

## Tasks & Acceptance

**Execution:**
- [x] `tests/test_season_flip.py` -- failing tests for every I/O matrix row -- red first
- [x] `src/frost_alert/ports/__init__.py` -- `AckInbox.poll` -- AD-1 / CAP-4
- [x] `src/frost_alert/domain/season.py` -- in/out apply -- FR11, FR12, AD-9
- [x] `src/frost_alert/adapters/telegram_ack_inbox.py` -- `getUpdates`, chat-id filter, `answerCallbackQuery` -- FR13, FR21
- [x] `src/frost_alert/apply_season.py` -- poll then apply; raise does not invent persist -- AD-9

**Acceptance Criteria:**
- Given `/in` or `plants_in` while monitoring, when the composer runs, then season is `suspended` and event/windows stay; every `callback_query` is answered.
- Given `/out` or `plants_out` while suspended, when the composer runs, then season is `monitoring` and event/windows are cleared.
- Given a foreign chat, empty poll, or HTTP/`ok: false`, when poll/apply runs, then ignore does not flip, offset still advances on received updates, and failures raise with no StateStore write.
- Given `uv run pytest`, when tests finish, then all pass, fixtures fake `urlopen`, setup has no season command, and no test opens a socket.

## Implementation Notes

`AckInbox.poll(*, telegram_offset) -> tuple[list[str], int]`. Domain `apply_intent` maps `in` → `suspended` (keep event/windows) and `out` → `monitoring` (clear both). `TelegramAckInbox` GETs `getUpdates` with `offset=telegram_offset+1` and `timeout=0`, answers every `callback_query`, filters chat id as str. `apply_telegram_acks` last-wins; no StateStore write. Failures raise `TelegramAckInboxError` `from None`. Last-wins test parametrizes unsorted `getUpdates` bodies so dropping adapter `update_id` sort fails. `uv run pytest` — 142 passed; sockets blocked.

## Spec Change Log

## Review Triage Log

- `false` — Blind: last-wins should apply only the last intent to the original state. Frozen matrix `/in` then `/out` is sequential apply in `update_id` order (`apply_season.py:21-24`); net season is monitoring and out clears event/windows. Apply-only-last is not what that row describes.
- `false` — Blind: `tests/test_package.py` FakeAckInbox must grow `poll`. Code Map only requires constructible; `test_fake_ports_cover_all_ports_without_network` only instantiates. Empty `pass` still constructs.
- `false` — Blind: missing `deleteWebhook`. Frozen Never forbids `setWebhook`; it does not require delete. Adapter never sets a webhook.
- `low` — Blind/Edge: `callback_query` without `message.chat` drops owner `plants_in` after answer. `_chat_id` reads only `callback_query.message.chat.id` (`telegram_ack_inbox.py:119-123`). Frost-alert buttons sit on a just-sent message; omitted `message` is not everyday. Reject (fallback `from.id` adds a branch).
- `false` — Blind/Edge: `answerCallbackQuery` failure stalls offset forever. Frozen HTTP row is raise / no apply. Offset is returned only on success, same persist-after-success as 2.3. Retry with the same offset is 2.5's write-after-success, not a poll bug.
- `false` — Blind: `apply_intent` does not constrain `monitoring`|`suspended`; `/out` while monitoring wipes windows. Store only has those two seasons. `out` always clears (FR12 same-day resume). Repeating `out` stays `monitoring` with `[]`. Matrix has no idempotent-`/out` row.
- `false` — Blind: frozen matrix omits unknown updates and bad JSON. Always already names both. Tests cover `/help` and bad JSON. Reject (spec edit).
- `false` — Blind: sprint-status `in-progress` vs spec `in-review`. Step-04 sets spec `in-review`; sprint review sync is a later step. Not runtime.
- `false` — Edge: missing/non-int `update_id` applies intents with a stale offset. Telegram always sends a positive int `update_id`. Unreachable.
- `false` — Edge: JSON `true`/`false` as `update_id` via `bool` subclass. Telegram never sends a boolean `update_id`. Unreachable.
- `false` — Edge: first `answerCallbackQuery` failure leaves later callbacks unanswered. Frozen HTTP row aborts poll on raise; remaining updates are not processed.
- `false` — Edge: `max(update_id)` below current `telegram_offset` moves offset backward. `getUpdates` with `offset=n+1` does not return older ids.
- `false` — Edge: `/IN`/`/OUT` do not match. Frozen token is `/in`|`/out` (Telegram command menu). Uppercase is unknown text: no flip, offset advances.
- `false` — Edge: `/in` in `caption` not `text`. Always reads message text. Caption is not a specified command path.
- `false` — Edge: negative `telegram_offset`. Store default is `0`; this story does not write a negative offset.
- `false` — Edge: `IncompleteRead` bypasses `TelegramAckInboxError`. Truncation still raises before apply; spec wrap list is HTTP/parse, not a specific type. Same except-tuple as `telegram_notifier.py`.
- `false` — Edge: missing `update_id` sorts as `0`. Telegram includes `update_id`. Unreachable.
- `medium` — Verification-gap: last-wins `update_id` order is only tested with already-sorted `/in` then `/out`. Dropping `updates.sort` at `telegram_ack_inbox.py:58` would still pass `test_last_wins_in_then_out`. Disposition: patch.

## Design Notes

Ack UX is `answerCallbackQuery` (clears the spinner) — no extra `sendMessage`. `timeout=0` so a cron tick does not long-poll. Offset is returned; 2.5 writes disk. Foreign-chat callbacks are answered but not applied.

Golden: monitoring, event `2026-01-16`, windows `[24]`, offset `0`, owner `/in` update_id `10` → `suspended`, same event/windows, offset `10`. Then `/out` → `monitoring`, `event_date=None`, windows `[]`.

## Verification

**Commands:**
- `uv run pytest` -- expected: all tests pass including every matrix row; isolation green; setup does not write `data/state.json`; no sockets
