from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

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
from app.db import get_session
from app.models.club_profile import ClubProfile
from app.services.club_trophy_service import ClubTrophyService

router = APIRouter(tags=["club-identity-trophies"])


@router.get("/api/clubs/{club_id}/trophy-cabinet", response_model=TrophyCabinetView)
def get_trophy_cabinet(
    club_id: str,
    team_scope: str | None = Query(default=None),
    recent_limit: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_session),
) -> TrophyCabinetView:
    return _build_cabinet(session=session, club_id=club_id, team_scope=team_scope, recent_limit=recent_limit)


@router.get("/api/clubs/{club_id}/honors-timeline", response_model=HonorsTimelineView)
def get_honors_timeline(
    club_id: str,
    team_scope: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> HonorsTimelineView:
    club = _require_club(session, club_id)
    trophies = _filtered_trophies(session=session, club_id=club_id, team_scope=team_scope)
    return HonorsTimelineView(
        club_id=club.id,
        club_name=club.club_name,
        honors=[_to_win_view(club, trophy) for trophy in trophies],
    )


@router.get("/api/clubs/{club_id}/season-honors", response_model=SeasonHonorsArchiveView)
def get_season_honors(
    club_id: str,
    season_label: str | None = Query(default=None),
    team_scope: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> SeasonHonorsArchiveView:
    club = _require_club(session, club_id)
    trophies = _filtered_trophies(session=session, club_id=club_id, team_scope=team_scope)
    if season_label is not None and season_label.strip():
        trophies = [item for item in trophies if item.season_label == season_label.strip()]

    grouped: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for trophy in trophies:
        grouped[(trophy.season_label, _team_scope(trophy))].append(trophy)

    records: list[SeasonHonorsRecordView] = []
    for (season, scope), items in grouped.items():
        ordered = sorted(items, key=lambda item: item.awarded_at, reverse=True)
        records.append(
            SeasonHonorsRecordView(
                snapshot_id=f"snapshot-{club.id}-{season}-{scope}",
                club_id=club.id,
                club_name=club.club_name,
                season_label=season,
                team_scope=scope,
                honors=[_to_win_view(club, trophy) for trophy in ordered],
                total_honors_count=len(ordered),
                major_honors_count=sum(1 for trophy in ordered if _is_major(trophy)),
                elite_honors_count=sum(1 for trophy in ordered if _is_elite(trophy)),
                recorded_at=ordered[0].awarded_at,
            )
        )

    records.sort(key=lambda item: (item.season_label, item.team_scope), reverse=True)
    return SeasonHonorsArchiveView(
        club_id=club.id,
        club_name=club.club_name,
        season_records=records,
    )


@router.get("/api/leaderboards/trophies", response_model=TrophyLeaderboardView)
def get_trophy_leaderboard(
    team_scope: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> TrophyLeaderboardView:
    clubs = session.scalars(select(ClubProfile).order_by(ClubProfile.club_name.asc())).all()
    entries: list[TrophyLeaderboardEntryView] = []
    for club in clubs:
        cabinet = _build_cabinet(session=session, club_id=club.id, team_scope=team_scope, recent_limit=5)
        entries.append(
            TrophyLeaderboardEntryView(
                club_id=club.id,
                club_name=club.club_name,
                total_honors_count=cabinet.total_honors_count,
                major_honors_count=cabinet.major_honors_count,
                elite_honors_count=cabinet.elite_honors_count,
                senior_honors_count=cabinet.senior_honors_count,
                academy_honors_count=cabinet.academy_honors_count,
                latest_honor_at=cabinet.recent_honors[0].earned_at if cabinet.recent_honors else None,
                summary_outputs=cabinet.summary_outputs,
            )
        )
    entries.sort(
        key=lambda item: (
            item.total_honors_count,
            item.elite_honors_count,
            item.major_honors_count,
            item.latest_honor_at or datetime.min,
        ),
        reverse=True,
    )
    return TrophyLeaderboardView(entries=entries[:limit])


def _build_cabinet(
    *,
    session: Session,
    club_id: str,
    team_scope: str | None,
    recent_limit: int,
) -> TrophyCabinetView:
    club = _require_club(session, club_id)
    trophies = _filtered_trophies(session=session, club_id=club_id, team_scope=team_scope)
    by_category: dict[tuple[str, str], list[Any]] = defaultdict(list)
    by_season: dict[str, list[Any]] = defaultdict(list)
    for trophy in trophies:
        by_category[(_trophy_type(trophy), _team_scope(trophy))].append(trophy)
        by_season[trophy.season_label].append(trophy)

    categories = [
        TrophyCategoryCountView(
            trophy_type=trophy_type,
            trophy_name=items[0].trophy_name,
            display_name=items[0].trophy_name,
            team_scope=scope,
            count=len(items),
            is_major_honor=_is_major(items[0]),
            is_elite_honor=_is_elite(items[0]),
        )
        for (trophy_type, scope), items in by_category.items()
    ]
    categories.sort(key=lambda item: (item.count, item.display_name), reverse=True)

    seasons = [
        TrophySeasonCountView(
            season_label=season,
            total_honors_count=len(items),
            major_honors_count=sum(1 for trophy in items if _is_major(trophy)),
            elite_honors_count=sum(1 for trophy in items if _is_elite(trophy)),
            senior_honors_count=sum(1 for trophy in items if _team_scope(trophy) == "senior"),
            academy_honors_count=sum(1 for trophy in items if _team_scope(trophy) == "academy"),
        )
        for season, items in by_season.items()
    ]
    seasons.sort(key=lambda item: item.season_label, reverse=True)

    summary_outputs = _summary_outputs(club.club_name, trophies)
    return TrophyCabinetView(
        club_id=club.id,
        club_name=club.club_name,
        total_honors_count=len(trophies),
        major_honors_count=sum(1 for trophy in trophies if _is_major(trophy)),
        elite_honors_count=sum(1 for trophy in trophies if _is_elite(trophy)),
        senior_honors_count=sum(1 for trophy in trophies if _team_scope(trophy) == "senior"),
        academy_honors_count=sum(1 for trophy in trophies if _team_scope(trophy) == "academy"),
        trophies_by_category=categories,
        trophies_by_season=seasons,
        recent_honors=[_to_win_view(club, trophy) for trophy in trophies[:recent_limit]],
        historic_honors_timeline=[_to_win_view(club, trophy) for trophy in trophies],
        summary_outputs=summary_outputs,
    )


def _filtered_trophies(*, session: Session, club_id: str, team_scope: str | None) -> list[Any]:
    _cabinet, trophies = ClubTrophyService(session).get_trophy_cabinet(club_id)
    return [trophy for trophy in trophies if team_scope in (None, "", _team_scope(trophy))]


def _require_club(session: Session, club_id: str) -> ClubProfile:
    club = session.get(ClubProfile, club_id)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"club {club_id} was not found")
    return club


def _to_win_view(club: ClubProfile, trophy: Any) -> TrophyWinView:
    metadata = dict(getattr(trophy, "metadata_json", {}) or {})
    return TrophyWinView(
        trophy_win_id=str(trophy.id),
        club_id=club.id,
        club_name=club.club_name,
        trophy_type=_trophy_type(trophy),
        trophy_name=str(trophy.trophy_name),
        season_label=str(trophy.season_label),
        competition_region=str(metadata.get("competition_region") or trophy.competition_source),
        competition_tier=str(
            metadata.get("competition_tier")
            or ("elite" if _is_elite(trophy) else "major" if _is_major(trophy) else "standard")
        ),
        final_result_summary=str(metadata.get("final_result_summary") or f"{club.club_name} won {trophy.trophy_name}."),
        earned_at=trophy.awarded_at,
        captain_name=_optional_string(metadata.get("captain_name")),
        top_performer_name=_optional_string(metadata.get("top_performer_name")),
        team_scope=_team_scope(trophy),
        is_major_honor=_is_major(trophy),
        is_elite_honor=_is_elite(trophy),
    )


def _trophy_type(trophy: Any) -> str:
    value = getattr(trophy, "trophy_type", None)
    return value.value if hasattr(value, "value") else str(value)


def _team_scope(trophy: Any) -> str:
    metadata = dict(getattr(trophy, "metadata_json", {}) or {})
    scope = str(metadata.get("team_scope") or "").strip().lower()
    if scope in {"senior", "academy"}:
        return scope
    source = str(getattr(trophy, "competition_source", "")).lower()
    return "academy" if "academy" in source or "youth" in source else "senior"


def _is_major(trophy: Any) -> bool:
    return _trophy_type(trophy) in {"league_title", "cup_title", "creator_cup", "dynasty_award"}


def _is_elite(trophy: Any) -> bool:
    trophy_name = str(getattr(trophy, "trophy_name", "")).lower()
    return _trophy_type(trophy) == "dynasty_award" or "world super cup" in trophy_name


def _summary_outputs(club_name: str, trophies: list[Any]) -> list[str]:
    if not trophies:
        return [f"{club_name} has not recorded an official honor yet."]
    outputs = [
        f"{club_name} has recorded {len(trophies)} honors.",
        f"Latest honor: {trophies[0].trophy_name} in {trophies[0].season_label}.",
    ]
    elite_count = sum(1 for trophy in trophies if _is_elite(trophy))
    if elite_count:
        outputs.append(f"Elite honors recorded: {elite_count}.")
    return outputs


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    resolved = str(value).strip()
    return resolved or None


__all__ = ["router"]
