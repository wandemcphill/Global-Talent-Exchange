from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_identity.models.trophy_models import (
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
    build_default_trophy_definitions,
)
from app.club_identity.trophies.schemas import (
    HonorsTimelineView,
    SeasonHonorsArchiveView,
    SeasonHonorsRecordView,
    TrophyCabinetView,
    TrophyCategoryCountView,
    TrophyLeaderboardEntryView,
    TrophyLeaderboardView,
    TrophySeasonCountView,
    TrophyWinView,
)
from app.club_identity.trophies.service import ClubHonorsNotFoundError
from app.db import get_session
from app.models.club_profile import ClubProfile
from app.schemas.club_trophy_core import ClubTrophyCore
from app.services.club_trophy_service import ClubTrophyService

router = APIRouter(tags=["club-identity-trophies"])

_DISPLAY_NAME_BY_TYPE = {
    definition.trophy_type: definition.display_name for definition in build_default_trophy_definitions()
}


class TrophyCabinetServiceLike(Protocol):
    def get_trophy_cabinet(
        self,
        club_id: str,
        *,
        team_scope: TrophyScope | None = None,
        recent_limit: int = 5,
    ) -> ClubHonorsSummary: ...

    def get_honors_timeline(
        self,
        club_id: str,
        *,
        team_scope: TrophyScope | None = None,
    ) -> HonorsTimeline: ...

    def get_season_honors(
        self,
        club_id: str,
        *,
        season_label: str | None = None,
        team_scope: TrophyScope | None = None,
    ) -> SeasonHonorsArchive: ...

    def get_trophy_leaderboard(
        self,
        *,
        team_scope: TrophyScope | None = None,
        limit: int = 20,
    ) -> TrophyLeaderboard: ...


def get_trophy_cabinet_service(
    session: Session = Depends(get_session),
) -> TrophyCabinetServiceLike:
    return _SqlTrophyCabinetServiceAdapter(session)


@router.get("/api/clubs/{club_id}/trophy-cabinet", response_model=TrophyCabinetView)
def get_trophy_cabinet(
    club_id: str,
    team_scope: str | None = Query(default=None),
    recent_limit: int = Query(default=5, ge=1, le=20),
    service: TrophyCabinetServiceLike = Depends(get_trophy_cabinet_service),
) -> TrophyCabinetView:
    try:
        summary = service.get_trophy_cabinet(
            club_id,
            team_scope=_resolved_team_scope(team_scope),
            recent_limit=recent_limit,
        )
    except ClubHonorsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_cabinet_view(summary)


@router.get("/api/clubs/{club_id}/honors-timeline", response_model=HonorsTimelineView)
def get_honors_timeline(
    club_id: str,
    team_scope: str | None = Query(default=None),
    service: TrophyCabinetServiceLike = Depends(get_trophy_cabinet_service),
) -> HonorsTimelineView:
    try:
        timeline = service.get_honors_timeline(
            club_id,
            team_scope=_resolved_team_scope(team_scope),
        )
    except ClubHonorsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_timeline_view(timeline)


@router.get("/api/clubs/{club_id}/season-honors", response_model=SeasonHonorsArchiveView)
def get_season_honors(
    club_id: str,
    season_label: str | None = Query(default=None),
    team_scope: str | None = Query(default=None),
    service: TrophyCabinetServiceLike = Depends(get_trophy_cabinet_service),
) -> SeasonHonorsArchiveView:
    try:
        archive = service.get_season_honors(
            club_id,
            season_label=season_label.strip() if season_label else None,
            team_scope=_resolved_team_scope(team_scope),
        )
    except ClubHonorsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_season_archive_view(archive)


@router.get("/api/leaderboards/trophies", response_model=TrophyLeaderboardView)
def get_trophy_leaderboard(
    team_scope: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    service: TrophyCabinetServiceLike = Depends(get_trophy_cabinet_service),
) -> TrophyLeaderboardView:
    leaderboard = service.get_trophy_leaderboard(
        team_scope=_resolved_team_scope(team_scope),
        limit=limit,
    )
    return _to_leaderboard_view(leaderboard)


class _SqlTrophyCabinetServiceAdapter:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._service = ClubTrophyService(session)

    def get_trophy_cabinet(
        self,
        club_id: str,
        *,
        team_scope: TrophyScope | None = None,
        recent_limit: int = 5,
    ) -> ClubHonorsSummary:
        wins = self._wins_for_club(club_id, team_scope=team_scope)
        return self._build_summary(wins=wins, recent_limit=recent_limit)

    def get_honors_timeline(
        self,
        club_id: str,
        *,
        team_scope: TrophyScope | None = None,
    ) -> HonorsTimeline:
        wins = self._wins_for_club(club_id, team_scope=team_scope)
        ordered = tuple(self._sort_wins(wins))
        return HonorsTimeline(
            club_id=club_id,
            club_name=ordered[0].club_name,
            honors=ordered,
        )

    def get_season_honors(
        self,
        club_id: str,
        *,
        season_label: str | None = None,
        team_scope: TrophyScope | None = None,
    ) -> SeasonHonorsArchive:
        wins = self._wins_for_club(club_id, team_scope=team_scope)
        filtered = tuple(win for win in wins if season_label is None or win.season_label == season_label)
        if not filtered:
            raise ClubHonorsNotFoundError(f"No trophy honors recorded for club {club_id}")

        grouped: dict[tuple[str, TrophyScope], list[ClubTrophyWin]] = defaultdict(list)
        for win in filtered:
            grouped[(win.season_label, win.team_scope)].append(win)

        records = tuple(
            sorted(
                (
                    SeasonHonorsRecord(
                        snapshot_id=f"snapshot-{club_id}-{season}-{scope}",
                        club_id=club_id,
                        club_name=items[0].club_name,
                        season_label=season,
                        team_scope=scope,
                        honors=tuple(self._sort_wins(items)),
                        total_honors_count=len(items),
                        major_honors_count=sum(1 for item in items if item.is_major_honor),
                        elite_honors_count=sum(1 for item in items if item.is_elite_honor),
                        recorded_at=max(item.earned_at for item in items),
                    )
                    for (season, scope), items in grouped.items()
                ),
                key=lambda record: (record.season_label, record.recorded_at),
                reverse=True,
            )
        )
        return SeasonHonorsArchive(
            club_id=club_id,
            club_name=records[0].club_name,
            season_records=records,
        )

    def get_trophy_leaderboard(
        self,
        *,
        team_scope: TrophyScope | None = None,
        limit: int = 20,
    ) -> TrophyLeaderboard:
        clubs = self._session.scalars(select(ClubProfile).order_by(ClubProfile.club_name.asc())).all()
        entries: list[TrophyLeaderboardEntry] = []
        for club in clubs:
            try:
                summary = self.get_trophy_cabinet(
                    club.id,
                    team_scope=team_scope,
                    recent_limit=5,
                )
            except ClubHonorsNotFoundError:
                continue
            latest_honor_at = summary.recent_honors[0].earned_at if summary.recent_honors else None
            entries.append(
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
                entries,
                key=lambda entry: (
                    -entry.major_honors_count,
                    -entry.total_honors_count,
                    -entry.elite_honors_count,
                    -(entry.latest_honor_at.timestamp() if entry.latest_honor_at else 0.0),
                    entry.club_name,
                ),
            )
        )
        return TrophyLeaderboard(entries=ordered[:limit])

    def _wins_for_club(
        self,
        club_id: str,
        *,
        team_scope: TrophyScope | None = None,
    ) -> tuple[ClubTrophyWin, ...]:
        club = self._session.get(ClubProfile, club_id)
        if club is None:
            raise ClubHonorsNotFoundError(f"No trophy honors recorded for club {club_id}")
        trophies = self._service.list_trophies(club_id)
        wins = tuple(
            self._to_legacy_win(club=club, trophy=trophy)
            for trophy in trophies
            if team_scope is None or self._team_scope(trophy) == team_scope
        )
        if not wins:
            raise ClubHonorsNotFoundError(f"No trophy honors recorded for club {club_id}")
        return tuple(self._sort_wins(wins))

    def _build_summary(
        self,
        *,
        wins: tuple[ClubTrophyWin, ...],
        recent_limit: int,
    ) -> ClubHonorsSummary:
        ordered = tuple(self._sort_wins(wins))
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
                        display_name=self._display_name_for(category_wins[0]),
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
        return ClubHonorsSummary(
            club_id=ordered[0].club_id,
            club_name=ordered[0].club_name,
            total_honors_count=len(ordered),
            major_honors_count=sum(1 for win in ordered if win.is_major_honor),
            elite_honors_count=sum(1 for win in ordered if win.is_elite_honor),
            senior_honors_count=sum(1 for win in ordered if win.team_scope == "senior"),
            academy_honors_count=sum(1 for win in ordered if win.team_scope == "academy"),
            trophies_by_category=trophies_by_category,
            trophies_by_season=trophies_by_season,
            recent_honors=ordered[:recent_limit],
            historic_honors_timeline=ordered,
            summary_outputs=tuple(f"{item.count}x {item.display_name}" for item in trophies_by_category),
        )

    def _display_name_for(self, win: ClubTrophyWin) -> str:
        return _DISPLAY_NAME_BY_TYPE.get(win.trophy_type, win.trophy_name)

    def _to_legacy_win(
        self,
        *,
        club: ClubProfile,
        trophy: ClubTrophyCore,
    ) -> ClubTrophyWin:
        metadata = dict(trophy.metadata_json or {})
        return ClubTrophyWin(
            trophy_win_id=trophy.id,
            award_reference=str(
                metadata.get("award_reference")
                or f"{club.id}:{trophy.trophy_type.value}:{trophy.season_label}:{trophy.id}"
            ),
            club_id=club.id,
            club_name=club.club_name,
            trophy_type=trophy.trophy_type.value,
            trophy_name=trophy.trophy_name,
            season_label=trophy.season_label,
            competition_region=str(metadata.get("competition_region") or trophy.competition_source),
            competition_tier=str(
                metadata.get("competition_tier")
                or ("elite" if self._is_elite(trophy) else "major" if self._is_major(trophy) else "standard")
            ),
            final_result_summary=str(
                metadata.get("final_result_summary") or f"{club.club_name} won {trophy.trophy_name}."
            ),
            earned_at=trophy.awarded_at,
            captain_name=_optional_string(metadata.get("captain_name")),
            top_performer_name=_optional_string(metadata.get("top_performer_name")),
            team_scope=self._team_scope(trophy),
            is_major_honor=self._is_major(trophy),
            is_elite_honor=self._is_elite(trophy),
        )

    @staticmethod
    def _sort_wins(
        wins: tuple[ClubTrophyWin, ...] | list[ClubTrophyWin],
    ) -> list[ClubTrophyWin]:
        return sorted(
            wins,
            key=lambda win: (
                win.earned_at,
                win.season_label,
                win.trophy_name,
                win.trophy_win_id,
            ),
            reverse=True,
        )

    @staticmethod
    def _team_scope(trophy: ClubTrophyCore) -> TrophyScope:
        metadata = dict(trophy.metadata_json or {})
        scope = str(metadata.get("team_scope") or "").strip().lower()
        if scope == "academy":
            return "academy"
        if scope == "senior":
            return "senior"
        source = trophy.competition_source.lower()
        if "academy" in source or "youth" in source:
            return "academy"
        return "senior"

    @staticmethod
    def _is_major(trophy: ClubTrophyCore) -> bool:
        return trophy.trophy_type.value in {
            "league_title",
            "cup_title",
            "creator_cup",
            "dynasty_award",
            "world_super_cup",
            "academy_champions_league",
        }

    @staticmethod
    def _is_elite(trophy: ClubTrophyCore) -> bool:
        return trophy.trophy_type.value == "world_super_cup" or "world super cup" in trophy.trophy_name.lower()


def _resolved_team_scope(team_scope: str | None) -> TrophyScope | None:
    normalized = (team_scope or "").strip().lower()
    if normalized in {"senior", "academy"}:
        return normalized
    return None


def _to_cabinet_view(summary: ClubHonorsSummary) -> TrophyCabinetView:
    return TrophyCabinetView(
        club_id=summary.club_id,
        club_name=summary.club_name,
        total_honors_count=summary.total_honors_count,
        major_honors_count=summary.major_honors_count,
        elite_honors_count=summary.elite_honors_count,
        senior_honors_count=summary.senior_honors_count,
        academy_honors_count=summary.academy_honors_count,
        trophies_by_category=[
            TrophyCategoryCountView(
                trophy_type=item.trophy_type,
                trophy_name=item.trophy_name,
                display_name=item.display_name,
                team_scope=item.team_scope,
                count=item.count,
                is_major_honor=item.is_major_honor,
                is_elite_honor=item.is_elite_honor,
            )
            for item in summary.trophies_by_category
        ],
        trophies_by_season=[
            TrophySeasonCountView(
                season_label=item.season_label,
                total_honors_count=item.total_honors_count,
                major_honors_count=item.major_honors_count,
                elite_honors_count=item.elite_honors_count,
                senior_honors_count=item.senior_honors_count,
                academy_honors_count=item.academy_honors_count,
            )
            for item in summary.trophies_by_season
        ],
        recent_honors=[_to_win_view(item) for item in summary.recent_honors],
        historic_honors_timeline=[_to_win_view(item) for item in summary.historic_honors_timeline],
        summary_outputs=list(summary.summary_outputs),
    )


def _to_timeline_view(timeline: HonorsTimeline) -> HonorsTimelineView:
    return HonorsTimelineView(
        club_id=timeline.club_id,
        club_name=timeline.club_name,
        honors=[_to_win_view(item) for item in timeline.honors],
    )


def _to_season_archive_view(
    archive: SeasonHonorsArchive,
) -> SeasonHonorsArchiveView:
    return SeasonHonorsArchiveView(
        club_id=archive.club_id,
        club_name=archive.club_name,
        season_records=[
            SeasonHonorsRecordView(
                snapshot_id=record.snapshot_id,
                club_id=record.club_id,
                club_name=record.club_name,
                season_label=record.season_label,
                team_scope=record.team_scope,
                honors=[_to_win_view(item) for item in record.honors],
                total_honors_count=record.total_honors_count,
                major_honors_count=record.major_honors_count,
                elite_honors_count=record.elite_honors_count,
                recorded_at=record.recorded_at,
            )
            for record in archive.season_records
        ],
    )


def _to_leaderboard_view(
    leaderboard: TrophyLeaderboard,
) -> TrophyLeaderboardView:
    return TrophyLeaderboardView(
        entries=[
            TrophyLeaderboardEntryView(
                club_id=entry.club_id,
                club_name=entry.club_name,
                total_honors_count=entry.total_honors_count,
                major_honors_count=entry.major_honors_count,
                elite_honors_count=entry.elite_honors_count,
                senior_honors_count=entry.senior_honors_count,
                academy_honors_count=entry.academy_honors_count,
                latest_honor_at=entry.latest_honor_at,
                summary_outputs=list(entry.summary_outputs),
            )
            for entry in leaderboard.entries
        ]
    )


def _to_win_view(win: ClubTrophyWin) -> TrophyWinView:
    return TrophyWinView(
        trophy_win_id=win.trophy_win_id,
        club_id=win.club_id,
        club_name=win.club_name,
        trophy_type=win.trophy_type,
        trophy_name=win.trophy_name,
        season_label=win.season_label,
        competition_region=win.competition_region,
        competition_tier=win.competition_tier,
        final_result_summary=win.final_result_summary,
        earned_at=win.earned_at,
        captain_name=win.captain_name,
        top_performer_name=win.top_performer_name,
        team_scope=win.team_scope,
        is_major_honor=win.is_major_honor,
        is_elite_honor=win.is_elite_honor,
    )


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = ["get_trophy_cabinet_service", "router"]
