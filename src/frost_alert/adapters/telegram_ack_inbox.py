from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

GET_UPDATES_URL = "https://api.telegram.org/bot{token}/getUpdates"
ANSWER_CALLBACK_URL = "https://api.telegram.org/bot{token}/answerCallbackQuery"
USER_AGENT = "Frost-alert (https://github.com/dabben1993/Frost-alert)"
TIMEOUT_S = 15
_COMMAND = re.compile(r"^/(in|out)(@\S+)?$")


class TelegramAckInboxError(Exception):
    pass


class TelegramAckInbox:
    def __init__(self, *, token: str, chat_id: str | int) -> None:
        self._token = token
        self._chat_id = str(chat_id)

    def poll(self, *, telegram_offset: int) -> tuple[list[str], int]:
        updates = self._get_updates(telegram_offset)
        for update in updates:
            callback = update.get("callback_query")
            if isinstance(callback, dict):
                self._answer_callback(callback)
        intents = [_intent_for(update, self._chat_id) for update in updates]
        filtered = [intent for intent in intents if intent is not None]
        ids = [
            update_id
            for update in updates
            if isinstance(update_id := update.get("update_id"), int)
        ]
        new_offset = max(ids) if ids else telegram_offset
        return filtered, new_offset

    def _get_updates(self, telegram_offset: int) -> list[dict[str, object]]:
        query = urllib.parse.urlencode(
            {"offset": telegram_offset + 1, "timeout": 0}
        )
        request = urllib.request.Request(
            f"{GET_UPDATES_URL.format(token=self._token)}?{query}",
            headers={"User-Agent": USER_AGENT},
            method="GET",
        )
        body = _read_ok_json(request)
        result = body.get("result")
        if not isinstance(result, list):
            raise TelegramAckInboxError("telegram poll failed")
        updates: list[dict[str, object]] = []
        for item in result:
            if isinstance(item, dict):
                updates.append(item)
        updates.sort(key=_update_id_sort)
        return updates

    def _answer_callback(self, callback: dict[str, object]) -> None:
        callback_id = callback.get("id")
        if not isinstance(callback_id, str) or callback_id == "":
            raise TelegramAckInboxError("telegram poll failed")
        payload = {"callback_query_id": callback_id}
        request = urllib.request.Request(
            ANSWER_CALLBACK_URL.format(token=self._token),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        _read_ok_json(request)


def _read_ok_json(request: urllib.request.Request) -> dict[str, object]:
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            raw = response.read().decode("utf-8")
        body = json.loads(raw)
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
        UnicodeError,
        ValueError,
    ):
        raise TelegramAckInboxError("telegram poll failed") from None
    if not isinstance(body, dict) or body.get("ok") is not True:
        raise TelegramAckInboxError("telegram poll failed")
    return body


def _update_id_sort(update: dict[str, object]) -> int:
    update_id = update.get("update_id")
    return update_id if isinstance(update_id, int) else 0


def _intent_for(update: dict[str, object], owner_chat_id: str) -> str | None:
    if _chat_id(update) != owner_chat_id:
        return None
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        data = callback.get("data")
        if data == "plants_in":
            return "in"
        if data == "plants_out":
            return "out"
        return None
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    return _command_intent(message.get("text"))


def _chat_id(update: dict[str, object]) -> str | None:
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        return _message_chat_id(callback.get("message"))
    return _message_chat_id(update.get("message"))


def _message_chat_id(message: object) -> str | None:
    if not isinstance(message, dict):
        return None
    chat = message.get("chat")
    if not isinstance(chat, dict) or "id" not in chat:
        return None
    return str(chat["id"])


def _command_intent(text: object) -> str | None:
    if not isinstance(text, str):
        return None
    parts = text.split()
    if not parts:
        return None
    match = _COMMAND.fullmatch(parts[0])
    if match is None:
        return None
    return match.group(1)
