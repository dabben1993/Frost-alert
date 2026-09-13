from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

from frost_alert.domain.classify import ForecastHour

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "Frost-alert (https://github.com/dabben1993/Frost-alert)"
TIMEOUT_S = 15
_HOUR = timedelta(hours=1)


class OpenMeteoForecastError(Exception):
    pass


class OpenMeteoForecast:
    def fetch(self, *, lat: float, lon: float) -> list[ForecastHour]:
        query = urllib.parse.urlencode(
            {
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m",
                "timezone": "UTC",
            }
        )
        request = urllib.request.Request(
            f"{FORECAST_URL}?{query}",
            headers={"User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                raw = response.read().decode("utf-8")
            payload = json.loads(raw)
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            OSError,
            UnicodeError,
            ValueError,
        ) as err:
            raise OpenMeteoForecastError("forecast fetch failed") from err
        return _series_from_payload(payload)


def _series_from_payload(payload: object) -> list[ForecastHour]:
    if not isinstance(payload, dict):
        raise OpenMeteoForecastError("malformed forecast payload")
    if payload.get("error") is True:
        raise OpenMeteoForecastError("open-meteo error response")
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise OpenMeteoForecastError("malformed hourly block")
    try:
        times = hourly["time"]
        temps = hourly["temperature_2m"]
    except KeyError as err:
        raise OpenMeteoForecastError("malformed hourly block") from err
    if not isinstance(times, list) or not isinstance(temps, list):
        raise OpenMeteoForecastError("malformed hourly block")
    if len(times) != len(temps) or not times:
        raise OpenMeteoForecastError("malformed hourly series")
    series: list[ForecastHour] = []
    previous: datetime | None = None
    for raw_time, raw_temp in zip(times, temps, strict=True):
        if not _is_number(raw_temp):
            raise OpenMeteoForecastError("malformed hourly temperature")
        hour_t = _parse_utc(raw_time)
        if previous is not None:
            if hour_t <= previous or hour_t - previous != _HOUR:
                raise OpenMeteoForecastError("malformed hourly timeline")
        previous = hour_t
        series.append(ForecastHour(t=hour_t, temp_c=raw_temp))
    return series


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise OpenMeteoForecastError("malformed hourly time")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as err:
        raise OpenMeteoForecastError("malformed hourly time") from err
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
