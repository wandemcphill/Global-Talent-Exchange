from __future__ import annotations


def resolve_seeded_score(home_power: int, away_power: int, *, allow_draw: bool) -> tuple[int, int, str | None]:
    difference = home_power - away_power

    if abs(difference) <= 4:
        if allow_draw:
            return 1, 1, None
        return 1, 1, "penalties"

    if difference > 0:
        if difference >= 12:
            return 3, 0, None
        return 2, 1, None

    if difference <= -12:
        return 0, 3, None
    return 1, 2, None
