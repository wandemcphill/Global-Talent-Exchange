from __future__ import annotations

"""Banded GSI pricing + potential-driven appreciation (feed-free).

Canonical home for the frozen launch pricing and the appreciation curve. Both the
import/seed/reprice scripts and the admin player editor import from here.

Each player's credit price = its tier band floor plus a composite of GSI (60%),
age (20%), and team factor (20%), placing it inside the band. 1 credit = ₦90.
Effective GSI grows from ingest `overall` toward `potential` as the player ages
(young players appreciate); it never auto-declines (veteran decline is a manual
admin re-rate, not an automatic tier crash).

Founder bands (₦): prospect floor 660, squad 900, solid 1,320, quality 2,120,
top_class 4,100–6,000, world_class 7,400–9,000.
"""

from dataclasses import dataclass
from datetime import date

NAIRA_PER_CREDIT = 90.0
# 1 GTEX Coin = ₦100 = 100 Fan Coin (wallet ledger rate). Player value is denominated
# in credits (₦90 each); trading happens in GTEX Coin (₦100 each). A player's full
# share float is worth its banded credit value, so display value and tradeable price
# agree: total_coin_value = value_credits * CREDIT_TO_COIN; per-share = that / shares.
NAIRA_PER_COIN = 100.0
CREDIT_TO_COIN = NAIRA_PER_CREDIT / NAIRA_PER_COIN  # 0.9 coin per credit

# The SoFIFA snapshot the ratings were captured at (CSV: 2025-06-03). Effective GSI
# grows from a player's age at this date toward potential. Shared by the importer's
# launch pricing and the appreciation scheduler so they agree from day one.
SOFIFA_SNAPSHOT_DATE = date(2025, 6, 3)

# Composite weights (founder-approved): GSI 60 / age 20 / team 20.
W_GSI = 0.60
W_AGE = 0.20
W_TEAM = 0.20


@dataclass(frozen=True, slots=True)
class PriceTier:
    code: str
    min_overall: int  # inclusive lower bound of the tier's GSI range
    overall_span: int  # width used to normalise GSI within the tier
    band_min_naira: float
    band_max_naira: float

    @property
    def band_min_credits(self) -> float:
        return self.band_min_naira / NAIRA_PER_CREDIT

    @property
    def band_max_credits(self) -> float:
        return self.band_max_naira / NAIRA_PER_CREDIT


# Ordered high -> low. overall_span sets how many rating points map floor->ceiling
# of the GSI component (e.g. world_class 88..96 spans 8 points).
PRICE_TIERS: tuple[PriceTier, ...] = (
    PriceTier("world_class", 88, 8, 7_400.0, 9_000.0),
    PriceTier("top_class", 84, 4, 4_100.0, 6_000.0),
    PriceTier("quality", 80, 4, 2_120.0, 4_099.0),
    PriceTier("solid", 75, 5, 1_320.0, 2_119.0),
    PriceTier("squad", 70, 5, 900.0, 1_319.0),
    PriceTier("prospect", 0, 70, 660.0, 899.0),
)


def resolve_price_tier(overall: int | None) -> PriceTier:
    value = overall if overall is not None else 0
    for tier in PRICE_TIERS:
        if value >= tier.min_overall:
            return tier
    return PRICE_TIERS[-1]


def _clamp01(value: float) -> float:
    return 0.0 if value < 0.0 else 1.0 if value > 1.0 else value


def _gsi_score(overall: int | None, tier: PriceTier) -> float:
    if overall is None:
        return 0.0
    return _clamp01((overall - tier.min_overall) / tier.overall_span)


def _age_score(age: float | None) -> float:
    """Youth premium: full at <=21, tapering to 0 by 33. Unknown age -> mid (0.5)."""
    if age is None:
        return 0.5
    if age <= 21:
        return 1.0
    if age >= 33:
        return 0.0
    return _clamp01((33.0 - age) / (33.0 - 21.0))


def _team_score(club_rating: int | None) -> float:
    """Normalise club strength. SoFIFA club_rating ~ 60 (weak) .. 85 (elite)."""
    if club_rating is None:
        return 0.5
    return _clamp01((club_rating - 60.0) / (85.0 - 60.0))


def age_from_dob(dob: date | None, as_of: date) -> float | None:
    if dob is None:
        return None
    years = (as_of - dob).days / 365.25
    return round(years, 2) if years > 0 else None


def compute_price_credits(
    *,
    overall: int | None,
    club_rating: int | None,
    age: float | None,
) -> tuple[float, str, float]:
    """Return (price_credits, tier_code, composite_score)."""
    tier = resolve_price_tier(overall)
    composite = W_GSI * _gsi_score(overall, tier) + W_AGE * _age_score(age) + W_TEAM * _team_score(club_rating)
    span = tier.band_max_credits - tier.band_min_credits
    price = tier.band_min_credits + (composite * span)
    return round(price, 2), tier.code, round(composite, 4)


def credits_to_naira(credits: float) -> float:
    return round(credits * NAIRA_PER_CREDIT, 2)


PEAK_AGE = 25.0  # potential is fully realised by ~25


def effective_gsi(
    *,
    overall: int,
    potential: int | None,
    age_at_ingest: float,
    current_age: float,
) -> float:
    """Effective GSI at `current_age`, anchored to `overall` at `age_at_ingest`.

    Only GROWS toward potential; never auto-declines (see module docstring).
    """
    ceiling = max(potential or overall, overall)
    if current_age > age_at_ingest and ceiling > overall and age_at_ingest < PEAK_AGE:
        frac = _clamp01((current_age - age_at_ingest) / (PEAK_AGE - age_at_ingest))
        return round(overall + (ceiling - overall) * frac, 1)
    return float(overall)


def projected_price_credits(
    *,
    overall: int,
    potential: int | None,
    club_rating: int | None,
    dob: date | None,
    ingest_date: date,
    as_of: date,
) -> tuple[float, str, float]:
    """Price at `as_of`, using effective GSI grown from the ingestion snapshot.

    At ingestion (as_of == ingest_date) this equals the frozen launch price; later
    dates reflect potential-driven appreciation.
    """
    if dob is None or overall is None:
        return compute_price_credits(overall=overall, club_rating=club_rating, age=None)
    age_at_ingest = (ingest_date - dob).days / 365.25
    current_age = (as_of - dob).days / 365.25
    eff = effective_gsi(
        overall=overall,
        potential=potential,
        age_at_ingest=age_at_ingest,
        current_age=current_age,
    )
    return compute_price_credits(overall=int(round(eff)), club_rating=club_rating, age=current_age)


def _dna_int(dna: dict | None, *keys: str) -> int | None:
    if not isinstance(dna, dict):
        return None
    for key in keys:
        value = dna.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


def banded_credits_from_dna(dna: dict | None, *, dob: date | None, ingest_date: date, as_of: date) -> float | None:
    """Banded credit value from a stored dna_profile (SoFIFA real or regen), or None
    if no rating is present. Uses the same projected banded model as the display value."""
    overall = _dna_int(dna, "sofifa_overall", "overall")
    if overall is None:
        return None
    potential = _dna_int(dna, "sofifa_potential", "potential")
    club_rating = _dna_int(dna, "sofifa_club_rating")
    price, _tier, _ = projected_price_credits(
        overall=overall,
        potential=potential,
        club_rating=club_rating,
        dob=dob,
        ingest_date=ingest_date,
        as_of=as_of,
    )
    return price


def share_price_coin_from_credits(value_credits: float, total_shares: int, *, min_coin: float = 0.001) -> float:
    """Per-share GTEX Coin price so the full float equals the player's banded value:
    total_coin = value_credits * CREDIT_TO_COIN; per-share = total_coin / total_shares."""
    shares = max(int(total_shares or 1), 1)
    per_share = (value_credits * CREDIT_TO_COIN) / shares
    return round(max(per_share, min_coin), 4)
