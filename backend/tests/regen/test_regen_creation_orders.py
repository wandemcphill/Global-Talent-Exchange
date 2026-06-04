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
from app.core.events import InMemoryEventPublisher
from app.ingestion.models import Country, Player
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.regen import RegenProfile
from app.models.regen_creation_order import RegenCreationOrder, RegenCreationOrderStatus
from app.models.regen_ecosystem import CareerEvent, RegenBloodlineLink
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransaction, LedgerUnit
from app.regen_universe.models import RegenAchievement, RegenStoryEvent
from app.regen_universe.service import RegenUniverseService
from app.regen_creation.router import router
from app.regen_creation.schemas import RequestSonCreateRequest
from app.regen_creation.service import RegenCreationService, RegenCreationValidationError
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


def _client(
    session,
    *,
    current_user: User | None = None,
    event_publisher: InMemoryEventPublisher | None = None,
) -> TestClient:
    app = FastAPI()
    if event_publisher is not None:
        app.state.event_publisher = event_publisher
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


def _create_country(
    session,
    *,
    code: str = "NG",
    name: str = "Nigeria",
    enabled: bool = True,
    market_region: str = "test",
) -> Country:
    country = Country(
        source_provider="manual",
        provider_external_id=f"country:{code}",
        name=name,
        alpha2_code=code,
        alpha3_code=code,
        fifa_code=code,
        confederation_code="CAF",
        market_region=market_region,
        is_enabled_for_universe=enabled,
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
    dna_profile: dict[str, object] | None = None,
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
        dna_profile=dna_profile
        or {
            "current_rating": 72,
            "generation": 1,
            "traits": ["line breaker", "press resistant", "late runner"],
            "archetype": "poacher",
            "tempo": 0.71,
            "risk_taking": 0.58,
            "creativity": 0.46,
            "discipline": 0.56,
        },
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


def _request_son_payload(player: Player, *, requested_name: str = "Event Jr") -> dict[str, object]:
    return {
        "parent_player_id": player.id,
        "selected_traits": ["line breaker", "press resistant", "late runner"],
        "requested_name": requested_name,
        "payment_method": "wallet",
    }


def test_request_son_requires_authentication(session) -> None:
    client = _client(session)

    response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": "missing-parent",
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "payment_method": "wallet",
        },
    )

    assert response.status_code == 401


def test_request_son_options_list_owned_parent_players(session) -> None:
    user = _create_user(session, email="owner@example.com", username="ownerone", full_name="Owner One")
    club = _create_club(session, owner=user, slug="owner-one-fc", name="Owner One FC")
    country = _create_country(session)
    _create_country(session, code="GH", name="Ghana", market_region="west-africa")
    _create_country(session, code="BR", name="Brazil", enabled=False)
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
    parent_payload = payload["eligible_parents"][0]
    assert parent_payload["player_id"] == player.id
    assert parent_payload["current_rating"] == 72
    assert parent_payload["nationality"] == "Nigeria"
    assert parent_payload["traits"] == ["line breaker", "press resistant", "late runner"]
    assert parent_payload["generation"] == 1
    assert parent_payload["dna_profile"]["archetype"] == "poacher"
    assert payload["default_country_code"] == "NG"
    assert payload["default_position"] == "AM"
    nationality_codes = [item["code"] for item in payload["nationality_options"]]
    assert nationality_codes == ["GH", "NG"]
    assert payload["nationality_options"][0]["name"] == "Ghana"
    assert payload["nationality_options"][0]["market_region"] == "west-africa"
    assert payload["nationality_options"][1]["is_default"] is True
    assert "BR" not in nationality_codes
    position_options = {item["code"]: item for item in payload["position_options"]}
    assert set(position_options) == {"GK", "CB", "RB", "LB", "DM", "CM", "AM", "RW", "LW", "ST"}
    assert position_options["AM"]["is_default"] is True
    assert position_options["AM"]["aliases"] == ["CAM"]
    assert position_options["ST"]["aliases"] == ["CF"]
    assert payload["pricing"]["base_cost_coin"] is not None


def test_request_son_options_filter_parents_without_three_selectable_traits(session) -> None:
    user = _create_user(
        session,
        email="parent-filter@example.com",
        username="parentfilter",
        full_name="Parent Filter",
    )
    club = _create_club(session, owner=user, slug="parent-filter-fc", name="Parent Filter FC")
    country = _create_country(session)
    eligible_parent = _create_player(
        session,
        club=club,
        country=country,
        external_id="eligible-parent",
        full_name="Eligible Parent",
        dna_profile={
            "current_rating": 74,
            "generation": 1,
            "traits": ["line breaker", "press resistant", "late runner"],
        },
    )
    _create_player(
        session,
        club=club,
        country=country,
        external_id="blocked-parent",
        full_name="Blocked Parent",
        dna_profile={
            "current_rating": 70,
            "generation": 1,
            "traits": ["line breaker", "line-breaker", "line breaker"],
        },
    )

    client = _client(session, current_user=user)
    response = client.get("/api/regens/request-son/options")

    assert response.status_code == 200
    parent_ids = [item["player_id"] for item in response.json()["eligible_parents"]]
    assert parent_ids == [eligible_parent.id]


def test_request_son_options_filter_parents_missing_canonical_truth(session) -> None:
    user = _create_user(
        session,
        email="parent-truth@example.com",
        username="parenttruth",
        full_name="Parent Truth",
    )
    club = _create_club(session, owner=user, slug="parent-truth-fc", name="Parent Truth FC")
    country = _create_country(session)
    eligible_parent = _create_player(
        session,
        club=club,
        country=country,
        external_id="truth-eligible-parent",
        full_name="Truth Eligible",
    )
    _create_player(
        session,
        club=club,
        country=country,
        external_id="truth-missing-generation",
        full_name="Missing Generation",
        dna_profile={
            "current_rating": 71,
            "traits": ["line breaker", "press resistant", "late runner"],
            "tempo": 0.62,
        },
    )
    _create_player(
        session,
        club=club,
        country=country,
        external_id="truth-missing-rating",
        full_name="Missing Rating",
        dna_profile={
            "generation": 1,
            "traits": ["line breaker", "press resistant", "late runner"],
            "tempo": 0.62,
        },
    )
    _create_player(
        session,
        club=club,
        country=country,
        external_id="truth-missing-position",
        full_name="Missing Position",
        position="",
    )
    missing_country = _create_player(
        session,
        club=club,
        country=country,
        external_id="truth-missing-country",
        full_name="Missing Country",
    )
    missing_country.country_id = None
    session.commit()

    client = _client(session, current_user=user)
    response = client.get("/api/regens/request-son/options")

    assert response.status_code == 200
    parent_ids = [item["player_id"] for item in response.json()["eligible_parents"]]
    assert parent_ids == [eligible_parent.id]


def test_request_son_preview_rejects_parent_missing_canonical_truth(session) -> None:
    user = _create_user(
        session,
        email="preview-truth@example.com",
        username="previewtruth",
        full_name="Preview Truth",
    )
    club = _create_club(session, owner=user, slug="preview-truth-fc", name="Preview Truth FC")
    country = _create_country(session)
    parent = _create_player(
        session,
        club=club,
        country=country,
        external_id="preview-missing-generation",
        full_name="Preview Missing Generation",
        dna_profile={
            "current_rating": 72,
            "traits": ["line breaker", "press resistant", "late runner"],
            "tempo": 0.71,
            "risk_taking": 0.58,
            "creativity": 0.46,
            "discipline": 0.56,
        },
    )
    _fund_user(session, user, amount=Decimal("500.0000"))

    client = _client(session, current_user=user)
    response = client.post(
        "/api/regens/request-son/preview",
        json={
            "parent_player_id": parent.id,
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "requested_name": "Truth Son",
            "requested_country_code": "NG",
            "requested_position": "ST",
            "payment_method": "wallet",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "request_son_parent_missing_generation"


def test_request_son_preview_returns_backend_projection_and_wallet_state(session) -> None:
    user = _create_user(session, email="preview@example.com", username="previewuser", full_name="Preview User")
    club = _create_club(session, owner=user, slug="preview-fc", name="Preview FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="preview-parent",
        full_name="Tomi Adebayo",
    )
    _fund_user(session, user, amount=Decimal("500.0000"))

    client = _client(session, current_user=user)
    response = client.post(
        "/api/regens/request-son/preview",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["late runner", "line breaker", "press resistant"],
            "requested_name": "Tayo Adebayo",
            "requested_country_code": "NG",
            "requested_position": "ST",
            "payment_method": "wallet",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["parent"]["player_id"] == player.id
    assert payload["selected_traits"] == ["late runner", "line breaker", "press resistant"]
    assert set(payload["projected_dna"]) == {"PAC", "SHO", "PAS", "DRI", "DEF", "PHY"}
    assert all(1 <= value <= 99 for value in payload["projected_dna"].values())
    assert isinstance(payload["projected_dna_profile"], dict)
    assert payload["projected_dna_profile"]
    assert payload["projected_ovr"] > 0
    assert payload["projected_pot"] >= payload["projected_ovr"]
    assert payload["parent_generation"] == 1
    assert payload["projected_generation"] == 2
    assert payload["generation_label"] == "GEN-2"
    assert Decimal(str(payload["total_cost_coin"])) > Decimal("0.0000")
    assert payload["wallet"]["can_pay_with_wallet"] is True
    assert payload["wallet"]["available_balance"] == "500.0000"
    assert payload["wallet"]["reserved_balance"] == "0.0000"
    assert payload["wallet"]["locked_balance"] == "0.0000"
    assert payload["wallet"]["pending_withdrawal_balance"] == "0.0000"
    assert payload["wallet"]["total_balance"] == "500.0000"
    assert payload["wallet"]["currency"] == "coin"
    assert payload["wallet"]["lock_reasons"] == []
    assert payload["wallet"]["blocked_reason"] is None
    assert payload["blocked_reason"] is None


def test_request_son_requires_exactly_three_selected_traits(session) -> None:
    user = _create_user(session, email="traits@example.com", username="traitsuser", full_name="Traits User")
    club = _create_club(session, owner=user, slug="traits-fc", name="Traits FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="traits-parent",
        full_name="Kunle Traits",
    )

    client = _client(session, current_user=user)
    response = client.post(
        "/api/regens/request-son/preview",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "press resistant"],
            "payment_method": "wallet",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize("payment_method", ["korapay", "manual", "bank_transfer_manual"])
def test_request_son_rejects_external_payment_methods(session, payment_method: str) -> None:
    user = _create_user(
        session,
        email=f"external-{payment_method}@example.com",
        username=f"external{payment_method.replace('_', '')}",
        full_name="External Payment",
    )
    club = _create_club(session, owner=user, slug=f"external-{payment_method}-fc", name="External Payment FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id=f"external-{payment_method}-parent",
        full_name="External Parent",
    )

    client = _client(session, current_user=user)
    response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "payment_method": payment_method,
        },
    )

    assert response.status_code == 422
    order_count = session.scalar(select(func.count(RegenCreationOrder.id)))
    assert int(order_count or 0) == 0


def test_request_son_service_rejects_external_payment_method_before_order_creation(session) -> None:
    user = _create_user(
        session,
        email="service-external@example.com",
        username="serviceexternal",
        full_name="Service External",
    )
    payload = RequestSonCreateRequest.model_construct(
        parent_player_id="parent-1",
        selected_traits=["line breaker", "press resistant", "late runner"],
        payment_method="korapay",
    )

    with pytest.raises(
        RegenCreationValidationError,
        match="request_son_requires_wallet_payment",
    ):
        RegenCreationService(session).create_request_son_order(
            actor=user,
            payload=payload,
        )

    order_count = session.scalar(select(func.count(RegenCreationOrder.id)))
    assert int(order_count or 0) == 0


def test_request_son_rejects_traits_not_owned_by_parent(session) -> None:
    user = _create_user(session, email="wrongtraits@example.com", username="wrongtraits", full_name="Wrong Traits")
    club = _create_club(session, owner=user, slug="wrong-traits-fc", name="Wrong Traits FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="wrong-traits-parent",
        full_name="Wrong Trait Parent",
    )

    client = _client(session, current_user=user)
    response = client.post(
        "/api/regens/request-son/preview",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "press resistant", "invented aura"],
            "payment_method": "wallet",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "selected_traits_must_belong_to_parent"


def test_request_son_rejects_canonical_duplicate_selected_traits(session) -> None:
    user = _create_user(
        session,
        email="duplicate-traits@example.com",
        username="duplicatetraits",
        full_name="Duplicate Traits",
    )
    club = _create_club(session, owner=user, slug="duplicate-traits-fc", name="Duplicate Traits FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="duplicate-traits-parent",
        full_name="Duplicate Trait Parent",
    )

    client = _client(session, current_user=user)
    response = client.post(
        "/api/regens/request-son/preview",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "line-breaker", "late runner"],
            "payment_method": "wallet",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "selected_traits_must_be_three_unique_parent_traits"


def test_wallet_request_son_order_requires_available_wallet_balance(session) -> None:
    user = _create_user(
        session,
        email="insufficient-wallet@example.com",
        username="insufficientwallet",
        full_name="Insufficient Wallet",
    )
    club = _create_club(session, owner=user, slug="insufficient-wallet-fc", name="Insufficient Wallet FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="insufficient-wallet-parent",
        full_name="Insufficient Wallet Parent",
    )

    client = _client(session, current_user=user)
    preview_response = client.post(
        "/api/regens/request-son/preview",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "payment_method": "wallet",
        },
    )
    create_response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "payment_method": "wallet",
        },
    )

    assert preview_response.status_code == 200
    assert preview_response.json()["wallet"]["blocked_reason"] == "insufficient_wallet_balance"
    assert create_response.status_code == 400
    assert create_response.json()["detail"] == "insufficient_wallet_balance"


def test_wallet_request_son_create_reserves_then_settles_on_confirmation(session) -> None:
    user = _create_user(
        session,
        email="wallet-create-debit@example.com",
        username="walletcreatedebit",
        full_name="Wallet Create Debit",
    )
    club = _create_club(session, owner=user, slug="wallet-create-debit-fc", name="Wallet Create Debit FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="wallet-create-debit-parent",
        full_name="Immediate Debit Parent",
    )
    _fund_user(session, user, amount=Decimal("250.0000"))

    client = _client(session, current_user=user)
    first_response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "requested_name": "Immediate Debit Jr",
            "payment_method": "wallet",
        },
    )
    assert first_response.status_code == 201
    first_payload = first_response.json()
    order_id = first_payload["id"]
    amount_coin = Decimal(str(first_payload["amount_coin"]))
    assert first_payload["status"] == "pending_payment"
    assert first_payload["payment_provider"] == "wallet"
    assert first_payload["payment_reference"] == f"regen-wallet-reserve:{order_id}"
    assert first_payload["wallet_reservation"]["status"] == "reserved"
    assert first_payload["wallet_reservation"]["kind"] == "regen_creation_order"
    assert first_payload["wallet_reservation"]["key"] == order_id
    assert first_payload["wallet_reservation"]["amount_coin"] == str(amount_coin)
    assert first_payload["wallet_reservation"]["reference"] == f"regen-wallet-reserve:{order_id}"
    assert first_payload["wallet_reservation"]["lock_reason"] == "Build-a-Son creation reservation"
    assert first_payload["paid_at"] is None

    summary = WalletService().get_wallet_summary(session, user, currency=LedgerUnit.COIN)
    assert summary.available_balance == Decimal("250.0000") - amount_coin
    assert summary.reserved_balance == amount_coin
    assert summary.locked_balance == amount_coin
    assert len(summary.lock_reasons) == 1
    assert summary.lock_reasons[0].code == "regen_creation_order_reservation"
    assert summary.lock_reasons[0].label == "Build-a-Son creation reservation"
    assert summary.lock_reasons[0].reference == order_id

    second_preview = client.post(
        "/api/regens/request-son/preview",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "requested_name": "Second Debit Jr",
            "payment_method": "wallet",
        },
    )
    assert second_preview.status_code == 200
    assert second_preview.json()["wallet"]["blocked_reason"] == "insufficient_wallet_balance"
    assert second_preview.json()["wallet"]["reserved_balance"] == str(amount_coin)
    assert second_preview.json()["wallet"]["locked_balance"] == str(amount_coin)
    assert second_preview.json()["wallet"]["lock_reasons"] == [f"Build-a-Son creation reservation: {amount_coin} coin"]

    paid_response = client.post(f"/api/regens/creation-orders/{order_id}/pay-with-wallet")
    assert paid_response.status_code == 200
    paid_payload = paid_response.json()
    assert paid_payload["status"] == "generated"
    assert paid_payload["payment_reference"] == f"regen-wallet-{order_id}"
    assert paid_payload["wallet_reservation"]["status"] == "settled"
    assert paid_payload["wallet_reservation"]["reference"] == f"regen-wallet-settle:{order_id}"
    assert paid_payload["paid_at"] is not None
    assert paid_payload["generated_player"] is not None

    settled_summary = WalletService().get_wallet_summary(session, user, currency=LedgerUnit.COIN)
    assert settled_summary.available_balance == Decimal("250.0000") - amount_coin
    assert settled_summary.reserved_balance == Decimal("0.0000")
    assert settled_summary.lock_reasons == ()

    second_response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "requested_name": "Second Debit Jr",
            "payment_method": "wallet",
        },
    )
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "owner_son_paid_request_limit_reached"

    reserve_count = session.scalar(
        select(func.count(LedgerTransaction.id)).where(
            LedgerTransaction.idempotency_key == f"regen-wallet-reserve:{order_id}",
            LedgerTransaction.source_tag == LedgerSourceTag.COSMETIC_SPEND,
        )
    )
    settle_count = session.scalar(
        select(func.count(LedgerTransaction.id)).where(
            LedgerTransaction.idempotency_key == f"regen-wallet-settle:{order_id}",
            LedgerTransaction.source_tag == LedgerSourceTag.COSMETIC_SPEND,
        )
    )
    assert int(reserve_count or 0) == 1
    assert int(settle_count or 0) == 1


def test_request_son_lifecycle_events_use_app_publisher(session) -> None:
    user = _create_user(
        session,
        email="regen-events@example.com",
        username="regenevents",
        full_name="Regen Events",
    )
    club = _create_club(session, owner=user, slug="regen-events-fc", name="Regen Events FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="regen-events-parent",
        full_name="Event Parent",
    )
    _fund_user(session, user, amount=Decimal("250.0000"))
    publisher = InMemoryEventPublisher()
    client = _client(session, current_user=user, event_publisher=publisher)

    create_response = client.post("/api/regens/request-son", json=_request_son_payload(player))
    assert create_response.status_code == 201
    create_payload = create_response.json()
    order_id = create_payload["id"]
    assert create_payload["audit_reference"] == f"regen-creation-order:{order_id}"

    create_event_names = [event.name for event in publisher.published_events]
    assert "regen.creation_order.created" in create_event_names
    assert "wallet.transaction.appended" in create_event_names
    assert any(
        event.name == "wallet.transaction.appended" and event.payload["reference"] == f"regen-wallet-reserve:{order_id}"
        for event in publisher.published_events
    )
    created_event = next(event for event in publisher.published_events if event.name == "regen.creation_order.created")
    assert created_event.payload["order_id"] == order_id
    assert created_event.payload["status"] == "pending_payment"
    assert created_event.payload["previous_status"] is None
    assert created_event.payload["wallet_reservation"]["status"] == "reserved"
    assert created_event.payload["audit_reference"] == f"regen-creation-order:{order_id}:created"
    assert created_event.headers["audit_reference"] == f"regen-creation-order:{order_id}:created"

    pay_response = client.post(f"/api/regens/creation-orders/{order_id}/pay-with-wallet")
    assert pay_response.status_code == 200
    pay_payload = pay_response.json()
    assert pay_payload["status"] == "generated"
    assert pay_payload["audit_reference"] == f"regen-creation-order:{order_id}"

    event_names = [event.name for event in publisher.published_events]
    assert "regen.creation_order.paid" in event_names
    assert "regen.creation_order.generated" in event_names
    assert any(
        event.name == "wallet.transaction.appended" and event.payload["reference"] == f"regen-wallet-settle:{order_id}"
        for event in publisher.published_events
    )
    paid_event = next(event for event in publisher.published_events if event.name == "regen.creation_order.paid")
    generated_event = next(
        event for event in publisher.published_events if event.name == "regen.creation_order.generated"
    )
    assert paid_event.payload["previous_status"] == "pending_payment"
    assert paid_event.payload["status"] == "paid"
    assert paid_event.payload["wallet_reservation"]["status"] == "settled"
    assert generated_event.payload["previous_status"] == "paid"
    assert generated_event.payload["status"] == "generated"
    assert generated_event.payload["generated_player_id"] == pay_payload["generated_player_id"]
    assert generated_event.payload["audit_reference"] == f"regen-creation-order:{order_id}:generated"


def test_request_son_cancel_event_uses_app_publisher(session) -> None:
    user = _create_user(
        session,
        email="regen-cancel-event@example.com",
        username="regencancelevent",
        full_name="Regen Cancel Event",
    )
    club = _create_club(session, owner=user, slug="regen-cancel-event-fc", name="Regen Cancel Event FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="regen-cancel-event-parent",
        full_name="Cancel Event Parent",
    )
    _fund_user(session, user, amount=Decimal("250.0000"))
    publisher = InMemoryEventPublisher()
    client = _client(session, current_user=user, event_publisher=publisher)

    create_response = client.post(
        "/api/regens/request-son",
        json=_request_son_payload(player, requested_name="Cancel Event Jr"),
    )
    assert create_response.status_code == 201
    order_id = create_response.json()["id"]
    publisher.published_events.clear()

    cancel_response = client.post(f"/api/regens/creation-orders/{order_id}/cancel")
    assert cancel_response.status_code == 200
    cancel_payload = cancel_response.json()
    assert cancel_payload["status"] == "cancelled"
    assert cancel_payload["audit_reference"] == f"regen-creation-order:{order_id}"

    event_names = [event.name for event in publisher.published_events]
    assert "regen.creation_order.cancelled" in event_names
    assert any(
        event.name == "wallet.transaction.appended" and event.payload["reference"] == f"regen-wallet-release:{order_id}"
        for event in publisher.published_events
    )
    cancelled_event = next(
        event for event in publisher.published_events if event.name == "regen.creation_order.cancelled"
    )
    assert cancelled_event.payload["order_id"] == order_id
    assert cancelled_event.payload["previous_status"] == "pending_payment"
    assert cancelled_event.payload["status"] == "cancelled"
    assert cancelled_event.payload["wallet_reservation"]["status"] == "released"
    assert cancelled_event.payload["audit_reference"] == f"regen-creation-order:{order_id}:cancelled"


def test_wallet_request_son_cancel_releases_reserved_balance(session) -> None:
    user = _create_user(
        session,
        email="wallet-cancel@example.com",
        username="walletcancel",
        full_name="Wallet Cancel",
    )
    club = _create_club(session, owner=user, slug="wallet-cancel-fc", name="Wallet Cancel FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="wallet-cancel-parent",
        full_name="Cancel Reserve Parent",
    )
    _fund_user(session, user, amount=Decimal("250.0000"))

    client = _client(session, current_user=user)
    create_response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "requested_name": "Cancel Reserve Jr",
            "payment_method": "wallet",
        },
    )
    assert create_response.status_code == 201
    order_payload = create_response.json()
    order_id = order_payload["id"]
    amount_coin = Decimal(str(order_payload["amount_coin"]))

    reserved_summary = WalletService().get_wallet_summary(session, user, currency=LedgerUnit.COIN)
    assert reserved_summary.available_balance == Decimal("250.0000") - amount_coin
    assert reserved_summary.reserved_balance == amount_coin

    cancel_response = client.post(f"/api/regens/creation-orders/{order_id}/cancel")
    assert cancel_response.status_code == 200
    cancel_payload = cancel_response.json()
    assert cancel_payload["status"] == "cancelled"
    assert cancel_payload["payment_reference"] == f"regen-wallet-reserve:{order_id}"
    assert cancel_payload["wallet_reservation"]["status"] == "released"
    assert cancel_payload["wallet_reservation"]["reference"] == f"regen-wallet-release:{order_id}"
    assert cancel_payload["paid_at"] is None
    assert cancel_payload["generated_player"] is None

    released_summary = WalletService().get_wallet_summary(session, user, currency=LedgerUnit.COIN)
    assert released_summary.available_balance == Decimal("250.0000")
    assert released_summary.reserved_balance == Decimal("0.0000")
    assert released_summary.lock_reasons == ()

    second_cancel = client.post(f"/api/regens/creation-orders/{order_id}/cancel")
    assert second_cancel.status_code == 200
    assert second_cancel.json()["wallet_reservation"]["status"] == "released"

    reserve_count = session.scalar(
        select(func.count(LedgerTransaction.id)).where(
            LedgerTransaction.idempotency_key == f"regen-wallet-reserve:{order_id}",
            LedgerTransaction.source_tag == LedgerSourceTag.COSMETIC_SPEND,
        )
    )
    release_count = session.scalar(
        select(func.count(LedgerTransaction.id)).where(
            LedgerTransaction.idempotency_key == f"regen-wallet-release:{order_id}",
            LedgerTransaction.source_tag == LedgerSourceTag.COSMETIC_SPEND,
        )
    )
    assert int(reserve_count or 0) == 1
    assert int(release_count or 0) == 1


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
            "selected_traits": ["line breaker", "press resistant", "late runner"],
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
    _fund_user(session, user, amount=Decimal("500.0000"))

    client = _client(session, current_user=user)
    response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "requested_name": "Afolabi Balogun",
            "requested_position": "CAM",
            "payment_method": "wallet",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending_payment"
    assert payload["payment_provider"] == "wallet"
    assert payload["wallet_reservation"]["status"] == "reserved"
    assert payload["selected_traits"] == ["line breaker", "press resistant", "late runner"]
    assert payload["requested_position"] == "AM"
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
            "selected_traits": ["line breaker", "press resistant", "late runner"],
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
    generated_payload = payload["generated_player"]
    assert generated_payload["full_name"].startswith("Ayo Adeyemi")
    order = session.get(RegenCreationOrder, order_id)
    generated_player = session.get(Player, payload["generated_player_id"])
    generated_regen = session.get(RegenProfile, payload["generated_regen_profile_id"])
    assert order is not None
    assert generated_player is not None
    assert generated_regen is not None
    saved_preview = order.metadata_json["request_son_preview"]
    assert generated_payload["current_rating"] == saved_preview["projected_ovr"]
    assert generated_payload["potential_rating"] == saved_preview["projected_pot"]
    assert generated_payload["generation_number"] == 2
    assert generated_payload["generation_label"] == "GEN-2"
    assert generated_payload["traits"] == ["line breaker", "press resistant", "late runner"]
    assert generated_payload["lineage"] == ["Samuel Adeyemi", generated_payload["full_name"]]
    assert generated_payload["dna_profile"] == saved_preview["projected_dna"]
    assert generated_player.dna_profile["traits"] == ["line breaker", "press resistant", "late runner"]
    assert generated_player.dna_profile["generation"] == 2
    assert generated_player.dna_profile["generation_label"] == "GEN-2"
    for key in ("archetype", "tempo", "risk_taking", "creativity", "discipline"):
        assert generated_player.dna_profile[key] == saved_preview["projected_dna_profile"][key]
    assert generated_regen.current_gsi == saved_preview["projected_ovr"]
    assert generated_regen.current_ability_range_json == {
        "minimum": saved_preview["projected_ovr"],
        "maximum": saved_preview["projected_ovr"],
    }
    assert generated_regen.potential_range_json == {
        "minimum": saved_preview["projected_ovr"],
        "maximum": saved_preview["projected_pot"],
    }
    assert generated_player.market_value_eur == float(saved_preview["projected_ovr"]) * 12_500.0
    assert generated_player.dna_profile["projected_dna"] == saved_preview["projected_dna"]
    for code, value in saved_preview["projected_dna"].items():
        assert generated_player.dna_profile[code] == value
    assert generated_player.dna_profile["selected_traits"] == saved_preview["selected_traits"]
    assert generated_regen.metadata_json["current_rating"] == saved_preview["projected_ovr"]
    assert generated_regen.metadata_json["potential_rating"] == saved_preview["projected_pot"]
    assert generated_regen.metadata_json["projected_ovr"] == saved_preview["projected_ovr"]
    assert generated_regen.metadata_json["projected_pot"] == saved_preview["projected_pot"]
    assert generated_regen.metadata_json["selected_traits"] == ["line breaker", "press resistant", "late runner"]
    assert generated_regen.metadata_json["projected_dna"] == saved_preview["projected_dna"]
    assert generated_regen.metadata_json["lineage"]["parent_player_id"] == player.id
    assert generated_regen.metadata_json["lineage"]["parent_generation"] == 1
    assert generated_regen.metadata_json["lineage"]["generation"] == 2
    assert generated_regen.metadata_json["projected_value_coin"] > 0
    assert generated_regen.metadata_json["rarity_tier"] == "rare"

    universe_lookup = RegenUniverseService(session).get_player_lookup(generated_player.id)
    assert universe_lookup is not None
    universe_player = universe_lookup["player"]
    assert universe_player["source_type"] == "requested_son"
    assert universe_player["generation_number"] == 2
    assert universe_player["generation_label"] == "GEN-2"
    assert universe_player["rarity_tier"] == "rare"
    assert universe_player["projected_value_coin"] == generated_regen.metadata_json["projected_value_coin"]
    assert universe_player["traits"] == ["line breaker", "press resistant", "late runner"]
    assert universe_player["lineage"] == ["Samuel Adeyemi", generated_payload["full_name"]]
    assert universe_player["dna_profile"]["projected_dna"] == saved_preview["projected_dna"]

    options_response = client.get("/api/regens/request-son/options")
    assert options_response.status_code == 200
    generated_parent_payload = next(
        item for item in options_response.json()["eligible_parents"] if item["player_id"] == generated_player.id
    )
    assert generated_parent_payload["traits"] == ["line breaker", "press resistant", "late runner"]
    assert generated_parent_payload["generation"] == 2
    assert generated_parent_payload["dna_profile"]["generation_label"] == "GEN-2"

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


def test_wallet_payment_reconciles_order_and_debits_wallet_once(session) -> None:
    user = _create_user(
        session,
        email="wallet-reconcile@example.com",
        username="walletreconcile",
        full_name="Wallet Reconcile",
    )
    club = _create_club(session, owner=user, slug="wallet-reconcile-fc", name="Wallet Reconcile FC")
    country = _create_country(session)
    player = _create_player(
        session,
        club=club,
        country=country,
        external_id="wallet-reconcile-parent",
        full_name="Tunde Reconcile",
    )
    _fund_user(session, user, amount=Decimal("500.0000"))

    client = _client(session, current_user=user)
    create_response = client.post(
        "/api/regens/request-son",
        json={
            "parent_player_id": player.id,
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "requested_name": "Bayo Reconcile",
            "requested_position": "CM",
            "payment_method": "wallet",
        },
    )
    assert create_response.status_code == 201
    order_payload = create_response.json()
    order_id = order_payload["id"]
    amount_coin = Decimal(str(order_payload["amount_coin"]))

    first_pay = client.post(f"/api/regens/creation-orders/{order_id}/pay-with-wallet")
    second_pay = client.post(f"/api/regens/creation-orders/{order_id}/pay-with-wallet")

    assert first_pay.status_code == 200
    assert second_pay.status_code == 200
    assert first_pay.json()["status"] == "generated"
    assert second_pay.json()["status"] == "generated"
    assert first_pay.json()["generated_player_id"] == second_pay.json()["generated_player_id"]
    assert first_pay.json()["payment_provider"] == "wallet"
    assert first_pay.json()["payment_reference"] == f"regen-wallet-{order_id}"

    summary = WalletService().get_wallet_summary(session, user, currency=LedgerUnit.COIN)
    assert summary.available_balance == Decimal("500.0000") - amount_coin
    assert summary.reserved_balance == Decimal("0.0000")
    reserve_count = session.scalar(
        select(func.count(LedgerTransaction.id)).where(
            LedgerTransaction.idempotency_key == f"regen-wallet-reserve:{order_id}",
            LedgerTransaction.source_tag == LedgerSourceTag.COSMETIC_SPEND,
        )
    )
    settle_count = session.scalar(
        select(func.count(LedgerTransaction.id)).where(
            LedgerTransaction.idempotency_key == f"regen-wallet-settle:{order_id}",
            LedgerTransaction.source_tag == LedgerSourceTag.COSMETIC_SPEND,
        )
    )
    assert int(reserve_count or 0) == 1
    assert int(settle_count or 0) == 1


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
            "selected_traits": ["line breaker", "press resistant", "late runner"],
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
