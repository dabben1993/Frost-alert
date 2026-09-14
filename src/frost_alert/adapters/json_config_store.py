from __future__ import annotations

import json
from pathlib import Path


class JsonConfigStore:
    def __init__(self, root: Path | str | None = None) -> None:
        self._root = Path.cwd() if root is None else Path(root)

    def write(
        self,
        *,
        place_name: str,
        lat: float,
        lon: float,
        elevation_m: float,
        timezone: str,
        threshold_c: float,
        scale: str,
    ) -> None:
        path = self._root / "config" / "user.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "place_name": place_name,
            "lat": lat,
            "lon": lon,
            "elevation_m": _json_number(elevation_m),
            "timezone": timezone,
            "threshold_c": _json_number(threshold_c),
            "scale": scale,
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def load(self) -> dict:
        path = self._root / "config" / "user.json"
        return json.loads(path.read_text(encoding="utf-8"))


def _json_number(value: float) -> int | float:
    if value == int(value):
        return int(value)
    return value
