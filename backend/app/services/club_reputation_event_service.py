from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.services.club_reputation_service import ClubReputationService

_EVENT_WEIGHTS: dict[str, int] = {
    "competition_participation": 12,
    "competition_completion": 18,
    "competition_win": 90,
    "creator_competition_performance": 40,
    "fair_play": 20,
    "community_growth": 30,
    "sustained_activity": 24,
    "trophy_prestige": 1,
}


@dataclass(slots=True)
class ClubReputationEventService:
    session: Session

    def record_achievement(
        self,
        *,
        club_id: str,
        achievement_key: str,
        source: str,
        quantity: int = 1,
        season: int | None = None,
        summary: str | None = None,
        milestone: str | None = None,
        badge_code: str | None = None,
        payload: dict[str, object] | None = None,
        auto_commit: bool = True,
    ):
        if achievement_key not in _EVENT_WEIGHTS:
            raise ValueError(f"unsupported reputation achievement: {achievement_key}")
        delta = _EVENT_WEIGHTS[achievement_key] * max(quantity, 0)
        return ClubReputationService(self.session).apply_delta(
            club_id=club_id,
            delta=delta,
            event_type=achievement_key,
            source=source,
            summary=summary or achievement_key.replace("_", " ").title(),
            season=season,
            milestone=milestone,
            badge_code=badge_code,
            payload=payload,
            auto_commit=auto_commit,
        )
