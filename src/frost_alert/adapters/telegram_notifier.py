from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from frost_alert.domain.classify import Classification

SEND_MESSAGE_URL = "https://api.telegram.org/bot{token}/sendMessage"
USER_AGENT = "Frost-alert (https://github.com/dabben1993/Frost-alert)"
TIMEOUT_S = 15
_ACK_BUTTON_TEXT = "Plants are in overwintering"
_ACK_CALLBACK = "plants_in"


class TelegramNotifierError(Exception):
    pass


class TelegramNotifier:
    def __init__(self, *, token: str, chat_id: str | int) -> None:
        self._token = token
        self._chat_id = chat_id

    def send_frost_alert(
        self,
        *,
        classification: Classification,
        place_name: str,
        threshold_c: int | float,
        scale: str,
        timezone: str,
    ) -> None:
        payload = {
            "chat_id": self._chat_id,
            "text": _message_text(
                classification,
                place_name=place_name,
                threshold_c=threshold_c,
                scale=scale,
                timezone=timezone,
            ),
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": _ACK_BUTTON_TEXT, "callback_data": _ACK_CALLBACK}]
                ]
            },
        }
        request = urllib.request.Request(
            SEND_MESSAGE_URL.format(token=self._token),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
            },
            method="POST",
        )
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
            raise TelegramNotifierError("telegram send failed") from None
        if not isinstance(body, dict) or body.get("ok") is not True:
            raise TelegramNotifierError("telegram send failed")


def _message_text(
    classification: Classification,
    *,
    place_name: str,
    threshold_c: int | float,
    scale: str,
    timezone: str,
) -> str:
    if classification.t is None:
        raise TelegramNotifierError("telegram send failed")
    preview = f"❄️ Frost risk in ~{classification.window}h"
    crossing = _format_temp(classification.temp_c, scale)
    threshold = _format_temp(threshold_c, scale)
    when = _local_stamp(classification.t, timezone)
    body = f"{place_name}\n{crossing} at {when} (threshold {threshold})"
    return f"{preview}\n{body}"


def _local_stamp(moment: datetime, timezone: str) -> str:
    return moment.astimezone(ZoneInfo(timezone)).strftime("%Y-%m-%d %H:%M")


def _format_temp(temp_c: int | float | None, scale: str) -> str:
    if temp_c is None:
        raise TelegramNotifierError("telegram send failed")
    if scale == "F":
        value = temp_c * 9 / 5 + 32
        unit = "F"
    else:
        value = temp_c
        unit = "C"
    rounded = round(float(value), 1)
    if rounded == int(rounded):
        number = str(int(rounded))
    else:
        number = f"{rounded:.1f}"
    return f"{number}°{unit}"
