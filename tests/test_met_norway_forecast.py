from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime

import pytest

from frost_alert.adapters.met_norway_forecast import MetNorwayForecast, MetNorwayForecastError
from frost_alert.domain.classify import ForecastHour

LAT = 59.32932
LON = 18.06857
ELEVATION_M = 28.4
GOLDEN_TIMES = [
    "2026-01-15T12:00:00Z",
    "2026-01-15T13:00:00Z",
    "2026-01-15T14:00:00Z",
    "2026-01-15T18:00:00Z",
]
GOLDEN_TEMPS = [4.0, 3.0, 2.0, 1.0]
GOLDEN_SERIES = [
    ForecastHour(t=datetime(2026, 1, 15, 12, 0, tzinfo=UTC), temp_c=4.0),
    ForecastHour(t=datetime(2026, 1, 15, 13, 0, tzinfo=UTC), temp_c=3.0),
    ForecastHour(t=datetime(2026, 1, 15, 14, 0, tzinfo=UTC), temp_c=2.0),
]


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


def _item(time: str, temp: object, *, include_temp: bool = True) -> dict[str, object]:
    details: dict[str, object] = {}
    if include_temp:
        details["air_temperature"] = temp
    return {"time": time, "data": {"instant": {"details": details}}}


def _compact_payload(
    items: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if items is None:
        items = [
            _item(time, temp) for time, temp in zip(GOLDEN_TIMES, GOLDEN_TEMPS, strict=True)
        ]
    return {"properties": {"timeseries": items}}


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
    return MetNorwayForecast(elevation_m=ELEVATION_M).fetch(lat=LAT, lon=LON)


def test_request_shape_uses_compact_four_decimals_and_altitude(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _install_urlopen(
        monkeypatch,
        body=json.dumps(_compact_payload()).encode("utf-8"),
    )
    MetNorwayForecast(elevation_m=ELEVATION_M).fetch(lat=LAT, lon=LON)
    parsed = urllib.parse.urlparse(str(captured["url"]))
    query = urllib.parse.parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "api.met.no"
    assert parsed.path == "/weatherapi/locationforecast/2.0/compact"
    assert query["lat"] == ["59.3293"]
    assert query["lon"] == ["18.0686"]
    assert query["altitude"] == ["28.4"]
    assert captured["user_agent"] == "Frost-alert (https://github.com/dabben1993/Frost-alert)"
    assert captured["timeout"] == 15


def test_hourly_prefix_drops_six_hourly_tail(monkeypatch: pytest.MonkeyPatch) -> None:
    series = _fetch(monkeypatch, _compact_payload())
    assert series == GOLDEN_SERIES
    assert series[0].t == datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    assert series[0].temp_c == 4.0


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"properties": {}},
        {"properties": {"timeseries": "missing"}},
        {"properties": {"timeseries": [{"time": GOLDEN_TIMES[0]}]}},
        {
            "properties": {
                "timeseries": [_item(GOLDEN_TIMES[0], None, include_temp=False)],
            }
        },
    ],
)
def test_missing_keys_raise(monkeypatch: pytest.MonkeyPatch, payload: object) -> None:
    with pytest.raises(MetNorwayForecastError):
        _fetch(monkeypatch, payload)


def test_empty_prefix_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MetNorwayForecastError):
        _fetch(monkeypatch, _compact_payload(items=[]))


def test_null_temp_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MetNorwayForecastError):
        _fetch(
            monkeypatch,
            _compact_payload(items=[_item(GOLDEN_TIMES[0], None)]),
        )


@pytest.mark.parametrize("temp", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_temp_raises(monkeypatch: pytest.MonkeyPatch, temp: float) -> None:
    with pytest.raises(MetNorwayForecastError):
        _fetch(
            monkeypatch,
            _compact_payload(items=[_item(GOLDEN_TIMES[0], temp)]),
        )


def test_unsorted_times_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MetNorwayForecastError):
        _fetch(
            monkeypatch,
            _compact_payload(
                items=[
                    _item("2026-01-15T14:00:00Z", 2.0),
                    _item("2026-01-15T12:00:00Z", 4.0),
                    _item("2026-01-15T13:00:00Z", 3.0),
                ]
            ),
        )


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.HTTPError(
            "https://api.met.no/weatherapi/locationforecast/2.0/compact",
            500,
            "server error",
            {},
            None,
        ),
        TimeoutError(),
        urllib.error.URLError("connection refused"),
    ],
)
def test_http_and_transport_failures_raise(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    _install_urlopen(monkeypatch, error=error)
    with pytest.raises(MetNorwayForecastError):
        MetNorwayForecast(elevation_m=ELEVATION_M).fetch(lat=LAT, lon=LON)


def test_bad_json_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_urlopen(monkeypatch, body=b"not-json")
    with pytest.raises(MetNorwayForecastError):
        MetNorwayForecast(elevation_m=ELEVATION_M).fetch(lat=LAT, lon=LON)
