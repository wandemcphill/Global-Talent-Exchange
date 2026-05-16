from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.core.database import get_session
from app.models.admin_rules import AdminRewardRule
from app.models.economy_config import ServicePricingRule
from app.models.economy_governor import EconomyGovernorPolicy
from app.models.event_backbone import EventOutbox
from app.models.fast_match import FastMatchEntitlement, FastMatchSession, FastMatchSettlement
from app.models.risk_ops import AuditLog
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerAccount, LedgerBalanceProjection, LedgerEntry, LedgerTransaction
from app.simulation_matchmaking.router import router


def _build_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    AdminRewardRule.__table__.create(engine)
    ServicePricingRule.__table__.create(engine)
    EconomyGovernorPolicy.__table__.create(engine)
    LedgerAccount.__table__.create(engine)
    LedgerBalanceProjection.__table__.create(engine)
    LedgerTransaction.__table__.create(engine)
    LedgerEntry.__table__.create(engine)
    EventOutbox.__table__.create(engine)
    AuditLog.__table__.create(engine)
    FastMatchEntitlement.__table__.create(engine)
    FastMatchSettlement.__table__.create(engine)
    FastMatchSession.__table__.create(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return SessionLocal()


@pytest.fixture()
def client() -> TestClient:
    session = _build_session()
    user = User(
        id="user_123",
        email="user123@example.com",
        username="user123",
        display_name="Lagos United Owner",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    session.add_all(
        [
            user,
            ServicePricingRule(
                service_key="fast-match-entry",
                title="Fast Match entry",
                description="Fan Coin entry fee after free run",
                price_coin=Decimal("0.0000"),
                price_fancoin_equivalent=Decimal("25.0000"),
                active=True,
            ),
        ]
    )
    session.commit()

    def override_session():
        yield session

    application = FastAPI()
    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_current_user] = lambda: session.get(User, "user_123")
    application.include_router(router)
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()
    session.close()


def _profile(
    user_id: str,
    club_id: str,
    club_name: str,
    *,
    manager_rating: int,
    style: str,
    pressing: str,
    tempo: str,
    squad_strength: int,
    squad_depth: int,
    region: str = "AF-WEST",
) -> dict[str, object]:
    return {
        "user_id": user_id,
        "club_id": club_id,
        "club_name": club_name,
        "manager_rating": manager_rating,
        "tactical_profile": {
            "style": style,
            "pressing": pressing,
            "tempo": tempo,
        },
        "squad_strength": squad_strength,
        "squad_depth": squad_depth,
        "preferred_match_type": ["quick", "tournament", "hosted"],
        "connection_quality": "good",
        "region": region,
        "availability": "online",
    }


def _register_profiles(client: TestClient, prefix: str, *profiles: dict[str, object]) -> None:
    for profile in profiles:
        response = client.put(f"{prefix}/profiles/{profile['user_id']}", json=profile)
        assert response.status_code == 200


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_profile_upsert_round_trip(client: TestClient, prefix: str) -> None:
    payload = _profile(
        "user_123",
        "club_abc",
        "Lagos United",
        manager_rating=1420,
        style="possession",
        pressing="high",
        tempo="fast",
        squad_strength=78,
        squad_depth=65,
    )

    put_response = client.put(f"{prefix}/profiles/user_123", json=payload)
    get_response = client.get(f"{prefix}/profiles/user_123")

    assert put_response.status_code == 200
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["club_name"] == "Lagos United"
    assert body["manager_rating"] == 1420
    assert body["tactical_profile"]["style"] == "possession"


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_quick_game_prefers_tactical_clash_when_requested(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
        _profile(
            "user_456",
            "club_def",
            "Accra Breakers",
            manager_rating=1440,
            style="counter",
            pressing="medium",
            tempo="fast",
            squad_strength=80,
            squad_depth=66,
        ),
        _profile(
            "user_789",
            "club_ghi",
            "Abuja Control",
            manager_rating=1410,
            style="balanced",
            pressing="medium",
            tempo="normal",
            squad_strength=77,
            squad_depth=67,
        ),
    )

    response = client.post(
        f"{prefix}/quick-game",
        json={
            "mode": "quick_game",
            "user_id": "user_123",
            "preferences": {
                "match_style": "tactical_clash",
                "allow_tactical_clash": True,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["opponent"]["user_id"] == "user_456"
    assert body["match_context"]["type"] == "tactical_clash"
    assert body["simulation_bridge"]["recommended_mode"] == "live"
    assert body["simulation_bridge"]["match_engine_request"]["home_team"]["team_name"] == "Lagos United"


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_quick_game_falls_back_to_ai_when_queue_empty(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
    )

    response = client.post(
        f"{prefix}/quick-game",
        json={
            "mode": "quick_game",
            "user_id": "user_123",
            "preferences": {
                "match_style": "balanced",
                "allow_tactical_clash": True,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["opponent"]["is_bot"] is True
    assert body["match_context"]["queue_source"] == "bot"
    assert body["charge_on_loss"] is True
    assert body["entry_currency"] == "credit"
    assert body["entry_currency_label"] == "Fan Coin"
    assert body["fan_coin_entry_fee"] == "25.0000"
    assert body["free_matches_used"] == 1
    assert body["live_match_key"].startswith("fast-match:")
    assert body["rules_copy"] == "Play free until you lose or reach 10 matches."


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_fast_match_entitlement_endpoint_tracks_persisted_free_usage(
    client: TestClient,
    prefix: str,
) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
    )

    before = client.get(f"{prefix}/fast-match/entitlement")
    assert before.status_code == 200
    assert before.json()["free_matches_remaining"] == 10

    response = client.post(
        f"{prefix}/quick-game",
        json={
            "mode": "quick_game",
            "user_id": "user_123",
            "include_bots": True,
        },
    )
    assert response.status_code == 200

    after = client.get(f"{prefix}/fast-match/entitlement")
    assert after.status_code == 200
    body = after.json()
    assert body["free_matches_used"] == 1
    assert body["free_matches_remaining"] == 9
    assert body["entry_currency"] == "credit"
    assert body["entry_currency_label"] == "Fan Coin"


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_quick_game_allows_explicit_ai_fallback(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
    )

    response = client.post(
        f"{prefix}/quick-game",
        json={
            "mode": "quick_game",
            "user_id": "user_123",
            "include_bots": True,
            "preferences": {
                "match_style": "balanced",
                "allow_tactical_clash": True,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["opponent"]["is_bot"] is True
    assert body["match_context"]["queue_source"] == "bot"


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_quick_tournament_avoids_same_style_in_round_one(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
        _profile(
            "user_456",
            "club_def",
            "Accra Breakers",
            manager_rating=1440,
            style="counter",
            pressing="medium",
            tempo="fast",
            squad_strength=80,
            squad_depth=66,
        ),
        _profile(
            "user_789",
            "club_ghi",
            "Abuja Control",
            manager_rating=1410,
            style="balanced",
            pressing="medium",
            tempo="normal",
            squad_strength=77,
            squad_depth=67,
        ),
        _profile(
            "user_654",
            "club_jkl",
            "Kumasi Direct",
            manager_rating=1395,
            style="direct",
            pressing="high",
            tempo="fast",
            squad_strength=76,
            squad_depth=63,
        ),
    )

    response = client.post(
        f"{prefix}/quick-tournament",
        json={
            "mode": "quick_tournament",
            "user_id": "user_123",
            "size": 4,
            "preferences": {
                "avoid_same_style_early": True,
                "allow_bots": False,
                "preferred_execution_mode": "hybrid",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["narrative"] == "Clash of styles tournament"
    first_round = body["bracket"][0]["matches"]
    assert len(first_round) == 2
    for match in first_round:
        assert match["home"]["tactical_profile"]["style"] != match["away"]["tactical_profile"]["style"]


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_hosted_competition_preview_exposes_marketplace_hooks(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
        _profile(
            "user_456",
            "club_def",
            "Accra Breakers",
            manager_rating=1440,
            style="counter",
            pressing="medium",
            tempo="fast",
            squad_strength=80,
            squad_depth=66,
        ),
        _profile(
            "user_789",
            "club_ghi",
            "Abuja Control",
            manager_rating=1410,
            style="balanced",
            pressing="medium",
            tempo="normal",
            squad_strength=77,
            squad_depth=67,
        ),
        _profile(
            "user_654",
            "club_jkl",
            "Kumasi Direct",
            manager_rating=1395,
            style="direct",
            pressing="high",
            tempo="fast",
            squad_strength=76,
            squad_depth=63,
        ),
    )

    response = client.post(
        f"{prefix}/hosted-competitions/preview",
        json={
            "host_user_id": "user_123",
            "competition_type": "transfer_showcase_cup",
            "target_club_count": 4,
            "simulation_mode": "hybrid",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["format"] == "knockout"
    assert len(body["qualified_clubs"]) == 4
    assert body["marketplace_hooks"]["transfer_demand_updates"] is True


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_hosted_competition_preview_rejects_ai_or_bot_clubs(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
        _profile(
            "user_456",
            "club_def",
            "Accra Breakers",
            manager_rating=1440,
            style="counter",
            pressing="medium",
            tempo="fast",
            squad_strength=80,
            squad_depth=66,
        ),
    )

    response = client.post(
        f"{prefix}/hosted-competitions/preview",
        json={
            "host_user_id": "user_123",
            "competition_type": "transfer_showcase_cup",
            "target_club_count": 4,
            "simulation_mode": "hybrid",
            "allow_bots": True,
        },
    )

    assert response.status_code == 422
    assert "do not allow AI or bot participants" in response.text
