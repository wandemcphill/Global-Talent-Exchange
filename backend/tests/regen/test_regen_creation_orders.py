from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import app.models  # noqa: F401
from app.auth.dependencies import get_current_user, get_session
from app.auth.service import AuthService
from app.ingestion.models import Country, Player
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.regen import RegenProfile
from app.models.regen_ecosystem import CareerEvent, RegenBloodlineLink
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.regen_universe.models import RegenAchievement, RegenStoryEvent
from app.regen_creation.router import router
from app.regen_creation.service import RegenCreationService
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        engine.dispose()


def _client(session, *, current_user: User | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def _create_user(session, *, email: str, username: str, full_name: str) -> User:
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",  # pragma: allowlist secret
        full_name=full_name,
    )
    session.commit()
    return user


def _create_club(session, *, owner: User, slug: str, name: str, country_code: str = "NG") -> ClubProfile:
    club = ClubProfile(
        owner_user_id=owner.id,
        club_name=name,
        short_name=name[:12],
        slug=slug,
        primary_color="#0057B8",
        secondary_color="#FFFFFF",
        accent_color="#F5B400",
        country_code=country_code,
        region_name="Lagos",
        city_name="Lagos",
    )
    session.add(club)
    session.commit()
    return club


def _create_country(session, *, code: str = "NG", name: str = "Nigeria") -> Country:
    country = Country(
        source_provider="manual",
        provider_external_id=f"country:{code}",
        name=name,
        alpha2_code=code,
        alpha3_code=code,
        fifa_code=code,
        confederation_code="CAF",
        market_region="test",
        is_enabled_for_universe=True,
    )
    session.add(country)
    session.commit()
    return country


def _create_player(
    session,
    *,
    club: ClubProfile,
    country: Country,
    external_id: str,
    full_name: str,
    position: str = "ST",
) -> Player:
    player = Player(
        source_provider="manual",
        provider_external_id=external_id,
        country_id=country.id,
        current_club_profile_id=club.id,
        full_name=full_name,
        first_name=full_name.split(" ", 1)[0],
        last_name=full_name.split(" ", 1)[1] if " " in full_name else None,
        short_name=full_name,
        position=position,
        normalized_position="forward",
        is_tradable=True,
    )
    session.add(player)
    session.commit()
    return player


def _fund_user(session, user: User, *, amount: Decimal) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference=f"fund-{user.id}",
        description="Seed wallet coin balance for request-son tests",
        actor=user,
    )
    session.commit()


def test_request_son_requires_authentication(session) -> None:
    client = _client(session)

    response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": "missing-parent",
            "payment_method": "wallet",
        },
    )

    assert response.status_code == 401


def test_request_son_options_list_owned_parent_players(session) -> None:
    user = _create_user(session, email="owner@example.com", username="ownerone", full_name="Owner One")
    club = _create_club(session, owner=user, slug="owner-one-fc", name="Owner One FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="parent-options",
        full_name="Victor Adebayo",
    )

    client = _client(session, current_user=user)
    response = client.get("/api/regens/request-son/options")

    assert response.status_code == 200
    payload = response.json()
    assert payload["club_id"] == club.id
    assert payload["eligible_parents"][0]["player_id"] == player.id
    assert payload["pricing"]["base_cost_coin"] is not None


def test_user_cannot_request_son_for_someone_elses_club(session) -> None:
    owner = _create_user(session, email="club-owner@example.com", username="clubowner", full_name="Club Owner")
    intruder = _create_user(session, email="intruder@example.com", username="intruder", full_name="Intruder User")
    club = _create_club(session, owner=owner, slug="club-owner-fc", name="Club Owner FC")
    _create_club(session, owner=intruder, slug="intruder-fc", name="Intruder FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="other-club-player",
        full_name="Emeka Okoye",
    )

    client = _client(session, current_user=intruder)
    response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "payment_method": "wallet",
        },
    )

    assert response.status_code == 403
    assert "own club" in response.json()["detail"].lower()


def test_pending_order_does_not_generate_regen_before_payment(session) -> None:
    user = _create_user(session, email="pending@example.com", username="pendinguser", full_name="Pending User")
    club = _create_club(session, owner=user, slug="pending-fc", name="Pending FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="pending-parent",
        full_name="Sodiq Balogun",
    )

    client = _client(session, current_user=user)
    response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "requested_name": "Afolabi Balogun",
            "requested_position": "ST",
            "payment_method": "wallet",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending_payment"
    regen_count = session.scalar(
        select(func.count(RegenProfile.id)).where(RegenProfile.generation_source == "requested_son")
    )
    assert int(regen_count or 0) == 0


def test_wallet_payment_generates_exactly_one_regen(session) -> None:
    user = _create_user(session, email="wallet@example.com", username="walletuser", full_name="Wallet User")
    club = _create_club(session, owner=user, slug="wallet-fc", name="Wallet FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="wallet-parent",
        full_name="Samuel Adeyemi",
    )
    _fund_user(session, user, amount=Decimal("500.0000"))

    client = _client(session, current_user=user)
    create_response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "requested_name": "Ayo Adeyemi",
            "requested_position": "ST",
            "payment_method": "wallet",
        },
    )
    assert create_response.status_code == 201
    order_id = create_response.json()["id"]

    pay_response = client.post(f"/api/regens/creation-orders/{order_id}/pay-with-wallet")

    assert pay_response.status_code == 200
    payload = pay_response.json()
    assert payload["status"] == "generated"
    assert payload["generated_player"] is not None
    assert payload["generated_player"]["full_name"].startswith("Ayo Adeyemi")

    regen_count = session.scalar(
        select(func.count(RegenProfile.id)).where(RegenProfile.generation_source == "requested_son")
    )
    bloodline_count = session.scalar(select(func.count(RegenBloodlineLink.id)))
    career_event_count = session.scalar(
        select(func.count(CareerEvent.id)).where(CareerEvent.type == "requested_son_created")
    )
    story_event_count = session.scalar(
        select(func.count(RegenStoryEvent.id)).where(RegenStoryEvent.event_type == "requested_son_created")
    )
    achievement_count = session.scalar(
        select(func.count(RegenAchievement.id)).where(RegenAchievement.achievement_type == "requested_son_created")
    )
    assert int(regen_count or 0) == 1
    assert int(bloodline_count or 0) == 1
    assert int(career_event_count or 0) == 1
    assert int(story_event_count or 0) == 1
    assert int(achievement_count or 0) == 1


def test_duplicate_generation_call_returns_existing_generated_regen(session) -> None:
    user = _create_user(session, email="duplicate@example.com", username="duplicateuser", full_name="Duplicate User")
    club = _create_club(session, owner=user, slug="duplicate-fc", name="Duplicate FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="duplicate-parent",
        full_name="Kelechi Nwosu",
    )
    _fund_user(session, user, amount=Decimal("500.0000"))

    client = _client(session, current_user=user)
    create_response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "requested_name": "Chinedu Nwosu",
            "payment_method": "wallet",
        },
    )
    order_id = create_response.json()["id"]

    first_response = client.post(f"/api/regens/creation-orders/{order_id}/pay-with-wallet")
    second_response = client.post(f"/api/regens/creation-orders/{order_id}/generate-after-payment")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["generated_player_id"] == second_response.json()["generated_player_id"]
    regen_count = session.scalar(
        select(func.count(RegenProfile.id)).where(RegenProfile.generation_source == "requested_son")
    )
    assert int(regen_count or 0) == 1


def test_korapay_paid_callback_generates_exactly_once(session, monkeypatch: pytest.MonkeyPatch) -> None:
    user = _create_user(session, email="korapay@example.com", username="korapayuser", full_name="Korapay User")
    club = _create_club(session, owner=user, slug="korapay-fc", name="Korapay FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="korapay-parent",
        full_name="Musa Danjuma",
    )

    client = _client(session, current_user=user)
    create_response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "requested_name": "Haruna Danjuma",
            "requested_position": "RW",
            "payment_method": "korapay",
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["payment_reference"] is not None
    assert payload["payment_link"] is not None
    assert payload["status"] == "pending_payment"

    expected_amount = (Decimal(str(payload["amount_minor"])) / Decimal("100")).quantize(Decimal("0.0001"))
    monkeypatch.setattr(
        RegenCreationService,
        "_verify_korapay_transaction",
        lambda self, *, reference: {
            "data": {
                "id": f"verify-{reference}",
                "status": "success",
                "payment_reference": reference,
                "reference": reference,
                "amount": expected_amount,
            }
        },
    )

    order_id = payload["id"]
    first_generate = client.post(f"/api/regens/creation-orders/{order_id}/generate-after-payment")
    second_generate = client.post(f"/api/regens/creation-orders/{order_id}/generate-after-payment")

    assert first_generate.status_code == 200
    assert second_generate.status_code == 200
    assert first_generate.json()["generated_player_id"] == second_generate.json()["generated_player_id"]
    regen_count = session.scalar(
        select(func.count(RegenProfile.id)).where(RegenProfile.generation_source == "requested_son")
    )
    assert int(regen_count or 0) == 1
