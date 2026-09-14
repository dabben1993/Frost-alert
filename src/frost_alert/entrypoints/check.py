from __future__ import annotations

import json
import os
from collections.abc import Sequence

from frost_alert.adapters.json_config_store import JsonConfigStore
from frost_alert.adapters.json_state_store import JsonStateStore
from frost_alert.adapters.open_meteo_forecast import OpenMeteoForecast
from frost_alert.adapters.system_clock import SystemClock
from frost_alert.adapters.telegram_ack_inbox import TelegramAckInbox
from frost_alert.adapters.telegram_notifier import TelegramNotifier
from frost_alert.check_tick import run_check_tick
from frost_alert.ports import AckInbox, Clock, ConfigStore, ForecastSource, Notifier, StateStore


def main(
    argv: Sequence[str] | None = None,
    *,
    config_store: ConfigStore | None = None,
    state_store: StateStore | None = None,
    forecast: ForecastSource | None = None,
    notifier: Notifier | None = None,
    inbox: AckInbox | None = None,
    clock: Clock | None = None,
) -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id or not token.strip() or not chat_id.strip():
        return 1

    store = JsonConfigStore() if config_store is None else config_store
    persist = JsonStateStore() if state_store is None else state_store
    try:
        config = store.load()
        state = persist.load()
    except (FileNotFoundError, OSError, json.JSONDecodeError, UnicodeDecodeError):
        return 1
    source = OpenMeteoForecast() if forecast is None else forecast
    sender = (
        TelegramNotifier(token=token, chat_id=chat_id)
        if notifier is None
        else notifier
    )
    ack_inbox = (
        TelegramAckInbox(token=token, chat_id=chat_id) if inbox is None else inbox
    )
    time_source = SystemClock() if clock is None else clock
    try:
        result = run_check_tick(
            forecast=source,
            notifier=sender,
            inbox=ack_inbox,
            clock=time_source,
            config=config,
            state=state,
        )
    except Exception:
        return 1

    event_date = result["event_date"]
    windows = result["alerted_windows"]
    marked = [int(window) for window in windows] if isinstance(windows, list) else []
    persist.write(
        season=str(result["season"]),
        event_date=event_date if isinstance(event_date, str) else None,
        alerted_windows=marked,
        telegram_offset=int(result["telegram_offset"]),
    )
    return 0
