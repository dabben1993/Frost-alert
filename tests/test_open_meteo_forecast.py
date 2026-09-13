from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from frost_alert.adapters.open_meteo_forecast import OpenMeteoForecast, OpenMeteoForecastError
from frost_alert.domain.classify import ForecastHour

LAT = 59.33
LON = 18.07
TIMES = ["2026-01-15T12:00", "2026-01-15T13:00", "2026-01-15T14:00"]
TEMPS = [4.0, 3.0, 2.0]
GOLDEN_FIRST_T = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


class _FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not open a network connection")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def _hourly_payload(
    *,
    times: list[str] | None = None,
    temps: list[float | None] | None = None,
) -> dict[str, object]:
    return {"hourly": {"time": TIMES if times is None else times, "temperature_2m": TEMPS if temps is None else temps}}


def _install_urlopen(
    monkeypatch: pytest.MonkeyPatch,
    *,
    body: bytes | None = None,
    error: BaseException | None = None,
) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_urlopen(req: urllib.request.Request, timeout: float | None = None) -> _FakeHTTPResponse:
        captured["url"] = req.full_url
        captured["user_agent"] = req.get_header("User-agent")
        captured["timeout"] = timeout
        if error is not None:
            raise error
        assert body is not None
        return _FakeHTTPResponse(body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return captured


def _fetch(monkeypatch: pytest.MonkeyPatch, payload: object) -> list[ForecastHour]:
    body = json.dumps(payload).encode("utf-8")
    _install_urlopen(monkeypatch, body=body)
    return OpenMeteoForecast().fetch(lat=LAT, lon=LON)


def test_happy_path_returns_utc_celsius_series(monkeypatch: pytest.MonkeyPatch) -> None:
    series = _fetch(monkeypatch, _hourly_payload())
    assert series == [
        ForecastHour(t=datetime(2026, 1, 15, 12, 0, tzinfo=UTC), temp_c=4.0),
        ForecastHour(t=datetime(2026, 1, 15, 13, 0, tzinfo=UTC), temp_c=3.0),
        ForecastHour(t=datetime(2026, 1, 15, 14, 0, tzinfo=UTC), temp_c=2.0),
    ]
    assert [hour.t for hour in series] == sorted(hour.t for hour in series)
    assert all(hour.t.tzinfo is not None for hour in series)


def test_query_shape_uses_utc_hourly_temps_without_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _install_urlopen(
        monkeypatch,
        body=json.dumps(_hourly_payload()).encode("utf-8"),
    )
    OpenMeteoForecast().fetch(lat=LAT, lon=LON)
    parsed = urllib.parse.urlparse(str(captured["url"]))
    query = urllib.parse.parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "api.open-meteo.com"
    assert parsed.path == "/v1/forecast"
    assert query["latitude"] == [str(LAT)]
    assert query["longitude"] == [str(LON)]
    assert query["hourly"] == ["temperature_2m"]
    assert query["timezone"] == ["UTC"]
    assert "models" not in query
    assert "current_weather" not in query
    assert captured["user_agent"] == "Frost-alert (https://github.com/dabben1993/Frost-alert)"
    assert captured["timeout"] == 15


def test_gmt_as_local_attaches_utc_not_place_zone(monkeypatch: pytest.MonkeyPatch) -> None:
    series = _fetch(monkeypatch, _hourly_payload())
    first = series[0]
    assert first.t == GOLDEN_FIRST_T
    assert first.t.tzinfo is not None
    assert first.t.tzinfo == UTC
    assert first.t.utcoffset() == timedelta(0)
    stockholm = first.t.astimezone(ZoneInfo("Europe/Stockholm"))
    assert first.t != stockholm.replace(tzinfo=UTC)
    assert first.t.hour == 12
    assert first.t.tzinfo is not ZoneInfo("Europe/Stockholm")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"hourly": {"temperature_2m": TEMPS}},
        {"hourly": {"time": TIMES}},
        {"hourly": "missing"},
    ],
)
def test_missing_hourly_keys_raise(monkeypatch: pytest.MonkeyPatch, payload: object) -> None:
    with pytest.raises(OpenMeteoForecastError):
        _fetch(monkeypatch, payload)


def test_empty_arrays_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(OpenMeteoForecastError):
        _fetch(monkeypatch, _hourly_payload(times=[], temps=[]))


@pytest.mark.parametrize(
    ("times", "temps"),
    [
        (TIMES, TEMPS[:2]),
        (TIMES[:2], TEMPS),
    ],
)
def test_length_mismatch_raises(
    monkeypatch: pytest.MonkeyPatch,
    times: list[str],
    temps: list[float],
) -> None:
    with pytest.raises(OpenMeteoForecastError):
        _fetch(monkeypatch, _hourly_payload(times=times, temps=temps))


@pytest.mark.parametrize(
    "temps",
    [
        [None, 3.0, 2.0],
        [4.0, 3.0, None],
    ],
)
def test_null_temp_raises_without_dropping_hour(
    monkeypatch: pytest.MonkeyPatch,
    temps: list[float | None],
) -> None:
    with pytest.raises(OpenMeteoForecastError):
        _fetch(monkeypatch, _hourly_payload(temps=temps))


def test_unsorted_times_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(OpenMeteoForecastError):
        _fetch(
            monkeypatch,
            _hourly_payload(times=["2026-01-15T14:00", "2026-01-15T12:00", "2026-01-15T13:00"]),
        )


def test_non_hourly_gap_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(OpenMeteoForecastError):
        _fetch(
            monkeypatch,
            _hourly_payload(
                times=["2026-01-15T12:00", "2026-01-15T15:00"],
                temps=[4.0, 2.0],
            ),
        )


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.HTTPError("https://api.open-meteo.com/v1/forecast", 500, "server error", {}, None),
        urllib.error.HTTPError("https://api.open-meteo.com/v1/forecast", 429, "too many requests", {}, None),
        TimeoutError(),
        urllib.error.URLError("connection refused"),
        urllib.error.HTTPError("https://api.open-meteo.com/v1/forecast", 400, "bad request", {}, None),
    ],
)
def test_http_and_transport_failures_raise(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    _install_urlopen(monkeypatch, error=error)
    with pytest.raises(OpenMeteoForecastError):
        OpenMeteoForecast().fetch(lat=LAT, lon=LON)


def test_bad_json_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_urlopen(monkeypatch, body=b"not-json")
    with pytest.raises(OpenMeteoForecastError):
        OpenMeteoForecast().fetch(lat=LAT, lon=LON)


def test_open_meteo_error_object_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(OpenMeteoForecastError):
        _fetch(monkeypatch, {"error": True, "reason": "Invalid latitude"})
