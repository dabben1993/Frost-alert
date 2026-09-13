from typing import Protocol

from frost_alert.domain.classify import ForecastHour


class ForecastSource(Protocol):
    def fetch(self, *, lat: float, lon: float) -> list[ForecastHour]: ...


class Notifier(Protocol):
    pass


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
