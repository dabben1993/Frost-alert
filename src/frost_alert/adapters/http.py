from __future__ import annotations

import json
import urllib.request

USER_AGENT = "Frost-alert (https://github.com/dabben1993/Frost-alert)"
TIMEOUT_S = 15


def get_json(url: str) -> object:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)
