from __future__ import annotations

from frost_alert.apply_season import apply_telegram_acks
from frost_alert.domain.classify import classify
from frost_alert.ports import AckInbox, Clock, ForecastSource, Notifier
from frost_alert.send_frost_alert import maybe_send_frost_alert


def run_check_tick(
    *,
    forecast: ForecastSource,
    notifier: Notifier,
    inbox: AckInbox,
    clock: Clock,
    config: dict,
    state: dict[str, object],
) -> dict[str, object]:
    season = str(state["season"])
    stored_event = state["event_date"]
    event_date = stored_event if isinstance(stored_event, str) else None
    stored_windows = state["alerted_windows"]
    windows = [int(window) for window in stored_windows] if isinstance(stored_windows, list) else []
    offset = int(state["telegram_offset"])

    if season == "monitoring":
        series = forecast.fetch(lat=float(config["lat"]), lon=float(config["lon"]))
        classification = classify(
            series,
            config["threshold_c"],
            clock.now(),
            str(config["timezone"]),
        )
        if (
            classification.event_date is not None
            and classification.event_date != event_date
        ):
            windows = []
        if classification.event_date is not None:
            event_date = classification.event_date
        try:
            windows = maybe_send_frost_alert(
                notifier=notifier,
                classification=classification,
                alerted_windows=windows,
                place_name=str(config["place_name"]),
                threshold_c=config["threshold_c"],
                scale=str(config["scale"]),
                timezone=str(config["timezone"]),
            )
        except Exception:
            pass

    return apply_telegram_acks(
        inbox=inbox,
        season=season,
        event_date=event_date,
        alerted_windows=windows,
        telegram_offset=offset,
    )
