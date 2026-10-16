from __future__ import annotations

from dataclasses import dataclass
from math import log1p

FOLLOWED_CREATOR_BOOST = 0.25
TRENDING_FOLLOW_NETWORK_BOOST = 0.15
FOLLOWER_WEIGHT_MULTIPLIER = 0.05


@dataclass(frozen=True, slots=True)
class SocialBoostBreakdown:
    followed_boost: float = 0.0
    trending_follow_network_boost: float = 0.0
    follower_weight_boost: float = 0.0

    @property
    def total(self) -> float:
        return round(
            self.followed_boost + self.trending_follow_network_boost + self.follower_weight_boost,
            6,
        )

    @property
    def rank_score_boost(self) -> float:
        return round(self.trending_follow_network_boost + self.follower_weight_boost, 6)


@dataclass(frozen=True, slots=True)
class SocialBoostContext:
    user_id: str
    following_ids: frozenset[str]
    follower_counts: dict[str, int]
    network_popularity_counts: dict[str, int]


@dataclass(slots=True)
class SocialBoostService:
    follow_graph_service: object

    def build_context(
        self,
        *,
        user_id: str,
        creator_user_ids: set[str] | list[str] | tuple[str, ...],
    ) -> SocialBoostContext:
        resolved_creator_ids = {
            str(item).strip()
            for item in creator_user_ids
            if isinstance(item, str) and str(item).strip()
        }
        following_ids = frozenset(self.follow_graph_service.following_ids(user_id))
        follower_counts = self.follow_graph_service.follower_counts(resolved_creator_ids) if resolved_creator_ids else {}
        network_popularity_counts = (
            self.follow_graph_service.network_popularity_counts(
                user_id=user_id,
                creator_user_ids=resolved_creator_ids,
            )
            if resolved_creator_ids
            else {}
        )
        return SocialBoostContext(
            user_id=user_id,
            following_ids=following_ids,
            follower_counts=follower_counts,
            network_popularity_counts=network_popularity_counts,
        )

    def boost_for_creator(
        self,
        *,
        creator_user_id: str | None,
        context: SocialBoostContext | None,
    ) -> SocialBoostBreakdown:
        if context is None or not creator_user_id:
            return SocialBoostBreakdown()
        resolved_creator_id = str(creator_user_id).strip()
        if not resolved_creator_id:
            return SocialBoostBreakdown()
        followed_boost = FOLLOWED_CREATOR_BOOST if resolved_creator_id in context.following_ids else 0.0
        trending_follow_network_boost = (
            TRENDING_FOLLOW_NETWORK_BOOST
            if int(context.network_popularity_counts.get(resolved_creator_id, 0)) > 0
            else 0.0
        )
        follower_weight_boost = log1p(max(int(context.follower_counts.get(resolved_creator_id, 0)), 0)) * FOLLOWER_WEIGHT_MULTIPLIER
        return SocialBoostBreakdown(
            followed_boost=round(followed_boost, 6),
            trending_follow_network_boost=round(trending_follow_network_boost, 6),
            follower_weight_boost=round(follower_weight_boost, 6),
        )


__all__ = [
    "FOLLOWED_CREATOR_BOOST",
    "FOLLOWER_WEIGHT_MULTIPLIER",
    "SocialBoostBreakdown",
    "SocialBoostContext",
    "SocialBoostService",
    "TRENDING_FOLLOW_NETWORK_BOOST",
]
