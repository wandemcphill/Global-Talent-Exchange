"""List price for one player unit.

A 90-rated player in his positional prime costs 250 GTX. The same rating does
not mean the same price. A striker at 30 is leaving his prime. A centre-back
at 30 is inside his. Potential adds to the price only before that prime.
Recognition lifts a known player above an unknown one of the same rating, and
it does not lift a much lower rating over a higher one.

Legends are sold at their prime. Their age today does not cut the price.
"""

from __future__ import annotations

GSI_ANCHOR = 250.0
GSI_EXPONENT = 3.2
GSI_REFERENCE = 90.0
YOUTH_CAP = 1.16
DECLINE_FLOOR = 0.72

# Prime window (start age, end age) and how fast the price falls after it.
POSITION_CAREER: dict[str, tuple[float, float, float]] = {
    "GK": (29.0, 34.0, 0.025),
    "CB": (27.0, 32.0, 0.030),
    "LB": (25.0, 29.0, 0.050),
    "RB": (25.0, 29.0, 0.050),
    "LWB": (24.0, 28.0, 0.055),
    "RWB": (24.0, 28.0, 0.055),
    "FB": (25.0, 29.0, 0.050),
    "DM": (27.0, 31.0, 0.035),
    "CM": (26.0, 30.0, 0.045),
    "LM": (24.0, 28.0, 0.060),
    "RM": (24.0, 28.0, 0.060),
    "AM": (24.0, 28.0, 0.050),
    "LW": (22.0, 27.0, 0.065),
    "RW": (22.0, 27.0, 0.065),
    "ST": (24.0, 28.0, 0.060),
}

_COARSE_POSITIONS = {
    "goalkeeper": "GK",
    "keeper": "GK",
    "defender": "CB",
    "full-back": "FB",
    "fullback": "FB",
    "midfielder": "CM",
    "winger": "RW",
    "forward": "ST",
    "striker": "ST",
    "attacker": "ST",
}

# Famous players cost more than unknowns. The gap stays inside one rating point
# of the curve, so a household name does not outprice a clearly better player.
RECOGNITION = {
    "marquee": 1.08,
    "world_star": 1.08,
    "world_class": 1.05,
    "wonderkid": 1.04,
    "established": 1.00,
    "international": 1.00,
    "squad": 0.98,
    "prospect": 0.97,
    "watchlist": 0.96,
}

LEGEND_MULTIPLIER = 3.6
REGEN_MULTIPLIER = 2.0


def gsi_curve(gsi: float) -> float:
    """Real-player price at a given rating, before age, position, or fame."""
    rating = max(40.0, min(99.0, float(gsi)))
    price = GSI_ANCHOR * ((rating / GSI_REFERENCE) ** GSI_EXPONENT)
    if rating <= 70.0:
        price *= 0.40
    elif rating < 75.0:
        blend = (rating - 70.0) / 5.0
        price *= 0.40 + 0.60 * blend
    return price


def position_code(position: str | None) -> str:
    text = (position or "").strip()
    if not text:
        return "CM"
    token = text.split("/")[0].strip().upper()
    if token in POSITION_CAREER:
        return token
    coarse = text.strip().lower()
    if coarse in _COARSE_POSITIONS:
        return _COARSE_POSITIONS[coarse]
    return "CM"


def career_factor(
    *,
    age: float | None,
    position: str | None,
    current_gsi: int,
    potential_gsi: int,
    is_legend: bool,
) -> float:
    """1.0 inside the positional prime. Higher before it when growth remains. Lower after it."""
    if is_legend or age is None:
        return 1.0
    start, end, slope = POSITION_CAREER[position_code(position)]
    if age < start:
        earliness = min((start - age) / 5.0, 1.0)
        room = min(max(potential_gsi - current_gsi, 0) / 8.0, 1.0)
        return min(YOUTH_CAP, 1.0 + earliness * (0.06 + 0.20 * room))
    if age <= end:
        return 1.0
    return max(DECLINE_FLOOR, 1.0 - slope * (age - end))


def recognition_factor(tier: str | None, *, is_legend: bool) -> float:
    if is_legend:
        return 1.0
    return RECOGNITION.get((tier or "").strip().lower(), 1.0)


def acquisition_price(
    current_gsi: int,
    potential_gsi: int | None = None,
    *,
    age: float | None = None,
    position: str | None = None,
    tier: str | None = None,
    is_real: bool = True,
    is_legend: bool = False,
) -> float:
    """GTX price of one unit. Potential is never below the current rating."""
    current = max(40, min(99, int(current_gsi)))
    potential = max(current, min(99, int(potential_gsi if potential_gsi is not None else current)))
    price = gsi_curve(current)
    price *= career_factor(
        age=age,
        position=position,
        current_gsi=current,
        potential_gsi=potential,
        is_legend=is_legend,
    )
    price *= recognition_factor(tier, is_legend=is_legend)
    if is_legend:
        price *= LEGEND_MULTIPLIER
    elif not is_real:
        price *= REGEN_MULTIPLIER
    return round(max(15.0, price), 2)
