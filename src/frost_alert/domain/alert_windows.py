from __future__ import annotations

from collections.abc import Sequence

from frost_alert.domain.classify import Classification


def should_send(
    classification: Classification,
    alerted_windows: Sequence[int],
) -> bool:
    if not classification.risk_present:
        return False
    window = classification.window
    if window is None:
        return False
    return window not in alerted_windows


def mark_window(alerted_windows: Sequence[int], window: int) -> list[int]:
    return [*alerted_windows, window]
