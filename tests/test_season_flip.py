from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from frost_alert.adapters.telegram_ack_inbox import TelegramAckInbox, TelegramAckInboxError
from frost_alert.apply_season import apply_telegram_acks
from frost_alert.domain.season import apply_intent
from frost_alert.entrypoints.setup import main

TOKEN = "TEST_TOKEN"
CHAT_ID = "12345"
OTHER_CHAT = "99999"
GOLDEN_EVENT = "2026-01-16"
ROOT = Path(__file__).resolve().parents[1]


class _FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class FakeAckInbox:
    def __init__(
        self,
        *,
        intents: list[str] | None = None,
        new_offset: int | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._intents = [] if intents is None else intents
        self._new_offset = new_offset
        self._error = error
        self.polls: list[int] = []

    def poll(self, *, telegram_offset: int) -> tuple[list[str], int]:
        self.polls.append(telegram_offset)
        if self._error is not None:
            raise self._error
        offset = telegram_offset if self._new_offset is None else self._new_offset
        return list(self._intents), offset


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not open a network connection")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def _ok(result: object) -> bytes:
    return json.dumps({"ok": True, "result": result}).encode("utf-8")


def _command(update_id: int, text: str, *, chat_id: str = CHAT_ID) -> dict[str, object]:
    return {
        "update_id": update_id,
        "message": {"chat": {"id": int(chat_id)}, "text": text},
    }


def _callback(
    update_id: int,
    data: str,
    *,
    chat_id: str = CHAT_ID,
    callback_id: str = "cb1",
) -> dict[str, object]:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": callback_id,
            "data": data,
            "message": {"chat": {"id": int(chat_id)}},
        },
    }


def _http_error(code: int, method: str = "getUpdates") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        code,
        "error",
        {},
        None,
    )


def _install_urlopen(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[bytes | BaseException],
) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []
    queue = list(responses)

    def fake_urlopen(
        req: urllib.request.Request, timeout: float | None = None
    ) -> _FakeHTTPResponse:
        payload: object = None
        if req.data:
            payload = json.loads(req.data.decode("utf-8"))
        calls.append(
            {
                "url": req.full_url,
                "user_agent": req.get_header("User-agent"),
                "timeout": timeout,
                "method": req.get_method(),
                "content_type": req.get_header("Content-type"),
                "payload": payload,
            }
        )
        if not queue:
            raise AssertionError("unexpected extra urlopen call")
        item = queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return _FakeHTTPResponse(item)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


def _apply(
    monkeypatch: pytest.MonkeyPatch,
    *,
    responses: list[bytes | BaseException],
    season: str = "monitoring",
    event_date: str | None = GOLDEN_EVENT,
    alerted_windows: list[int] | None = None,
    telegram_offset: int = 0,
    chat_id: str | int = CHAT_ID,
) -> tuple[dict[str, object], list[int], list[dict[str, object]]]:
    calls = _install_urlopen(monkeypatch, responses)
    windows = [24] if alerted_windows is None else alerted_windows
    result = apply_telegram_acks(
        inbox=TelegramAckInbox(token=TOKEN, chat_id=chat_id),
        season=season,
        event_date=event_date,
        alerted_windows=windows,
        telegram_offset=telegram_offset,
    )
    return result, windows, calls


def _paths(calls: list[dict[str, object]]) -> list[str]:
    return [urllib.parse.urlparse(str(call["url"])).path for call in calls]


def _get_updates_call(calls: list[dict[str, object]]) -> dict[str, object]:
    for call in calls:
        path = urllib.parse.urlparse(str(call["url"])).path
        if path.endswith("/getUpdates"):
            return call
    raise AssertionError("getUpdates was not called")


def _answer_calls(calls: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        call
        for call in calls
        if urllib.parse.urlparse(str(call["url"])).path.endswith("/answerCallbackQuery")
    ]


@pytest.mark.parametrize(
    "update",
    [_command(10, "/in"), _callback(10, "plants_in")],
    ids=["command", "callback"],
)
def test_in_or_plants_in_suspends_and_keeps_event(
    monkeypatch: pytest.MonkeyPatch,
    update: dict[str, object],
) -> None:
    responses: list[bytes | BaseException] = [_ok([update])]
    if "callback_query" in update:
        responses.append(_ok(True))
    result, original, calls = _apply(monkeypatch, responses=responses)
    assert result == {
        "season": "suspended",
        "event_date": GOLDEN_EVENT,
        "alerted_windows": [24],
        "telegram_offset": 10,
    }
    assert original == [24]
    get_call = _get_updates_call(calls)
    parsed = urllib.parse.urlparse(str(get_call["url"]))
    query = urllib.parse.parse_qs(parsed.query)
    assert get_call["method"] == "GET"
    assert parsed.scheme == "https"
    assert parsed.netloc == "api.telegram.org"
    assert parsed.path == f"/bot{TOKEN}/getUpdates"
    assert query["offset"] == ["1"]
    assert query["timeout"] == ["0"]
    assert get_call["user_agent"] == "Frost-alert (https://github.com/dabben1993/Frost-alert)"
    assert get_call["timeout"] == 15
    assert "setWebhook" not in "".join(_paths(calls))
    assert not any(path.endswith("/sendMessage") for path in _paths(calls))
    if "callback_query" in update:
        answers = _answer_calls(calls)
        assert len(answers) == 1
        assert answers[0]["method"] == "POST"
        assert answers[0]["timeout"] == 15
        assert answers[0]["user_agent"] == (
            "Frost-alert (https://github.com/dabben1993/Frost-alert)"
        )
        assert answers[0]["content_type"] == "application/json"
        assert answers[0]["payload"] == {"callback_query_id": "cb1"}
    else:
        assert _answer_calls(calls) == []


@pytest.mark.parametrize(
    "update",
    [_command(11, "/out"), _callback(11, "plants_out", callback_id="cb-out")],
    ids=["command", "callback"],
)
def test_out_or_plants_out_resumes_and_clears(
    monkeypatch: pytest.MonkeyPatch,
    update: dict[str, object],
) -> None:
    responses: list[bytes | BaseException] = [_ok([update])]
    if "callback_query" in update:
        responses.append(_ok(True))
    windows = [24, 12]
    result, original, calls = _apply(
        monkeypatch,
        responses=responses,
        season="suspended",
        event_date=GOLDEN_EVENT,
        alerted_windows=windows,
        telegram_offset=5,
    )
    assert result == {
        "season": "monitoring",
        "event_date": None,
        "alerted_windows": [],
        "telegram_offset": 11,
    }
    assert original == [24, 12]
    if "callback_query" in update:
        answers = _answer_calls(calls)
        assert len(answers) == 1
        assert answers[0]["payload"] == {"callback_query_id": "cb-out"}
    else:
        assert _answer_calls(calls) == []


def test_idempotent_in_keeps_suspended(monkeypatch: pytest.MonkeyPatch) -> None:
    result, original, _calls = _apply(
        monkeypatch,
        responses=[_ok([_command(10, "/in")])],
        season="suspended",
        event_date=GOLDEN_EVENT,
        alerted_windows=[24],
    )
    assert result["season"] == "suspended"
    assert result["event_date"] == GOLDEN_EVENT
    assert result["alerted_windows"] == [24]
    assert result["telegram_offset"] == 10
    assert original == [24]


@pytest.mark.parametrize(
    "update",
    [
        _command(10, "/in", chat_id=OTHER_CHAT),
        _callback(10, "plants_in", chat_id=OTHER_CHAT, callback_id="cb-foreign"),
    ],
    ids=["command", "callback"],
)
def test_wrong_chat_does_not_flip_but_advances_offset(
    monkeypatch: pytest.MonkeyPatch,
    update: dict[str, object],
) -> None:
    responses: list[bytes | BaseException] = [_ok([update])]
    if "callback_query" in update:
        responses.append(_ok(True))
    result, original, calls = _apply(monkeypatch, responses=responses)
    assert result == {
        "season": "monitoring",
        "event_date": GOLDEN_EVENT,
        "alerted_windows": [24],
        "telegram_offset": 10,
    }
    assert original == [24]
    if "callback_query" in update:
        answers = _answer_calls(calls)
        assert len(answers) == 1
        assert answers[0]["payload"] == {"callback_query_id": "cb-foreign"}
    else:
        assert _answer_calls(calls) == []


def test_empty_poll_leaves_fields_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    result, original, calls = _apply(
        monkeypatch,
        responses=[_ok([])],
        telegram_offset=7,
    )
    assert result == {
        "season": "monitoring",
        "event_date": GOLDEN_EVENT,
        "alerted_windows": [24],
        "telegram_offset": 7,
    }
    assert original == [24]
    assert len(calls) == 1
    assert _answer_calls(calls) == []
    query = urllib.parse.parse_qs(urllib.parse.urlparse(str(calls[0]["url"])).query)
    assert query["offset"] == ["8"]
    assert query["timeout"] == ["0"]


@pytest.mark.parametrize(
    "updates",
    [
        [_command(10, "/in"), _command(12, "/out")],
        [_command(12, "/out"), _command(10, "/in")],
    ],
    ids=["in-then-out", "out-before-in"],
)
def test_last_wins_in_then_out(
    monkeypatch: pytest.MonkeyPatch,
    updates: list[dict[str, object]],
) -> None:
    result, original, _calls = _apply(
        monkeypatch,
        responses=[_ok(updates)],
    )
    assert result == {
        "season": "monitoring",
        "event_date": None,
        "alerted_windows": [],
        "telegram_offset": 12,
    }
    assert original == [24]


@pytest.mark.parametrize(
    "error",
    [
        _http_error(500),
        _http_error(429),
        _http_error(400),
        TimeoutError(),
        urllib.error.URLError("connection refused"),
    ],
)
def test_getupdates_http_failures_raise_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    windows = [24]
    calls = _install_urlopen(monkeypatch, [error])
    with pytest.raises(TelegramAckInboxError) as caught:
        apply_telegram_acks(
            inbox=TelegramAckInbox(token=TOKEN, chat_id=CHAT_ID),
            season="monitoring",
            event_date=GOLDEN_EVENT,
            alerted_windows=windows,
            telegram_offset=0,
        )
    assert windows == [24]
    assert caught.value.__cause__ is None
    assert TOKEN not in str(caught.value)
    assert len(calls) == 1
    assert _answer_calls(calls) == []


def test_getupdates_ok_false_raises_without_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    windows = [24]
    _install_urlopen(
        monkeypatch,
        [json.dumps({"ok": False, "description": "conflict"}).encode("utf-8")],
    )
    with pytest.raises(TelegramAckInboxError) as caught:
        apply_telegram_acks(
            inbox=TelegramAckInbox(token=TOKEN, chat_id=CHAT_ID),
            season="monitoring",
            event_date=GOLDEN_EVENT,
            alerted_windows=windows,
            telegram_offset=0,
        )
    assert windows == [24]
    assert caught.value.__cause__ is None
    assert TOKEN not in str(caught.value)


def test_getupdates_bad_json_raises_without_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    windows = [24]
    _install_urlopen(monkeypatch, [b"not-json"])
    with pytest.raises(TelegramAckInboxError) as caught:
        apply_telegram_acks(
            inbox=TelegramAckInbox(token=TOKEN, chat_id=CHAT_ID),
            season="monitoring",
            event_date=GOLDEN_EVENT,
            alerted_windows=windows,
            telegram_offset=0,
        )
    assert windows == [24]
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "error",
    [
        _http_error(500, "answerCallbackQuery"),
        _http_error(429, "answerCallbackQuery"),
        TimeoutError(),
        urllib.error.URLError("connection refused"),
        json.dumps({"ok": False, "description": "query is too old"}).encode("utf-8"),
        b"not-json",
    ],
)
def test_answer_callback_failures_raise_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    error: bytes | BaseException,
) -> None:
    windows = [24]
    _install_urlopen(monkeypatch, [_ok([_callback(10, "plants_in")]), error])
    with pytest.raises(TelegramAckInboxError) as caught:
        apply_telegram_acks(
            inbox=TelegramAckInbox(token=TOKEN, chat_id=CHAT_ID),
            season="monitoring",
            event_date=GOLDEN_EVENT,
            alerted_windows=windows,
            telegram_offset=0,
        )
    assert windows == [24]
    assert caught.value.__cause__ is None
    assert TOKEN not in str(caught.value)


def test_in_at_bot_is_a_command(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _original, _calls = _apply(
        monkeypatch,
        responses=[_ok([_command(10, "/in@FrostAlertBot extra")])],
    )
    assert result["season"] == "suspended"
    assert result["event_date"] == GOLDEN_EVENT
    assert result["alerted_windows"] == [24]
    assert result["telegram_offset"] == 10


def test_unknown_update_advances_offset_without_flip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, original, calls = _apply(
        monkeypatch,
        responses=[
            _ok(
                [
                    {
                        "update_id": 15,
                        "message": {"chat": {"id": int(CHAT_ID)}, "text": "/help"},
                    }
                ]
            )
        ],
    )
    assert result == {
        "season": "monitoring",
        "event_date": GOLDEN_EVENT,
        "alerted_windows": [24],
        "telegram_offset": 15,
    }
    assert original == [24]
    assert _answer_calls(calls) == []


def test_apply_intent_in_and_out_are_pure() -> None:
    windows = [24]
    season, event_date, next_windows = apply_intent(
        "monitoring", GOLDEN_EVENT, windows, "in"
    )
    assert season == "suspended"
    assert event_date == GOLDEN_EVENT
    assert next_windows == [24]
    assert windows == [24]
    season, event_date, cleared = apply_intent(
        "suspended", GOLDEN_EVENT, windows, "out"
    )
    assert season == "monitoring"
    assert event_date is None
    assert cleared == []
    assert windows == [24]
    season, event_date, still = apply_intent(
        "suspended", GOLDEN_EVENT, windows, "in"
    )
    assert (season, event_date, still) == ("suspended", GOLDEN_EVENT, [24])


def test_composer_last_wins_and_empty_poll_via_fake_inbox() -> None:
    last = apply_telegram_acks(
        inbox=FakeAckInbox(intents=["in", "out"], new_offset=12),
        season="monitoring",
        event_date=GOLDEN_EVENT,
        alerted_windows=[24],
        telegram_offset=0,
    )
    assert last == {
        "season": "monitoring",
        "event_date": None,
        "alerted_windows": [],
        "telegram_offset": 12,
    }
    empty = apply_telegram_acks(
        inbox=FakeAckInbox(intents=[], new_offset=None),
        season="suspended",
        event_date=GOLDEN_EVENT,
        alerted_windows=[24, 12],
        telegram_offset=4,
    )
    assert empty == {
        "season": "suspended",
        "event_date": GOLDEN_EVENT,
        "alerted_windows": [24, 12],
        "telegram_offset": 4,
    }


def test_composer_raise_does_not_invent_persist() -> None:
    windows = [24]
    inbox = FakeAckInbox(error=TelegramAckInboxError("telegram poll failed"))
    with pytest.raises(TelegramAckInboxError):
        apply_telegram_acks(
            inbox=inbox,
            season="monitoring",
            event_date=GOLDEN_EVENT,
            alerted_windows=windows,
            telegram_offset=0,
        )
    assert windows == [24]
    assert inbox.polls == [0]
    source = (ROOT / "src" / "frost_alert" / "apply_season.py").read_text(encoding="utf-8")
    assert "StateStore" not in source
    assert "state.json" not in source


def test_setup_has_no_season_command() -> None:
    assert main(["in"]) != 0
    assert main(["out"]) != 0
    source = (ROOT / "src" / "frost_alert" / "entrypoints" / "setup.py").read_text(
        encoding="utf-8"
    )
    assert "season" not in source
    assert "/in" not in source
    assert "/out" not in source
    assert "plants_in" not in source
    assert "plants_out" not in source
