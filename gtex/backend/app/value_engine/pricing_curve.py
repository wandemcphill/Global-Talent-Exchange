from __future__ import annotations

GTEX_PRICE_ANCHORS_MILLIONS: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (0.1, 0.08),
    (0.25, 0.12),
    (0.5, 0.20),
    (1.0, 0.45),
    (2.0, 1.0),
    (3.0, 1.5),
    (5.0, 2.5),
    (7.5, 3.75),
    (10.0, 5.0),
    (15.0, 8.0),
    (20.0, 12.0),
    (30.0, 20.0),
    (40.0, 30.0),
    (50.0, 40.0),
    (60.0, 50.0),
    (70.0, 58.0),
    (80.0, 65.0),
    (90.0, 70.0),
    (100.0, 75.0),
)


def interpolate_gtex_price_from_eur_value(real_world_value_eur: float) -> float:
    if real_world_value_eur <= 0:
        return 0.0

    value_millions = float(real_world_value_eur) / 1_000_000.0
    lower_anchor = GTEX_PRICE_ANCHORS_MILLIONS[0]
    for upper_anchor in GTEX_PRICE_ANCHORS_MILLIONS[1:]:
        if value_millions > upper_anchor[0]:
            lower_anchor = upper_anchor
            continue
        return round(
            _interpolate(
                lower_anchor[0],
                lower_anchor[1],
                upper_anchor[0],
                upper_anchor[1],
                value_millions,
            ),
            4,
        )
    return GTEX_PRICE_ANCHORS_MILLIONS[-1][1]


def round_gtex_display_value(value: float | None) -> float | None:
    if value is None:
        return None

    sign = -1.0 if value < 0 else 1.0
    magnitude = abs(float(value))
    if magnitude < 1.0:
        rounded = round(magnitude, 2)
    elif magnitude <= 10.0:
        rounded = round(magnitude, 1)
    else:
        rounded = round(magnitude * 2.0) / 2.0
    return round(sign * rounded, 2)


def _interpolate(x0: float, y0: float, x1: float, y1: float, x: float) -> float:
    if x1 <= x0:
        return y1
    ratio = (x - x0) / (x1 - x0)
    return y0 + ((y1 - y0) * ratio)
