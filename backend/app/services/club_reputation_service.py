from __future__ import annotations

# GTEX club reputation, trophy cabinet, dynasty progression, and jersey/custom branding
# are identity, progression, and cosmetic systems tied to transparent achievement and
# catalog-based customization. They are not wagering products, random-value mechanics,
# or luck-based monetization systems.

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.club_identity.models.reputation import ClubReputationProfile, ReputationSnapshot
from backend.app.common.enums.club_reputation_tier import ClubReputationTier
from backend.app.models.club_profile import ClubProfile
from backend.app.models.club_reputation_event import ClubReputationEvent
from backend.app.schemas.club_reputation_core import (
    ClubReputationCore,
    ReputationEventCore,
    ReputationScoreBreakdown,
    ReputationSnapshotCore,
)

_TIER_THRESHOLDS: tuple[tuple[ClubReputationTier, int], ...] = (
    (ClubReputationTier.LEGENDARY, 2200),
    (ClubReputationTier.ELITE, 1200),
    (ClubReputationTier.ESTABLISHED, 600),
    (ClubReputationTier.RISING, 200),
    (ClubReputationTier.GRASSROOTS, 0),
)

_LEGACY_TIER_BY_API_TIER: dict[ClubReputationTier, str] = {
    ClubReputationTier.GRASSROOTS: "Local",
    ClubReputationTier.RISING: "Rising",
    ClubReputationTier.ESTABLISHED: "Established",
    ClubReputationTier.ELITE: "Elite",
    ClubReputationTier.LEGENDARY: "Legendary",
}

_API_TIER_BY_LEGACY_TIER: dict[str, ClubReputationTier] = {
    value: key for key, value in _LEGACY_TIER_BY_API_TIER.items()
}
_API_TIER_BY_LEGACY_TIER["Dynasty"] = ClubReputationTier.LEGENDARY

_BREAKDOWN_BUCKETS: dict[str, str] = {
    "competition_participation": "competition_participation",
    "competition_completion": "competition_completion",
    "competition_win": "competition_wins",
    "creator_competition_performance": "creator_competition_performance",
    "fair_play": "fair_play",
    "community_growth": "community_growth",
    "sustained_activity": "sustained_activity",
    "trophy_prestige": "trophy_prestige",
}


@dataclass(slots=True)
class ClubReputationService:
    session: Session

    def ensure_profile(self, club_id: str) -> ClubReputationProfile:
        self._require_club(club_id)
        profile = self.session.scalar(
            select(ClubReputationProfile).where(ClubReputationProfile.club_id == club_id)
        )
        if profile is not None:
            return profile

        profile = ClubReputationProfile(
            club_id=club_id,
            current_score=0,
            highest_score=0,
            prestige_tier=_LEGACY_TIER_BY_API_TIER[ClubReputationTier.GRASSROOTS],
            total_seasons=0,
            consecutive_top_competition_seasons=0,
            consecutive_league_titles=0,
            consecutive_continental_titles=0,
            total_league_titles=0,
            total_continental_qualifications=0,
            total_continental_titles=0,
            total_world_super_cup_qualifications=0,
            total_world_super_cup_titles=0,
            total_top_scorer_awards=0,
            total_top_assist_awards=0,
        )
        self.session.add(profile)
        self.session.flush()
        return profile

    def get_reputation(self, club_id: str) -> ClubReputationCore:
        profile = self.ensure_profile(club_id)
        events = self.session.scalars(
            select(ClubReputationEvent)
            .where(ClubReputationEvent.club_id == club_id)
            .order_by(ClubReputationEvent.created_at.desc())
        ).all()
        last_snapshot = self.session.scalar(
            select(ReputationSnapshot)
            .where(ReputationSnapshot.club_id == club_id)
            .order_by(ReputationSnapshot.season.desc(), ReputationSnapshot.created_at.desc())
        )

        breakdown = ReputationScoreBreakdown()
        for event in events:
            bucket = _BREAKDOWN_BUCKETS.get(event.event_type)
            if bucket is not None:
                setattr(breakdown, bucket, getattr(breakdown, bucket) + event.delta)

        return ClubReputationCore(
            club_id=club_id,
            current_score=profile.current_score,
            highest_score=profile.highest_score,
            tier=self.to_api_tier(profile.prestige_tier),
            breakdown=breakdown,
            recent_events=[ReputationEventCore.model_validate(event) for event in events[:10]],
            last_snapshot=self._to_snapshot_core(last_snapshot),
        )

    def apply_delta(
        self,
        *,
        club_id: str,
        delta: int,
        event_type: str,
        source: str,
        summary: str,
        season: int | None = None,
        milestone: str | None = None,
        badge_code: str | None = None,
        payload: dict[str, object] | None = None,
        auto_commit: bool = True,
    ) -> ClubReputationEvent:
        profile = self.ensure_profile(club_id)
        profile.current_score += delta
        profile.highest_score = max(profile.highest_score, profile.current_score)
        profile.prestige_tier = _LEGACY_TIER_BY_API_TIER[self.score_to_tier(profile.current_score)]
        if season is not None:
            profile.last_active_season = season
            profile.total_seasons = max(profile.total_seasons, season)

        event = ClubReputationEvent(
            club_id=club_id,
            season=season,
            event_type=event_type,
            source=source,
            delta=delta,
            score_after=profile.current_score,
            summary=summary,
            milestone=milestone,
            badge_code=badge_code,
            payload=payload or {},
        )
        self.session.add(event)
        self.session.flush()
        if auto_commit:
            self.session.commit()
            self.session.refresh(event)
        return event

    def rollup_snapshot(
        self,
        *,
        club_id: str,
        season: int,
        badges: list[str] | None = None,
        milestones: list[str] | None = None,
    ) -> ReputationSnapshot:
        profile = self.ensure_profile(club_id)
        events = self.session.scalars(
            select(ClubReputationEvent)
            .where(
                ClubReputationEvent.club_id == club_id,
                ClubReputationEvent.season == season,
            )
            .order_by(ClubReputationEvent.created_at.asc())
        ).all()
        season_delta = sum(event.delta for event in events)
        score_after = profile.current_score
        score_before = score_after - season_delta

        snapshot = self.session.scalar(
            select(ReputationSnapshot).where(
                ReputationSnapshot.club_id == club_id,
                ReputationSnapshot.season == season,
            )
        )
        if snapshot is None:
            snapshot = ReputationSnapshot(
                club_id=club_id,
                season=season,
                score_before=score_before,
                season_delta=season_delta,
                score_after=score_after,
                prestige_tier=profile.prestige_tier,
                badges=badges or [],
                milestones=milestones or [],
                event_count=len(events),
            )
            self.session.add(snapshot)
        else:
            snapshot.score_before = score_before
            snapshot.season_delta = season_delta
            snapshot.score_after = score_after
            snapshot.prestige_tier = profile.prestige_tier
            snapshot.badges = badges or []
            snapshot.milestones = milestones or []
            snapshot.event_count = len(events)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    @staticmethod
    def score_to_tier(score: int) -> ClubReputationTier:
        for tier, minimum_score in _TIER_THRESHOLDS:
            if score >= minimum_score:
                return tier
        return ClubReputationTier.GRASSROOTS

    @staticmethod
    def to_api_tier(legacy_value: str) -> ClubReputationTier:
        return _API_TIER_BY_LEGACY_TIER.get(legacy_value, ClubReputationTier.GRASSROOTS)

    @staticmethod
    def _to_snapshot_core(snapshot: ReputationSnapshot | None) -> ReputationSnapshotCore | None:
        if snapshot is None:
            return None
        return ReputationSnapshotCore(
            id=snapshot.id,
            club_id=snapshot.club_id,
            season=snapshot.season,
            score_before=snapshot.score_before,
            season_delta=snapshot.season_delta,
            score_after=snapshot.score_after,
            tier=ClubReputationService.to_api_tier(snapshot.prestige_tier),
            badges=list(snapshot.badges),
            milestones=list(snapshot.milestones),
            event_count=snapshot.event_count,
            rolled_up_at=snapshot.rolled_up_at,
        )

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise LookupError(f"club {club_id} was not found")
        return club
