from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.app.club_identity.dynasty.api.router import router
from backend.app.club_identity.dynasty.repository import InMemoryDynastyReadRepository
from backend.app.club_identity.models.dynasty_models import ClubDynastySeasonSummary


def _season(
    *,
    club_id: str,
    club_name: str,
    season_index: int,
    league_finish: int | None,
    league_title: bool = False,
    champions_league_title: bool = False,
    world_super_cup_qualified: bool = False,
    world_super_cup_winner: bool = False,
    trophy_count: int = 0,
    reputation_gain: int = 0,
) -> ClubDynastySeasonSummary:
    return ClubDynastySeasonSummary(
        club_id=club_id,
        club_name=club_name,
        season_id=f"{club_id}-s{season_index}",
        season_label=f"20{20 + season_index}/20{21 + season_index}",
        season_index=season_index,
        league_finish=league_finish,
        league_title=league_title,
        champions_league_title=champions_league_title,
        world_super_cup_qualified=world_super_cup_qualified,
        world_super_cup_winner=world_super_cup_winner,
        trophy_count=trophy_count,
        reputation_gain=reputation_gain,
    )


@pytest.fixture()
def make_season():
    return _season


@pytest.fixture()
def rolling_window_seasons(make_season):
    return [
        make_season(club_id="club-roll", club_name="Rolling FC", season_index=1, league_finish=5, trophy_count=0, reputation_gain=2),
        make_season(club_id="club-roll", club_name="Rolling FC", season_index=2, league_finish=1, league_title=True, world_super_cup_qualified=True, trophy_count=2, reputation_gain=8),
        make_season(club_id="club-roll", club_name="Rolling FC", season_index=3, league_finish=3, trophy_count=1, reputation_gain=4),
        make_season(club_id="club-roll", club_name="Rolling FC", season_index=4, league_finish=2, trophy_count=1, reputation_gain=3),
        make_season(club_id="club-roll", club_name="Rolling FC", season_index=5, league_finish=1, league_title=True, world_super_cup_qualified=True, trophy_count=2, reputation_gain=7),
    ]


@pytest.fixture()
def emerging_power_seasons(make_season):
    return [
        make_season(club_id="club-rise", club_name="Rise FC", season_index=1, league_finish=4, trophy_count=1, reputation_gain=6),
        make_season(club_id="club-rise", club_name="Rise FC", season_index=2, league_finish=2, league_title=True, world_super_cup_qualified=True, trophy_count=2, reputation_gain=8),
    ]


@pytest.fixture()
def continental_dynasty_seasons(make_season):
    return [
        make_season(club_id="club-cont", club_name="Continental FC", season_index=1, league_finish=2, trophy_count=1, reputation_gain=5),
        make_season(club_id="club-cont", club_name="Continental FC", season_index=2, league_finish=1, league_title=True, world_super_cup_qualified=True, trophy_count=2, reputation_gain=6),
        make_season(club_id="club-cont", club_name="Continental FC", season_index=3, league_finish=3, champions_league_title=True, world_super_cup_qualified=True, trophy_count=2, reputation_gain=8),
        make_season(club_id="club-cont", club_name="Continental FC", season_index=4, league_finish=4, trophy_count=1, reputation_gain=6),
    ]


@pytest.fixture()
def global_dynasty_seasons(make_season):
    return [
        make_season(club_id="club-global", club_name="Global FC", season_index=1, league_finish=2, league_title=True, world_super_cup_qualified=True, trophy_count=2, reputation_gain=7),
        make_season(club_id="club-global", club_name="Global FC", season_index=2, league_finish=1, league_title=True, world_super_cup_qualified=True, trophy_count=2, reputation_gain=8),
        make_season(club_id="club-global", club_name="Global FC", season_index=3, league_finish=3, champions_league_title=True, world_super_cup_qualified=True, trophy_count=1, reputation_gain=7),
        make_season(club_id="club-global", club_name="Global FC", season_index=4, league_finish=2, world_super_cup_qualified=True, world_super_cup_winner=True, trophy_count=2, reputation_gain=10),
    ]


@pytest.fixture()
def fallen_giant_seasons(make_season):
    return [
        make_season(club_id="club-fall", club_name="Fallen FC", season_index=1, league_finish=1, league_title=True, trophy_count=2, reputation_gain=10),
        make_season(club_id="club-fall", club_name="Fallen FC", season_index=2, league_finish=2, champions_league_title=True, world_super_cup_qualified=True, trophy_count=2, reputation_gain=9),
        make_season(club_id="club-fall", club_name="Fallen FC", season_index=3, league_finish=1, league_title=True, world_super_cup_qualified=True, trophy_count=2, reputation_gain=8),
        make_season(club_id="club-fall", club_name="Fallen FC", season_index=4, league_finish=3, trophy_count=1, reputation_gain=7),
        make_season(club_id="club-fall", club_name="Fallen FC", season_index=5, league_finish=7, trophy_count=0, reputation_gain=1),
        make_season(club_id="club-fall", club_name="Fallen FC", season_index=6, league_finish=8, trophy_count=0, reputation_gain=1),
        make_season(club_id="club-fall", club_name="Fallen FC", season_index=7, league_finish=9, trophy_count=0, reputation_gain=1),
        make_season(club_id="club-fall", club_name="Fallen FC", season_index=8, league_finish=10, trophy_count=0, reputation_gain=0),
    ]


@pytest.fixture()
def streak_reset_seasons(make_season):
    return [
        make_season(club_id="club-streak", club_name="Streak FC", season_index=1, league_finish=3, trophy_count=1, reputation_gain=5),
        make_season(club_id="club-streak", club_name="Streak FC", season_index=2, league_finish=2, trophy_count=1, reputation_gain=4),
        make_season(club_id="club-streak", club_name="Streak FC", season_index=3, league_finish=6, trophy_count=0, reputation_gain=-2),
        make_season(club_id="club-streak", club_name="Streak FC", season_index=4, league_finish=4, trophy_count=1, reputation_gain=3),
    ]


@pytest.fixture()
def api_client(global_dynasty_seasons, continental_dynasty_seasons, fallen_giant_seasons):
    app = FastAPI()
    app.include_router(router)
    app.state.dynasty_repository = InMemoryDynastyReadRepository(
        {
            "club-global": global_dynasty_seasons,
            "club-cont": continental_dynasty_seasons,
            "club-fall": fallen_giant_seasons,
        }
    )
    with TestClient(app) as client:
        yield client
