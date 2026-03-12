from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.dependencies import get_session
from backend.app.common.enums.contract_status import ContractStatus
from backend.app.common.enums.injury_severity import InjurySeverity
from backend.app.common.enums.transfer_window_status import TransferWindowStatus
from backend.app.ingestion.models import Club as IngestionClub
from backend.app.ingestion.models import Competition, Match, Player, PlayerSeasonStat, Season
from backend.app.models.base import Base
from backend.app.models.club_profile import ClubProfile
from backend.app.models.player_career_entry import PlayerCareerEntry
from backend.app.models.player_contract import PlayerContract
from backend.app.models.player_injury_case import PlayerInjuryCase
from backend.app.models.player_lifecycle_event import PlayerLifecycleEvent
from backend.app.models.transfer_bid import TransferBid
from backend.app.models.transfer_window import TransferWindow
from backend.app.models.user import KycStatus, User, UserRole
from backend.app.schemas.player_lifecycle import (
    ContractCreateRequest,
    ContractRenewRequest,
    InjuryCreateRequest,
    InjuryRecoveryRequest,
    TransferBidAcceptRequest,
    TransferBidCreateRequest,
)
from backend.app.segments.player_lifecycle.segment_player_lifecycle import router
from backend.app.services.player_lifecycle_service import (
    PlayerLifecycleNotFoundError,
    PlayerLifecycleService,
    PlayerLifecycleValidationError,
)


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
        kyc_status=KycStatus.VERIFIED,
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
    summary_after_move = lifecycle_service.get_career_summary(context["player_id"], on_date=date(2026, 7, 2))

    assert accepted.status == "accepted"
    assert old_contract.status == ContractStatus.ACTIVE.value
    assert old_contract.ends_on == date(2026, 6, 30)
    assert summary_before_move.current_club_id == context["club_profile_id"]
    assert summary_before_move.contract_summary is not None
    assert summary_before_move.contract_summary.status == ContractStatus.ACTIVE
    assert summary_before_move.contract_summary.active_contract is not None
    assert summary_before_move.contract_summary.active_contract.club_id == context["club_profile_id"]
    assert summary_before_move.transfer_summary.accepted_bids == 1
    assert summary_before_move.transfer_summary.completed_bids == 0
    assert summary_after_move.contract_summary is not None
    assert summary_after_move.contract_summary.active_contract is not None
    assert summary_after_move.contract_summary.active_contract.club_id == context["buyer_profile_id"]


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
