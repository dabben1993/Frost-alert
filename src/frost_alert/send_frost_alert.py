from __future__ import annotations

from collections.abc import Sequence

from frost_alert.domain.alert_windows import mark_window, should_send
from frost_alert.domain.classify import Classification
from frost_alert.ports import Notifier


def maybe_send_frost_alert(
    *,
    notifier: Notifier,
    classification: Classification,
    alerted_windows: Sequence[int],
    place_name: str,
    threshold_c: int | float,
    scale: str,
    timezone: str,
) -> list[int]:
    pending = list(alerted_windows)
    if not should_send(classification, pending):
        return pending
    notifier.send_frost_alert(
        classification=classification,
        place_name=place_name,
        threshold_c=threshold_c,
        scale=scale,
        timezone=timezone,
    )
    window = classification.window
    if window is None:
        return pending
    return mark_window(pending, window)
