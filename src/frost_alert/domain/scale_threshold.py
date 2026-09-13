from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class InvalidSetupInput(Exception):
    """User-facing setup validation failure."""


@dataclass(frozen=True)
class ScaleAndThreshold:
    scale: str
    threshold_c: int | float


def resolve_scale_and_threshold(scale_raw: str, threshold_raw: str) -> ScaleAndThreshold:
    scale = scale_raw.strip().upper() or "C"
    if scale not in {"C", "F"}:
        raise InvalidSetupInput("Enter C or F for temperature scale.")

    text = threshold_raw.strip()
    if text == "":
        if scale == "C":
            return ScaleAndThreshold(scale="C", threshold_c=3)
        raise InvalidSetupInput(
            "Enter a number for the frost threshold in the chosen scale."
        )

    try:
        display = Decimal(text)
    except InvalidOperation as exc:
        raise InvalidSetupInput(
            "Enter a number for the frost threshold in the chosen scale."
        ) from exc

    if not display.is_finite():
        raise InvalidSetupInput(
            "Enter a number for the frost threshold in the chosen scale."
        )

    if scale == "F":
        threshold_c = (display - Decimal(32)) * Decimal(5) / Decimal(9)
    else:
        threshold_c = display

    return ScaleAndThreshold(scale=scale, threshold_c=_as_number(threshold_c))


def _as_number(value: Decimal) -> int | float:
    integral = value.to_integral_value()
    if value == integral:
        return int(integral)
    return float(value)
