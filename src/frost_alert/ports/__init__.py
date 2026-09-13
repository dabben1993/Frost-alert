from typing import Protocol


class ForecastSource(Protocol):
    pass


class Notifier(Protocol):
    pass


class AckInbox(Protocol):
    pass


class Watchdog(Protocol):
    pass


class ConfigStore(Protocol):
    def write_scale_and_threshold(self, scale: str, threshold_c: float) -> None: ...


class StateStore(Protocol):
    pass


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
