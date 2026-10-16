from __future__ import annotations

from app.club_identity.dynasty.repository import DynastyReadRepository
from app.club_identity.dynasty.services.era_label_service import EraLabelService
from app.club_identity.dynasty.services.fallen_giant_service import FallenGiantService
from app.club_identity.dynasty.services.rolling_window_service import RollingWindowService
from app.club_identity.models.dynasty_models import (
    ClubDynastyHistory,
    ClubDynastyProfile,
    ClubDynastySeasonSummary,
    DynastyAssessment,
    DynastyEra,
    DynastyEvent,
    DynastyLeaderboardEntry,
    DynastySnapshot,
    DynastyStatus,
    DynastyStreaks,
    EraLabel,
)


class DynastyDetectorService:
    def __init__(
        self,
        *,
        rolling_window_service: RollingWindowService | None = None,
        era_label_service: EraLabelService | None = None,
        fallen_giant_service: FallenGiantService | None = None,
    ) -> None:
        self._rolling_window_service = rolling_window_service or RollingWindowService()
        self._era_label_service = era_label_service or EraLabelService()
        self._fallen_giant_service = fallen_giant_service or FallenGiantService()

    def build_profile(self, seasons: list[ClubDynastySeasonSummary]) -> ClubDynastyProfile:
        history = self.build_history(seasons)
        latest = history.dynasty_timeline[-1] if history.dynasty_timeline else None
        recent_seasons = tuple(sorted(seasons, key=lambda season: season.season_index)[-4:])
        return ClubDynastyProfile(
            club_id=seasons[-1].club_id if seasons else "",
            club_name=seasons[-1].club_name if seasons else "",
            dynasty_status=latest.dynasty_status if latest is not None else DynastyStatus.NONE,
            current_era_label=latest.era_label if latest is not None else EraLabel.NONE,
            active_dynasty_flag=latest.active_dynasty if latest is not None else False,
            dynasty_score=latest.dynasty_score if latest is not None else 0,
            active_streaks=self._build_streaks(seasons),
            last_four_season_summary=recent_seasons,
            reasons=latest.reasons if latest is not None else tuple(),
            current_snapshot=latest,
            dynasty_timeline=history.dynasty_timeline,
            eras=history.eras,
            events=history.events,
        )

    def build_history(self, seasons: list[ClubDynastySeasonSummary]) -> ClubDynastyHistory:
        ordered = sorted(seasons, key=lambda season: season.season_index)
        snapshots: list[DynastySnapshot] = []
        for metrics in self._rolling_window_service.build_windows(ordered):
            assessment = self._era_label_service.assess(metrics)
            assessment = self._fallen_giant_service.maybe_mark_fallen_giant(
                assessment,
                metrics,
                snapshots,
            )
            snapshots.append(
                DynastySnapshot(
                    club_id=metrics.club_id,
                    club_name=metrics.club_name,
                    dynasty_status=assessment.dynasty_status,
                    era_label=assessment.era_label,
                    active_dynasty=assessment.active_dynasty,
                    dynasty_score=assessment.dynasty_score,
                    reasons=assessment.reasons,
                    metrics=metrics,
                )
            )

        club_id = ordered[-1].club_id if ordered else ""
        club_name = ordered[-1].club_name if ordered else ""
        return ClubDynastyHistory(
            club_id=club_id,
            club_name=club_name,
            dynasty_timeline=tuple(snapshots),
            eras=tuple(self._compress_eras(snapshots)),
            events=tuple(self._build_events(ordered, snapshots)),
        )

    def build_leaderboard(
        self,
        repository: DynastyReadRepository,
        *,
        limit: int = 25,
    ) -> list[DynastyLeaderboardEntry]:
        entries: list[DynastyLeaderboardEntry] = []
        for club_id in repository.list_club_ids():
            profile = self.build_profile(list(repository.get_club_season_summaries(club_id)))
            if profile.current_era_label is EraLabel.NONE and not profile.active_dynasty_flag:
                continue
            entries.append(
                DynastyLeaderboardEntry(
                    club_id=profile.club_id,
                    club_name=profile.club_name,
                    dynasty_status=profile.dynasty_status,
                    current_era_label=profile.current_era_label,
                    active_dynasty_flag=profile.active_dynasty_flag,
                    dynasty_score=profile.dynasty_score,
                    reasons=profile.reasons,
                )
            )
        entries.sort(
            key=lambda entry: (
                not entry.active_dynasty_flag,
                -entry.dynasty_score,
                entry.club_name,
            )
        )
        return entries[:limit]

    def _compress_eras(self, snapshots: list[DynastySnapshot]) -> list[DynastyEra]:
        eras: list[DynastyEra] = []
        active_group: list[DynastySnapshot] = []
        for snapshot in snapshots:
            if snapshot.era_label is EraLabel.NONE:
                if active_group:
                    eras.append(self._group_to_era(active_group, active=snapshots[-1] in active_group))
                    active_group = []
                continue
            if active_group and active_group[-1].era_label is snapshot.era_label:
                active_group.append(snapshot)
                continue
            if active_group:
                eras.append(self._group_to_era(active_group, active=snapshots[-1] in active_group))
            active_group = [snapshot]
        if active_group:
            eras.append(self._group_to_era(active_group, active=snapshots[-1] in active_group))
        return eras

    def _group_to_era(self, group: list[DynastySnapshot], *, active: bool) -> DynastyEra:
        start = group[0].metrics
        end = group[-1].metrics
        peak = max(group, key=lambda snapshot: snapshot.dynasty_score)
        return DynastyEra(
            era_label=group[-1].era_label,
            dynasty_status=group[-1].dynasty_status,
            start_season_id=start.window_end_season_id,
            start_season_label=start.window_end_season_label,
            end_season_id=end.window_end_season_id,
            end_season_label=end.window_end_season_label,
            peak_score=peak.dynasty_score,
            active=active,
            reasons=peak.reasons,
        )

    def _build_events(
        self,
        seasons: list[ClubDynastySeasonSummary],
        snapshots: list[DynastySnapshot],
    ) -> list[DynastyEvent]:
        events: list[DynastyEvent] = []
        for season in seasons:
            if season.league_title:
                events.append(
                    DynastyEvent(
                        season_id=season.season_id,
                        season_label=season.season_label,
                        event_type="league_title",
                        title="League Title",
                        detail="Won the domestic title that contributes directly to dynasty scoring.",
                        score_impact=24,
                    )
                )
            if season.champions_league_title:
                events.append(
                    DynastyEvent(
                        season_id=season.season_id,
                        season_label=season.season_label,
                        event_type="champions_league_title",
                        title="Champions League Title",
                        detail="Added the continental honor that unlocks upper-tier dynasty labels.",
                        score_impact=34,
                    )
                )
            if season.world_super_cup_qualified:
                events.append(
                    DynastyEvent(
                        season_id=season.season_id,
                        season_label=season.season_label,
                        event_type="world_super_cup_qualification",
                        title="World Super Cup Qualification",
                        detail="Stayed on the global stage long enough to keep dynasty momentum alive.",
                        score_impact=7,
                    )
                )
            if season.world_super_cup_winner:
                events.append(
                    DynastyEvent(
                        season_id=season.season_id,
                        season_label=season.season_label,
                        event_type="world_super_cup_title",
                        title="World Super Cup Winner",
                        detail="Reached the rare global peak required for the strongest dynasty category.",
                        score_impact=42,
                    )
                )

        previous_label = EraLabel.NONE
        for snapshot in snapshots:
            if snapshot.era_label is previous_label:
                continue
            if snapshot.era_label is not EraLabel.NONE:
                events.append(
                    DynastyEvent(
                        season_id=snapshot.metrics.window_end_season_id,
                        season_label=snapshot.metrics.window_end_season_label,
                        event_type="era_change",
                        title=snapshot.era_label.value,
                        detail="Dynasty criteria crossed a new threshold at the end of this season.",
                        score_impact=snapshot.dynasty_score,
                    )
                )
            previous_label = snapshot.era_label
        return events

    def _build_streaks(self, seasons: list[ClubDynastySeasonSummary]) -> DynastyStreaks:
        ordered = sorted(seasons, key=lambda season: season.season_index, reverse=True)
        return DynastyStreaks(
            top_four=self._count_streak(ordered, lambda season: season.top_four_finish),
            trophy_seasons=self._count_streak(ordered, lambda season: season.trophy_count > 0),
            world_super_cup_qualification=self._count_streak(
                ordered, lambda season: season.world_super_cup_qualified
            ),
            positive_reputation=self._count_streak(ordered, lambda season: season.reputation_gain > 0),
        )

    def _count_streak(
        self,
        seasons: list[ClubDynastySeasonSummary],
        predicate,
    ) -> int:
        streak = 0
        for season in seasons:
            if not predicate(season):
                break
            streak += 1
        return streak


class DynastyQueryService:
    def __init__(
        self,
        repository: DynastyReadRepository,
        *,
        detector: DynastyDetectorService | None = None,
    ) -> None:
        self._repository = repository
        self._detector = detector or DynastyDetectorService()

    def get_profile(self, club_id: str) -> ClubDynastyProfile | None:
        seasons = list(self._repository.get_club_season_summaries(club_id))
        if not seasons:
            return None
        return self._detector.build_profile(seasons)

    def get_history(self, club_id: str) -> ClubDynastyHistory | None:
        seasons = list(self._repository.get_club_season_summaries(club_id))
        if not seasons:
            return None
        return self._detector.build_history(seasons)

    def get_eras(self, club_id: str) -> tuple[DynastyEra, ...] | None:
        history = self.get_history(club_id)
        if history is None:
            return None
        return history.eras

    def get_leaderboard(self, *, limit: int = 25) -> list[DynastyLeaderboardEntry]:
        return self._detector.build_leaderboard(self._repository, limit=limit)
