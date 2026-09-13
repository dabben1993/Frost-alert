from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class ForecastHour:
    t: datetime
    temp_c: int | float


@dataclass(frozen=True)
class Classification:
    risk_present: bool
    window: int | None
    event_date: str | None
    t: datetime | None
    temp_c: int | float | None


_LOOKAHEAD = timedelta(hours=30)
_WINDOW_24_AFTER = timedelta(hours=12)
_WINDOW_12_AFTER = timedelta(hours=6)
_ZERO = timedelta(0)


def classify(
    series: Sequence[ForecastHour],
    threshold_c: int | float,
    now: datetime,
    timezone: str,
) -> Classification:
    first: ForecastHour | None = None
    for hour in series:
        remaining = hour.t - now
        if remaining <= _ZERO or remaining > _LOOKAHEAD:
            continue
        if hour.temp_c > threshold_c:
            continue
        if first is None or hour.t < first.t:
            first = hour
    if first is None:
        return Classification(
            risk_present=False,
            window=None,
            event_date=None,
            t=None,
            temp_c=None,
        )
    remaining = first.t - now
    if remaining > _WINDOW_24_AFTER:
        window = 24
    elif remaining > _WINDOW_12_AFTER:
        window = 12
    else:
        window = 6
    event_date = first.t.astimezone(ZoneInfo(timezone)).date().isoformat()
    return Classification(
        risk_present=True,
        window=window,
        event_date=event_date,
        t=first.t,
        temp_c=first.temp_c,
    )
