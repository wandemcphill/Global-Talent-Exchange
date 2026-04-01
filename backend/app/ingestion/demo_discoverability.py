from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Sequence

CANONICAL_DEMO_PLAYER_COUNT = 120
CANONICAL_INITIAL_VISIBLE_PLAYERS = 100
CANONICAL_LIQUID_PLAYER_COUNT = 30
CANONICAL_ILLIQUID_PLAYER_COUNT = 60

PRICE_QUANTUM = Decimal("0.0001")
EUR_QUANTUM = Decimal("0.01")
MOVEMENT_PATTERN = (
    Decimal("0.1200"),
    Decimal("0.0800"),
    Decimal("0.0500"),
    Decimal("-0.0500"),
    Decimal("-0.0800"),
    Decimal("-0.1200"),
)


@dataclass(frozen=True, slots=True)
class DemoSupplyBand:
    code: str
    name: str
    rank: int
    market_value_min_eur: Decimal
    market_value_max_eur: Decimal
    current_value_min_credits: Decimal
    current_value_max_credits: Decimal
    circulating_supply: int
    target_share: Decimal
    holder_count_base: int
    watchlist_base: int
    display_label: str

    @property
    def daily_pack_supply(self) -> int:
        return max(1, self.circulating_supply // 200)

    @property
    def season_mint_cap(self) -> int:
        return self.circulating_supply


@dataclass(frozen=True, slots=True)
class CanonicalDemoPlayerProfile:
    player_id: str
    band: DemoSupplyBand
    market_value_eur: Decimal
    previous_credits: Decimal
    current_credits: Decimal
    movement_pct: Decimal
    holder_count_score: int
    watchlist_score: int

    @property
    def trend_state(self) -> str:
        return "rising" if self.movement_pct > 0 else "falling" if self.movement_pct < 0 else "flat"


@dataclass(frozen=True, slots=True)
class CanonicalDemoSeedPlan:
    player_profiles: tuple[CanonicalDemoPlayerProfile, ...]
    band_counts: dict[str, int]

    def profile_by_player_id(self) -> dict[str, CanonicalDemoPlayerProfile]:
        return {profile.player_id: profile for profile in self.player_profiles}

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_count": len(self.player_profiles),
            "visible_player_target": min(CANONICAL_INITIAL_VISIBLE_PLAYERS, len(self.player_profiles)),
            "seeded_liquidity_target": min(
                CANONICAL_LIQUID_PLAYER_COUNT + CANONICAL_ILLIQUID_PLAYER_COUNT,
                len(self.player_profiles),
            ),
            "band_counts": dict(self.band_counts),
            "bands": [
                {
                    "code": band.code,
                    "name": band.name,
                    "display_label": band.display_label,
                    "market_value_min_eur": float(band.market_value_min_eur),
                    "market_value_max_eur": float(band.market_value_max_eur),
                    "current_value_min_credits": float(band.current_value_min_credits),
                    "current_value_max_credits": float(band.current_value_max_credits),
                    "circulating_supply": band.circulating_supply,
                }
                for band in DEMO_SUPPLY_BANDS
            ],
        }


DEMO_SUPPLY_BANDS: tuple[DemoSupplyBand, ...] = (
    DemoSupplyBand(
        code="band_a",
        name="Band A",
        rank=1,
        market_value_min_eur=Decimal("100000"),
        market_value_max_eur=Decimal("1000000"),
        current_value_min_credits=Decimal("0.0800"),
        current_value_max_credits=Decimal("0.4500"),
        circulating_supply=10_000,
        target_share=Decimal("0.3750"),
        holder_count_base=72,
        watchlist_base=18,
        display_label="EUR 0.1m to EUR 1m | 0.08 to 0.45 GTEX | 10,000 copies",
    ),
    DemoSupplyBand(
        code="band_b",
        name="Band B",
        rank=2,
        market_value_min_eur=Decimal("1000000"),
        market_value_max_eur=Decimal("5000000"),
        current_value_min_credits=Decimal("0.4500"),
        current_value_max_credits=Decimal("2.5000"),
        circulating_supply=1_000,
        target_share=Decimal("0.3333"),
        holder_count_base=56,
        watchlist_base=16,
        display_label="EUR 1m to EUR 5m | 0.45 to 2.5 GTEX | 1,000 copies",
    ),
    DemoSupplyBand(
        code="band_c",
        name="Band C",
        rank=3,
        market_value_min_eur=Decimal("5000000"),
        market_value_max_eur=Decimal("20000000"),
        current_value_min_credits=Decimal("2.5000"),
        current_value_max_credits=Decimal("12.0000"),
        circulating_supply=300,
        target_share=Decimal("0.1667"),
        holder_count_base=42,
        watchlist_base=12,
        display_label="EUR 5m to EUR 20m | 2.5 to 12 GTEX | 300 copies",
    ),
    DemoSupplyBand(
        code="band_d",
        name="Band D",
        rank=4,
        market_value_min_eur=Decimal("20000000"),
        market_value_max_eur=Decimal("60000000"),
        current_value_min_credits=Decimal("12.0000"),
        current_value_max_credits=Decimal("50.0000"),
        circulating_supply=10,
        target_share=Decimal("0.0833"),
        holder_count_base=30,
        watchlist_base=10,
        display_label="EUR 20m to EUR 60m | 12 to 50 GTEX | 10 copies",
    ),
    DemoSupplyBand(
        code="band_e",
        name="Band E",
        rank=5,
        market_value_min_eur=Decimal("60000000"),
        market_value_max_eur=Decimal("125000000"),
        current_value_min_credits=Decimal("50.0000"),
        current_value_max_credits=Decimal("75.0000"),
        circulating_supply=5,
        target_share=Decimal("0.0417"),
        holder_count_base=22,
        watchlist_base=8,
        display_label="EUR 60m to EUR 100m+ | 50 to 75 GTEX | 5 copies",
    ),
)


def build_canonical_demo_seed_plan(
    player_ids: Sequence[str],
    *,
    random_seed: int,
) -> CanonicalDemoSeedPlan:
    ordered_player_ids = tuple(player_ids)
    band_counts = canonical_band_counts_for_player_count(len(ordered_player_ids))
    profiles: list[CanonicalDemoPlayerProfile] = []
    cursor = 0
    for band in DEMO_SUPPLY_BANDS:
        count = band_counts.get(band.code, 0)
        band_player_ids = ordered_player_ids[cursor:cursor + count]
        cursor += count
        for index, player_id in enumerate(band_player_ids):
            sequence_position = index + 1
            market_value_eur = _interpolate_decimal(
                band.market_value_min_eur,
                band.market_value_max_eur,
                position=sequence_position,
                total=len(band_player_ids),
                quantum=EUR_QUANTUM,
            )
            current_credits = _interpolate_decimal(
                band.current_value_min_credits,
                band.current_value_max_credits,
                position=sequence_position,
                total=len(band_player_ids),
                quantum=PRICE_QUANTUM,
            )
            movement_template = MOVEMENT_PATTERN[
                (random_seed + band.rank + sequence_position) % len(MOVEMENT_PATTERN)
            ]
            previous_credits = _clamp_decimal(
                current_credits / (Decimal("1.0000") + movement_template),
                band.current_value_min_credits,
                band.current_value_max_credits,
            ).quantize(PRICE_QUANTUM, rounding=ROUND_HALF_UP)
            movement_pct = Decimal("0.0000")
            if previous_credits > 0:
                movement_pct = (
                    (current_credits - previous_credits) / previous_credits
                ).quantize(PRICE_QUANTUM, rounding=ROUND_HALF_UP)
            profiles.append(
                CanonicalDemoPlayerProfile(
                    player_id=player_id,
                    band=band,
                    market_value_eur=market_value_eur,
                    previous_credits=previous_credits,
                    current_credits=current_credits,
                    movement_pct=movement_pct,
                    holder_count_score=band.holder_count_base + ((sequence_position + band.rank) % 14),
                    watchlist_score=band.watchlist_base + ((sequence_position * 2 + band.rank) % 9),
                )
            )
    return CanonicalDemoSeedPlan(
        player_profiles=tuple(profiles),
        band_counts=band_counts,
    )


def canonical_band_counts_for_player_count(player_count: int) -> dict[str, int]:
    if player_count <= 0:
        return {band.code: 0 for band in DEMO_SUPPLY_BANDS}

    exact_counts = {
        band.code: band.target_share * Decimal(player_count)
        for band in DEMO_SUPPLY_BANDS
    }
    counts = {
        band.code: int(exact_counts[band.code].to_integral_value(rounding="ROUND_FLOOR"))
        for band in DEMO_SUPPLY_BANDS
    }
    assigned = sum(counts.values())
    remaining = player_count - assigned
    ranked_remainders = sorted(
        DEMO_SUPPLY_BANDS,
        key=lambda band: (
            exact_counts[band.code] - Decimal(counts[band.code]),
            band.target_share,
            -band.rank,
        ),
        reverse=True,
    )
    for offset in range(remaining):
        counts[ranked_remainders[offset % len(ranked_remainders)].code] += 1

    if player_count >= len(DEMO_SUPPLY_BANDS):
        zero_bands = [band for band in DEMO_SUPPLY_BANDS if counts[band.code] == 0]
        donors = sorted(
            DEMO_SUPPLY_BANDS,
            key=lambda band: (counts[band.code], band.target_share, -band.rank),
            reverse=True,
        )
        for zero_band in zero_bands:
            donor = next((band for band in donors if counts[band.code] > 1), None)
            if donor is None:
                break
            counts[donor.code] -= 1
            counts[zero_band.code] += 1

    return counts


def liquidity_band_code_for_market_value_eur(value: Decimal) -> str:
    credits = value / Decimal("100000")
    if credits < Decimal("50"):
        return "entry"
    if credits < Decimal("150"):
        return "growth"
    if credits < Decimal("400"):
        return "premium"
    if credits < Decimal("1000"):
        return "bluechip"
    return "marquee"


def _interpolate_decimal(
    minimum: Decimal,
    maximum: Decimal,
    *,
    position: int,
    total: int,
    quantum: Decimal,
) -> Decimal:
    if total <= 1:
        ratio = Decimal("0.5")
    else:
        ratio = Decimal(position) / Decimal(total + 1)
    return (minimum + ((maximum - minimum) * ratio)).quantize(quantum, rounding=ROUND_HALF_UP)


def _clamp_decimal(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


__all__ = [
    "CANONICAL_DEMO_PLAYER_COUNT",
    "CANONICAL_ILLIQUID_PLAYER_COUNT",
    "CANONICAL_INITIAL_VISIBLE_PLAYERS",
    "CANONICAL_LIQUID_PLAYER_COUNT",
    "CanonicalDemoPlayerProfile",
    "CanonicalDemoSeedPlan",
    "DEMO_SUPPLY_BANDS",
    "DemoSupplyBand",
    "build_canonical_demo_seed_plan",
    "canonical_band_counts_for_player_count",
    "liquidity_band_code_for_market_value_eur",
]
