from __future__ import annotations

import inspect
import socket
from datetime import datetime, timedelta, timezone

import pytest

from frost_alert.domain.classify import Classification, ForecastHour, classify

NOW = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
ZONE = "Europe/Stockholm"
THRESHOLD_C = 3
GOLDEN_HOUR = datetime(2026, 1, 16, 6, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not open a network connection")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def _hour(*, hours: float, temp_c: float, now: datetime = NOW) -> ForecastHour:
    return ForecastHour(t=now + timedelta(hours=hours), temp_c=temp_c)


def _classify(
    hours: list[ForecastHour],
    *,
    now: datetime = NOW,
    threshold_c: float = THRESHOLD_C,
    timezone: str = ZONE,
) -> Classification:
    return classify(hours, threshold_c, now, timezone)


def _absent(result: Classification) -> None:
    assert result.risk_present is False
    assert result.window is None
    assert result.event_date is None
    assert result.t is None
    assert result.temp_c is None


def test_classify_signature_uses_series_threshold_now_and_timezone() -> None:
    params = inspect.signature(classify).parameters
    assert list(params) == ["series", "threshold_c", "now", "timezone"]
    assert "clock" not in {name.lower() for name in params}
    assert not any("live" in name.lower() or "current" in name.lower() for name in params)


def test_matrix_present_in_lookahead() -> None:
    hour = ForecastHour(t=GOLDEN_HOUR, temp_c=2)
    result = _classify([hour])
    assert result.risk_present is True
    assert result.window == 24
    assert result.event_date == "2026-01-16"
    assert result.t == GOLDEN_HOUR
    assert result.temp_c == 2
    assert result.t - NOW == timedelta(hours=18)


def test_matrix_all_above() -> None:
    _absent(_classify([_hour(hours=18, temp_c=4), _hour(hours=24, temp_c=5)]))


def test_matrix_empty_series() -> None:
    _absent(_classify([]))


def test_matrix_daytime_crossing() -> None:
    # 14:00 Europe/Stockholm on 2026-01-15 is 13:00 UTC (UTC+1).
    daytime = ForecastHour(
        t=datetime(2026, 1, 15, 13, 0, tzinfo=timezone.utc),
        temp_c=0,
    )
    result = _classify([daytime])
    assert result.risk_present is True
    assert result.window == 6
    assert result.event_date == "2026-01-15"
    assert result.t == daytime.t
    assert result.temp_c == 0


def test_matrix_window_exactly_12h() -> None:
    result = _classify([_hour(hours=12, temp_c=0)])
    assert result.risk_present is True
    assert result.window == 12
    assert result.t - NOW == timedelta(hours=12)


def test_matrix_window_exactly_6h() -> None:
    result = _classify([_hour(hours=6, temp_c=0)])
    assert result.risk_present is True
    assert result.window == 6
    assert result.t - NOW == timedelta(hours=6)


def test_matrix_lookahead_exactly_30h() -> None:
    result = _classify([_hour(hours=30, temp_c=0)])
    assert result.risk_present is True
    assert result.window == 24
    assert result.t - NOW == timedelta(hours=30)


def test_matrix_lookahead_over_30h_ignored() -> None:
    _absent(_classify([_hour(hours=31, temp_c=0)]))


def test_matrix_remaining_zero_or_past_ignored() -> None:
    _absent(
        _classify(
            [
                ForecastHour(t=NOW, temp_c=0),
                _hour(hours=-1, temp_c=-5),
                _hour(hours=30, temp_c=5),
            ]
        )
    )


def test_matrix_at_threshold() -> None:
    result = _classify([_hour(hours=18, temp_c=THRESHOLD_C)])
    assert result.risk_present is True
    assert result.window == 24
    assert result.temp_c == THRESHOLD_C


def test_matrix_same_day_revision() -> None:
    first = _classify([ForecastHour(t=GOLDEN_HOUR, temp_c=2)])
    revised = _classify(
        [ForecastHour(t=datetime(2026, 1, 16, 12, 0, tzinfo=timezone.utc), temp_c=-1)]
    )
    assert first.event_date == "2026-01-16"
    assert revised.event_date == "2026-01-16"
    assert first.t != revised.t


def test_matrix_new_local_date() -> None:
    prior = _classify([ForecastHour(t=GOLDEN_HOUR, temp_c=2)])
    later_now = datetime(2026, 1, 16, 23, 0, tzinfo=timezone.utc)
    nxt = _classify(
        [ForecastHour(t=datetime(2026, 1, 17, 6, 0, tzinfo=timezone.utc), temp_c=1)],
        now=later_now,
    )
    assert prior.event_date == "2026-01-16"
    assert nxt.event_date == "2026-01-17"
    assert nxt.risk_present is True


def test_matrix_two_dates_uses_first_qualifying_hour() -> None:
    # Monday 2026-01-12 evening is above; Tuesday 02:00 local (01:00 UTC) is at/below.
    now = datetime(2026, 1, 12, 18, 0, tzinfo=timezone.utc)
    monday_evening = ForecastHour(
        t=datetime(2026, 1, 12, 20, 0, tzinfo=timezone.utc),
        temp_c=10,
    )
    tuesday_0200_local = ForecastHour(
        t=datetime(2026, 1, 13, 1, 0, tzinfo=timezone.utc),
        temp_c=0,
    )
    result = _classify([monday_evening, tuesday_0200_local], now=now)
    assert result.risk_present is True
    assert result.event_date == "2026-01-13"
    assert result.t == tuesday_0200_local.t


def test_matrix_event_date_is_iana_local_not_utc_date() -> None:
    # 23:00 UTC on 2026-01-15 is 00:00 on 2026-01-16 in Europe/Stockholm (UTC+1).
    crossing = ForecastHour(
        t=datetime(2026, 1, 15, 23, 0, tzinfo=timezone.utc),
        temp_c=0,
    )
    assert crossing.t.date().isoformat() == "2026-01-15"
    result = _classify([crossing])
    assert result.risk_present is True
    assert result.event_date == "2026-01-16"
    assert result.t == crossing.t


def test_earliest_qualifying_t_is_order_independent() -> None:
    later = _hour(hours=18, temp_c=0)
    earlier = _hour(hours=8, temp_c=1)
    forward = _classify([earlier, later])
    reversed_series = _classify([later, earlier])
    assert forward.t == earlier.t == reversed_series.t
    assert forward.event_date == reversed_series.event_date
    assert forward.window == reversed_series.window == 12
