from __future__ import annotations

import urllib.request

from frost_alert.adapters.http import TIMEOUT_S, USER_AGENT


class HealthchecksWatchdog:
    def __init__(self, url: str) -> None:
        self._url = url

    def ping(self) -> None:
        target = self._url.strip()
        if not target:
            return
        request = urllib.request.Request(
            target,
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            response.read()
