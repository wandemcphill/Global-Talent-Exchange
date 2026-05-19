from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
import app.players.read_models  # noqa: F401
from app.core.config import get_settings
from app.ingestion.models import Player
from app.models.integrity import IntegrityIncident
from app.models.base import Base
from app.models.card_access import CardSwapExecution
from app.models.club_profile import ClubProfile
from app.models.player_cards import (
    PlayerCard,
    PlayerCardHolding,
    PlayerCardListing,
    PlayerCardSale,
    PlayerCardTier,
    PlayerCardMomentum,
    PlayerMarketValueSnapshot,
    PlayerStatsSnapshot,
)
from app.models.regen import RegenOnboardingFlag, RegenProfile
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.real_world_football import PlayerDemandSignal, RealWorldFootballEvent, TrendingPlayerFlag
from app.models.risk_ops import SystemEvent
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.market.player_eligibility_policy import market_access_payload
from app.player_cards.marketplace_service import PlayerCardMarketplaceService
from app.player_cards.service import PlayerCardMarketService, PlayerCardValidationError
from app.player_import_engine.service import PlayerImportService
from app.players.read_models import PlayerSummaryReadModel
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
    with SessionLocal() as db_session:
        yield db_session


@pytest.fixture(autouse=True)
def _configure_test_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GTE_DATABASE_URL", "sqlite+pysqlite:///:memory:")


def _create_user(session, *, user_id: str, email: str, username: str, role: UserRole = UserRole.USER) -> User:
    user = User(id=user_id, email=email, username=username, password_hash="hashed", role=role)
    session.add(user)
    session.flush()
    return user


def _create_player(
    session, *, player_id: str, name: str, position: str = "forward", value_eur: float = 2_000_000
) -> Player:
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=player_id,
        full_name=name,
        position=position.upper(),
        normalized_position=position.lower(),
        market_value_eur=value_eur,
        is_tradable=True,
    )
    session.add(player)
    session.flush()
    return player


def _create_summary(
    session,
    *,
    player: Player,
    club_name: str = "GTEX FC",
    rating: float = 7.5,
    value_credits: float = 20.0,
    summary_json: dict[str, object] | None = None,
) -> None:
    summary = PlayerSummaryReadModel(
        player_id=player.id,
        player_name=player.full_name,
        current_club_name=club_name,
        last_snapshot_at=player.last_synced_at,
        current_value_credits=value_credits,
        previous_value_credits=value_credits,
        movement_pct=0.0,
        average_rating=rating,
        market_interest_score=0,
        summary_json=summary_json or {},
    )
    session.add(summary)
    session.flush()


def _create_tier(session, *, tier_id: str, code: str) -> PlayerCardTier:
    tier = PlayerCardTier(
        id=tier_id,
        code=code,
        name=code.title(),
        rarity_rank=1,
        max_supply=1000,
        supply_multiplier=1.0,
        base_mint_price_credits=Decimal("10.0"),
        color_hex="#FFD700",
        is_active=True,
        metadata_json={},
    )
    session.add(tier)
    session.flush()
    return tier


def _create_card(session, *, card_id: str, player: Player, tier: PlayerCardTier, variant: str = "base") -> PlayerCard:
    card = PlayerCard(
        id=card_id,
        player_id=player.id,
        tier_id=tier.id,
        edition_code="base",
        display_name=f"{player.full_name} {tier.name}",
        season_label="2026",
        card_variant=variant,
        supply_total=10,
        supply_available=10,
        is_active=True,
        metadata_json={},
    )
    session.add(card)
    session.flush()
    return card


def _create_stats_snapshot(
    session,
    *,
    player_id: str,
    stats_json: dict[str, object],
) -> PlayerStatsSnapshot:
    snapshot = PlayerStatsSnapshot(
        player_id=player_id,
        as_of=datetime.now(UTC),
        source_type="match_engine",
        stats_json=stats_json,
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def _create_real_world_event(session, *, player_id: str, event_id: str) -> RealWorldFootballEvent:
    event = RealWorldFootballEvent(
        id=event_id,
        player_id=player_id,
        event_type="match.spike",
        source_type="manual",
        source_label="test-suite",
        dedupe_key=f"dedupe:{event_id}",
        title="Market spike",
        severity=1.0,
        occurred_at=datetime.now(UTC),
        approved_at=datetime.now(UTC),
        metadata_json={},
        raw_payload_json={},
        normalized_payload_json={},
    )
    session.add(event)
    session.flush()
    return event


def _seed_wallet(session, wallet: WalletService, user: User, *, amount: Decimal) -> None:
    account = wallet.get_user_account(session, user, LedgerUnit.COIN)
    platform = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=platform, amount=-amount),
            LedgerPosting(account=account, amount=amount),
        ],
        reason=LedgerEntryReason.DEPOSIT,
        reference=f"seed-{user.id}",
        description="seed funds",
        actor=user,
    )


def test_free_regen_loan_floor_and_settlement(session) -> None:
    lender = _create_user(session, user_id="lender", email="lender@example.com", username="lender")
    borrower = _create_user(session, user_id="borrower", email="borrower@example.com", username="borrower")
    player = _create_player(
        session, player_id="player-regen", name="Regen Star", position="forward", value_eur=2_000_000
    )
    _create_summary(session, player=player, rating=8.1, value_credits=20.0)
    tier = _create_tier(session, tier_id="tier-regen", code="elite")
    card = _create_card(session, card_id="card-regen", player=player, tier=tier, variant="regen_unique")
    session.add(
        PlayerCardHolding(
            player_card_id=card.id, owner_user_id=lender.id, quantity_total=1, quantity_reserved=0, metadata_json={}
        )
    )
    session.flush()

    wallet = WalletService()
    _seed_wallet(session, wallet, borrower, amount=Decimal("10.0000"))
    service = PlayerCardMarketplaceService(session=session, wallet_service=wallet)
    platform_account = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    platform_balance_before = wallet.get_balance(session, platform_account)

    listing = service.create_loan_listing(
        actor=lender, player_card_id=card.id, total_slots=1, duration_days=7, loan_fee_credits=Decimal("0.0000")
    )
    negotiation = service.create_loan_negotiation(
        actor=borrower,
        listing_id=listing["listing_id"],
        proposed_duration_days=7,
        proposed_loan_fee_credits=Decimal("0.0000"),
    )
    contract = service.accept_loan_negotiation(actor=lender, negotiation_id=negotiation["negotiation_id"])
    settled = service.settle_loan_contract(actor=borrower, contract_id=contract["loan_contract_id"])

    lender_balance = wallet.get_balance(session, wallet.get_user_account(session, lender, LedgerUnit.COIN))
    borrower_balance = wallet.get_balance(session, wallet.get_user_account(session, borrower, LedgerUnit.COIN))
    platform_balance = wallet.get_balance(session, platform_account)

    assert settled["fee_floor_applied"] is True
    assert settled["effective_loan_fee_credits"] == Decimal("1.0000")
    assert settled["platform_fee_credits"] == Decimal("0.4000")
    assert settled["lender_net_credits"] == Decimal("0.6000")
    assert lender_balance == Decimal("0.6000")
    assert borrower_balance == Decimal("9.0000")
    assert platform_balance - platform_balance_before == Decimal("0.4000")

    returned = service.return_loan_contract(actor=borrower, contract_id=contract["loan_contract_id"])
    assert returned["status"] == "returned"


def test_real_player_sale_can_settle_with_runtime_value_fallback(session) -> None:
    seller = _create_user(
        session, user_id="real-sale-seller", email="real-sale-seller@example.com", username="real-sale-seller"
    )
    buyer = _create_user(
        session, user_id="real-sale-buyer", email="real-sale-buyer@example.com", username="real-sale-buyer"
    )
    player = _create_player(
        session,
        player_id="real-sale-player",
        name="Real Sale Player",
        position="forward",
        value_eur=25_000_000,
    )
    player.is_real_player = True
    tier = _create_tier(session, tier_id="tier-real-sale", code="elite-real-sale")
    card = _create_card(session, card_id="card-real-sale", player=player, tier=tier)
    session.add(
        PlayerCardHolding(
            player_card_id=card.id,
            owner_user_id=seller.id,
            quantity_total=1,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    session.flush()

    wallet = WalletService()
    _seed_wallet(session, wallet, buyer, amount=Decimal("100.0000"))
    service = PlayerCardMarketplaceService(session=session, wallet_service=wallet)

    listing = service.create_sale_listing(
        actor=seller,
        player_card_id=card.id,
        quantity=1,
        price_per_card_credits=Decimal("20.0000"),
    )
    sale = service.buy_sale_listing(actor=buyer, listing_id=listing["listing_id"])

    assert listing["latest_value_credits"] > 0
    assert sale["status"] == "settled"
    assert sale["price_per_card_credits"] == Decimal("20.0000")


def test_real_player_loan_accepts_with_runtime_value_fallback(session) -> None:
    lender = _create_user(
        session, user_id="real-loan-lender", email="real-loan-lender@example.com", username="real-loan-lender"
    )
    borrower = _create_user(
        session,
        user_id="real-loan-borrower",
        email="real-loan-borrower@example.com",
        username="real-loan-borrower",
    )
    player = _create_player(
        session,
        player_id="real-loan-player",
        name="Real Loan Player",
        position="midfielder",
        value_eur=25_000_000,
    )
    player.is_real_player = True
    tier = _create_tier(session, tier_id="tier-real-loan", code="elite-real-loan")
    card = _create_card(session, card_id="card-real-loan", player=player, tier=tier)
    session.add(
        PlayerCardHolding(
            player_card_id=card.id,
            owner_user_id=lender.id,
            quantity_total=1,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())
    listing = service.create_loan_listing(
        actor=lender,
        player_card_id=card.id,
        total_slots=1,
        duration_days=7,
        loan_fee_credits=Decimal("0.0000"),
    )
    negotiation = service.create_loan_negotiation(
        actor=borrower,
        listing_id=listing["listing_id"],
        proposed_duration_days=7,
        proposed_loan_fee_credits=Decimal("0.0000"),
    )
    contract = service.accept_loan_negotiation(actor=lender, negotiation_id=negotiation["negotiation_id"])

    assert contract["status"] == "accepted_pending_settlement"
    assert contract["effective_loan_fee_credits"] > Decimal("0.0000")
    assert contract["fee_floor_applied"] is True


def test_starter_regen_card_cannot_enter_user_market(session) -> None:
    owner = _create_user(session, user_id="starter-owner", email="starter-owner@example.com", username="starter-owner")
    player = _create_player(session, player_id="player-starter-regen", name="Starter Regen", position="midfielder")
    _create_summary(session, player=player, rating=6.8, value_credits=12.0)
    tier = _create_tier(session, tier_id="tier-starter-regen", code="starter-regen")
    card = _create_card(session, card_id="card-starter-regen", player=player, tier=tier, variant="regen_unique")
    club = ClubProfile(
        id="club-starter-regen",
        owner_user_id=owner.id,
        club_name="Starter FC",
        slug="starter-fc",
        primary_color="#111111",
        secondary_color="#222222",
        accent_color="#333333",
        country_code="NG",
        region_name="Lagos",
        city_name="Ajah",
    )
    regen = RegenProfile(
        id="regen-starter-profile",
        regen_id="regen-starter-profile",
        player_id=player.id,
        linked_unique_card_id=card.id,
        generated_for_club_id=club.id,
        birth_country_code="NG",
        primary_position="CM",
        current_gsi=60,
        current_ability_range_json={"minimum": 55, "maximum": 62},
        potential_range_json={"minimum": 68, "maximum": 76},
        scout_confidence="medium",
        generation_source="new_club",
        club_quality_score=50.0,
        metadata_json={},
    )
    onboarding = RegenOnboardingFlag(
        regen_id=regen.id,
        club_id=club.id,
        onboarding_type="starter_bundle",
        squad_bucket="first_team",
        is_non_tradable=True,
        replacement_only=True,
        metadata_json={},
    )
    session.add_all([club, regen, onboarding])
    session.add(
        PlayerCardHolding(
            player_card_id=card.id, owner_user_id=owner.id, quantity_total=1, quantity_reserved=0, metadata_json={}
        )
    )
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())
    with pytest.raises(PlayerCardValidationError, match="starter_regen_non_tradeable"):
        service.create_sale_listing(
            actor=owner,
            player_card_id=card.id,
            quantity=1,
            price_per_card_credits=Decimal("10.0000"),
        )
    with pytest.raises(PlayerCardValidationError, match="starter_regen_non_tradeable"):
        service.create_loan_listing(
            actor=owner,
            player_card_id=card.id,
            total_slots=1,
            duration_days=7,
            loan_fee_credits=Decimal("1.0000"),
        )
    with pytest.raises(PlayerCardValidationError, match="starter_regen_non_tradeable"):
        service.create_swap_listing(actor=owner, player_card_id=card.id)


def test_preseeded_national_regens_cannot_be_card_minted(session) -> None:
    admin = _create_user(session, user_id="card-admin", email="card-admin@example.com", username="card-admin")
    _create_tier(session, tier_id="tier-preseed-block", code="elite-preseed-block")
    seed = NationalRegenSeed(
        seed_key="seed:card:block",
        display_name="Mamadou Faye",
        age=18,
        age_band="u20",
        country_code="SN",
        country_name="Senegal",
        seed_type="preseeded_national_pool",
        primary_position="RW",
        current_rating=70,
        potential_rating=84,
        growth_curve=0.72,
        rarity_tier="rare",
        status="available",
        metadata_json={},
    )
    session.add(seed)
    session.flush()

    service = PlayerCardMarketService(session=session)
    with pytest.raises(
        PlayerCardValidationError,
        match="national-pool-only and cannot be card minted",
    ):
        service.apply_supply_batch(
            actor=admin,
            player_id=seed.id,
            tier_code="elite-preseed-block",
            quantity=1,
            edition_code="base",
            season_label="2026",
            batch_key="batch:preseed:block",
            owner_user_id=admin.id,
            source_type="admin_seed",
            source_reference="seed:card:block",
        )


def test_admin_can_mint_preseeded_regen_card_and_owner_can_list_it(session) -> None:
    admin = _create_user(
        session,
        user_id="card-admin-mint",
        email="card-admin-mint@example.com",
        username="card-admin-mint",
        role=UserRole.ADMIN,
    )
    owner = _create_user(session, user_id="regen-owner", email="regen-owner@example.com", username="regen-owner")
    _create_tier(session, tier_id="tier-preseed-mint", code="elite-preseed-mint")
    seed = NationalRegenSeed(
        seed_key="seed:card:mint",
        display_name="Moussa Diop",
        age=18,
        age_band="u20",
        country_code="SN",
        country_name="Senegal",
        seed_type="preseeded_national_pool",
        primary_position="ST",
        current_rating=72,
        potential_rating=88,
        growth_curve=0.78,
        rarity_tier="elite",
        status="available",
        metadata_json={},
    )
    session.add(seed)
    session.flush()

    service = PlayerCardMarketService(session=session)
    batch = service.apply_preseeded_national_regen_supply_batch(
        actor=admin,
        seed_id=seed.id,
        tier_code="elite-preseed-mint",
        quantity=2,
        edition_code="preseeded_regen",
        season_label="2026",
        batch_key="batch:preseed:mint",
        owner_user_id=owner.id,
        source_reference=None,
    )

    player = session.get(Player, batch.player_id)
    card = session.get(PlayerCard, batch.player_card_id)
    holding = session.scalar(
        select(PlayerCardHolding).where(
            PlayerCardHolding.owner_user_id == owner.id,
            PlayerCardHolding.player_card_id == batch.player_card_id,
        )
    )
    access = market_access_payload(seed)
    player_access = market_access_payload(player)

    assert player is not None
    assert player.id != seed.id
    assert player.dna_profile["national_seed_id"] == seed.id
    assert player.dna_profile["admin_trade_enabled"] is True
    assert seed.metadata_json["minted_player_id"] == player.id
    assert seed.metadata_json["national_pool_only"] is False
    assert access["card_mint_eligible"] is True
    assert access["tradable"] is True
    assert access["national_pool_only"] is False
    assert player_access["is_preseeded_national_regen"] is True
    assert player_access["admin_trade_enabled"] is True
    assert player_access["national_pool_only"] is False
    assert card is not None
    assert card.card_variant == "preseeded_regen"
    assert holding is not None
    assert holding.quantity_total == 2

    listing = service.create_listing(
        actor=owner,
        player_card_id=batch.player_card_id,
        quantity=1,
        price_per_card_credits=Decimal("12.0000"),
    )
    assert listing["status"] == "open"


def test_card_supply_import_can_mint_preseeded_regen_with_national_seed_id(session) -> None:
    admin = _create_user(
        session,
        user_id="card-import-admin",
        email="card-import-admin@example.com",
        username="card-import-admin",
        role=UserRole.ADMIN,
    )
    owner = _create_user(
        session,
        user_id="card-import-owner",
        email="card-import-owner@example.com",
        username="card-import-owner",
    )
    _create_tier(session, tier_id="tier-preseed-import", code="elite-preseed-import")
    seed = NationalRegenSeed(
        seed_key="seed:card:import",
        display_name="Ibrahima Kane",
        age=19,
        age_band="u20",
        country_code="SN",
        country_name="Senegal",
        seed_type="preseeded_national_pool",
        primary_position="AM",
        current_rating=71,
        potential_rating=86,
        growth_curve=0.75,
        rarity_tier="rare",
        status="available",
        metadata_json={},
    )
    session.add(seed)
    session.flush()

    job, items = PlayerImportService(session).create_card_supply_job(
        actor=admin,
        source_label="preseed import",
        rows=[
            {
                "national_seed_id": seed.id,
                "tier_code": "elite-preseed-import",
                "quantity": 1,
                "edition_code": "preseeded_regen",
                "owner_user_id": owner.id,
                "batch_key": "batch:preseed:import",
            }
        ],
        commit=True,
    )

    assert job.imported_items == 1
    assert items[0].linked_player_id is not None
    assert items[0].linked_player_id != seed.id
    assert (
        session.scalar(
            select(PlayerCardHolding)
            .join(PlayerCard)
            .where(
                PlayerCard.player_id == items[0].linked_player_id,
                PlayerCardHolding.owner_user_id == owner.id,
            )
        )
        is not None
    )


def test_sale_listing_guardrails_reject_price_outside_reference_band(session) -> None:
    seller = _create_user(session, user_id="guard-seller", email="guard-seller@example.com", username="guard-seller")
    player = _create_player(session, player_id="guard-player", name="Guarded Price")
    _create_summary(session, player=player, value_credits=20.0)
    tier = _create_tier(session, tier_id="tier-guard", code="elite")
    card = _create_card(session, card_id="card-guard", player=player, tier=tier)
    session.add(
        PlayerCardHolding(
            player_card_id=card.id, owner_user_id=seller.id, quantity_total=1, quantity_reserved=0, metadata_json={}
        )
    )
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())

    with pytest.raises(PlayerCardValidationError, match="Listing price must stay between"):
        service.create_sale_listing(
            actor=seller,
            player_card_id=card.id,
            quantity=1,
            price_per_card_credits=Decimal("50.0000"),
        )

    assert session.scalar(select(func.count(PlayerCardListing.id))) == 0


def test_sale_listing_relist_cooldown_persists_integrity_snapshot(session) -> None:
    seller = _create_user(
        session, user_id="cooldown-seller", email="cooldown-seller@example.com", username="cooldown-seller"
    )
    player = _create_player(session, player_id="cooldown-player", name="Cooldown Seller")
    _create_summary(session, player=player, value_credits=20.0)
    tier = _create_tier(session, tier_id="tier-cooldown", code="gold")
    card = _create_card(session, card_id="card-cooldown", player=player, tier=tier)
    session.add(
        PlayerCardHolding(
            player_card_id=card.id, owner_user_id=seller.id, quantity_total=2, quantity_reserved=0, metadata_json={}
        )
    )
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())
    listing = service.create_sale_listing(
        actor=seller,
        player_card_id=card.id,
        quantity=1,
        price_per_card_credits=Decimal("18.0000"),
    )
    stored_listing = session.scalar(
        select(PlayerCardListing).where(PlayerCardListing.listing_id == listing["listing_id"])
    )

    assert stored_listing is not None
    assert stored_listing.integrity_context_json["reference_source"] == "player_summary.current_value"
    assert stored_listing.integrity_context_json["relist_cooldown_active"] is False

    service.cancel_sale_listing(actor=seller, listing_id=listing["listing_id"])
    with pytest.raises(PlayerCardValidationError, match="relist cooldown"):
        service.create_sale_listing(
            actor=seller,
            player_card_id=card.id,
            quantity=1,
            price_per_card_credits=Decimal("18.0000"),
        )


def test_sale_integrity_signals_repeated_pair_and_price_anomaly(session) -> None:
    seller = _create_user(session, user_id="signal-seller", email="signal-seller@example.com", username="signal-seller")
    buyer = _create_user(session, user_id="signal-buyer", email="signal-buyer@example.com", username="signal-buyer")
    player = _create_player(session, player_id="signal-player", name="Signal Player")
    _create_summary(session, player=player, value_credits=12.0)
    tier = _create_tier(session, tier_id="tier-signal", code="elite")
    card = _create_card(session, card_id="card-signal", player=player, tier=tier)
    session.add(
        PlayerCardHolding(
            player_card_id=card.id, owner_user_id=seller.id, quantity_total=3, quantity_reserved=0, metadata_json={}
        )
    )
    session.flush()

    wallet = WalletService()
    _seed_wallet(session, wallet, buyer, amount=Decimal("100.0000"))
    base_settings = get_settings()
    integrity_config = replace(
        base_settings.player_card_market_integrity,
        listing_price_ceiling_ratio=3.50,
        price_spike_alert_ratio=2.00,
    )
    service = PlayerCardMarketplaceService(
        session=session,
        wallet_service=wallet,
        settings=replace(base_settings, player_card_market_integrity=integrity_config),
    )

    for price in (Decimal("10.0000"), Decimal("10.0000"), Decimal("30.0000")):
        listing = service.create_sale_listing(
            actor=seller, player_card_id=card.id, quantity=1, price_per_card_credits=price
        )
        service.buy_sale_listing(actor=buyer, listing_id=listing["listing_id"])

    incidents = session.scalars(
        select(IntegrityIncident).where(IntegrityIncident.incident_type == "repeated_card_trade_pair")
    ).all()
    latest_sale = session.scalar(
        select(PlayerCardSale)
        .where(PlayerCardSale.player_card_id == card.id)
        .order_by(PlayerCardSale.created_at.desc())
    )
    anomaly_event = session.scalar(select(SystemEvent).where(SystemEvent.event_type == "player_card_price_anomaly"))

    assert len(incidents) == 2
    assert latest_sale is not None
    assert "repeated_pair_trade" in latest_sale.integrity_flags_json["signals"]
    assert "price_anomaly" in latest_sale.integrity_flags_json["signals"]
    assert anomaly_event is not None
    assert anomaly_event.metadata_json["sale_id"] == latest_sale.sale_id


def test_marketplace_search_filters_and_exact_views(session) -> None:
    seller = _create_user(session, user_id="seller-search", email="seller-search@example.com", username="seller-search")
    loan_owner = _create_user(session, user_id="loan-owner", email="loan-owner@example.com", username="loan-owner")
    swap_owner = _create_user(session, user_id="swap-owner", email="swap-owner@example.com", username="swap-owner")

    sale_player = _create_player(
        session, player_id="player-sale", name="Ayo Seller", position="forward", value_eur=1_500_000
    )
    loan_player = _create_player(
        session, player_id="player-loan", name="Bola Lender", position="midfielder", value_eur=2_500_000
    )
    swap_player = _create_player(
        session, player_id="player-swap", name="Chika Swapper", position="defender", value_eur=1_000_000
    )
    _create_summary(session, player=sale_player, club_name="Red City", rating=7.2, value_credits=15.0)
    _create_summary(session, player=loan_player, club_name="Blue City", rating=8.4, value_credits=25.0)
    _create_summary(session, player=swap_player, club_name="Blue City", rating=6.8, value_credits=10.0)

    tier = _create_tier(session, tier_id="tier-search", code="gold")
    sale_card = _create_card(session, card_id="sale-card", player=sale_player, tier=tier)
    loan_card = _create_card(session, card_id="loan-card", player=loan_player, tier=tier, variant="regen_unique")
    swap_card = _create_card(session, card_id="swap-card", player=swap_player, tier=tier)

    session.add(
        PlayerCardHolding(
            player_card_id=sale_card.id,
            owner_user_id=seller.id,
            quantity_total=2,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    session.add(
        PlayerCardHolding(
            player_card_id=loan_card.id,
            owner_user_id=loan_owner.id,
            quantity_total=1,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    session.add(
        PlayerCardHolding(
            player_card_id=swap_card.id,
            owner_user_id=swap_owner.id,
            quantity_total=1,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())
    service.create_sale_listing(
        actor=seller,
        player_card_id=sale_card.id,
        quantity=1,
        price_per_card_credits=Decimal("12.0000"),
        is_negotiable=True,
    )
    service.create_loan_listing(
        actor=loan_owner,
        player_card_id=loan_card.id,
        total_slots=1,
        duration_days=5,
        loan_fee_credits=Decimal("3.5000"),
    )
    service.create_swap_listing(actor=swap_owner, player_card_id=swap_card.id)

    loan_results = service.search_marketplace(listing_type="loan", asset_origin="regen_newgen", sort="cheapest")
    all_results = service.search_marketplace(search="city", club="Blue", availability="available", sort="highest_rated")

    assert loan_results["total"] == 1
    assert loan_results["items"][0]["listing_type"] == "loan"
    assert loan_results["items"][0]["asset_origin"] == "regen_newgen"
    assert all(item["club_name"] == "Blue City" for item in all_results["items"])
    assert all_results["items"][0]["player_name"] == "Bola Lender"


def test_marketplace_search_preserves_avatar_seed_and_latest_value(session) -> None:
    seller = _create_user(session, user_id="seed-seller", email="seed-seller@example.com", username="seed-seller")
    player = _create_player(
        session, player_id="seed-player", name="Seed Player", position="forward", value_eur=2_000_000
    )
    player.dna_profile = {
        "finishing": 91,
        "shooting": 89,
        "movement": 88,
        "pace": 87,
        "composure": 90,
        "physical": 77,
        "mentality": 83,
    }
    _create_summary(
        session,
        player=player,
        value_credits=44.0,
        summary_json={
            "avatar_seed_token": "canonical-market-seed",
            "avatar_dna_seed": "440044",
            "global_scouting_index": 75,
        },
    )
    tier = _create_tier(session, tier_id="tier-seed", code="elite")
    card = _create_card(session, card_id="seed-card", player=player, tier=tier)
    session.add(
        PlayerCardHolding(
            player_card_id=card.id,
            owner_user_id=seller.id,
            quantity_total=1,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())
    created = service.create_sale_listing(
        actor=seller,
        player_card_id=card.id,
        quantity=1,
        price_per_card_credits=Decimal("44.0000"),
    )
    payload = service.search_marketplace(listing_type="sale", limit=10, offset=0)

    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["listing_id"] == created["listing_id"]
    assert item["latest_value_credits"] == 44.0
    assert item["avatar"]["seed_token"] == "canonical-market-seed"
    assert created["global_scouting_index"] == item["global_scouting_index"]
    assert item["global_scouting_index"] not in {65, 75, 85}
    assert item["gsi_band"] in {"Elite", "World Class"}


def test_marketplace_search_canonicalizes_legacy_position_buckets(session) -> None:
    seller = _create_user(
        session,
        user_id="position-seller",
        email="position-seller@example.com",
        username="position-seller",
    )
    player = _create_player(
        session,
        player_id="position-player",
        name="Loose Forward",
        position="forward",
        value_eur=2_000_000,
    )
    _create_summary(session, player=player, club_name="Red City", rating=8.2, value_credits=31.0)
    tier = _create_tier(session, tier_id="tier-position", code="gold")
    card = _create_card(session, card_id="position-card", player=player, tier=tier)
    session.add(
        PlayerCardHolding(
            player_card_id=card.id,
            owner_user_id=seller.id,
            quantity_total=1,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())
    service.create_sale_listing(
        actor=seller,
        player_card_id=card.id,
        quantity=1,
        price_per_card_credits=Decimal("31.0000"),
    )

    payload = service.search_marketplace(listing_type="sale", position="ST", limit=10, offset=0)

    assert payload["total"] == 1
    assert payload["items"][0]["position"] == "ST"


def test_marketplace_search_applies_player_price_engine_signals(session) -> None:
    seller = _create_user(session, user_id="engine-seller", email="engine-seller@example.com", username="engine-seller")
    player = _create_player(
        session, player_id="engine-player", name="Engine Nine", position="forward", value_eur=4_000_000
    )
    _create_summary(session, player=player, club_name="Green Pulse", rating=8.0, value_credits=40.0)
    tier = _create_tier(session, tier_id="tier-engine", code="platinum")
    card = _create_card(session, card_id="engine-card", player=player, tier=tier)
    session.add(
        PlayerCardHolding(
            player_card_id=card.id,
            owner_user_id=seller.id,
            quantity_total=1,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    _create_stats_snapshot(
        session,
        player_id=player.id,
        stats_json={
            "goals": 2,
            "assists": 1,
            "rating": 8.0,
            "mistakes": 1,
        },
    )
    event = _create_real_world_event(session, player_id=player.id, event_id="event-engine")
    session.add(
        TrendingPlayerFlag(
            player_id=player.id,
            event_id=event.id,
            flag_type="hot_streak",
            flag_label="Trending",
            trend_score=60.0,
            priority=1,
            status="active",
            started_at=datetime.now(UTC) - timedelta(hours=1),
            expires_at=datetime.now(UTC) + timedelta(hours=4),
            source="test-suite",
            metadata_json={},
        )
    )
    session.add(
        PlayerDemandSignal(
            player_id=player.id,
            event_id=event.id,
            signal_type="fan_rush",
            signal_label="Fan rush",
            demand_score=8.0,
            scouting_interest_delta=3.0,
            recommendation_priority_delta=2.0,
            market_buzz_score=12.0,
            status="active",
            started_at=datetime.now(UTC) - timedelta(hours=1),
            expires_at=datetime.now(UTC) + timedelta(hours=4),
            source="test-suite",
            metadata_json={},
        )
    )
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())
    service.create_sale_listing(
        actor=seller,
        player_card_id=card.id,
        quantity=1,
        price_per_card_credits=Decimal("42.0000"),
    )

    payload = service.search_marketplace(listing_type="sale", limit=10, offset=0)

    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["market_price_credits"] == Decimal("46.2000")
    assert item["price_change_credits"] == Decimal("4.2000")
    assert item["price_change_percent"] == 10.0
    assert item["price_direction"] == "up"
    assert item["performance_score"] == pytest.approx(14.1)
    assert item["available_shares"] == 1
    assert item["buy_volume"] == 0
    assert item["sell_volume"] == 1
    assert item["liquidity_signal"] == "Low liquidity"
    assert item["low_liquidity_warning"] is True
    assert item["is_trending"] is True
    assert item["trending_badge"] == "Trending"
    assert item["hype_factor"] == pytest.approx(3.1)
    assert item["change_capped"] is True
    assert session.scalar(select(func.count(PlayerMarketValueSnapshot.id))) == 1
    momentum = session.scalar(select(PlayerCardMomentum).where(PlayerCardMomentum.player_id == player.id))
    assert momentum is None


def test_swap_execution_transfers_holdings(session) -> None:
    owner = _create_user(session, user_id="swap-lister", email="swap-lister@example.com", username="swap-lister")
    counterparty = _create_user(
        session, user_id="swap-counter", email="swap-counter@example.com", username="swap-counter"
    )
    owner_player = _create_player(session, player_id="player-owner", name="Owner Card")
    counter_player = _create_player(session, player_id="player-counter", name="Counter Card")
    _create_summary(session, player=owner_player, value_credits=12.0)
    _create_summary(session, player=counter_player, value_credits=18.0)
    tier = _create_tier(session, tier_id="tier-swap", code="silver")
    owner_card = _create_card(session, card_id="owner-card", player=owner_player, tier=tier)
    counter_card = _create_card(session, card_id="counter-card", player=counter_player, tier=tier)

    session.add(
        PlayerCardHolding(
            player_card_id=owner_card.id,
            owner_user_id=owner.id,
            quantity_total=1,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    session.add(
        PlayerCardHolding(
            player_card_id=counter_card.id,
            owner_user_id=counterparty.id,
            quantity_total=1,
            quantity_reserved=0,
            metadata_json={},
        )
    )
    session.flush()

    service = PlayerCardMarketplaceService(session=session, wallet_service=WalletService())
    listing = service.create_swap_listing(
        actor=owner, player_card_id=owner_card.id, requested_player_card_id=counter_card.id
    )
    execution = service.execute_swap_listing(
        actor=counterparty, listing_id=listing["listing_id"], counterparty_player_card_id=counter_card.id
    )

    owner_received = (
        session.query(PlayerCardHolding).filter_by(owner_user_id=owner.id, player_card_id=counter_card.id).one()
    )
    counter_received = (
        session.query(PlayerCardHolding).filter_by(owner_user_id=counterparty.id, player_card_id=owner_card.id).one()
    )

    assert execution["status"] == "executed"
    assert owner_received.quantity_total == 1
    assert counter_received.quantity_total == 1
    assert session.query(CardSwapExecution).count() == 1
