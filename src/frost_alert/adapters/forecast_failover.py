from __future__ import annotations

import urllib.error

from frost_alert.domain.classify import ForecastHour
from frost_alert.ports import ForecastSource


class FailoverForecast:
    def __init__(self, primary: ForecastSource, fallback: ForecastSource) -> None:
        self._primary = primary
        self._fallback = fallback

    def fetch(self, *, lat: float, lon: float) -> list[ForecastHour]:
        try:
            return self._primary.fetch(lat=lat, lon=lon)
        except Exception as err:
            if _is_client_error_without_failover(err):
                raise
            return self._fallback.fetch(lat=lat, lon=lon)


def _is_client_error_without_failover(error: BaseException) -> bool:
    cause = error.__cause__
    if not isinstance(cause, urllib.error.HTTPError):
        return False
    code = cause.code
    return 400 <= code <= 499 and code != 429
