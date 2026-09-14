from typing import Protocol

from frost_alert.domain.classify import Classification, ForecastHour


class ForecastSource(Protocol):
    def fetch(self, *, lat: float, lon: float) -> list[ForecastHour]: ...


class Notifier(Protocol):
    def send_frost_alert(
        self,
        *,
        classification: Classification,
        place_name: str,
        threshold_c: int | float,
        scale: str,
        timezone: str,
    ) -> None: ...


class AckInbox(Protocol):
    pass


class Watchdog(Protocol):
    pass


class ConfigStore(Protocol):
    def write(
        self,
        *,
        place_name: str,
        lat: float,
        lon: float,
        elevation_m: float,
        timezone: str,
        threshold_c: float,
        scale: str,
    ) -> None: ...


class StateStore(Protocol):
    def load(self) -> dict[str, object]: ...


class Clock(Protocol):
    pass


__all__ = [
    "AckInbox",
    "Clock",
    "ConfigStore",
    "ForecastSource",
    "Notifier",
    "StateStore",
    "Watchdog",
]
