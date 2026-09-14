from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

STATE_KEYS = {
    "season",
    "event_date",
    "alerted_windows",
    "telegram_offset",
    "updated_at",
}
_SEASONS = {"monitoring", "suspended"}
_WINDOWS = {24, 12, 6}


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
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _validated(payload)

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


def _validated(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict) or set(payload) != STATE_KEYS:
        raise ValueError("invalid state.json")
    if payload["season"] not in _SEASONS:
        raise ValueError("invalid state.json")
    event_date = payload["event_date"]
    if event_date is not None:
        if not isinstance(event_date, str):
            raise ValueError("invalid state.json")
        try:
            parsed = date.fromisoformat(event_date)
        except ValueError:
            raise ValueError("invalid state.json") from None
        if parsed.isoformat() != event_date:
            raise ValueError("invalid state.json")
    windows = payload["alerted_windows"]
    if not isinstance(windows, list) or not all(_is_window(item) for item in windows):
        raise ValueError("invalid state.json")
    if not _is_int(payload["telegram_offset"]):
        raise ValueError("invalid state.json")
    _require_utc_iso(payload["updated_at"])
    return payload


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_window(value: object) -> bool:
    return _is_int(value) and value in _WINDOWS


def _require_utc_iso(value: object) -> None:
    if not isinstance(value, str):
        raise ValueError("invalid state.json")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("invalid state.json") from None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("invalid state.json")


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
