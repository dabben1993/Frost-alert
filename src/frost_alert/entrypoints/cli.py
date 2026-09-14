from __future__ import annotations

import sys
from collections.abc import Sequence

from frost_alert.entrypoints.check import main as check_main
from frost_alert.entrypoints.setup import main as setup_main

USAGE = "Usage: frost-alert setup|check"


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["setup"]:
        return setup_main(args)
    if args[:1] == ["check"]:
        return check_main(args)
    print(USAGE, file=sys.stderr)
    return 1
