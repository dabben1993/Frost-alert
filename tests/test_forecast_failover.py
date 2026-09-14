from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pytest

from frost_alert.adapters.forecast_failover import FailoverForecast
from frost_alert.adapters.json_config_store import JsonConfigStore
from frost_alert.adapters.json_state_store import JsonStateStore
from frost_alert.adapters.met_norway_forecast import MetNorwayForecast, MetNorwayForecastError
from frost_alert.adapters.open_meteo_forecast import OpenMeteoForecast, OpenMeteoForecastError
from frost_alert.domain.classify import ForecastHour
from frost_alert.entrypoints.check import main as check_main
from frost_alert.ports import ForecastSource

LAT = 59.33
LON = 18.07
TOKEN = "TEST_TOKEN"
CHAT_ID = "12345"
OM_TIMES = ["2026-01-15T12:00", "2026-01-15T13:00", "2026-01-15T14:00"]
OM_TEMPS = [4.0, 3.0, 2.0]
OM_SERIES = [
    ForecastHour(t=datetime(2026, 1, 15, 12, 0, tzinfo=UTC), temp_c=4.0),
    ForecastHour(t=datetime(2026, 1, 15, 13, 0, tzinfo=UTC), temp_c=3.0),
    ForecastHour(t=datetime(2026, 1, 15, 14, 0, tzinfo=UTC), temp_c=2.0),
]
MET_SERIES = [
    ForecastHour(t=datetime(2026, 1, 15, 12, 0, tzinfo=UTC), temp_c=9.0),
    ForecastHour(t=datetime(2026, 1, 15, 13, 0, tzinfo=UTC), temp_c=8.0),
    ForecastHour(t=datetime(2026, 1, 15, 14, 0, tzinfo=UTC), temp_c=7.0),
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


class RecordingForecast:
    def __init__(
        self,
        series: list[ForecastHour] | None = None,
        error: BaseException | None = None,
        inner: ForecastSource | None = None,
    ) -> None:
        self._series = [] if series is None else series
        self._error = error
        self._inner = inner
        self.calls: list[tuple[float, float]] = []

    def fetch(self, *, lat: float, lon: float) -> list[ForecastHour]:
        self.calls.append((lat, lon))
        if self._inner is not None:
            return self._inner.fetch(lat=lat, lon=lon)
        if self._error is not None:
            raise self._error
        return list(self._series)


class FakeClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


class SilentNotifier:
    def send_frost_alert(self, **_kwargs: object) -> None:
        return None


class SilentInbox:
    def __init__(self) -> None:
        self.last_offset = 0

    def poll(self, *, telegram_offset: int) -> tuple[list[str], int]:
        self.last_offset = telegram_offset
        return [], telegram_offset


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not open a network connection")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def _om_payload(*, temps: list[float] | None = None) -> dict[str, object]:
    return {
        "hourly": {
            "time": OM_TIMES,
            "temperature_2m": OM_TEMPS if temps is None else temps,
        }
    }


def _met_payload() -> dict[str, object]:
    entries = [
        ("2026-01-15T12:00:00Z", 9.0),
        ("2026-01-15T13:00:00Z", 8.0),
        ("2026-01-15T14:00:00Z", 7.0),
        ("2026-01-15T18:00:00Z", 6.0),
    ]
    return {
        "properties": {
            "timeseries": [
                {
                    "time": time,
                    "data": {"instant": {"details": {"air_temperature": temp}}},
                }
                for time, temp in entries
            ]
        }
    }


def _http_error(url: str, code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "error", {}, None)


def _wrapped(cause: BaseException) -> OpenMeteoForecastError:
    error = OpenMeteoForecastError("forecast fetch failed")
    error.__cause__ = cause
    return error


def _install_urlopen(
    monkeypatch: pytest.MonkeyPatch,
    *,
    om: bytes | BaseException,
    met: bytes | BaseException | None = None,
) -> list[str]:
    hosts: list[str] = []

    def fake_urlopen(req: urllib.request.Request, timeout: float | None = None) -> _FakeHTTPResponse:
        url = req.full_url
        hosts.append(url)
        if "api.open-meteo.com" in url:
            if isinstance(om, BaseException):
                raise om
            return _FakeHTTPResponse(om)
        if "api.met.no" in url:
            if met is None:
                raise AssertionError("MET Norway must not be called")
            if isinstance(met, BaseException):
                raise met
            return _FakeHTTPResponse(met)
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return hosts


def _vendor_order(hosts: list[str]) -> list[str]:
    order: list[str] = []
    for url in hosts:
        if "api.open-meteo.com" in url:
            order.append("open-meteo")
        elif "api.met.no" in url:
            order.append("met-norway")
    return order


def test_open_meteo_success_does_not_call_met(monkeypatch: pytest.MonkeyPatch) -> None:
    hosts = _install_urlopen(
        monkeypatch,
        om=json.dumps(_om_payload()).encode("utf-8"),
    )
    fallback = RecordingForecast(series=MET_SERIES)
    series = FailoverForecast(OpenMeteoForecast(), fallback).fetch(lat=LAT, lon=LON)
    assert series == OM_SERIES
    assert fallback.calls == []
    assert all("api.met.no" not in url for url in hosts)
    assert any("api.open-meteo.com" in url for url in hosts)


@pytest.mark.parametrize(
    "om_error",
    [
        TimeoutError(),
        urllib.error.URLError("connection refused"),
        _http_error("https://api.open-meteo.com/v1/forecast", 500),
        _http_error("https://api.open-meteo.com/v1/forecast", 429),
    ],
)
def test_availability_failure_fetches_met(
    monkeypatch: pytest.MonkeyPatch,
    om_error: BaseException,
) -> None:
    hosts = _install_urlopen(
        monkeypatch,
        om=om_error,
        met=json.dumps(_met_payload()).encode("utf-8"),
    )
    primary = RecordingForecast(inner=OpenMeteoForecast())
    fallback = RecordingForecast(inner=MetNorwayForecast(elevation_m=28.4))
    series = FailoverForecast(primary, fallback).fetch(lat=LAT, lon=LON)
    assert series == MET_SERIES
    assert primary.calls == [(LAT, LON)]
    assert fallback.calls == [(LAT, LON)]
    assert _vendor_order(hosts) == ["open-meteo", "met-norway"]


@pytest.mark.parametrize(
    "temps",
    [
        [],
        [float("nan"), 3.0, 2.0],
        [4.0, float("inf"), 2.0],
    ],
)
def test_malformed_open_meteo_fetches_met(
    monkeypatch: pytest.MonkeyPatch,
    temps: list[float],
) -> None:
    times = [] if not temps else OM_TIMES
    payload = {"hourly": {"time": times, "temperature_2m": temps}}
    hosts = _install_urlopen(
        monkeypatch,
        om=json.dumps(payload).encode("utf-8"),
        met=json.dumps(_met_payload()).encode("utf-8"),
    )
    primary = RecordingForecast(inner=OpenMeteoForecast())
    fallback = RecordingForecast(inner=MetNorwayForecast(elevation_m=28.4))
    series = FailoverForecast(primary, fallback).fetch(lat=LAT, lon=LON)
    assert series == MET_SERIES
    assert primary.calls == [(LAT, LON)]
    assert fallback.calls == [(LAT, LON)]
    assert _vendor_order(hosts) == ["open-meteo", "met-norway"]


@pytest.mark.parametrize("code", [400, 401, 403, 404, 418])
def test_open_meteo_4xx_does_not_call_met(
    monkeypatch: pytest.MonkeyPatch,
    code: int,
) -> None:
    hosts = _install_urlopen(
        monkeypatch,
        om=_http_error("https://api.open-meteo.com/v1/forecast", code),
        met=json.dumps(_met_payload()).encode("utf-8"),
    )
    fallback = RecordingForecast(series=MET_SERIES)
    with pytest.raises(OpenMeteoForecastError):
        FailoverForecast(OpenMeteoForecast(), fallback).fetch(lat=LAT, lon=LON)
    assert fallback.calls == []
    assert all("api.met.no" not in url for url in hosts)


def test_dual_miss_raises_met_error_not_open_meteo_series(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_urlopen(
        monkeypatch,
        om=_http_error("https://api.open-meteo.com/v1/forecast", 500),
        met=_http_error(
            "https://api.met.no/weatherapi/locationforecast/2.0/compact",
            500,
        ),
    )
    with pytest.raises(MetNorwayForecastError):
        FailoverForecast(OpenMeteoForecast(), MetNorwayForecast(elevation_m=28.4)).fetch(
            lat=LAT,
            lon=LON,
        )


def test_malformed_met_after_failover_does_not_return_open_meteo_leftovers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_urlopen(
        monkeypatch,
        om=_http_error("https://api.open-meteo.com/v1/forecast", 500),
        met=json.dumps({"properties": {"timeseries": []}}).encode("utf-8"),
    )
    with pytest.raises(MetNorwayForecastError):
        FailoverForecast(OpenMeteoForecast(), MetNorwayForecast(elevation_m=28.4)).fetch(
            lat=LAT,
            lon=LON,
        )


def test_wrapped_4xx_without_live_adapters_does_not_call_fallback() -> None:
    primary = RecordingForecast(
        error=_wrapped(_http_error("https://api.open-meteo.com/v1/forecast", 400)),
    )
    fallback = RecordingForecast(series=MET_SERIES)
    with pytest.raises(OpenMeteoForecastError):
        FailoverForecast(primary, fallback).fetch(lat=LAT, lon=LON)
    assert fallback.calls == []
    assert primary.calls == [(LAT, LON)]


def test_check_default_wires_failover_with_stored_elevation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", CHAT_ID)
    JsonConfigStore(tmp_path).write(
        place_name="Stockholm",
        lat=LAT,
        lon=LON,
        elevation_m=28,
        timezone="Europe/Stockholm",
        threshold_c=3,
        scale="C",
    )
    captured: dict[str, object] = {}

    class Primary:
        def fetch(self, *, lat: float, lon: float) -> list[ForecastHour]:
            return [
                ForecastHour(t=datetime(2026, 1, 16, 6, 0, tzinfo=UTC), temp_c=8),
            ]

    class Fallback:
        def __init__(self, elevation_m: float) -> None:
            captured["elevation_m"] = elevation_m

        def fetch(self, *, lat: float, lon: float) -> list[ForecastHour]:
            raise AssertionError("MET Norway must not be called on Open-Meteo success")

    class WiredFailover:
        def __init__(self, primary: object, fallback: object) -> None:
            captured["primary"] = primary
            captured["fallback"] = fallback
            self._primary = primary

        def fetch(self, *, lat: float, lon: float) -> list[ForecastHour]:
            return self._primary.fetch(lat=lat, lon=lon)

    monkeypatch.setattr("frost_alert.entrypoints.check.OpenMeteoForecast", Primary)
    monkeypatch.setattr("frost_alert.entrypoints.check.MetNorwayForecast", Fallback)
    monkeypatch.setattr("frost_alert.entrypoints.check.FailoverForecast", WiredFailover)
    inbox = SilentInbox()
    code = check_main(
        ["check"],
        config_store=JsonConfigStore(tmp_path),
        state_store=JsonStateStore(tmp_path),
        notifier=SilentNotifier(),
        inbox=inbox,
        clock=FakeClock(),
    )
    assert code == 0
    assert captured["elevation_m"] == 28.0
    assert isinstance(captured["primary"], Primary)
    assert isinstance(captured["fallback"], Fallback)
    assert inbox.last_offset == 0
