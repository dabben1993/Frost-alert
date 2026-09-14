from __future__ import annotations

from collections.abc import Sequence

from frost_alert.domain.season import apply_intent
from frost_alert.ports import AckInbox


def apply_telegram_acks(
    *,
    inbox: AckInbox,
    season: str,
    event_date: str | None,
    alerted_windows: Sequence[int],
    telegram_offset: int,
) -> dict[str, object]:
    intents, new_offset = inbox.poll(telegram_offset=telegram_offset)
    next_season = season
    next_event = event_date
    next_windows = list(alerted_windows)
    for intent in intents:
        next_season, next_event, next_windows = apply_intent(
            next_season, next_event, next_windows, intent
        )
    return {
        "season": next_season,
        "event_date": next_event,
        "alerted_windows": next_windows,
        "telegram_offset": new_offset,
    }
