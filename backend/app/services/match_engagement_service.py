from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.club_finance.service import ClubFinanceService
from app.live_ops.service import LiveOpsService
from app.models.club_profile import ClubProfile
from app.models.competition_match import CompetitionMatch
from app.predictions.models import PredictionOutcome
from app.predictions.service import PredictionService


@dataclass(slots=True)
class MatchEngagementService:
    session: Session

    def apply_match_result(
        self,
        *,
        match_id: str,
        home_club_id: str | None,
        away_club_id: str | None,
        home_score: int,
        away_score: int,
        home_user_id: str | None = None,
        away_user_id: str | None = None,
    ) -> None:
        winner_user_id = None
        if home_score > away_score:
            winner_user_id = home_user_id or self._owner_id(home_club_id)
        elif away_score > home_score:
            winner_user_id = away_user_id or self._owner_id(away_club_id)
        PredictionService(self.session).resolve_match(
            match_id=match_id,
            actual_outcome=self._actual_outcome(home_score=home_score, away_score=away_score),
        )
        ClubFinanceService(self.session).record_match_result(
            match_id=match_id,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            home_score=home_score,
            away_score=away_score,
            home_user_id=home_user_id,
            away_user_id=away_user_id,
        )
        LiveOpsService(self.session).record_match_xp(
            match_id=match_id,
            home_user_id=home_user_id or self._owner_id(home_club_id),
            away_user_id=away_user_id or self._owner_id(away_club_id),
            winner_user_id=winner_user_id,
        )

    def apply_match_result_from_competition_match(self, *, match: CompetitionMatch) -> None:
        self.apply_match_result(
            match_id=match.id,
            home_club_id=match.home_club_id,
            away_club_id=match.away_club_id,
            home_score=match.home_score,
            away_score=match.away_score,
        )

    def _owner_id(self, club_id: str | None) -> str | None:
        if not club_id:
            return None
        club = self.session.get(ClubProfile, club_id)
        return club.owner_user_id if club is not None else None

    @staticmethod
    def _actual_outcome(*, home_score: int, away_score: int) -> PredictionOutcome:
        if home_score > away_score:
            return PredictionOutcome.HOME_WIN
        if away_score > home_score:
            return PredictionOutcome.AWAY_WIN
        return PredictionOutcome.DRAW


__all__ = ["MatchEngagementService"]
