from __future__ import annotations

import sys
from collections.abc import Sequence

from frost_alert.adapters.json_config_store import JsonConfigStore
from frost_alert.domain.scale_threshold import InvalidSetupInput, resolve_scale_and_threshold
from frost_alert.ports import ConfigStore

USAGE = "Usage: frost-alert setup"


def main(
    argv: Sequence[str] | None = None,
    *,
    config_store: ConfigStore | None = None,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["setup"]:
        print(USAGE, file=sys.stderr)
        return 1

    scale_raw = input("Temperature scale (C or F) [C]: ")
    threshold_raw = input("Frost threshold in that scale [3 when C]: ")

    try:
        result = resolve_scale_and_threshold(scale_raw, threshold_raw)
    except InvalidSetupInput as exc:
        print(exc, file=sys.stderr)
        return 1

    store = JsonConfigStore() if config_store is None else config_store
    store.write_scale_and_threshold(result.scale, result.threshold_c)
    return 0
