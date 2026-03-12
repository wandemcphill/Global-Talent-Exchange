from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from backend.app.club_identity.models.trophy_models import (
    ClubHonorsSummary,
    ClubTrophyWin,
    HonorsTimeline,
    SeasonHonorsArchive,
    SeasonHonorsRecord,
    TrophyCategoryCount,
    TrophyLeaderboard,
    TrophyLeaderboardEntry,
    TrophyScope,
    TrophySeasonCount,
)
from backend.app.club_identity.trophies.repository import TrophyRepository, get_trophy_repository


class TrophyDefinitionNotFoundError(LookupError):
    pass


class ClubHonorsNotFoundError(LookupError):
    pass


class DuplicateTrophyAwardError(ValueError):
    pass


class TrophyCabinetService:
    def __init__(self, *, repository: TrophyRepository | None = None) -> None:
        self.repository = repository or get_trophy_repository()

    def award_trophy(
        self,
        *,
        club_id: str,
        club_name: str,
        trophy_type: str,
        season_label: str,
        final_result_summary: str,
        earned_at: datetime | None = None,
        captain_name: str | None = None,
        top_performer_name: str | None = None,
        award_reference: str | None = None,
    ) -> ClubTrophyWin:
        definition = self.repository.get_definition(trophy_type)
        if definition is None:
            raise TrophyDefinitionNotFoundError(f"Unknown trophy definition: {trophy_type}")

        resolved_reference = award_reference or f"{club_id}:{trophy_type}:{season_label}:{final_result_summary}"
        if any(
            win.award_reference == resolved_reference and win.club_id == club_id
            for win in self.repository.list_trophy_wins(club_id=club_id)
        ):
            raise DuplicateTrophyAwardError(
                f"Trophy award already recorded for club {club_id} and reference {resolved_reference}"
            )

        trophy_win = ClubTrophyWin(
            trophy_win_id=f"trophy-{uuid4().hex[:12]}",
            award_reference=resolved_reference,
            club_id=club_id,
            club_name=club_name,
            trophy_type=definition.trophy_type,
            trophy_name=definition.trophy_name,
            season_label=season_label,
            competition_region=definition.competition_region,
            competition_tier=definition.competition_tier,
            final_result_summary=final_result_summary,
            earned_at=earned_at or datetime.now(timezone.utc),
            captain_name=captain_name,
            top_performer_name=top_performer_name,
            team_scope=definition.team_scope,
            is_major_honor=definition.is_major_honor,
            is_elite_honor=definition.is_elite_honor,
        )
        self.repository.append_trophy_win(trophy_win)
        self._snapshot_season_honors(
            club_id=club_id,
            club_name=club_name,
            season_label=season_label,
            team_scope=definition.team_scope,
        )
        return trophy_win

    def get_trophy_cabinet(
        self,
        club_id: str,
        *,
        team_scope: TrophyScope | None = None,
        recent_limit: int = 5,
    ) -> ClubHonorsSummary:
        wins = self._wins_for_club(club_id, team_scope=team_scope)
        if not wins:
            raise ClubHonorsNotFoundError(f"No trophy honors recorded for club {club_id}")
        return self._build_summary(wins=wins, recent_limit=recent_limit)

    def get_honors_timeline(
        self,
        club_id: str,
        *,
        team_scope: TrophyScope | None = None,
    ) -> HonorsTimeline:
        wins = self._wins_for_club(club_id, team_scope=team_scope)
        if not wins:
            raise ClubHonorsNotFoundError(f"No trophy honors recorded for club {club_id}")
        ordered = self._sort_wins(wins)
        return HonorsTimeline(
            club_id=club_id,
            club_name=ordered[0].club_name,
            honors=tuple(ordered),
        )

    def get_season_honors(
        self,
        club_id: str,
        *,
        season_label: str | None = None,
        team_scope: TrophyScope | None = None,
    ) -> SeasonHonorsArchive:
        snapshots = self.repository.list_season_snapshots(club_id=club_id, season_label=season_label)
        latest_by_key: dict[tuple[str, TrophyScope], SeasonHonorsRecord] = {}
        for snapshot in snapshots:
            if team_scope is not None and snapshot.team_scope != team_scope:
                continue
            key = (snapshot.season_label, snapshot.team_scope)
            current = latest_by_key.get(key)
            if current is None or snapshot.recorded_at > current.recorded_at:
                latest_by_key[key] = snapshot
        if not latest_by_key:
            raise ClubHonorsNotFoundError(f"No trophy honors recorded for club {club_id}")

        ordered = tuple(
            sorted(
                latest_by_key.values(),
                key=lambda snapshot: (snapshot.season_label, snapshot.recorded_at),
                reverse=True,
            )
        )
        return SeasonHonorsArchive(
            club_id=club_id,
            club_name=ordered[0].club_name,
            season_records=ordered,
        )

    def get_trophy_leaderboard(
        self,
        *,
        team_scope: TrophyScope | None = None,
        limit: int = 20,
    ) -> TrophyLeaderboard:
        grouped: dict[str, list[ClubTrophyWin]] = defaultdict(list)
        for win in self.repository.list_trophy_wins():
            if team_scope is not None and win.team_scope != team_scope:
                continue
            grouped[win.club_id].append(win)

        summaries: list[TrophyLeaderboardEntry] = []
        for club_wins in grouped.values():
            summary = self._build_summary(wins=tuple(club_wins), recent_limit=5)
            latest_honor_at = max((win.earned_at for win in club_wins), default=None)
            summaries.append(
                TrophyLeaderboardEntry(
                    club_id=summary.club_id,
                    club_name=summary.club_name,
                    total_honors_count=summary.total_honors_count,
                    major_honors_count=summary.major_honors_count,
                    elite_honors_count=summary.elite_honors_count,
                    senior_honors_count=summary.senior_honors_count,
                    academy_honors_count=summary.academy_honors_count,
                    latest_honor_at=latest_honor_at,
                    summary_outputs=summary.summary_outputs,
                )
            )

        ordered = tuple(
            sorted(
                summaries,
                key=lambda entry: (
                    -entry.major_honors_count,
                    -entry.total_honors_count,
                    -entry.elite_honors_count,
                    -(entry.latest_honor_at.timestamp() if entry.latest_honor_at is not None else 0.0),
                    entry.club_name,
                ),
                reverse=False,
            )
        )
        return TrophyLeaderboard(entries=ordered[:limit])

    def _snapshot_season_honors(
        self,
        *,
        club_id: str,
        club_name: str,
        season_label: str,
        team_scope: TrophyScope,
    ) -> None:
        wins = tuple(
            win
            for win in self.repository.list_trophy_wins(club_id=club_id)
            if win.season_label == season_label and win.team_scope == team_scope
        )
        snapshot = SeasonHonorsRecord(
            snapshot_id=f"snapshot-{uuid4().hex[:12]}",
            club_id=club_id,
            club_name=club_name,
            season_label=season_label,
            team_scope=team_scope,
            honors=tuple(self._sort_wins(wins)),
            total_honors_count=len(wins),
            major_honors_count=sum(1 for win in wins if win.is_major_honor),
            elite_honors_count=sum(1 for win in wins if win.is_elite_honor),
            recorded_at=datetime.now(timezone.utc),
        )
        self.repository.append_season_snapshot(snapshot)

    def _wins_for_club(
        self,
        club_id: str,
        *,
        team_scope: TrophyScope | None = None,
    ) -> tuple[ClubTrophyWin, ...]:
        wins = tuple(
            win
            for win in self.repository.list_trophy_wins(club_id=club_id)
            if team_scope is None or win.team_scope == team_scope
        )
        return wins

    def _build_summary(
        self,
        *,
        wins: tuple[ClubTrophyWin, ...],
        recent_limit: int,
    ) -> ClubHonorsSummary:
        ordered = tuple(self._sort_wins(wins))
        club_name = ordered[0].club_name
        club_id = ordered[0].club_id

        category_map: dict[tuple[str, TrophyScope], list[ClubTrophyWin]] = defaultdict(list)
        season_map: dict[str, list[ClubTrophyWin]] = defaultdict(list)
        for win in ordered:
            category_map[(win.trophy_type, win.team_scope)].append(win)
            season_map[win.season_label].append(win)

        trophies_by_category = tuple(
            sorted(
                (
                    TrophyCategoryCount(
                        trophy_type=category_wins[0].trophy_type,
                        trophy_name=category_wins[0].trophy_name,
                        display_name=self._display_name_for(category_wins[0].trophy_type),
                        team_scope=category_wins[0].team_scope,
                        count=len(category_wins),
                        is_major_honor=category_wins[0].is_major_honor,
                        is_elite_honor=category_wins[0].is_elite_honor,
                    )
                    for category_wins in category_map.values()
                ),
                key=lambda item: (-item.count, item.display_name),
            )
        )
        trophies_by_season = tuple(
            sorted(
                (
                    TrophySeasonCount(
                        season_label=season_label,
                        total_honors_count=len(season_wins),
                        major_honors_count=sum(1 for win in season_wins if win.is_major_honor),
                        elite_honors_count=sum(1 for win in season_wins if win.is_elite_honor),
                        senior_honors_count=sum(1 for win in season_wins if win.team_scope == "senior"),
                        academy_honors_count=sum(1 for win in season_wins if win.team_scope == "academy"),
                    )
                    for season_label, season_wins in season_map.items()
                ),
                key=lambda item: item.season_label,
                reverse=True,
            )
        )
        summary_outputs = tuple(f"{item.count}x {item.display_name}" for item in trophies_by_category)
        return ClubHonorsSummary(
            club_id=club_id,
            club_name=club_name,
            total_honors_count=len(ordered),
            major_honors_count=sum(1 for win in ordered if win.is_major_honor),
            elite_honors_count=sum(1 for win in ordered if win.is_elite_honor),
            senior_honors_count=sum(1 for win in ordered if win.team_scope == "senior"),
            academy_honors_count=sum(1 for win in ordered if win.team_scope == "academy"),
            trophies_by_category=trophies_by_category,
            trophies_by_season=trophies_by_season,
            recent_honors=ordered[:recent_limit],
            historic_honors_timeline=ordered,
            summary_outputs=summary_outputs,
        )

    def _display_name_for(self, trophy_type: str) -> str:
        definition = self.repository.get_definition(trophy_type)
        if definition is None:
            return trophy_type
        return definition.display_name

    @staticmethod
    def _sort_wins(wins: tuple[ClubTrophyWin, ...] | list[ClubTrophyWin]) -> list[ClubTrophyWin]:
        return sorted(
            wins,
            key=lambda win: (win.earned_at, win.season_label, win.trophy_name, win.trophy_win_id),
            reverse=True,
        )


__all__ = [
    "ClubHonorsNotFoundError",
    "DuplicateTrophyAwardError",
    "TrophyCabinetService",
    "TrophyDefinitionNotFoundError",
]
