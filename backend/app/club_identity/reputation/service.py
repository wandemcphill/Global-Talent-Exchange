from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.club_identity.models.reputation import ClubReputationProfile, PrestigeTier, ReputationEventLog, ReputationSnapshot
from backend.app.club_identity.reputation.prestige_tier_service import PrestigeTierService
from backend.app.club_identity.reputation.schemas import (
    ClubPrestigeView,
    ClubReputationHistoryView,
    ClubReputationView,
    PrestigeLeaderboardEntry,
    PrestigeLeaderboardView,
    ReputationMilestoneView,
    SeasonReputationSnapshotView,
)


@dataclass(slots=True)
class ClubReputationQueryService:
    session: Session
    prestige_tier_service: PrestigeTierService = field(default_factory=PrestigeTierService)

    def get_reputation(self, club_id: str) -> ClubReputationView:
        profile = self._get_profile(club_id)
        milestone_events = self.session.scalars(
            select(ReputationEventLog)
            .where(
                ReputationEventLog.club_id == club_id,
                (ReputationEventLog.milestone.is_not(None)) | (ReputationEventLog.badge_code.is_not(None)),
            )
            .order_by(ReputationEventLog.delta.desc(), ReputationEventLog.created_at.desc())
        ).all()
        badges = list(dict.fromkeys(event.badge_code for event in milestone_events if event.badge_code))
        biggest_milestones = [
            ReputationMilestoneView(
                title=event.milestone or event.summary,
                badge_code=event.badge_code,
                season=event.season,
                delta=event.delta,
                occurred_at=event.created_at,
            )
            for event in milestone_events[:5]
        ]
        return ClubReputationView(
            club_id=club_id,
            current_score=profile.current_score,
            current_prestige_tier=PrestigeTier(profile.prestige_tier),
            highest_score=profile.highest_score,
            last_active_season=profile.last_active_season,
            badges_earned=badges,
            biggest_milestones=biggest_milestones,
        )

    def get_history(self, club_id: str) -> ClubReputationHistoryView:
        profile = self._get_profile(club_id)
        snapshots = self.session.scalars(
            select(ReputationSnapshot)
            .where(ReputationSnapshot.club_id == club_id)
            .order_by(ReputationSnapshot.season.asc())
        ).all()
        return ClubReputationHistoryView(
            club_id=club_id,
            current_score=profile.current_score,
            current_prestige_tier=PrestigeTier(profile.prestige_tier),
            history=[
                SeasonReputationSnapshotView(
                    season=snapshot.season,
                    score_before=snapshot.score_before,
                    season_delta=snapshot.season_delta,
                    score_after=snapshot.score_after,
                    prestige_tier=PrestigeTier(snapshot.prestige_tier),
                    badges=list(snapshot.badges),
                    milestones=list(snapshot.milestones),
                    event_count=snapshot.event_count,
                    rolled_up_at=snapshot.rolled_up_at,
                )
                for snapshot in snapshots
            ],
        )

    def get_prestige(self, club_id: str) -> ClubPrestigeView:
        profile = self._get_profile(club_id)
        progress = self.prestige_tier_service.get_progress(profile.current_score)
        return ClubPrestigeView(
            club_id=club_id,
            current_score=profile.current_score,
            current_prestige_tier=progress.current_tier,
            next_tier=progress.next_tier,
            points_to_next_tier=progress.points_to_next_tier,
        )

    def get_leaderboard(self, limit: int = 20) -> PrestigeLeaderboardView:
        profiles = self.session.scalars(
            select(ClubReputationProfile).order_by(
                ClubReputationProfile.current_score.desc(),
                ClubReputationProfile.highest_score.desc(),
                ClubReputationProfile.club_id.asc(),
            )
        ).all()
        return PrestigeLeaderboardView(
            leaderboard=[
                PrestigeLeaderboardEntry(
                    club_id=profile.club_id,
                    current_score=profile.current_score,
                    current_prestige_tier=PrestigeTier(profile.prestige_tier),
                    highest_score=profile.highest_score,
                    total_seasons=profile.total_seasons,
                )
                for profile in profiles[: max(limit, 0)]
            ]
        )

    def _get_profile(self, club_id: str) -> ClubReputationProfile:
        profile = self.session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club_id))
        if profile is not None:
            return profile
        return ClubReputationProfile(
            club_id=club_id,
            current_score=0,
            highest_score=0,
            prestige_tier=PrestigeTier.LOCAL.value,
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
