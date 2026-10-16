from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums.dynasty_milestone_type import DynastyMilestoneType
from app.models.club_dynasty_milestone import ClubDynastyMilestone
from app.models.club_dynasty_progress import ClubDynastyProgress
from app.models.club_profile import ClubProfile
from app.schemas.club_dynasty_core import ClubDynastyMilestoneCore, ClubDynastyProgressCore

_LEVEL_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (1800, "Legendary Legacy"),
    (1200, "Elite Dynasty"),
    (700, "Established Dynasty"),
    (300, "Rising Legacy"),
    (0, "Foundations"),
)

_MILESTONE_DEFINITIONS: tuple[dict[str, object], ...] = (
    {
        "milestone_type": DynastyMilestoneType.SEASONS_COMPLETED,
        "title": "Five-Season Foundation",
        "description": "Complete five seasons to establish a lasting club identity.",
        "required_value": 5,
        "dynasty_points": 120,
    },
    {
        "milestone_type": DynastyMilestoneType.TOP_FINISH_STREAK,
        "title": "Top Finish Streak",
        "description": "Deliver three straight top finishes.",
        "required_value": 3,
        "dynasty_points": 140,
    },
    {
        "milestone_type": DynastyMilestoneType.PARTICIPATION_STREAK,
        "title": "Ever-Present Club",
        "description": "Maintain a five-season competition participation streak.",
        "required_value": 5,
        "dynasty_points": 100,
    },
    {
        "milestone_type": DynastyMilestoneType.TROPHY_STREAK,
        "title": "Cabinet Momentum",
        "description": "Win trophies in back-to-back legacy cycles.",
        "required_value": 2,
        "dynasty_points": 160,
    },
    {
        "milestone_type": DynastyMilestoneType.COMMUNITY_PRESTIGE,
        "title": "Community Prestige",
        "description": "Build 150 community prestige points through qualified participation.",
        "required_value": 150,
        "dynasty_points": 90,
    },
    {
        "milestone_type": DynastyMilestoneType.CLUB_LOYALTY,
        "title": "Club Loyalty",
        "description": "Accumulate 100 loyalty points across sustained club activity.",
        "required_value": 100,
        "dynasty_points": 90,
    },
    {
        "milestone_type": DynastyMilestoneType.CREATOR_LEGACY,
        "title": "Creator Legacy",
        "description": "Build 100 creator legacy points from creator-hosted achievements.",
        "required_value": 100,
        "dynasty_points": 110,
    },
)


@dataclass(slots=True)
class ClubDynastyService:
    session: Session

    def ensure_progress(self, club_id: str) -> ClubDynastyProgress:
        self._require_club(club_id)
        progress = self.session.scalar(
            select(ClubDynastyProgress).where(ClubDynastyProgress.club_id == club_id)
        )
        if progress is not None:
            return progress
        progress = ClubDynastyProgress(club_id=club_id)
        self.session.add(progress)
        self.session.flush()
        return progress

    def record_season_outcome(
        self,
        *,
        club_id: str,
        season_label: str,
        participated: bool = True,
        top_finish: bool = False,
        trophy_won: bool = False,
        community_prestige_delta: int = 0,
        loyalty_points_delta: int = 0,
        creator_legacy_delta: int = 0,
        auto_commit: bool = True,
    ) -> ClubDynastyProgress:
        progress = self.ensure_progress(club_id)
        if participated:
            progress.seasons_completed += 1
            progress.participation_streak += 1
        else:
            progress.participation_streak = 0
        progress.consecutive_top_finishes = progress.consecutive_top_finishes + 1 if top_finish else 0
        progress.trophy_streak = progress.trophy_streak + 1 if trophy_won else 0
        progress.community_prestige_points += max(community_prestige_delta, 0)
        progress.club_loyalty_points += max(loyalty_points_delta, 0)
        progress.creator_legacy_points += max(creator_legacy_delta, 0)
        progress.last_season_label = season_label

        self._recompute_score(progress)
        self._sync_milestones(progress)
        if auto_commit:
            self.session.commit()
            self.session.refresh(progress)
        return progress

    def record_trophy(
        self,
        *,
        club_id: str,
        prestige_weight: int,
        auto_commit: bool = True,
    ) -> ClubDynastyProgress:
        progress = self.ensure_progress(club_id)
        progress.creator_legacy_points += max(prestige_weight // 4, 1)
        self._recompute_score(progress)
        self._sync_milestones(progress)
        if auto_commit:
            self.session.commit()
            self.session.refresh(progress)
        return progress

    def get_dynasty(self, club_id: str) -> tuple[ClubDynastyProgressCore, list[ClubDynastyMilestoneCore]]:
        progress = self.ensure_progress(club_id)
        milestones = self.session.scalars(
            select(ClubDynastyMilestone)
            .where(ClubDynastyMilestone.club_id == club_id)
            .order_by(
                ClubDynastyMilestone.is_unlocked.desc(),
                ClubDynastyMilestone.dynasty_points.desc(),
                ClubDynastyMilestone.required_value.asc(),
            )
        ).all()
        if not milestones:
            self._sync_milestones(progress)
            self.session.commit()
            milestones = self.session.scalars(
                select(ClubDynastyMilestone)
                .where(ClubDynastyMilestone.club_id == club_id)
                .order_by(
                    ClubDynastyMilestone.is_unlocked.desc(),
                    ClubDynastyMilestone.dynasty_points.desc(),
                    ClubDynastyMilestone.required_value.asc(),
                )
            ).all()
        return (
            ClubDynastyProgressCore.model_validate(progress),
            [ClubDynastyMilestoneCore.model_validate(item) for item in milestones],
        )

    def _sync_milestones(self, progress: ClubDynastyProgress) -> None:
        metrics = {
            DynastyMilestoneType.SEASONS_COMPLETED: progress.seasons_completed,
            DynastyMilestoneType.TOP_FINISH_STREAK: progress.consecutive_top_finishes,
            DynastyMilestoneType.PARTICIPATION_STREAK: progress.participation_streak,
            DynastyMilestoneType.TROPHY_STREAK: progress.trophy_streak,
            DynastyMilestoneType.COMMUNITY_PRESTIGE: progress.community_prestige_points,
            DynastyMilestoneType.CLUB_LOYALTY: progress.club_loyalty_points,
            DynastyMilestoneType.CREATOR_LEGACY: progress.creator_legacy_points,
        }
        existing = {
            (item.milestone_type, item.required_value): item
            for item in self.session.scalars(
                select(ClubDynastyMilestone).where(ClubDynastyMilestone.club_id == progress.club_id)
            ).all()
        }
        for definition in _MILESTONE_DEFINITIONS:
            milestone_type = definition["milestone_type"]
            required_value = int(definition["required_value"])
            current_value = metrics[milestone_type]
            key = (milestone_type.value, required_value)
            milestone = existing.get(key)
            if milestone is None:
                milestone = ClubDynastyMilestone(
                    club_id=progress.club_id,
                    milestone_type=milestone_type.value,
                    title=str(definition["title"]),
                    description=str(definition["description"]),
                    required_value=required_value,
                    progress_value=current_value,
                    dynasty_points=int(definition["dynasty_points"]),
                    is_unlocked=current_value >= required_value,
                    unlocked_at=datetime.now(timezone.utc) if current_value >= required_value else None,
                    metadata_json={"metric_key": milestone_type.value},
                )
                self.session.add(milestone)
                continue
            milestone.progress_value = current_value
            if not milestone.is_unlocked and current_value >= required_value:
                milestone.is_unlocked = True
                milestone.unlocked_at = datetime.now(timezone.utc)

    @staticmethod
    def _recompute_score(progress: ClubDynastyProgress) -> None:
        progress.dynasty_score = (
            progress.seasons_completed * 50
            + progress.consecutive_top_finishes * 75
            + progress.participation_streak * 25
            + progress.trophy_streak * 100
            + progress.community_prestige_points
            + progress.club_loyalty_points * 2
            + progress.creator_legacy_points * 3
        )
        progress.dynasty_level, progress.dynasty_title = ClubDynastyService._resolve_level(progress.dynasty_score)
        progress.showcase_summary_json = {
            "seasons_completed": progress.seasons_completed,
            "top_finish_streak": progress.consecutive_top_finishes,
            "participation_streak": progress.participation_streak,
            "trophy_streak": progress.trophy_streak,
        }

    @staticmethod
    def _resolve_level(score: int) -> tuple[int, str]:
        for offset, (threshold, title) in enumerate(_LEVEL_THRESHOLDS):
            if score >= threshold:
                return len(_LEVEL_THRESHOLDS) - offset, title
        return 1, "Foundations"

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise LookupError(f"club {club_id} was not found")
        return club
