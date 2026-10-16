from __future__ import annotations

from datetime import date
from time import perf_counter

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.legend_layer.registry import (
    LAUNCH_REGISTRY_SIZE,
    REGISTRY_SCHEMA_VERSION,
    LegendaryRegistry,
    LegendaryRegistryError,
    seed_legendary_registry,
)
from app.market.service import MarketPlayerQueryService
from app.models.base import Base
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User, UserRole
from app.national_team_engine.tournament_service import NationalTeamTournamentService


def _payload(count: int = LAUNCH_REGISTRY_SIZE) -> dict:
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "records": [
            {
                "legendary_profile_id": f"legend-{index:04d}",
                "full_name": f"Legendary Player {index:04d}",
                "nationality": "Nigeria" if index % 2 else "Brazil",
                "nationality_code": "NGA" if index % 2 else "BRA",
                "primary_position": "ST" if index % 3 else "CM",
                "market_value_eur": 1_000_000 + index,
                "date_of_birth": date(1970, 1, 1).isoformat(),
                "is_active": True,
                "is_tradable": True,
                "rental_policy": "existing_rules",
            }
            for index in range(count)
        ],
    }


def _session():
    load_model_modules()
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    actor = User(
        id="legendary-registry-operator",
        email="legendary-registry-operator@example.com",
        username="legendary-registry-operator",
        password_hash="hash",
        role=UserRole.ADMIN,
    )
    session.add(actor)
    session.flush()
    return session, actor, engine


def test_launch_registry_rejects_non_launch_and_duplicate_payloads() -> None:
    payload = _payload(2)
    payload["records"][1]["legendary_profile_id"] = payload["records"][0]["legendary_profile_id"]
    with pytest.raises(LegendaryRegistryError, match="duplicate"):
        LegendaryRegistry.from_payload(payload, expected_count=2)

    payload = _payload(2)
    payload["records"][0]["is_active"] = False
    with pytest.raises(LegendaryRegistryError, match="active"):
        LegendaryRegistry.from_payload(payload, expected_count=2)


def test_2000_registry_is_idempotent_searchable_market_ready_and_nationally_eligible() -> None:
    session, actor, _ = _session()
    try:
        registry = LegendaryRegistry.from_payload(_payload())
        first = seed_legendary_registry(session, registry=registry, actor=actor)
        session.commit()
        second = seed_legendary_registry(session, registry=registry, actor=actor)
        session.commit()

        assert first == {
            "total": LAUNCH_REGISTRY_SIZE,
            "created": LAUNCH_REGISTRY_SIZE,
            "updated": 0,
            "markets_issued": LAUNCH_REGISTRY_SIZE,
            "markets_existing": 0,
        }
        assert second == {
            "total": LAUNCH_REGISTRY_SIZE,
            "created": 0,
            "updated": LAUNCH_REGISTRY_SIZE,
            "markets_issued": 0,
            "markets_existing": LAUNCH_REGISTRY_SIZE,
        }
        assert session.scalar(select(func.count()).select_from(Player).where(Player.source_provider == "legendary_player_foundation")) == 2000
        assert session.scalar(select(func.count()).select_from(PlayerShareMarket)) == 2000

        started = perf_counter()
        search = MarketPlayerQueryService(session).list_players(search="Legendary Player 1999", limit=20)
        assert [item.player_id for item in search.items]
        assert perf_counter() - started < 10.0

        # The normal pool query applies the country filter before its cap. The
        # pool's existing cap/ranking rules still decide which eligible player
        # is offered, so this deliberately checks a normal in-pool candidate,
        # not an invented legendary exception.
        pool = NationalTeamTournamentService(session)._national_pool(
            filters=NationalTeamTournamentService(session)._normalize_pool_filters(country_code="NGA"), limit=300
        )
        assert any(item["player_name"] == "Legendary Player 0001" for item in pool)
        assert all(item["country_code"] in {"NG", "NGA"} for item in pool)
    finally:
        session.close()


def test_relevant_indexes_are_declared_without_legendary_specific_tables() -> None:
    session, _, engine = _session()
    try:
        indexes = {index["name"] for index in inspect(engine).get_indexes("ingestion_players")}
        assert "ix_ingestion_players_country_id" in indexes
        assert "ix_ingestion_players_full_name" in indexes
        unique_constraints = {item["name"] for item in inspect(engine).get_unique_constraints("ingestion_players")}
        assert "uq_ingestion_players_provider_external_id" in unique_constraints
        assert "legendary" not in " ".join(inspect(engine).get_table_names()).lower()
    finally:
        session.close()
