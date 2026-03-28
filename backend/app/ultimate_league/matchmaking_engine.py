from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MatchmakingEngineError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class QueueCompetitor:
    competitor_id: str
    display_name: str
    elo_rating: int
    tier_key: str | None = None
    region: str | None = None
    queue_entered_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class MatchProposal:
    match_id: str
    home: QueueCompetitor
    away: QueueCompetitor
    rating_gap: int
    search_window_used: int
    same_tier: bool
    same_region: bool


@dataclass(frozen=True, slots=True)
class MatchmakingBatch:
    proposals: tuple[MatchProposal, ...]
    unmatched: tuple[QueueCompetitor, ...]


@dataclass(frozen=True, slots=True)
class EloRatingUpdate:
    home_competitor_id: str
    away_competitor_id: str
    expected_home_score: float
    expected_away_score: float
    actual_home_score: float
    actual_away_score: float
    home_delta: int
    away_delta: int
    home_new_rating: int
    away_new_rating: int
    effective_k_factor: float


@dataclass(slots=True)
class EloMatchmakingEngine:
    base_search_window: int = 75
    expansion_per_minute: int = 15
    max_search_window: int = 275
    k_factor: int = 32

    def expected_score(self, rating: int, opponent_rating: int) -> float:
        exponent = (opponent_rating - rating) / 400.0
        return 1.0 / (1.0 + (10.0 ** exponent))

    def search_window(self, competitor: QueueCompetitor, *, now: datetime | None = None) -> int:
        effective_now = now or _utcnow()
        if competitor.queue_entered_at is None:
            return self.base_search_window
        waited_seconds = max(0.0, (effective_now - competitor.queue_entered_at).total_seconds())
        waited_minutes = int(waited_seconds // 60)
        return min(
            self.max_search_window,
            self.base_search_window + (waited_minutes * self.expansion_per_minute),
        )

    def build_pairs(
        self,
        competitors: list[QueueCompetitor] | tuple[QueueCompetitor, ...],
        *,
        now: datetime | None = None,
        prefer_same_tier: bool = True,
    ) -> MatchmakingBatch:
        effective_now = now or _utcnow()
        waiting = sorted(
            competitors,
            key=lambda competitor: (
                competitor.queue_entered_at or effective_now,
                competitor.elo_rating,
                competitor.competitor_id,
            ),
        )
        proposals: list[MatchProposal] = []
        unmatched: list[QueueCompetitor] = waiting[:]

        index = 0
        while index < len(unmatched):
            requester = unmatched[index]
            opponent_index = self._find_best_opponent(
                requester,
                unmatched,
                requester_index=index,
                now=effective_now,
                require_same_tier=prefer_same_tier,
            )
            if opponent_index is None and prefer_same_tier:
                opponent_index = self._find_best_opponent(
                    requester,
                    unmatched,
                    requester_index=index,
                    now=effective_now,
                    require_same_tier=False,
                )
            if opponent_index is None:
                index += 1
                continue

            opponent = unmatched.pop(opponent_index)
            requester = unmatched.pop(index)
            search_window_used = max(
                self.search_window(requester, now=effective_now),
                self.search_window(opponent, now=effective_now),
            )
            proposals.append(
                MatchProposal(
                    match_id=f"ultimate-match-{uuid4().hex[:12]}",
                    home=requester,
                    away=opponent,
                    rating_gap=abs(requester.elo_rating - opponent.elo_rating),
                    search_window_used=search_window_used,
                    same_tier=requester.tier_key == opponent.tier_key,
                    same_region=bool(requester.region and requester.region == opponent.region),
                )
            )

        return MatchmakingBatch(proposals=tuple(proposals), unmatched=tuple(unmatched))

    def record_match(
        self,
        *,
        home: QueueCompetitor,
        away: QueueCompetitor,
        home_score: int,
        away_score: int,
        importance: float = 1.0,
    ) -> EloRatingUpdate:
        if home_score < 0 or away_score < 0:
            raise MatchmakingEngineError("Scores must be zero or positive integers.")
        if importance <= 0:
            raise MatchmakingEngineError("Match importance must be greater than zero.")

        expected_home = self.expected_score(home.elo_rating, away.elo_rating)
        expected_away = 1.0 - expected_home
        if home_score == away_score:
            actual_home = 0.5
            actual_away = 0.5
        elif home_score > away_score:
            actual_home = 1.0
            actual_away = 0.0
        else:
            actual_home = 0.0
            actual_away = 1.0

        score_margin = abs(home_score - away_score)
        margin_multiplier = 1.0 + min(0.75, score_margin * 0.10)
        upset_multiplier = 1.0 + abs(actual_home - expected_home)
        effective_k = float(self.k_factor) * importance * margin_multiplier * upset_multiplier

        home_delta = int(round(effective_k * (actual_home - expected_home)))
        if home_delta == 0 and actual_home != actual_away:
            home_delta = 1 if actual_home > actual_away else -1
        away_delta = -home_delta

        return EloRatingUpdate(
            home_competitor_id=home.competitor_id,
            away_competitor_id=away.competitor_id,
            expected_home_score=expected_home,
            expected_away_score=expected_away,
            actual_home_score=actual_home,
            actual_away_score=actual_away,
            home_delta=home_delta,
            away_delta=away_delta,
            home_new_rating=home.elo_rating + home_delta,
            away_new_rating=away.elo_rating + away_delta,
            effective_k_factor=effective_k,
        )

    def _find_best_opponent(
        self,
        requester: QueueCompetitor,
        pool: list[QueueCompetitor],
        *,
        requester_index: int,
        now: datetime,
        require_same_tier: bool,
    ) -> int | None:
        best_index: int | None = None
        best_score: tuple[int, int, int, int, str] | None = None
        requester_window = self.search_window(requester, now=now)

        for index, candidate in enumerate(pool):
            if index == requester_index:
                continue
            if require_same_tier and requester.tier_key != candidate.tier_key:
                continue

            rating_gap = abs(requester.elo_rating - candidate.elo_rating)
            candidate_window = self.search_window(candidate, now=now)
            search_window_used = max(requester_window, candidate_window)
            if rating_gap > search_window_used:
                continue

            same_tier = int(requester.tier_key == candidate.tier_key)
            same_region = int(bool(requester.region and requester.region == candidate.region))
            combined_wait_seconds = int(
                self._waiting_seconds(requester, now=now) + self._waiting_seconds(candidate, now=now)
            )
            score = (
                same_tier,
                same_region,
                -rating_gap,
                combined_wait_seconds,
                candidate.competitor_id,
            )
            if best_score is None or score > best_score:
                best_index = index
                best_score = score
        return best_index

    def _waiting_seconds(self, competitor: QueueCompetitor, *, now: datetime) -> float:
        if competitor.queue_entered_at is None:
            return 0.0
        return max(0.0, (now - competitor.queue_entered_at).total_seconds())


__all__ = [
    "EloMatchmakingEngine",
    "EloRatingUpdate",
    "MatchmakingBatch",
    "MatchmakingEngineError",
    "MatchProposal",
    "QueueCompetitor",
]
