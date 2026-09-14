from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
from datetime import UTC, datetime, timedelta

from frost_alert.adapters.http import get_json
from frost_alert.domain.classify import ForecastHour

FORECAST_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
_HOUR = timedelta(hours=1)


class MetNorwayForecastError(Exception):
    pass


class MetNorwayForecast:
    def __init__(self, elevation_m: float) -> None:
        self._elevation_m = elevation_m

    def fetch(self, *, lat: float, lon: float) -> list[ForecastHour]:
        query = urllib.parse.urlencode(
            {
                "lat": f"{lat:.4f}",
                "lon": f"{lon:.4f}",
                "altitude": self._elevation_m,
            }
        )
        try:
            payload = get_json(f"{FORECAST_URL}?{query}")
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            OSError,
            UnicodeError,
            ValueError,
        ) as err:
            raise MetNorwayForecastError("forecast fetch failed") from err
        return _series_from_payload(payload)


def _series_from_payload(payload: object) -> list[ForecastHour]:
    if not isinstance(payload, dict):
        raise MetNorwayForecastError("malformed forecast payload")
    properties = payload.get("properties")
    if not isinstance(properties, dict):
        raise MetNorwayForecastError("malformed forecast payload")
    timeseries = properties.get("timeseries")
    if not isinstance(timeseries, list):
        raise MetNorwayForecastError("malformed timeseries")
    hours = [_hour_from_item(item) for item in timeseries]
    _require_sorted(hours)
    prefix = _hourly_prefix(hours)
    if not prefix:
        raise MetNorwayForecastError("malformed hourly series")
    return prefix


def _hour_from_item(item: object) -> ForecastHour:
    if not isinstance(item, dict):
        raise MetNorwayForecastError("malformed timeseries item")
    data = item.get("data")
    if not isinstance(data, dict):
        raise MetNorwayForecastError("malformed timeseries item")
    instant = data.get("instant")
    if not isinstance(instant, dict):
        raise MetNorwayForecastError("malformed timeseries item")
    details = instant.get("details")
    if not isinstance(details, dict) or "air_temperature" not in details:
        raise MetNorwayForecastError("malformed timeseries item")
    temp = details["air_temperature"]
    if not _is_number(temp):
        raise MetNorwayForecastError("malformed air temperature")
    return ForecastHour(t=_parse_utc(item.get("time")), temp_c=temp)


def _require_sorted(hours: list[ForecastHour]) -> None:
    previous: datetime | None = None
    for hour in hours:
        if previous is not None and hour.t <= previous:
            raise MetNorwayForecastError("malformed timeseries order")
        previous = hour.t


def _hourly_prefix(hours: list[ForecastHour]) -> list[ForecastHour]:
    if not hours:
        return []
    prefix = [hours[0]]
    previous = hours[0]
    for hour in hours[1:]:
        if hour.t - previous.t != _HOUR:
            break
        prefix.append(hour)
        previous = hour
    return prefix


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise MetNorwayForecastError("malformed timeseries time")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as err:
        raise MetNorwayForecastError("malformed timeseries time") from err
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _is_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )
