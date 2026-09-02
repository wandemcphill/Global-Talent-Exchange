from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.competition_match import CompetitionMatch
from app.models.player_match_performance import PlayerMatchPerformance

#: A performance must carry at least this many minutes to be allowed to influence
#: valuation. A player who came on for the last thirty seconds did not meaningfully
#: perform, and letting such rows count would make the signal trivially farmable by
#: repeated late cameos.
MINIMUM_VALUATION_MINUTES = 15

INELIGIBLE_NO_MINUTES = "insufficient_minutes"
INELIGIBLE_SENT_OFF_EARLY = "sent_off_early"


@dataclass(frozen=True, slots=True)
class PerformanceRecordingResult:
    """What a single recording pass actually did, for logging and for tests."""

    written: int
    skipped_non_canonical: int
    skipped_no_rating: int
    ineligible: int
    already_recorded: bool = False


@dataclass(slots=True)
class PlayerMatchPerformanceRecorder:
    """Persists per-player performance for a completed *competition* match.

    This closes the first and most important break in the chain
    ``match -> performance -> form -> valuation -> market -> ownership``. Before
    this existed, ratings produced by the match engine were computed and thrown
    away on every simulation.

    The recorder is deliberately conservative:

    * Only canonical ``ingestion_players`` ids are stored. Synthetic squad ids
      (``"{team_id}-p{shirt}"``, produced when a simulation runs without a database
      session) are dropped, because they cannot be joined to a tradable player and
      would silently corrupt form.
    * It is idempotent. Re-settling or re-running a match does not double-count.
    * Eligibility for valuation is decided *here*, once, and stored on the row, so
      that an auditor can later ask "why did this match move his value?" and get an
      answer from the data rather than from re-running the policy.
    """

    session: Session

    def record_match(
        self,
        *,
        match: CompetitionMatch,
        player_stats: Iterable[Any],
    ) -> PerformanceRecordingResult:
        existing = self.session.scalar(
            select(PlayerMatchPerformance.id).where(PlayerMatchPerformance.match_id == match.id).limit(1)
        )
        if existing is not None:
            # Already recorded. `complete_match` can legitimately be reached twice
            # for the same fixture, so this is a normal outcome, not an error.
            return PerformanceRecordingResult(
                written=0,
                skipped_non_canonical=0,
                skipped_no_rating=0,
                ineligible=0,
                already_recorded=True,
            )

        stats = list(player_stats)
        if not stats:
            return PerformanceRecordingResult(0, 0, 0, 0)

        canonical_ids = self._canonical_player_ids([self._read(item, "player_id") for item in stats])
        occurred_at = self._occurred_at(match)
        club_ids = {match.home_club_id, match.away_club_id}

        written = 0
        skipped_non_canonical = 0
        skipped_no_rating = 0
        ineligible = 0
        seen: set[str] = set()

        for item in stats:
            player_id = self._read(item, "player_id")
            if not player_id or player_id not in canonical_ids:
                skipped_non_canonical += 1
                continue
            if player_id in seen:
                # Defensive: the same footballer must not appear twice in one match.
                continue
            rating = self._read(item, "rating")
            if rating is None:
                skipped_no_rating += 1
                continue

            minutes = int(self._read(item, "minutes_played") or 0)
            red_card = bool(self._read(item, "red_card") or False)
            eligible, reason = self._eligibility(minutes=minutes, red_card=red_card)
            if not eligible:
                ineligible += 1

            team_id = self._read(item, "team_id")
            self.session.add(
                PlayerMatchPerformance(
                    player_id=player_id,
                    player_name=self._read(item, "player_name"),
                    match_id=match.id,
                    competition_id=match.competition_id,
                    club_id=team_id if team_id in club_ids else None,
                    occurred_at=occurred_at,
                    rating=float(rating),
                    started=bool(self._read(item, "started") or False),
                    minutes_played=minutes,
                    goals=int(self._read(item, "goals") or 0),
                    assists=int(self._read(item, "assists") or 0),
                    saves=int(self._read(item, "saves") or 0),
                    shots_on_target=int(self._read(item, "shots_on_target") or 0),
                    key_passes=int(self._read(item, "key_passes") or 0),
                    tackles_won=int(self._read(item, "tackles_won") or 0),
                    interceptions=int(self._read(item, "interceptions") or 0),
                    yellow_cards=int(self._read(item, "yellow_cards") or 0),
                    red_card=red_card,
                    xg=float(self._read(item, "xg") or 0.0),
                    eligible_for_valuation=eligible,
                    ineligibility_reason=reason,
                )
            )
            seen.add(player_id)
            written += 1

        self.session.flush()
        return PerformanceRecordingResult(
            written=written,
            skipped_non_canonical=skipped_non_canonical,
            skipped_no_rating=skipped_no_rating,
            ineligible=ineligible,
        )

    @staticmethod
    def _eligibility(*, minutes: int, red_card: bool) -> tuple[bool, str | None]:
        if minutes < MINIMUM_VALUATION_MINUTES:
            if red_card:
                # A red card inside the opening minutes is a real, meaningful event,
                # but it is not a *performance* over enough minutes to rate fairly.
                return False, INELIGIBLE_SENT_OFF_EARLY
            return False, INELIGIBLE_NO_MINUTES
        return True, None

    def _canonical_player_ids(self, candidate_ids: Sequence[str | None]) -> set[str]:
        wanted = {pid for pid in candidate_ids if pid}
        if not wanted:
            return set()
        rows = self.session.scalars(select(Player.id).where(Player.id.in_(wanted))).all()
        return set(rows)

    @staticmethod
    def _occurred_at(match: CompetitionMatch) -> datetime:
        for candidate in (match.completed_at, match.scheduled_at):
            if candidate is not None:
                if candidate.tzinfo is None:
                    return candidate.replace(tzinfo=timezone.utc)
                return candidate.astimezone(timezone.utc)
        return datetime.now(timezone.utc)

    @staticmethod
    def _read(item: Any, field: str) -> Any:
        if isinstance(item, dict):
            return item.get(field)
        return getattr(item, field, None)


__all__ = [
    "MINIMUM_VALUATION_MINUTES",
    "INELIGIBLE_NO_MINUTES",
    "INELIGIBLE_SENT_OFF_EARLY",
    "PerformanceRecordingResult",
    "PlayerMatchPerformanceRecorder",
]
