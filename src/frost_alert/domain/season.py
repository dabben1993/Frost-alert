from __future__ import annotations

from collections.abc import Sequence


def apply_intent(
    season: str,
    event_date: str | None,
    alerted_windows: Sequence[int],
    intent: str,
) -> tuple[str, str | None, list[int]]:
    windows = list(alerted_windows)
    if intent == "in":
        return "suspended", event_date, windows
    if intent == "out":
        return "monitoring", None, []
    return season, event_date, windows
