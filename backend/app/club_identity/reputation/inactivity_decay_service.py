from __future__ import annotations

from dataclasses import dataclass

from backend.app.club_identity.models.reputation import ClubReputationProfile, ReputationEventType


@dataclass(frozen=True, slots=True)
class InactivityDecayDecision:
    seasons_inactive: int
    delta: int
    summary: str


class InactivityDecayService:
    grace_seasons = 2
    per_season_decay = 10
    max_decay = 60

    def calculate_decay(self, profile: ClubReputationProfile, target_season: int) -> InactivityDecayDecision | None:
        if profile.last_active_season is None:
            return None
        seasons_inactive = max(target_season - profile.last_active_season - 1, 0)
        if seasons_inactive <= self.grace_seasons:
            return None
        decay_steps = seasons_inactive - self.grace_seasons
        raw_decay = min(decay_steps * self.per_season_decay, self.max_decay)
        capped_decay = min(raw_decay, max(profile.current_score // 12, 15))
        if capped_decay <= 0:
            return None
        return InactivityDecayDecision(
            seasons_inactive=seasons_inactive,
            delta=-capped_decay,
            summary=f"Mild inactivity decay applied after {seasons_inactive} inactive seasons",
        )

    def as_event_payload(self, decision: InactivityDecayDecision) -> dict[str, object]:
        return {
            "event_type": ReputationEventType.INACTIVITY_DECAY.value,
            "source": "inactivity_decay",
            "delta": decision.delta,
            "summary": decision.summary,
            "payload": {
                "seasons_inactive": decision.seasons_inactive,
                "grace_seasons": self.grace_seasons,
            },
        }
