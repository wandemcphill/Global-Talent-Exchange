from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

DEFAULT_SEASON_DURATION_DAYS = 30
DEFAULT_SOFT_RESET_FACTOR = 0.5
DEFAULT_REWARD_BOARD = "global"


@dataclass(frozen=True, slots=True)
class RankTierDefinition:
    key: str
    label: str
    min_rating: int


DEFAULT_RANK_TIERS: tuple[RankTierDefinition, ...] = (
    RankTierDefinition(key="legend", label="Legend", min_rating=1700),
    RankTierDefinition(key="elite", label="Elite", min_rating=1500),
    RankTierDefinition(key="gold", label="Gold", min_rating=1300),
    RankTierDefinition(key="silver", label="Silver", min_rating=1125),
    RankTierDefinition(key="bronze", label="Bronze", min_rating=0),
)


@dataclass(frozen=True, slots=True)
class SeasonRewardTier:
    rank_position: int
    title: str
    coins: Decimal
    trophies: int
    badges: tuple[str, ...]
    visibility_boost: int = 0
    exclusive_tournament_key: str | None = None


DEFAULT_REWARD_TIERS: tuple[SeasonRewardTier, ...] = (
    SeasonRewardTier(
        rank_position=1,
        title="Champion",
        coins=Decimal("1000.0000"),
        trophies=3,
        badges=("season_champion",),
        visibility_boost=30,
        exclusive_tournament_key="legend-invitational",
    ),
    SeasonRewardTier(
        rank_position=2,
        title="Finalist",
        coins=Decimal("500.0000"),
        trophies=2,
        badges=("season_finalist",),
        visibility_boost=20,
        exclusive_tournament_key="elite-showcase",
    ),
    SeasonRewardTier(
        rank_position=3,
        title="Podium",
        coins=Decimal("250.0000"),
        trophies=1,
        badges=("season_podium",),
        visibility_boost=15,
        exclusive_tournament_key="elite-showcase",
    ),
    SeasonRewardTier(
        rank_position=4,
        title="Top Four",
        coins=Decimal("125.0000"),
        trophies=1,
        badges=("season_top_four",),
        visibility_boost=10,
    ),
    SeasonRewardTier(
        rank_position=5,
        title="Top Five",
        coins=Decimal("75.0000"),
        trophies=0,
        badges=("season_top_five",),
        visibility_boost=5,
    ),
)


def rank_tier_for_rating(rating: int | float) -> RankTierDefinition:
    resolved_rating = int(round(float(rating)))
    for tier in DEFAULT_RANK_TIERS:
        if resolved_rating >= tier.min_rating:
            return tier
    return DEFAULT_RANK_TIERS[-1]


def reward_tier_for_rank(rank_position: int) -> SeasonRewardTier | None:
    for tier in DEFAULT_REWARD_TIERS:
        if tier.rank_position == int(rank_position):
            return tier
    return None


def serialize_rank_tier(tier: RankTierDefinition) -> dict[str, Any]:
    return {
        "key": tier.key,
        "label": tier.label,
        "min_rating": tier.min_rating,
    }


def serialize_reward_tier(tier: SeasonRewardTier) -> dict[str, Any]:
    return {
        "rank_position": tier.rank_position,
        "title": tier.title,
        "coins": str(tier.coins),
        "trophies": tier.trophies,
        "badges": list(tier.badges),
        "visibility_boost": tier.visibility_boost,
        "exclusive_tournament_key": tier.exclusive_tournament_key,
    }


def carry_over_player_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(metadata or {})
    reward_entitlements = payload.get("reward_entitlements")
    if isinstance(reward_entitlements, dict) and reward_entitlements:
        return {"reward_entitlements": dict(reward_entitlements)}
    return {}


__all__ = [
    "DEFAULT_RANK_TIERS",
    "DEFAULT_REWARD_BOARD",
    "DEFAULT_REWARD_TIERS",
    "DEFAULT_SEASON_DURATION_DAYS",
    "DEFAULT_SOFT_RESET_FACTOR",
    "RankTierDefinition",
    "SeasonRewardTier",
    "carry_over_player_metadata",
    "rank_tier_for_rating",
    "reward_tier_for_rank",
    "serialize_rank_tier",
    "serialize_reward_tier",
]
