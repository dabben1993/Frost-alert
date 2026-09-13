from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
USER_AGENT = "Frost-alert (https://github.com/dabben1993/Frost-alert)"
TIMEOUT_S = 15


@dataclass(frozen=True)
class GeocodePlace:
    place_name: str
    lat: float
    lon: float
    elevation_m: float
    timezone: str
    admin1: str | None = None
    country: str | None = None


class OpenMeteoGeocoder:
    def geocode(self, name: str) -> GeocodePlace | None:
        query = urllib.parse.urlencode({"name": name, "count": 1})
        request = urllib.request.Request(
            f"{GEOCODE_URL}?{query}",
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
        ):
            return None
        return _place_from_payload(payload)


def _place_from_payload(payload: object) -> GeocodePlace | None:
    if not isinstance(payload, dict):
        return None
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        return None
    first = results[0]
    if not isinstance(first, dict):
        return None
    try:
        place_name = first["name"]
        lat = first["latitude"]
        lon = first["longitude"]
        elevation_m = first["elevation"]
        timezone = first["timezone"]
    except KeyError:
        return None
    if not isinstance(place_name, str) or not isinstance(timezone, str):
        return None
    if not _is_number(lat) or not _is_number(lon) or not _is_number(elevation_m):
        return None
    return GeocodePlace(
        place_name=place_name,
        lat=lat,
        lon=lon,
        elevation_m=elevation_m,
        timezone=timezone,
        admin1=_optional_text(first.get("admin1")),
        country=_optional_text(first.get("country")),
    )


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _optional_text(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
