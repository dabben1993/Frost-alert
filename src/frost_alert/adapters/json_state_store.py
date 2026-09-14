from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class JsonStateStore:
    def __init__(self, root: Path | str | None = None) -> None:
        self._root = Path.cwd() if root is None else Path(root)

    def load(self) -> dict[str, object]:
        path = self._root / "data" / "state.json"
        if not path.is_file():
            return {
                "season": "monitoring",
                "event_date": None,
                "alerted_windows": [],
                "telegram_offset": 0,
                "updated_at": _utc_now_iso(),
            }
        return json.loads(path.read_text(encoding="utf-8"))

    def write(
        self,
        *,
        season: str,
        event_date: str | None,
        alerted_windows: list[int],
        telegram_offset: int,
    ) -> None:
        path = self._root / "data" / "state.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "season": season,
            "event_date": event_date,
            "alerted_windows": list(alerted_windows),
            "telegram_offset": telegram_offset,
            "updated_at": _utc_now_iso(),
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
