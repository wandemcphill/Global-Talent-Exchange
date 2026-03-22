from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.fast_cups.api.router import router
from app.fast_cups.models.domain import FastCup, FastCupDivision, FastCupEntrant
from app.fast_cups.services.ecosystem import FastCupEcosystemService

BASE_NOW = datetime(2026, 7, 1, 12, 2, tzinfo=UTC)


def _build_entrant(
    index: int,
    *,
    division: FastCupDivision,
    registered_at: datetime,
) -> FastCupEntrant:
    prefix = "academy" if division is FastCupDivision.ACADEMY else "senior"
    return FastCupEntrant(
        club_id=f"{prefix}-club-{index:03d}",
        club_name=f"{prefix.title()} Club {index:03d}",
        division=division,
        rating=5000 - index,
        registered_at=registered_at,
    )


def _select_cup(
    ecosystem: FastCupEcosystemService,
    *,
    now: datetime,
    division: FastCupDivision,
    size: int,
) -> FastCup:
    cups = ecosystem.list_upcoming_cups(now=now, horizon_intervals=4)
    return next(cup for cup in cups if cup.division is division and cup.size == size)


def _fill_cup(ecosystem: FastCupEcosystemService, cup: FastCup) -> FastCup:
    join_at = cup.slot.registration_opens_at + timedelta(minutes=3)
    updated = cup
    for index in range(1, cup.size + 1):
        updated = ecosystem.join_cup(
            cup_id=updated.cup_id,
            entrant=_build_entrant(index, division=updated.division, registered_at=join_at),
            now=join_at,
        )
    return updated


@pytest.fixture()
def base_now() -> datetime:
    return BASE_NOW


@pytest.fixture()
def ecosystem() -> FastCupEcosystemService:
    return FastCupEcosystemService()


@pytest.fixture()
def api_client(ecosystem: FastCupEcosystemService) -> TestClient:
    app = FastAPI()
    app.state.fast_cup_ecosystem = ecosystem
    app.include_router(router)
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def build_entrant():
    return _build_entrant


@pytest.fixture()
def select_cup():
    return _select_cup


@pytest.fixture()
def fill_cup():
    return _fill_cup
