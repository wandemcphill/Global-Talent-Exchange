from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.dependencies import get_session
from backend.app.common.enums.contract_status import ContractStatus
from backend.app.common.enums.injury_severity import InjurySeverity
from backend.app.common.enums.transfer_window_status import TransferWindowStatus
from backend.app.club_identity.models.reputation import ClubReputationProfile
from backend.app.ingestion.models import Club as IngestionClub
from backend.app.ingestion.models import Competition, Match, Player, PlayerSeasonStat, Season
from backend.app.models.base import Base
from backend.app.models.club_infra import ClubFacility
from backend.app.models.player_cards import PlayerCard, PlayerCardTier
from backend.app.models.club_profile import ClubProfile
from backend.app.models.notification_center import PlatformAnnouncement
from backend.app.models.notification_record import NotificationRecord
from backend.app.models.player_career_entry import PlayerCareerEntry
from backend.app.models.player_contract import PlayerContract
from backend.app.models.player_injury_case import PlayerInjuryCase
from backend.app.models.player_lifecycle_event import PlayerLifecycleEvent
from backend.app.models.regen import (
    CurrencyConversionQuote,
    MajorTransferAnnouncement,
    RegenBigClubApproach,
    RegenOfferVisibilityState,
    RegenOriginMetadata,
    RegenPersonalityProfile,
    RegenProfile,
    RegenTeamDynamicsEffect,
    RegenTransferPressureState,
    TransferHeadlineMediaRecord,
)
from backend.app.models.story_feed import StoryFeedItem
from backend.app.models.transfer_bid import TransferBid
from backend.app.models.transfer_window import TransferWindow
from backend.app.models.user import KycStatus, User, UserRole
from backend.app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from backend.app.schemas.player_lifecycle import (
    BigClubApproachRequest,
    ContractCreateRequest,
    ContractRenewRequest,
    InjuryCreateRequest,
    InjuryRecoveryRequest,
    RegenContractOfferQuoteRequest,
    RegenPressureResolutionRequest,
    RegenSpecialTrainingRequest,
    RegenTransferListingRequest,
    TransferBidAcceptRequest,
    TransferBidCreateRequest,
    TransferBidRejectRequest,
)
from backend.app.segments.player_lifecycle.segment_player_lifecycle import router
from backend.app.services.player_lifecycle_service import (
    PlayerLifecycleNotFoundError,
    PlayerLifecycleService,
    PlayerLifecycleValidationError,
)
from backend.app.services.regen_transfer_addon import AUTO_CONVERSION_PREMIUM_BPS
from backend.app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def lifecycle_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def lifecycle_service(lifecycle_session: Session) -> PlayerLifecycleService:
    return PlayerLifecycleService(lifecycle_session)


@pytest.fixture()
def lifecycle_api(lifecycle_session: Session):
    app = FastAPI()
    app.include_router(router)

    def _session_override():
        yield lifecycle_session

    app.dependency_overrides[get_session] = _session_override
    with TestClient(app) as client:
        yield client


def seed_base_context(session: Session) -> dict[str, str]:
    user = User(
        id="user-owner",
        email="owner@example.com",
        username="owner",
        display_name="Owner",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    club_profile = ClubProfile(
        id="club-profile-metro",
        owner_user_id=user.id,
        club_name="Metro FC",
        short_name="MFC",
        slug="metro-fc",
        primary_color="#112233",
        secondary_color="#445566",
        accent_color="#ddeeff",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
    )
    buyer_profile = ClubProfile(
        id="club-profile-river",
        owner_user_id=user.id,
        club_name="River FC",
        short_name="RFC",
        slug="river-fc",
        primary_color="#223344",
        secondary_color="#ffffff",
        accent_color="#ff9900",
        country_code="ES",
        region_name="Madrid",
        city_name="Madrid",
    )
    prior_profile = ClubProfile(
        id="club-profile-prior",
        owner_user_id=user.id,
        club_name="Old Town FC",
        short_name="OTF",
        slug="old-town-fc",
        primary_color="#554433",
        secondary_color="#bbbbbb",
        accent_color="#11aa77",
        country_code="NG",
        region_name="Abuja",
        city_name="Abuja",
    )
    competition = Competition(
        id="competition-premier",
        source_provider="test",
        provider_external_id="competition-premier",
        name="Premier League",
        slug="premier-league",
    )
    current_season = Season(
        id="season-current",
        source_provider="test",
        provider_external_id="season-current",
        competition_id=competition.id,
        label="2025/26",
        year_start=2025,
        year_end=2026,
        season_status="in_progress",
    )
    previous_season = Season(
        id="season-previous",
        source_provider="test",
        provider_external_id="season-previous",
        competition_id=competition.id,
        label="2024/25",
        year_start=2024,
        year_end=2025,
        season_status="completed",
    )
    current_club = IngestionClub(
        id="ing-club-current",
        source_provider="test",
        provider_external_id="ing-club-current",
        current_competition_id=competition.id,
        name="Arsenal FC",
        slug="arsenal-fc",
    )
    opponent_club = IngestionClub(
        id="ing-club-opponent",
        source_provider="test",
        provider_external_id="ing-club-opponent",
        current_competition_id=competition.id,
        name="Chelsea FC",
        slug="chelsea-fc",
    )
    player = Player(
        id="player-1",
        source_provider="test",
        provider_external_id="player-1",
        current_club_id=current_club.id,
        current_club_profile_id=club_profile.id,
        current_competition_id=competition.id,
        full_name="Ayo Forward",
        normalized_position="forward",
    )
    match = Match(
        id="match-1",
        source_provider="test",
        provider_external_id="match-1",
        competition_id=competition.id,
        season_id=current_season.id,
        home_club_id=current_club.id,
        away_club_id=opponent_club.id,
        kickoff_at=datetime(2026, 3, 1, 15, 0),
        status="completed",
        home_score=2,
        away_score=1,
    )

    session.add_all(
        [
            user,
            club_profile,
            buyer_profile,
            prior_profile,
            competition,
            current_season,
            previous_season,
            current_club,
            opponent_club,
            player,
            match,
        ]
    )
    session.commit()
    return {
        "player_id": player.id,
        "club_profile_id": club_profile.id,
        "buyer_profile_id": buyer_profile.id,
        "prior_profile_id": prior_profile.id,
        "competition_id": competition.id,
        "current_season_id": current_season.id,
        "previous_season_id": previous_season.id,
        "current_ingestion_club_id": current_club.id,
    }


def add_window(session: Session, *, window_id: str, opens_on: date, closes_on: date) -> TransferWindow:
    window = TransferWindow(
        id=window_id,
        territory_code="ENG",
        label=f"Window {window_id}",
        status="upcoming",
        opens_on=opens_on,
        closes_on=closes_on,
    )
    session.add(window)
    session.commit()
    return window


def fund_wallet(
    session: Session,
    *,
    user_id: str,
    coin: Decimal = Decimal("0.0000"),
    credit: Decimal = Decimal("0.0000"),
) -> None:
    user = session.get(User, user_id)
    assert user is not None
    wallet_service = WalletService()
    if coin > Decimal("0.0000"):
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(
                    account=wallet_service.ensure_platform_account(session, LedgerUnit.COIN),
                    amount=-coin,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                ),
                LedgerPosting(
                    account=wallet_service.get_user_account(session, user, LedgerUnit.COIN),
                    amount=coin,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference=f"test-fund:{user.id}:coin",
            description="Test GTex Coin funding",
            actor=user,
        )
    if credit > Decimal("0.0000"):
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(
                    account=wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT),
                    amount=-credit,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                ),
                LedgerPosting(
                    account=wallet_service.get_user_account(session, user, LedgerUnit.CREDIT),
                    amount=credit,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference=f"test-fund:{user.id}:credit",
            description="Test Fan Coin funding",
            actor=user,
        )
    session.commit()


def seed_regen_context(
    session: Session,
    *,
    player_id: str,
    generated_for_club_id: str,
    generated_at: datetime,
    potential_max: int = 74,
    decision_traits: dict[str, int] | None = None,
) -> RegenProfile:
    resolved_traits = {
        "ambition": 74,
        "loyalty": 78,
        "professionalism": 72,
        "greed": 34,
        "patience": 62,
        "hometown_affinity": 86,
        "trophy_hunger": 58,
        "media_appetite": 28,
        "temperament": 60,
        "adaptability": 52,
    }
    if decision_traits:
        resolved_traits.update(decision_traits)
    regen = RegenProfile(
        id=f"regen-db-{player_id}",
        regen_id=f"regen-{player_id}",
        player_id=player_id,
        linked_unique_card_id=f"card-{player_id}",
        generated_for_club_id=generated_for_club_id,
        birth_country_code="NG",
        birth_region="Lagos",
        birth_city="Lagos",
        primary_position="ST",
        secondary_positions_json=["RW"],
        generated_at=generated_at,
        current_gsi=66,
        current_ability_range_json={"minimum": 61, "maximum": 68},
        potential_range_json={"minimum": max(65, potential_max - 6), "maximum": potential_max},
        scout_confidence="High",
        generation_source="new_club",
        status="active",
        club_quality_score=62.0,
        metadata_json={
            "decision_traits": resolved_traits,
            "career_state": {
                "contract_currency": "FanCoin",
                "transfer_listed": False,
                "free_agent": False,
                "retired": False,
            },
        },
    )
    session.add(regen)
    session.flush()
    session.add(
        RegenPersonalityProfile(
            id=f"regen-personality-{player_id}",
            regen_profile_id=regen.id,
            temperament=resolved_traits["temperament"],
            leadership=58,
            ambition=resolved_traits["ambition"],
            loyalty=resolved_traits["loyalty"],
            work_rate=resolved_traits["professionalism"],
            flair=56,
            resilience=resolved_traits["patience"],
            personality_tags_json=["grounded", "driven"],
        )
    )
    session.add(
        RegenOriginMetadata(
            id=f"regen-origin-{player_id}",
            regen_profile_id=regen.id,
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            hometown_club_affinity="Metro FC",
            ethnolinguistic_profile="yoruba",
            religion_naming_pattern="christian",
            urbanicity="urban",
            metadata_json={},
        )
    )
    session.commit()
    return regen


def test_player_career_summary_aggregates_stats_and_lifecycle_state(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = seed_base_context(lifecycle_session)
    window = add_window(
        lifecycle_session,
        window_id="window-career",
        opens_on=date(2026, 1, 1),
        closes_on=date(2026, 3, 31),
    )
    lifecycle_session.add_all(
        [
            PlayerSeasonStat(
                id="season-stat-current",
                source_provider="test",
                provider_external_id="season-stat-current",
                player_id=context["player_id"],
                club_id=context["current_ingestion_club_id"],
                competition_id=context["competition_id"],
                season_id=context["current_season_id"],
                appearances=30,
                starts=28,
                minutes=2520,
                goals=14,
                assists=6,
                clean_sheets=0,
                saves=0,
                average_rating=7.4,
            ),
            PlayerSeasonStat(
                id="season-stat-previous",
                source_provider="test",
                provider_external_id="season-stat-previous",
                player_id=context["player_id"],
                club_id=context["current_ingestion_club_id"],
                competition_id=context["competition_id"],
                season_id=context["previous_season_id"],
                appearances=24,
                starts=22,
                minutes=1980,
                goals=8,
                assists=5,
                clean_sheets=0,
                saves=0,
                average_rating=7.1,
            ),
            PlayerCareerEntry(
                id="career-entry-legacy",
                player_id=context["player_id"],
                club_id=None,
                club_name="River Plate",
                season_label="2023/24",
                appearances=20,
                goals=4,
                assists=3,
                average_rating=7,
                honours_json=[],
            ),
            PlayerInjuryCase(
                id="injury-old",
                player_id=context["player_id"],
                club_id=context["club_profile_id"],
                severity="minor",
                injury_type="Ankle knock",
                occurred_on=date(2026, 1, 10),
                expected_return_on=date(2026, 1, 18),
                recovered_on=date(2026, 1, 16),
                recovery_days=8,
            ),
            PlayerContract(
                id="contract-active",
                player_id=context["player_id"],
                club_id=context["club_profile_id"],
                status="active",
                wage_amount=Decimal("120000.00"),
                signed_on=date(2026, 1, 1),
                starts_on=date(2026, 1, 1),
                ends_on=date(2027, 6, 30),
            ),
            TransferBid(
                id="bid-completed",
                window_id=window.id,
                player_id=context["player_id"],
                selling_club_id=context["prior_profile_id"],
                buying_club_id=context["club_profile_id"],
                status="completed",
                bid_amount=Decimal("25000000.00"),
                structured_terms_json={
                    "submitted_on": "2026-01-05",
                    "accepted_on": "2026-01-08",
                    "completed_on": "2026-01-08",
                },
            ),
        ]
    )
    lifecycle_session.commit()

    summary = lifecycle_service.get_career_summary(context["player_id"], on_date=date(2026, 3, 12))

    assert summary.player_name == "Ayo Forward"
    assert summary.current_club_id == context["club_profile_id"]
    assert summary.current_club_name == "Metro FC"
    assert summary.totals.appearances == 74
    assert summary.totals.starts == 50
    assert summary.totals.goals == 26
    assert summary.totals.assists == 14
    assert summary.contract_summary is not None
    assert summary.contract_summary.status == ContractStatus.ACTIVE
    assert summary.injury_summary.total_cases == 1
    assert summary.injury_summary.active is None
    assert summary.transfer_summary.completed_bids == 1
    assert summary.transfer_summary.last_buying_club_id == context["club_profile_id"]
    assert summary.availability.available is True
    assert summary.seasonal_progression[0].season_label == "2025/26"
    assert any(item.season_label == "2023/24" for item in summary.seasonal_progression)


def test_injury_availability_lifecycle(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = seed_base_context(lifecycle_session)

    injury = lifecycle_service.create_injury_case(
        context["player_id"],
        InjuryCreateRequest(
            severity=InjurySeverity.MODERATE,
            injury_type="Hamstring strain",
            occurred_on=date(2026, 3, 1),
            recovery_days=10,
            club_id=context["club_profile_id"],
        ),
    )

    unavailable = lifecycle_service.get_player_availability(context["player_id"], on_date=date(2026, 3, 5))
    recovered = lifecycle_service.recover_injury(
        context["player_id"],
        injury.id,
        InjuryRecoveryRequest(recovered_on=date(2026, 3, 6), notes="Back in full training"),
    )
    available = lifecycle_service.get_player_availability(context["player_id"], on_date=date(2026, 3, 7))

    assert unavailable.available is False
    assert unavailable.unavailable_until == date(2026, 3, 11)
    assert unavailable.active_injury is not None
    assert recovered.recovered_on == date(2026, 3, 6)
    assert "Back in full training" in (recovered.notes or "")
    assert available.available is True
    assert available.active_injury is None
    events = lifecycle_service.list_events(context["player_id"], limit=10)
    assert [event.event_type for event in events[:2]] == ["injury_recovered", "injury_created"]


def test_contract_lifecycle_status_and_renewal(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    contract = lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("90000.00"),
            signed_on=date(2025, 7, 1),
            starts_on=date(2025, 7, 1),
            ends_on=date(2026, 4, 1),
        ),
    )

    summary_before = lifecycle_service.get_contract_summary(context["player_id"], on_date=date(2026, 3, 12))
    renewed = lifecycle_service.renew_contract(
        context["player_id"],
        contract.id,
        ContractRenewRequest(
            new_ends_on=date(2027, 6, 30),
            wage_amount=Decimal("110000.00"),
            release_clause_amount=Decimal("50000000.00"),
        ),
        reference_on=date(2026, 3, 12),
    )
    summary_after = lifecycle_service.get_contract_summary(context["player_id"], on_date=date(2026, 3, 12))
    summary_expired = lifecycle_service.get_contract_summary(context["player_id"], on_date=date(2027, 7, 1))

    assert summary_before is not None
    assert summary_before.status == ContractStatus.EXPIRING
    assert renewed.wage_amount == Decimal("110000.00")
    assert renewed.release_clause_amount == Decimal("50000000.00")
    assert summary_after is not None
    assert summary_after.status == ContractStatus.ACTIVE
    assert summary_expired is not None
    assert summary_expired.status == ContractStatus.EXPIRED
    assert lifecycle_session.get(Player, context["player_id"]).current_club_profile_id == context["club_profile_id"]
    events = lifecycle_service.list_events(context["player_id"], limit=10)
    assert any(event.event_type == "contract_created" for event in events)
    assert any(event.event_type == "contract_renewed" for event in events)


def test_transfer_window_open_closed_validation(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("75000.00"),
            signed_on=date(2026, 1, 1),
            starts_on=date(2026, 1, 1),
            ends_on=date(2027, 1, 1),
        ),
    )
    window = add_window(
        lifecycle_session,
        window_id="window-validation",
        opens_on=date(2026, 6, 1),
        closes_on=date(2026, 8, 31),
    )

    with pytest.raises(PlayerLifecycleValidationError, match="closed"):
        lifecycle_service.create_bid(
            window.id,
            TransferBidCreateRequest(
                player_id=context["player_id"],
                buying_club_id=context["buyer_profile_id"],
                bid_amount=Decimal("1000000.00"),
            ),
            submitted_on=date(2026, 5, 1),
        )

    exempt_bid = lifecycle_service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=context["buyer_profile_id"],
            bid_amount=Decimal("1000000.00"),
            allow_outside_window=True,
            exemption_reason="Court-approved emergency replacement",
        ),
        submitted_on=date(2026, 5, 1),
    )

    assert exempt_bid.status == "submitted"
    assert lifecycle_service.to_transfer_window_view(window, reference_on=date(2026, 5, 1)).status == TransferWindowStatus.UPCOMING
    assert lifecycle_service.to_transfer_window_view(window, reference_on=date(2026, 6, 15)).status == TransferWindowStatus.OPEN
    assert lifecycle_service.to_transfer_window_view(window, reference_on=date(2026, 9, 1)).status == TransferWindowStatus.CLOSED


def test_transfer_bid_flow_completes_contract_move(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    window = add_window(
        lifecycle_session,
        window_id="window-transfer",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )
    old_contract = lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("80000.00"),
            signed_on=date(2025, 7, 1),
            starts_on=date(2025, 7, 1),
            ends_on=date(2026, 12, 31),
        ),
    )
    bid = lifecycle_service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=context["buyer_profile_id"],
            bid_amount=Decimal("4500000.00"),
            wage_offer_amount=Decimal("95000.00"),
        ),
        submitted_on=date(2026, 3, 12),
    )
    accepted = lifecycle_service.accept_bid(
        window.id,
        bid.id,
        TransferBidAcceptRequest(
            contract_ends_on=date(2028, 6, 30),
            contract_starts_on=date(2026, 3, 12),
            wage_amount=Decimal("95000.00"),
            signed_on=date(2026, 3, 12),
        ),
        reference_on=date(2026, 3, 12),
    )
    lifecycle_session.refresh(old_contract)

    buyer_contract = next(
        contract
        for contract in lifecycle_service.get_contracts(context["player_id"])
        if contract.club_id == context["buyer_profile_id"]
    )
    summary = lifecycle_service.get_career_summary(context["player_id"], on_date=date(2026, 3, 12))

    assert accepted.status == "completed"
    assert old_contract.status == ContractStatus.TERMINATED.value
    assert old_contract.ends_on == date(2026, 3, 11)
    assert buyer_contract.wage_amount == Decimal("95000.00")
    assert summary.transfer_summary.completed_bids == 1
    assert summary.contract_summary is not None
    assert summary.contract_summary.active_contract is not None
    assert summary.contract_summary.active_contract.club_id == context["buyer_profile_id"]
    assert lifecycle_session.get(Player, context["player_id"]).current_club_profile_id == context["buyer_profile_id"]
    events = lifecycle_service.list_events(context["player_id"], limit=10)
    assert any(event.event_type == "contract_terminated" for event in events)
    assert any(event.event_type == "transfer_bid_accepted" for event in events)


def test_player_overview_and_timeline_surface_ui_ready_badges(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    add_window(
        lifecycle_session,
        window_id="window-overview",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("85000.00"),
            signed_on=date(2026, 3, 1),
            starts_on=date(2026, 3, 1),
            ends_on=date(2027, 6, 30),
        ),
    )
    lifecycle_service.create_injury_case(
        context["player_id"],
        InjuryCreateRequest(
            severity=InjurySeverity.MINOR,
            injury_type="Calf issue",
            occurred_on=date(2026, 3, 10),
            recovery_days=4,
            club_id=context["club_profile_id"],
        ),
    )

    overview = lifecycle_service.get_player_overview(
        context["player_id"],
        on_date=date(2026, 3, 12),
        territory_code="ENG",
        event_limit=5,
    )

    assert overview.availability_badge.status == "injured"
    assert overview.contract_badge is not None
    assert overview.contract_badge.status == "active"
    assert overview.transfer_status.window_open is True
    assert overview.transfer_status.eligible is False
    assert overview.recent_events
    assert overview.recent_events[0].event_type == "injury_created"


def test_future_transfer_acceptance_keeps_current_contract_active_until_move_date(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    window = add_window(
        lifecycle_session,
        window_id="window-future-transfer",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )
    old_contract = lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("80000.00"),
            signed_on=date(2025, 7, 1),
            starts_on=date(2025, 7, 1),
            ends_on=date(2026, 6, 30),
        ),
    )
    bid = lifecycle_service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=context["buyer_profile_id"],
            bid_amount=Decimal("4500000.00"),
            wage_offer_amount=Decimal("95000.00"),
        ),
        submitted_on=date(2026, 3, 12),
    )

    accepted = lifecycle_service.accept_bid(
        window.id,
        bid.id,
        TransferBidAcceptRequest(
            contract_ends_on=date(2028, 6, 30),
            contract_starts_on=date(2026, 7, 1),
            wage_amount=Decimal("95000.00"),
            signed_on=date(2026, 3, 12),
        ),
        reference_on=date(2026, 3, 12),
    )
    lifecycle_session.refresh(old_contract)

    summary_before_move = lifecycle_service.get_career_summary(context["player_id"], on_date=date(2026, 3, 12))

    assert accepted.status == "accepted"
    assert old_contract.status == ContractStatus.ACTIVE.value
    assert old_contract.ends_on == date(2026, 6, 30)
    assert summary_before_move.current_club_id == context["club_profile_id"]
    assert lifecycle_session.get(Player, context["player_id"]).current_club_profile_id == context["club_profile_id"]
    assert summary_before_move.contract_summary is not None
    assert summary_before_move.contract_summary.status == ContractStatus.ACTIVE
    assert summary_before_move.contract_summary.active_contract is not None
    assert summary_before_move.contract_summary.active_contract.club_id == context["club_profile_id"]
    assert summary_before_move.transfer_summary.accepted_bids == 1
    assert summary_before_move.transfer_summary.completed_bids == 0

    summary_after_move = lifecycle_service.get_career_summary(context["player_id"], on_date=date(2026, 7, 2))
    lifecycle_session.refresh(old_contract)

    assert old_contract.status == ContractStatus.TERMINATED.value
    assert old_contract.ends_on == date(2026, 6, 30)
    assert summary_after_move.contract_summary is not None
    assert summary_after_move.contract_summary.active_contract is not None
    assert summary_after_move.contract_summary.active_contract.club_id == context["buyer_profile_id"]
    assert lifecycle_session.get(Player, context["player_id"]).current_club_profile_id == context["buyer_profile_id"]
    assert lifecycle_service.list_player_transfer_bids(context["player_id"])[0].status == "completed"


def test_lifecycle_write_operations_validate_club_references(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    window = add_window(
        lifecycle_session,
        window_id="window-club-validation",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )

    with pytest.raises(PlayerLifecycleNotFoundError, match="Club profile missing-club was not found"):
        lifecycle_service.create_contract(
            context["player_id"],
            ContractCreateRequest(
                club_id="missing-club",
                wage_amount=Decimal("50000.00"),
                signed_on=date(2026, 1, 1),
                starts_on=date(2026, 1, 1),
                ends_on=date(2026, 12, 31),
            ),
        )

    with pytest.raises(PlayerLifecycleNotFoundError, match="Club profile missing-club was not found"):
        lifecycle_service.create_injury_case(
            context["player_id"],
            InjuryCreateRequest(
                severity=InjurySeverity.MINOR,
                injury_type="Impact injury",
                occurred_on=date(2026, 3, 1),
                club_id="missing-club",
            ),
        )

    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("75000.00"),
            signed_on=date(2026, 1, 1),
            starts_on=date(2026, 1, 1),
            ends_on=date(2027, 1, 1),
        ),
    )

    with pytest.raises(PlayerLifecycleNotFoundError, match="Club profile missing-club was not found"):
        lifecycle_service.create_bid(
            window.id,
            TransferBidCreateRequest(
                player_id=context["player_id"],
                buying_club_id="missing-club",
                bid_amount=Decimal("1000000.00"),
            ),
            submitted_on=date(2026, 3, 12),
        )


def test_reject_transfer_bid_leaves_player_state_unchanged(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    window = add_window(
        lifecycle_session,
        window_id="window-reject-transfer",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("80000.00"),
            signed_on=date(2025, 7, 1),
            starts_on=date(2025, 7, 1),
            ends_on=date(2026, 12, 31),
        ),
    )
    bid = lifecycle_service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=context["buyer_profile_id"],
            bid_amount=Decimal("3500000.00"),
        ),
        submitted_on=date(2026, 3, 12),
    )

    rejected = lifecycle_service.reject_bid(window.id, bid.id, TransferBidRejectRequest(reason="No fit"))

    assert rejected.status == "rejected"
    assert lifecycle_session.get(Player, context["player_id"]).current_club_profile_id == context["club_profile_id"]
    assert lifecycle_service.get_contract_summary(context["player_id"], on_date=date(2026, 3, 12)).active_contract.club_id == context["club_profile_id"]


def test_repeated_transfer_accept_is_blocked_without_corrupting_state(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    window = add_window(
        lifecycle_session,
        window_id="window-repeat-accept",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("80000.00"),
            signed_on=date(2025, 7, 1),
            starts_on=date(2025, 7, 1),
            ends_on=date(2026, 12, 31),
        ),
    )
    bid = lifecycle_service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=context["buyer_profile_id"],
            bid_amount=Decimal("4500000.00"),
            wage_offer_amount=Decimal("95000.00"),
        ),
        submitted_on=date(2026, 3, 12),
    )
    lifecycle_service.accept_bid(
        window.id,
        bid.id,
        TransferBidAcceptRequest(
            contract_ends_on=date(2028, 6, 30),
            contract_starts_on=date(2026, 3, 12),
            wage_amount=Decimal("95000.00"),
            signed_on=date(2026, 3, 12),
        ),
        reference_on=date(2026, 3, 12),
    )

    with pytest.raises(PlayerLifecycleValidationError, match="Only submitted transfer bids can be accepted"):
        lifecycle_service.accept_bid(
            window.id,
            bid.id,
            TransferBidAcceptRequest(
                contract_ends_on=date(2028, 6, 30),
                contract_starts_on=date(2026, 3, 12),
                wage_amount=Decimal("95000.00"),
                signed_on=date(2026, 3, 12),
            ),
            reference_on=date(2026, 3, 12),
        )

    contracts = lifecycle_service.get_contracts(context["player_id"])
    assert len([contract for contract in contracts if contract.club_id == context["buyer_profile_id"]]) == 1


def test_lifecycle_snapshot_endpoint_returns_ui_ready_contract(
    lifecycle_api: TestClient,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    add_window(
        lifecycle_session,
        window_id="window-api-snapshot",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )
    lifecycle_service = PlayerLifecycleService(lifecycle_session)
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("99000.00"),
            signed_on=date(2026, 3, 1),
            starts_on=date(2026, 3, 1),
            ends_on=date(2027, 6, 30),
        ),
    )

    response = lifecycle_api.get(
        f"/api/players/{context['player_id']}/lifecycle-snapshot",
        params={"as_of": "2026-03-12", "territory_code": "ENG"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["player_id"] == context["player_id"]
    assert payload["career_summary"]["contract_summary"]["active_contract"]["club_id"] == context["club_profile_id"]
    assert payload["availability_badge"]["available"] is True


def test_regen_summary_can_retire_player_and_archive_market_state(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    seed_regen_context(
        lifecycle_session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2023, 2, 1, 12, 0),
        potential_max=72,
    )
    contract = lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("64000.00"),
            signed_on=date(2025, 7, 1),
            starts_on=date(2025, 7, 1),
            ends_on=date(2027, 6, 30),
        ),
    )

    regen_summary = lifecycle_service.get_regen_summary(context["player_id"], on_date=date(2026, 3, 12))
    lifecycle_session.refresh(contract)

    assert regen_summary is not None
    assert regen_summary.retired is True
    assert regen_summary.lifecycle_phase == "retired"
    assert regen_summary.agency_message == "Retired from the active football economy."
    assert lifecycle_session.get(Player, context["player_id"]).is_tradable is False
    assert lifecycle_session.get(Player, context["player_id"]).current_club_profile_id is None
    assert contract.status == ContractStatus.TERMINATED.value
    events = lifecycle_service.list_events(context["player_id"], limit=20)
    assert any(event.event_type == "regen_retired" for event in events)


def test_regen_bid_resolution_prefers_hometown_fit_over_highest_salary(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    hometown_profile = ClubProfile(
        id="club-profile-hometown",
        owner_user_id="user-owner",
        club_name="Lagos Stars",
        short_name="LGS",
        slug="lagos-stars",
        primary_color="#001122",
        secondary_color="#aabbcc",
        accent_color="#ff6600",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
    )
    lifecycle_session.add(hometown_profile)
    lifecycle_session.add_all(
        [
            ClubReputationProfile(club_id=context["buyer_profile_id"], current_score=92, highest_score=92, prestige_tier="Elite"),
            ClubReputationProfile(club_id=hometown_profile.id, current_score=38, highest_score=38, prestige_tier="Rising"),
            ClubFacility(club_id=context["buyer_profile_id"], training_level=2, academy_level=2, medical_level=1, branding_level=1),
            ClubFacility(club_id=hometown_profile.id, training_level=4, academy_level=4, medical_level=1, branding_level=1),
        ]
    )
    lifecycle_session.commit()
    seed_regen_context(
        lifecycle_session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2025, 8, 1, 10, 0),
        potential_max=75,
        decision_traits={
            "ambition": 60,
            "loyalty": 90,
            "professionalism": 72,
            "greed": 20,
            "patience": 60,
            "hometown_affinity": 95,
            "trophy_hunger": 40,
            "adaptability": 55,
        },
    )
    window = add_window(
        lifecycle_session,
        window_id="window-regen-free-agent",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )
    fund_wallet(
        lifecycle_session,
        user_id="user-owner",
        coin=Decimal("5000.0000"),
        credit=Decimal("200000.0000"),
    )
    lifecycle_service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=context["buyer_profile_id"],
            bid_amount=Decimal("4500000.00"),
            wage_offer_amount=Decimal("140000.00"),
            contract_years=3,
        ),
        submitted_on=date(2026, 3, 12),
    )
    lifecycle_service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=hometown_profile.id,
            bid_amount=Decimal("1800000.00"),
            wage_offer_amount=Decimal("85000.00"),
            contract_years=3,
        ),
        submitted_on=date(2026, 3, 12),
    )

    evaluations = lifecycle_service.evaluate_regen_bids(window.id, context["player_id"], reference_on=date(2026, 3, 12))
    resolution = lifecycle_service.resolve_regen_bid(window.id, context["player_id"], reference_on=date(2026, 3, 12))
    summary = lifecycle_service.get_career_summary(context["player_id"], on_date=date(2026, 3, 12))

    assert evaluations[0].buying_club_id == hometown_profile.id
    assert evaluations[0].preferred is True
    assert resolution.accepted_bid.buying_club_id == hometown_profile.id
    assert resolution.accepted_bid.status == "completed"
    assert summary.contract_summary is not None
    assert summary.contract_summary.active_contract is not None
    assert summary.contract_summary.active_contract.club_id == hometown_profile.id


def test_regen_special_training_obeys_cooldowns_and_lifetime_caps(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    seed_regen_context(
        lifecycle_session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2025, 9, 1, 10, 0),
        potential_max=60,
    )
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("72000.00"),
            signed_on=date(2026, 1, 1),
            starts_on=date(2026, 1, 1),
            ends_on=date(2027, 6, 30),
        ),
    )

    before = lifecycle_service.get_regen_summary(context["player_id"], on_date=date(2026, 3, 12))
    after_minor = lifecycle_service.apply_regen_special_training(
        context["player_id"],
        RegenSpecialTrainingRequest(package_type="minor", club_id=context["club_profile_id"], notes="Mobility block"),
        reference_on=date(2026, 3, 12),
    )

    assert before is not None
    assert after_minor.special_training.projected_ceiling > before.special_training.projected_ceiling
    assert after_minor.special_training.projected_ceiling <= 85

    with pytest.raises(PlayerLifecycleValidationError, match="cooldown"):
        lifecycle_service.apply_regen_special_training(
            context["player_id"],
            RegenSpecialTrainingRequest(package_type="minor", club_id=context["club_profile_id"]),
            reference_on=date(2026, 4, 1),
        )

    lifecycle_service.apply_regen_special_training(
        context["player_id"],
        RegenSpecialTrainingRequest(package_type="major", club_id=context["club_profile_id"], notes="Final tailored package"),
        reference_on=date(2026, 8, 1),
    )

    with pytest.raises(PlayerLifecycleValidationError, match="one major"):
        lifecycle_service.apply_regen_special_training(
            context["player_id"],
            RegenSpecialTrainingRequest(package_type="major", club_id=context["club_profile_id"]),
            reference_on=date(2027, 1, 1),
        )


def test_regen_transfer_listing_flows_into_player_overview(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    add_window(
        lifecycle_session,
        window_id="window-regen-transfer-list",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )
    seed_regen_context(
        lifecycle_session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2025, 10, 1, 9, 0),
        potential_max=73,
    )
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("70000.00"),
            signed_on=date(2026, 1, 1),
            starts_on=date(2026, 1, 1),
            ends_on=date(2027, 1, 1),
        ),
    )

    regen_summary = lifecycle_service.update_regen_transfer_listing(
        context["player_id"],
        RegenTransferListingRequest(listed=True, reason="Needs a faster route to first-team minutes"),
        reference_on=date(2026, 3, 12),
    )
    overview = lifecycle_service.get_player_overview(context["player_id"], on_date=date(2026, 3, 12), territory_code="ENG")

    assert regen_summary.transfer_listed is True
    assert overview.regen_summary is not None
    assert overview.regen_summary.transfer_listed is True
    assert overview.regen_summary.agency_message == "Requested to be transfer listed."
    assert any(event.event_type == "regen_transfer_listed" for event in overview.recent_events)


def test_lifecycle_api_smoke_for_injury_and_availability(
    lifecycle_api: TestClient,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)

    created = lifecycle_api.post(
        f"/api/players/{context['player_id']}/injuries",
        json={
            "severity": "minor",
            "injury_type": "Ankle knock",
            "occurred_on": "2026-03-12",
            "recovery_days": 5,
            "club_id": context["club_profile_id"],
        },
    )
    availability = lifecycle_api.get(
        f"/api/players/{context['player_id']}/availability",
        params={"on_date": "2026-03-13"},
    )

    assert created.status_code == 201, created.text
    assert availability.status_code == 200, availability.text
    payload = availability.json()
    assert payload["available"] is False
    assert payload["unavailable_until"] == "2026-03-17"
    assert payload["active_injury"]["injury_type"] == "Ankle knock"


def test_lifecycle_api_overview_and_events(
    lifecycle_api: TestClient,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    add_window(
        lifecycle_session,
        window_id="window-api-overview",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )
    lifecycle_service = PlayerLifecycleService(lifecycle_session)
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("99000.00"),
            signed_on=date(2026, 3, 1),
            starts_on=date(2026, 3, 1),
            ends_on=date(2027, 6, 30),
        ),
    )

    overview = lifecycle_api.get(
        f"/api/players/{context['player_id']}/overview",
        params={"as_of": "2026-03-12", "territory_code": "ENG"},
    )
    events = lifecycle_api.get(f"/api/players/{context['player_id']}/events")

    assert overview.status_code == 200, overview.text
    assert events.status_code == 200, events.text
    overview_payload = overview.json()
    assert overview_payload["contract_badge"]["status"] == "active"
    assert overview_payload["transfer_status"]["window_open"] is True
    assert events.json()[0]["event_type"] == "contract_created"


def test_big_club_approach_pushes_regen_into_pressure_state(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    seed_regen_context(
        lifecycle_session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2025, 11, 1, 10, 0),
        decision_traits={
            "ambition": 90,
            "loyalty": 28,
            "professionalism": 74,
            "greed": 60,
            "patience": 38,
            "hometown_affinity": 35,
            "trophy_hunger": 82,
        },
    )
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("65000.00"),
            signed_on=date(2026, 1, 1),
            starts_on=date(2026, 1, 1),
            ends_on=date(2027, 6, 30),
        ),
    )
    lifecycle_session.add_all(
        [
            ClubReputationProfile(
                club_id=context["club_profile_id"],
                current_score=34,
                highest_score=34,
                prestige_tier="Established",
            ),
            ClubReputationProfile(
                club_id=context["buyer_profile_id"],
                current_score=94,
                highest_score=94,
                prestige_tier="Elite",
                total_league_titles=11,
                total_continental_titles=4,
            ),
        ]
    )
    lifecycle_session.commit()

    summary = lifecycle_service.record_big_club_approach(
        context["player_id"],
        BigClubApproachRequest(approaching_club_id=context["buyer_profile_id"], notes="Elite enquiry"),
        reference_on=date(2026, 3, 12),
    )

    approach = lifecycle_session.scalar(
        select(RegenBigClubApproach).order_by(RegenBigClubApproach.created_at.desc())
    )
    assert summary.pressure_state is not None
    assert summary.pressure_state.current_state in {
        "attracted_by_bigger_club",
        "considering_transfer",
        "transfer_requested",
        "unsettled",
    }
    assert summary.pressure_state.transfer_desire > 0
    assert summary.pressure_state.last_big_club_id == context["buyer_profile_id"]
    assert approach is not None
    assert approach.resisted is False


def test_loyal_regen_can_resist_big_club_unsettling(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    seed_regen_context(
        lifecycle_session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2025, 11, 1, 10, 0),
        decision_traits={
            "ambition": 62,
            "loyalty": 96,
            "professionalism": 72,
            "greed": 18,
            "patience": 64,
            "hometown_affinity": 98,
            "trophy_hunger": 44,
        },
    )
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("65000.00"),
            signed_on=date(2026, 1, 1),
            starts_on=date(2026, 1, 1),
            ends_on=date(2027, 6, 30),
        ),
    )
    lifecycle_session.add_all(
        [
            ClubReputationProfile(
                club_id=context["club_profile_id"],
                current_score=58,
                highest_score=58,
                prestige_tier="Rising",
            ),
            ClubReputationProfile(
                club_id=context["buyer_profile_id"],
                current_score=93,
                highest_score=93,
                prestige_tier="Elite",
                total_league_titles=9,
                total_continental_titles=3,
            ),
        ]
    )
    lifecycle_session.commit()

    summary = lifecycle_service.record_big_club_approach(
        context["player_id"],
        BigClubApproachRequest(approaching_club_id=context["buyer_profile_id"]),
        reference_on=date(2026, 3, 12),
    )

    approach = lifecycle_session.scalar(
        select(RegenBigClubApproach).order_by(RegenBigClubApproach.created_at.desc())
    )
    assert summary.pressure_state is not None
    assert summary.pressure_state.current_state not in {"transfer_requested", "unsettled"}
    assert summary.pressure_state.active_transfer_request is False
    assert approach is not None
    assert approach.resisted is True


def test_transfer_request_can_be_created_and_withdrawn_after_resolution(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    seed_regen_context(
        lifecycle_session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2025, 10, 1, 9, 0),
    )
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("70000.00"),
            signed_on=date(2026, 1, 1),
            starts_on=date(2026, 1, 1),
            ends_on=date(2027, 1, 1),
        ),
    )

    requested = lifecycle_service.update_regen_transfer_listing(
        context["player_id"],
        RegenTransferListingRequest(listed=True, reason="Ambition outgrowing current project"),
        reference_on=date(2026, 3, 1),
    )
    withdrawn = lifecycle_service.apply_regen_pressure_resolution(
        context["player_id"],
        RegenPressureResolutionRequest(
            resolution_type="trophy_win",
            trophy_credit=55,
            notes="Cup win changed the mood",
        ),
        reference_on=date(2026, 3, 25),
    )

    assert requested.transfer_listed is True
    assert requested.pressure_state is not None
    assert requested.pressure_state.active_transfer_request is True
    assert withdrawn.transfer_listed is False
    assert withdrawn.pressure_state is not None
    assert withdrawn.pressure_state.active_transfer_request is False


def test_unresolved_regen_unrest_applies_team_dynamics_penalties(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    regen = seed_regen_context(
        lifecycle_session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2025, 10, 1, 9, 0),
    )
    lifecycle_session.scalar(
        select(RegenPersonalityProfile).where(RegenPersonalityProfile.regen_profile_id == regen.id)
    ).leadership = 82
    lifecycle_session.commit()
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("70000.00"),
            signed_on=date(2026, 1, 1),
            starts_on=date(2026, 1, 1),
            ends_on=date(2027, 1, 1),
        ),
    )
    lifecycle_service.update_regen_transfer_listing(
        context["player_id"],
        RegenTransferListingRequest(listed=True, reason="Wants a bigger stage"),
        reference_on=date(2026, 3, 1),
    )

    summary = lifecycle_service.get_regen_summary(context["player_id"], on_date=date(2026, 3, 20))
    effect = lifecycle_session.scalar(select(RegenTeamDynamicsEffect))

    assert summary is not None
    assert summary.team_dynamics is not None
    assert summary.team_dynamics.active is True
    assert summary.team_dynamics.morale_penalty > 0
    assert summary.team_dynamics.chemistry_penalty > 0
    assert effect is not None
    assert effect.active is True
    assert effect.influences_younger_players is True


def test_free_agent_offer_market_hides_competing_salary_amounts(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    seed_regen_context(
        lifecycle_session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2025, 12, 1, 9, 0),
    )
    fund_wallet(
        lifecycle_session,
        user_id="user-owner",
        coin=Decimal("250.0000"),
        credit=Decimal("100000.0000"),
    )
    window = add_window(
        lifecycle_session,
        window_id="window-offer-market",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )

    lifecycle_service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=context["buyer_profile_id"],
            bid_amount=Decimal("1.00"),
            wage_offer_amount=Decimal("1800.00"),
            contract_years=3,
        ),
        submitted_on=date(2026, 3, 12),
    )
    lifecycle_service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=context["prior_profile_id"],
            bid_amount=Decimal("1.00"),
            wage_offer_amount=Decimal("2100.00"),
            contract_years=2,
        ),
        submitted_on=date(2026, 3, 12),
    )

    offer_market = lifecycle_service.get_regen_offer_market(context["player_id"], on_date=date(2026, 3, 12))
    public_view = lifecycle_service.to_transfer_bid_view(lifecycle_service.list_window_bids(window.id)[0])
    visibility_state = lifecycle_session.scalar(select(RegenOfferVisibilityState))

    assert offer_market.visible_offer_count == 2
    assert offer_market.hidden_competing_salary_amounts is True
    assert public_view.wage_offer_amount is None
    assert public_view.structured_terms_json["contract_offer"]["salary_offer_hidden"] is True
    assert "offered_salary_fancoin_per_year" not in public_view.structured_terms_json["contract_offer"]
    assert visibility_state is not None
    assert visibility_state.visible_offer_count == 2


def test_contract_offer_quote_generates_auto_conversion_premium(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    seed_regen_context(
        lifecycle_session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2025, 12, 1, 9, 0),
    )
    fund_wallet(
        lifecycle_session,
        user_id="user-owner",
        coin=Decimal("100.0000"),
        credit=Decimal("100.0000"),
    )

    quote = lifecycle_service.quote_regen_contract_offer(
        context["player_id"],
        RegenContractOfferQuoteRequest(
            offering_club_id=context["buyer_profile_id"],
            offered_salary_fancoin_per_year=Decimal("1500.00"),
            contract_years=2,
        ),
        reference_on=date(2026, 3, 12),
    )
    quote_row = lifecycle_session.scalar(select(CurrencyConversionQuote))

    assert quote.required_fancoin == Decimal("3000.0000")
    assert quote.shortfall_fancoin == Decimal("2900.0000")
    assert quote.gtex_required_for_conversion > quote.direct_gtex_equivalent
    assert quote.conversion_premium_bps == AUTO_CONVERSION_PREMIUM_BPS
    assert quote.can_cover_shortfall is True
    assert quote_row is not None
    assert quote_row.premium_bps == AUTO_CONVERSION_PREMIUM_BPS


def test_major_regen_transfer_creates_headline_and_announcement_records(
    lifecycle_service: PlayerLifecycleService,
    lifecycle_session: Session,
) -> None:
    context = seed_base_context(lifecycle_session)
    seed_regen_context(
        lifecycle_session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2025, 10, 1, 9, 0),
        potential_max=84,
    )
    window = add_window(
        lifecycle_session,
        window_id="window-major-headline",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )
    lifecycle_service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("75000.00"),
            signed_on=date(2025, 7, 1),
            starts_on=date(2025, 7, 1),
            ends_on=date(2027, 6, 30),
        ),
    )
    bid = lifecycle_service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=context["buyer_profile_id"],
            bid_amount=Decimal("120.00"),
            wage_offer_amount=Decimal("40000.00"),
        ),
        submitted_on=date(2026, 3, 12),
    )

    lifecycle_service.accept_bid(
        window.id,
        bid.id,
        TransferBidAcceptRequest(
            contract_ends_on=date(2029, 3, 11),
            contract_starts_on=date(2026, 3, 12),
            wage_amount=Decimal("40000.00"),
            signed_on=date(2026, 3, 12),
        ),
        reference_on=date(2026, 3, 12),
    )

    headline = lifecycle_session.scalar(select(TransferHeadlineMediaRecord))
    announcement = lifecycle_session.scalar(select(MajorTransferAnnouncement))
    story = lifecycle_session.scalar(select(StoryFeedItem))
    platform_announcement = lifecycle_session.scalar(select(PlatformAnnouncement))

    assert headline is not None
    assert headline.estimated_transfer_fee_eur > 0
    assert "GTex Coin" in headline.headline_text
    assert "Estimated Real-World Equivalent" in headline.detail_text
    assert headline.announcement_tier == "platform_headline"
    assert announcement is not None
    assert announcement.announcement_tier == "platform_headline"
    assert "global_news_feed" in announcement.surfaces_json
    assert "transfer_center" in announcement.surfaces_json
    assert story is not None
    assert story.featured is True
    assert platform_announcement is not None
    assert platform_announcement.announcement_key.startswith("regen-transfer:")
    assert lifecycle_session.scalar(select(NotificationRecord)) is not None
