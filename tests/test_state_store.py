from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from pathlib import Path

import pytest

from frost_alert.adapters.json_state_store import JsonStateStore

STATE_KEYS = {
    "season",
    "event_date",
    "alerted_windows",
    "telegram_offset",
    "updated_at",
}


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not open a network connection")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def test_load_missing_state_returns_five_default_keys_only(tmp_path: Path) -> None:
    payload = JsonStateStore(tmp_path).load()
    assert set(payload) == STATE_KEYS
    assert payload["season"] == "monitoring"
    assert payload["event_date"] is None
    assert payload["alerted_windows"] == []
    assert payload["telegram_offset"] == 0
    updated_at = payload["updated_at"]
    assert isinstance(updated_at, str)
    parsed = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def test_load_missing_state_does_not_create_file(tmp_path: Path) -> None:
    path = tmp_path / "data" / "state.json"
    JsonStateStore(tmp_path).load()
    assert not path.exists()
    assert not (tmp_path / "data").exists()


def test_write_creates_data_dir_and_stamps_updated_at(tmp_path: Path) -> None:
    path = tmp_path / "data" / "state.json"
    assert not path.exists()
    JsonStateStore(tmp_path).write(
        season="monitoring",
        event_date="2026-01-16",
        alerted_windows=[24],
        telegram_offset=3,
    )
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == STATE_KEYS
    assert payload["season"] == "monitoring"
    assert payload["event_date"] == "2026-01-16"
    assert payload["alerted_windows"] == [24]
    assert payload["telegram_offset"] == 3
    updated_at = payload["updated_at"]
    assert isinstance(updated_at, str)
    parsed = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def test_write_then_load_round_trip(tmp_path: Path) -> None:
    store = JsonStateStore(tmp_path)
    store.write(
        season="suspended",
        event_date=None,
        alerted_windows=[],
        telegram_offset=0,
    )
    payload = store.load()
    assert payload["season"] == "suspended"
    assert payload["event_date"] is None
    assert payload["alerted_windows"] == []
    assert payload["telegram_offset"] == 0
    assert payload["updated_at"]
