from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.champions_league.api.router import router
from app.champions_league.models.domain import AdvancementStatus, ClubCandidate, ClubSeed, LeagueStandingRow


def _build_candidates(total: int = 60) -> list[ClubCandidate]:
    regions = ("Africa", "Americas", "Asia", "Europe")
    tiers = ("tier_1", "tier_2", "tier_3", "tier_4")
    clubs: list[ClubCandidate] = []
    for index in range(total):
        clubs.append(
            ClubCandidate(
                club_id=f"club-{index + 1:02d}",
                club_name=f"Club {index + 1:02d}",
                region=regions[index % len(regions)],
                tier=tiers[index % len(tiers)],
                ranking_points=1600 - (index * 7),
                domestic_rank=(index % 8) + 1,
            )
        )
    return clubs


def _build_league_clubs(total: int = 36) -> list[ClubSeed]:
    return [
        ClubSeed(
            club_id=f"league-club-{index:02d}",
            club_name=f"League Club {index:02d}",
            seed=index,
            region="Europe" if index % 2 else "Africa",
            tier="tier_1" if index <= 12 else "tier_2",
        )
        for index in range(1, total + 1)
    ]


def _build_standings_rows(total: int = 36) -> list[LeagueStandingRow]:
    rows: list[LeagueStandingRow] = []
    for rank in range(1, total + 1):
        advancement = AdvancementStatus.ELIMINATED
        if rank <= 8:
            advancement = AdvancementStatus.ROUND_OF_16
        elif rank <= 24:
            advancement = AdvancementStatus.KNOCKOUT_PLAYOFF
        rows.append(
            LeagueStandingRow(
                club_id=f"standings-club-{rank:02d}",
                club_name=f"Standings Club {rank:02d}",
                seed=rank,
                played=6,
                wins=max(0, 7 - ((rank + 2) // 6)),
                draws=rank % 2,
                losses=max(0, 6 - (max(0, 7 - ((rank + 2) // 6)) + (rank % 2))),
                goals_for=60 - rank,
                goals_against=rank // 2,
                goal_difference=(60 - rank) - (rank // 2),
                points=120 - rank,
                rank=rank,
                advancement_status=advancement,
            )
        )
    return rows


@pytest.fixture()
def api_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def build_candidates():
    return _build_candidates


@pytest.fixture()
def build_league_clubs():
    return _build_league_clubs


@pytest.fixture()
def build_standings_rows():
    return _build_standings_rows
