from __future__ import annotations

import socket
import urllib.request

import pytest

from frost_alert.adapters.healthchecks_watchdog import HealthchecksWatchdog

PING_URL = "https://hc-ping.com/test-uuid"


class _FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not open a network connection")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def _install_urlopen(
    monkeypatch: pytest.MonkeyPatch,
    *,
    body: bytes | None = None,
    error: BaseException | None = None,
) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_urlopen(
        req: urllib.request.Request, timeout: float | None = None
    ) -> _FakeHTTPResponse:
        captured["url"] = req.full_url
        captured["user_agent"] = req.get_header("User-agent")
        captured["timeout"] = timeout
        captured["method"] = req.get_method()
        if error is not None:
            raise error
        assert body is not None
        return _FakeHTTPResponse(body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return captured


def test_ping_gets_url_with_identifying_ua_and_15s_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _install_urlopen(monkeypatch, body=b"OK")
    HealthchecksWatchdog(PING_URL).ping()
    assert captured["url"] == PING_URL
    assert captured["method"] == "GET"
    assert captured["user_agent"] == "Frost-alert (https://github.com/dabben1993/Frost-alert)"
    assert captured["timeout"] == 15


def test_ping_does_not_parse_response_as_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_urlopen(monkeypatch, body=b"OK")
    HealthchecksWatchdog(PING_URL).ping()


def test_blank_url_skips_ping(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("blank ping URL must not open HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    HealthchecksWatchdog("").ping()
    HealthchecksWatchdog("   ").ping()
