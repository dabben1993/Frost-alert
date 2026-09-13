from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import Protocol

from frost_alert.adapters.json_config_store import JsonConfigStore
from frost_alert.adapters.open_meteo_geocoder import OpenMeteoGeocoder
from frost_alert.domain.scale_threshold import InvalidSetupInput, resolve_scale_and_threshold
from frost_alert.ports import ConfigStore

USAGE = "Usage: frost-alert setup"


class _Geocoder(Protocol):
    def geocode(self, name: str) -> object | None: ...


def main(
    argv: Sequence[str] | None = None,
    *,
    config_store: ConfigStore | None = None,
    geocoder: _Geocoder | None = None,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["setup"]:
        print(USAGE, file=sys.stderr)
        return 1

    scale_raw = input("Temperature scale (C or F) [C]: ")
    threshold_raw = input("Frost threshold in that scale [3 when C]: ")

    try:
        result = resolve_scale_and_threshold(scale_raw, threshold_raw)
    except InvalidSetupInput as exc:
        print(exc, file=sys.stderr)
        return 1

    location_raw = input("Location (city, postal code, or coordinates): ")
    query = location_raw.strip()
    if query == "":
        print("No matching place found.", file=sys.stderr)
        return 1

    coder = OpenMeteoGeocoder() if geocoder is None else geocoder
    try:
        place = coder.geocode(query)
    except Exception:
        place = None
    if place is None:
        print("No matching place found.", file=sys.stderr)
        return 1

    print(_shown_place(place))
    confirm_raw = input("Use this place? [Y/n]: ")
    if not _confirmed(confirm_raw):
        print("Place rejected.", file=sys.stderr)
        return 1

    store = JsonConfigStore() if config_store is None else config_store
    store.write(
        place_name=place.place_name,
        lat=place.lat,
        lon=place.lon,
        elevation_m=place.elevation_m,
        timezone=place.timezone,
        threshold_c=result.threshold_c,
        scale=result.scale,
    )
    return 0


def _shown_place(place: object) -> str:
    parts = [str(getattr(place, "place_name"))]
    for attr in ("admin1", "country"):
        value = getattr(place, attr, None)
        if value:
            parts.append(str(value))
    return ", ".join(parts)


def _confirmed(raw: str) -> bool:
    text = raw.strip()
    return text == "" or text in {"y", "Y"}
