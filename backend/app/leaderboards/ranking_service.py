from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.trust_middleware import SharedTrustMiddleware
from app.leaderboards.models import LeaderboardMatchResult, LeaderboardPlayerRating, LeaderboardSeason
from app.leaderboards.season_config import DEFAULT_RANK_TIERS, rank_tier_for_rating
from app.models.user import User
from app.models.user_region import UserRegionProfile

DEFAULT_RATING = 1200
DEFAULT_K_FACTOR = 32
DEFAULT_DIVISION = "bronze"
DIVISION_THRESHOLDS: tuple[tuple[int, str], ...] = tuple(
    (tier.min_rating, tier.key) for tier in DEFAULT_RANK_TIERS
)


@dataclass(frozen=True, slots=True)
class RatingUpdateResult:
    player_a_old_rating: int
    player_b_old_rating: int
    player_a_new_rating: int
    player_b_new_rating: int
    player_a_delta: int
    player_b_delta: int
    expected_a: float
    expected_b: float
    actual_a: float
    actual_b: float


@dataclass(frozen=True, slots=True)
class MatchRatingUpdate:
    season_id: str
    match_id: str
    source_event_id: str | None
    result: float
    player_a: LeaderboardPlayerRating
    player_b: LeaderboardPlayerRating
    rating_update: RatingUpdateResult
    match_record: LeaderboardMatchResult


def _coerce_rating(player: Any, *, default_rating: int = DEFAULT_RATING) -> int:
    rating = getattr(player, "rating", player)
    if rating is None:
        return int(default_rating)
    return int(round(float(rating)))


def _normalize_result(result: float | int) -> float:
    normalized = float(result)
    if normalized not in {0.0, 0.5, 1.0}:
        raise ValueError("result must be one of: 1, 0.5, 0")
    return normalized


def expected_score(player_rating: int | float, opponent_rating: int | float) -> float:
    player_value = float(player_rating)
    opponent_value = float(opponent_rating)
    return 1.0 / (1.0 + (10.0 ** ((opponent_value - player_value) / 400.0)))


def update_ratings(
    player_a: Any,
    player_b: Any,
    result: float | int,
    *,
    k_factor: int = DEFAULT_K_FACTOR,
    default_rating: int = DEFAULT_RATING,
) -> RatingUpdateResult:
    normalized_result = _normalize_result(result)
    rating_a = _coerce_rating(player_a, default_rating=default_rating)
    rating_b = _coerce_rating(player_b, default_rating=default_rating)
    expected_a = expected_score(rating_a, rating_b)
    expected_b = expected_score(rating_b, rating_a)
    actual_a = normalized_result
    actual_b = 1.0 - normalized_result
    new_rating_a = int(round(rating_a + (int(k_factor) * (actual_a - expected_a))))
    new_rating_b = int(round(rating_b + (int(k_factor) * (actual_b - expected_b))))
    return RatingUpdateResult(
        player_a_old_rating=rating_a,
        player_b_old_rating=rating_b,
        player_a_new_rating=new_rating_a,
        player_b_new_rating=new_rating_b,
        player_a_delta=new_rating_a - rating_a,
        player_b_delta=new_rating_b - rating_b,
        expected_a=expected_a,
        expected_b=expected_b,
        actual_a=actual_a,
        actual_b=actual_b,
    )


@dataclass(slots=True)
class RankingService:
    session: Session
    default_rating: int = DEFAULT_RATING
    default_k_factor: int = DEFAULT_K_FACTOR
    trust_middleware: SharedTrustMiddleware | None = None

    def __post_init__(self) -> None:
        if self.trust_middleware is None:
            self.trust_middleware = SharedTrustMiddleware(session=self.session)

    def ensure_player_rating(
        self,
        *,
        season: LeaderboardSeason,
        player_id: str,
        display_name: str | None = None,
        region: str | None = None,
    ) -> LeaderboardPlayerRating:
        resolved_player_id = str(player_id or "").strip()
        if not resolved_player_id:
            raise ValueError("player_id is required")
        existing = self.session.scalar(
            select(LeaderboardPlayerRating).where(
                LeaderboardPlayerRating.season_id == season.id,
                LeaderboardPlayerRating.player_id == resolved_player_id,
            )
        )
        if existing is not None:
            self._refresh_player_identity(existing, display_name=display_name, region=region)
            return existing

        rating = max(int(season.default_rating or self.default_rating), 0)
        entry = LeaderboardPlayerRating(
            season_id=season.id,
            player_id=resolved_player_id,
            display_name=self._resolve_display_name(player_id=resolved_player_id, fallback=display_name),
            region=self._resolve_region(player_id=resolved_player_id, fallback=region),
            division=self.division_for_rating(rating),
            rating=rating,
            highest_rating=rating,
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def record_match_result(
        self,
        *,
        season: LeaderboardSeason,
        match_id: str,
        player_a_id: str,
        player_b_id: str,
        result: float | int,
        source_event_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MatchRatingUpdate:
        resolved_match_id = str(match_id or "").strip()
        if not resolved_match_id:
            raise ValueError("match_id is required")
        resolved_player_a = str(player_a_id or "").strip()
        resolved_player_b = str(player_b_id or "").strip()
        if not resolved_player_a or not resolved_player_b:
            raise ValueError("player_a_id and player_b_id are required")
        if resolved_player_a == resolved_player_b:
            raise ValueError("A match cannot update ratings for the same player twice")

        normalized_result = _normalize_result(result)
        player_a = self.ensure_player_rating(season=season, player_id=resolved_player_a)
        player_b = self.ensure_player_rating(season=season, player_id=resolved_player_b)
        raw_rating_update = update_ratings(
            player_a,
            player_b,
            normalized_result,
            k_factor=int(season.k_factor or self.default_k_factor),
            default_rating=int(season.default_rating or self.default_rating),
        )
        player_a_trust = self.trust_middleware.decision_for_user_id(resolved_player_a)
        player_b_trust = self.trust_middleware.decision_for_user_id(resolved_player_b)
        match_weight = min(player_a_trust.weight, player_b_trust.weight)
        rating_update = (
            raw_rating_update
            if match_weight > 0
            else RatingUpdateResult(
                player_a_old_rating=raw_rating_update.player_a_old_rating,
                player_b_old_rating=raw_rating_update.player_b_old_rating,
                player_a_new_rating=raw_rating_update.player_a_old_rating,
                player_b_new_rating=raw_rating_update.player_b_old_rating,
                player_a_delta=0,
                player_b_delta=0,
                expected_a=raw_rating_update.expected_a,
                expected_b=raw_rating_update.expected_b,
                actual_a=raw_rating_update.actual_a,
                actual_b=raw_rating_update.actual_b,
            )
        )

        player_a.rating = rating_update.player_a_new_rating
        player_b.rating = rating_update.player_b_new_rating
        if match_weight > 0:
            player_a.points += 3 if normalized_result == 1.0 else 1 if normalized_result == 0.5 else 0
            player_b.points += 3 if normalized_result == 0.0 else 1 if normalized_result == 0.5 else 0
            player_a.matches_played += 1
            player_b.matches_played += 1
            player_a.highest_rating = max(player_a.highest_rating, player_a.rating)
            player_b.highest_rating = max(player_b.highest_rating, player_b.rating)
            player_a.last_rating_delta = rating_update.player_a_delta
            player_b.last_rating_delta = rating_update.player_b_delta
            player_a.last_match_id = resolved_match_id
            player_b.last_match_id = resolved_match_id
            player_a.last_result = normalized_result
            player_b.last_result = 1.0 - normalized_result
            now = datetime.now(timezone.utc)
            player_a.last_active_at = now
            player_b.last_active_at = now
            player_a.division = self.division_for_rating(player_a.rating)
            player_b.division = self.division_for_rating(player_b.rating)

            if normalized_result == 1.0:
                player_a.wins += 1
                player_b.losses += 1
            elif normalized_result == 0.0:
                player_b.wins += 1
                player_a.losses += 1
            else:
                player_a.draws += 1
                player_b.draws += 1

        match_record = LeaderboardMatchResult(
            season_id=season.id,
            match_id=resolved_match_id,
            source_event_id=str(source_event_id).strip() if source_event_id else None,
            player_a_id=resolved_player_a,
            player_b_id=resolved_player_b,
            result=normalized_result,
            player_a_rating_before=rating_update.player_a_old_rating,
            player_b_rating_before=rating_update.player_b_old_rating,
            player_a_rating_after=rating_update.player_a_new_rating,
            player_b_rating_after=rating_update.player_b_new_rating,
            metadata_json={
                **dict(metadata or {}),
                "trust": {
                    "match_weight": match_weight,
                    "player_a": {
                        "trust_score": player_a_trust.trust_score,
                        "weight": player_a_trust.weight,
                    },
                    "player_b": {
                        "trust_score": player_b_trust.trust_score,
                        "weight": player_b_trust.weight,
                    },
                },
            },
        )
        self.session.add(match_record)
        self.session.flush()
        return MatchRatingUpdate(
            season_id=season.id,
            match_id=resolved_match_id,
            source_event_id=match_record.source_event_id,
            result=normalized_result,
            player_a=player_a,
            player_b=player_b,
            rating_update=rating_update,
            match_record=match_record,
        )

    @staticmethod
    def division_for_rating(rating: int | float) -> str:
        return rank_tier_for_rating(rating).key

    def _refresh_player_identity(
        self,
        entry: LeaderboardPlayerRating,
        *,
        display_name: str | None,
        region: str | None,
    ) -> None:
        resolved_display_name = self._resolve_display_name(player_id=entry.player_id, fallback=display_name)
        if resolved_display_name and resolved_display_name != entry.display_name:
            entry.display_name = resolved_display_name
        resolved_region = self._resolve_region(player_id=entry.player_id, fallback=region)
        if resolved_region != entry.region:
            entry.region = resolved_region

    def _resolve_display_name(self, *, player_id: str, fallback: str | None = None) -> str:
        if fallback is not None and str(fallback).strip():
            return str(fallback).strip()
        user = self.session.get(User, player_id)
        if user is None:
            return player_id
        for candidate in (user.display_name, user.full_name, user.username, user.email):
            if candidate is not None and str(candidate).strip():
                return str(candidate).strip()
        return player_id

    def _resolve_region(self, *, player_id: str, fallback: str | None = None) -> str | None:
        profile = self.session.scalar(
            select(UserRegionProfile).where(UserRegionProfile.user_id == player_id)
        )
        if profile is not None and profile.region_code:
            resolved = str(profile.region_code).strip().lower()
            return resolved or None
        if fallback is None:
            return None
        resolved = str(fallback).strip().lower()
        return resolved or None


__all__ = [
    "DEFAULT_DIVISION",
    "DEFAULT_K_FACTOR",
    "DEFAULT_RATING",
    "DIVISION_THRESHOLDS",
    "MatchRatingUpdate",
    "RankingService",
    "RatingUpdateResult",
    "expected_score",
    "update_ratings",
]
