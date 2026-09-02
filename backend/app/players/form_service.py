from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.player_match_performance import PlayerMatchPerformance

#: How many recent eligible competition performances make up a form window.
FORM_WINDOW_SIZE = 6

#: No more than this many performances from any *single* competition may occupy the
#: window. This is the anti-farming guard: without it, an owner who can spin up or
#: influence one competition could stack it with favourable fixtures for a player
#: they hold. Capping per-competition contribution forces genuine form to be earned
#: across the wider fixture list.
MAX_PERFORMANCES_PER_COMPETITION = 3

#: Below this many counted performances the window is not a trustworthy read on
#: form, and must not be allowed to influence valuation at all.
MINIMUM_MATCHES_FOR_SIGNAL = 3

#: Rating movement (0-10 scale) below this is noise, not a trajectory.
TREND_EPSILON = 0.15

TREND_RISING = "rising"
TREND_STEADY = "steady"
TREND_FALLING = "falling"

#: The neutral rating. A player performing exactly at this level is, by definition,
#: doing nothing to move his own value in either direction. It matches the baseline
#: the existing real-world value engine already uses (``scoring.py``).
BASELINE_RATING = 6.5


@dataclass(frozen=True, slots=True)
class FormEntry:
    """One performance as it appears inside a form window."""

    match_id: str
    competition_id: str
    occurred_at: datetime
    rating: float
    minutes_played: int
    goals: int
    assists: int


@dataclass(frozen=True, slots=True)
class PlayerFormWindow:
    """A deterministic, bounded read on a footballer's recent competition form.

    Everything here is derived from persisted competition performances. Nothing is
    inferred, estimated or invented: if a player has not played eligible competition
    matches, the window is empty and says so, rather than guessing.
    """

    player_id: str
    entries: tuple[FormEntry, ...] = ()
    matches_counted: int = 0
    competitions_counted: int = 0
    average_rating: float | None = None
    trend: str = TREND_STEADY
    trend_delta: float = 0.0
    total_minutes: int = 0
    total_goals: int = 0
    total_assists: int = 0
    excluded_by_competition_cap: int = 0

    @property
    def has_sample(self) -> bool:
        return self.matches_counted > 0

    @property
    def is_signal_eligible(self) -> bool:
        """Whether this window is allowed to influence valuation at all."""
        return self.matches_counted >= MINIMUM_MATCHES_FOR_SIGNAL and self.average_rating is not None

    @property
    def rating_above_baseline(self) -> float:
        if self.average_rating is None:
            return 0.0
        return self.average_rating - BASELINE_RATING


@dataclass(slots=True)
class PlayerFormService:
    """Builds rolling form windows from persisted competition performances."""

    session: Session
    window_size: int = FORM_WINDOW_SIZE
    max_per_competition: int = MAX_PERFORMANCES_PER_COMPETITION

    def build_window(self, player_id: str, *, as_of: datetime | None = None) -> PlayerFormWindow:
        stmt = (
            select(PlayerMatchPerformance)
            .where(
                PlayerMatchPerformance.player_id == player_id,
                PlayerMatchPerformance.eligible_for_valuation.is_(True),
            )
            # Deterministic ordering: two performances recorded at the same instant
            # must always resolve the same way, or the same inputs could yield two
            # different valuations.
            .order_by(
                PlayerMatchPerformance.occurred_at.desc(),
                PlayerMatchPerformance.id.desc(),
            )
        )
        if as_of is not None:
            stmt = stmt.where(PlayerMatchPerformance.occurred_at <= as_of)
        # Over-fetch so the per-competition cap still has candidates to fall back on.
        candidates = list(self.session.scalars(stmt.limit(self.window_size * 4)).all())
        return self.build_window_from_records(player_id, candidates)

    def list_recent_performances(
        self,
        player_id: str,
        *,
        limit: int = FORM_WINDOW_SIZE,
    ) -> list[PlayerMatchPerformance]:
        """Recent competition performances, newest first.

        Unlike :meth:`build_window` this includes rows that are ineligible for
        valuation: a holder is entitled to see the cameo appearance even though it
        does not move the price, and hiding it would be more confusing than showing
        it alongside its reason.
        """
        stmt = (
            select(PlayerMatchPerformance)
            .where(PlayerMatchPerformance.player_id == player_id)
            .order_by(
                PlayerMatchPerformance.occurred_at.desc(),
                PlayerMatchPerformance.id.desc(),
            )
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def build_window_from_records(
        self,
        player_id: str,
        records: Sequence[PlayerMatchPerformance],
    ) -> PlayerFormWindow:
        selected: list[PlayerMatchPerformance] = []
        per_competition: dict[str, int] = {}
        excluded = 0

        for record in records:
            if len(selected) >= self.window_size:
                break
            used = per_competition.get(record.competition_id, 0)
            if used >= self.max_per_competition:
                excluded += 1
                continue
            per_competition[record.competition_id] = used + 1
            selected.append(record)

        if not selected:
            return PlayerFormWindow(player_id=player_id, excluded_by_competition_cap=excluded)

        entries = tuple(
            FormEntry(
                match_id=record.match_id,
                competition_id=record.competition_id,
                occurred_at=record.occurred_at,
                rating=float(record.rating),
                minutes_played=record.minutes_played,
                goals=record.goals,
                assists=record.assists,
            )
            for record in selected
        )

        ratings = [entry.rating for entry in entries]
        average_rating = round(sum(ratings) / len(ratings), 3)
        trend, trend_delta = self._trend(ratings)

        return PlayerFormWindow(
            player_id=player_id,
            entries=entries,
            matches_counted=len(entries),
            competitions_counted=len(per_competition),
            average_rating=average_rating,
            trend=trend,
            trend_delta=trend_delta,
            total_minutes=sum(entry.minutes_played for entry in entries),
            total_goals=sum(entry.goals for entry in entries),
            total_assists=sum(entry.assists for entry in entries),
            excluded_by_competition_cap=excluded,
        )

    @staticmethod
    def _trend(ratings_newest_first: list[float]) -> tuple[str, float]:
        """Compare the recent half of the window against the older half.

        Trajectory is what a holder actually cares about: not "is he good" but "is he
        getting better or worse". With fewer than four matches there is not enough to
        split, so we report steady rather than manufacture a direction.
        """
        if len(ratings_newest_first) < 4:
            return TREND_STEADY, 0.0
        split = len(ratings_newest_first) // 2
        recent = ratings_newest_first[:split]
        prior = ratings_newest_first[split:]
        delta = round((sum(recent) / len(recent)) - (sum(prior) / len(prior)), 3)
        if delta > TREND_EPSILON:
            return TREND_RISING, delta
        if delta < -TREND_EPSILON:
            return TREND_FALLING, delta
        return TREND_STEADY, delta


__all__ = [
    "BASELINE_RATING",
    "FORM_WINDOW_SIZE",
    "MAX_PERFORMANCES_PER_COMPETITION",
    "MINIMUM_MATCHES_FOR_SIGNAL",
    "TREND_EPSILON",
    "TREND_FALLING",
    "TREND_RISING",
    "TREND_STEADY",
    "FormEntry",
    "PlayerFormWindow",
    "PlayerFormService",
]
