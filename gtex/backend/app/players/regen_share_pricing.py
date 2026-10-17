"""Share pricing for pre-seeded national regens: rating, upside (potential) and rarity.

Calibrated against live markets: real players sit around 0.05 GTX/share (p95 ~0.10),
so a common 70/88 regen opens near 0.026, a legendary 82/98 near 0.09.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

PRICING_MODEL = "regen_rating_potential_rarity_v1"
RARITY_MULTIPLIERS = {"common": Decimal("1.00"), "rare": Decimal("1.10"), "elite": Decimal("1.30"), "legendary": Decimal("1.75")}
MIN_PRICE = Decimal("0.0050")
MAX_PRICE = Decimal("0.2500")


def regen_share_price(rating: int | float | None, potential: int | float | None, rarity: str | None) -> Decimal:
    current = float(rating or 60)
    ceiling = max(float(potential or current), current)
    base = 0.012 * (1.06 ** (current - 60))
    upside = 1 + min(max(ceiling - current, 0.0), 30.0) * 0.012
    price = Decimal(str(base * upside)) * RARITY_MULTIPLIERS.get((rarity or "common").lower(), Decimal("1.00"))
    return min(max(price, MIN_PRICE), MAX_PRICE).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
