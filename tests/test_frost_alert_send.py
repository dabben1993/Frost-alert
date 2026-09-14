from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime

import pytest

from frost_alert.adapters.telegram_notifier import TelegramNotifier, TelegramNotifierError
from frost_alert.domain.alert_windows import mark_window, should_send
from frost_alert.domain.classify import Classification
from frost_alert.send_frost_alert import maybe_send_frost_alert

TOKEN = "TEST_TOKEN"
CHAT_ID = "12345"
PLACE = "Stockholm"
ZONE = "Europe/Stockholm"
THRESHOLD_C = 3
GOLDEN_T = datetime(2026, 1, 16, 6, 0, tzinfo=UTC)
OK_BODY = json.dumps({"ok": True, "result": {"message_id": 1}}).encode("utf-8")


class _FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _RecordingNotifier:
    def __init__(self, error: BaseException | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self._error = error

    def send_frost_alert(
        self,
        *,
        classification: Classification,
        place_name: str,
        threshold_c: int | float,
        scale: str,
        timezone: str,
    ) -> None:
        self.calls.append(
            {
                "classification": classification,
                "place_name": place_name,
                "threshold_c": threshold_c,
                "scale": scale,
                "timezone": timezone,
            }
        )
        if self._error is not None:
            raise self._error


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not open a network connection")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def _classification(
    *,
    risk_present: bool = True,
    window: int | None = 24,
    event_date: str | None = "2026-01-16",
    t: datetime | None = GOLDEN_T,
    temp_c: int | float | None = 2,
) -> Classification:
    return Classification(
        risk_present=risk_present,
        window=window,
        event_date=event_date,
        t=t,
        temp_c=temp_c,
    )


def _install_urlopen(
    monkeypatch: pytest.MonkeyPatch,
    *,
    body: bytes | None = None,
    error: BaseException | None = None,
) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_urlopen(req: urllib.request.Request, timeout: float | None = None) -> _FakeHTTPResponse:
        captured["url"] = req.full_url
        captured["user_agent"] = req.get_header("User-agent")
        captured["timeout"] = timeout
        captured["method"] = req.get_method()
        captured["content_type"] = req.get_header("Content-type")
        captured["payload"] = json.loads(req.data.decode("utf-8") if req.data else "null")
        if error is not None:
            raise error
        assert body is not None
        return _FakeHTTPResponse(body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return captured


def _send(
    monkeypatch: pytest.MonkeyPatch,
    *,
    classification: Classification | None = None,
    alerted_windows: list[int] | None = None,
    scale: str = "C",
    body: bytes = OK_BODY,
    error: BaseException | None = None,
) -> tuple[list[int], dict[str, object]]:
    captured = _install_urlopen(monkeypatch, body=None if error is not None else body, error=error)
    notifier = TelegramNotifier(token=TOKEN, chat_id=CHAT_ID)
    windows = maybe_send_frost_alert(
        notifier=notifier,
        classification=_classification() if classification is None else classification,
        alerted_windows=[] if alerted_windows is None else alerted_windows,
        place_name=PLACE,
        threshold_c=THRESHOLD_C,
        scale=scale,
        timezone=ZONE,
    )
    return windows, captured


@pytest.mark.parametrize("window", [24, 12, 6])
def test_happy_path_sends_preview_first_and_marks_window(
    monkeypatch: pytest.MonkeyPatch,
    window: int,
) -> None:
    windows, captured = _send(monkeypatch, classification=_classification(window=window))
    assert windows == [window]
    parsed = urllib.parse.urlparse(str(captured["url"]))
    assert captured["method"] == "POST"
    assert parsed.scheme == "https"
    assert parsed.netloc == "api.telegram.org"
    assert parsed.path == f"/bot{TOKEN}/sendMessage"
    assert captured["user_agent"] == "Frost-alert (https://github.com/dabben1993/Frost-alert)"
    assert captured["timeout"] == 15
    assert captured["content_type"] == "application/json"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["chat_id"] == CHAT_ID
    assert "parse_mode" not in payload
    text = payload["text"]
    assert isinstance(text, str)
    first, _, body = text.partition("\n")
    assert "❄️" in first
    assert "Frost risk" in first
    assert f"~{window}h" in first
    assert PLACE in body
    assert "2°C" in body
    assert "3°C" in body
    assert "2026-01-16 07:00" in body
    button = payload["reply_markup"]["inline_keyboard"][0][0]
    assert button["callback_data"] == "plants_in"
    assert "overwintering" in button["text"].lower()


@pytest.mark.parametrize("window", [24, 12, 6])
def test_already_marked_skips_http(window: int) -> None:
    notifier = _RecordingNotifier()
    original = [window]
    windows = maybe_send_frost_alert(
        notifier=notifier,
        classification=_classification(window=window),
        alerted_windows=original,
        place_name=PLACE,
        threshold_c=THRESHOLD_C,
        scale="C",
        timezone=ZONE,
    )
    assert windows == [window]
    assert notifier.calls == []
    assert original == [window]


def test_absent_risk_skips_http() -> None:
    notifier = _RecordingNotifier()
    original = [12]
    windows = maybe_send_frost_alert(
        notifier=notifier,
        classification=_classification(
            risk_present=False,
            window=None,
            event_date=None,
            t=None,
            temp_c=None,
        ),
        alerted_windows=original,
        place_name=PLACE,
        threshold_c=THRESHOLD_C,
        scale="C",
        timezone=ZONE,
    )
    assert windows == [12]
    assert notifier.calls == []
    assert original == [12]


def test_missing_window_skips_http() -> None:
    notifier = _RecordingNotifier()
    windows = maybe_send_frost_alert(
        notifier=notifier,
        classification=_classification(window=None),
        alerted_windows=[],
        place_name=PLACE,
        threshold_c=THRESHOLD_C,
        scale="C",
        timezone=ZONE,
    )
    assert windows == []
    assert notifier.calls == []


def test_scale_f_body_uses_fahrenheit(monkeypatch: pytest.MonkeyPatch) -> None:
    _windows, captured = _send(monkeypatch, scale="F")
    payload = captured["payload"]
    assert isinstance(payload, dict)
    text = str(payload["text"])
    _first, _, body = text.partition("\n")
    assert "35.6°F" in body
    assert "37.4°F" in body
    assert "°C" not in body
    assert "2°C" not in text
    assert "3°C" not in text


@pytest.mark.parametrize("window", [24, 12, 6])
def test_preview_line_omits_opened_facts(monkeypatch: pytest.MonkeyPatch, window: int) -> None:
    _windows, captured = _send(monkeypatch, classification=_classification(window=window))
    payload = captured["payload"]
    assert isinstance(payload, dict)
    text = str(payload["text"])
    first = text.split("\n", 1)[0]
    assert f"~{window}h" in first
    assert PLACE not in first
    assert "2°C" not in first
    assert "3°C" not in first
    assert "35.6" not in first
    assert "/in" not in first
    assert "plants_in" not in first
    assert "/in" not in text
    assert "plants_in" not in text


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.HTTPError(
            "https://api.telegram.org/botTEST_TOKEN/sendMessage",
            500,
            "server error",
            {},
            None,
        ),
        urllib.error.HTTPError(
            "https://api.telegram.org/botTEST_TOKEN/sendMessage",
            429,
            "too many requests",
            {},
            None,
        ),
        urllib.error.HTTPError(
            "https://api.telegram.org/botTEST_TOKEN/sendMessage",
            400,
            "bad request",
            {},
            None,
        ),
        TimeoutError(),
        urllib.error.URLError("connection refused"),
    ],
)
def test_http_failures_raise_without_marking(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    original: list[int] = []
    with pytest.raises(TelegramNotifierError):
        _send(monkeypatch, alerted_windows=original, error=error)
    assert original == []


def test_ok_false_raises_without_marking(monkeypatch: pytest.MonkeyPatch) -> None:
    original: list[int] = []
    with pytest.raises(TelegramNotifierError):
        _send(
            monkeypatch,
            alerted_windows=original,
            body=json.dumps({"ok": False, "description": "forbidden"}).encode("utf-8"),
        )
    assert original == []


def test_bad_json_raises_without_marking(monkeypatch: pytest.MonkeyPatch) -> None:
    original: list[int] = []
    with pytest.raises(TelegramNotifierError):
        _send(monkeypatch, alerted_windows=original, body=b"not-json")
    assert original == []


def test_notifier_raise_leaves_windows_unchanged() -> None:
    notifier = _RecordingNotifier(error=RuntimeError("send failed"))
    original = [12]
    with pytest.raises(RuntimeError, match="send failed"):
        maybe_send_frost_alert(
            notifier=notifier,
            classification=_classification(),
            alerted_windows=original,
            place_name=PLACE,
            threshold_c=THRESHOLD_C,
            scale="C",
            timezone=ZONE,
        )
    assert original == [12]
    assert len(notifier.calls) == 1


def test_domain_skip_and_mark_are_pure() -> None:
    present = _classification()
    absent = _classification(
        risk_present=False,
        window=None,
        event_date=None,
        t=None,
        temp_c=None,
    )
    assert should_send(present, []) is True
    assert should_send(present, [24]) is False
    assert should_send(absent, []) is False
    assert should_send(_classification(window=None), []) is False
    windows = [12]
    assert mark_window(windows, 24) == [12, 24]
    assert windows == [12]
