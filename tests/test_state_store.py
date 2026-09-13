from __future__ import annotations

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
