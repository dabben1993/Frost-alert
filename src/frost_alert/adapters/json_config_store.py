from __future__ import annotations

import json
from pathlib import Path


class JsonConfigStore:
    def __init__(self, root: Path | str | None = None) -> None:
        self._root = Path.cwd() if root is None else Path(root)

    def write_scale_and_threshold(self, scale: str, threshold_c: float) -> None:
        path = self._root / "config" / "user.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"scale": scale, "threshold_c": _json_number(threshold_c)}
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _json_number(value: float) -> int | float:
    if value == int(value):
        return int(value)
    return value
