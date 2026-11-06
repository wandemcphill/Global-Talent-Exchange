from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.ecosystem_events import (
    EcosystemActor,
    EcosystemClubContext,
    EcosystemConsumerRegistration,
    EcosystemDomain,
    EcosystemEvent,
    EcosystemEventBus,
    EcosystemEventPriority,
    EcosystemEventVersionAdapter,
    EcosystemEvidence,
    EcosystemResolutionStatus,
    EcosystemSubject,
    UnauthorizedSettlementBypassError,
)
from app.core.events import InMemoryEventPublisher
from app.models.base import Base
from app.models.event_backbone import EventConsumerState, EventDeadLetter, EventOutbox


@pytest.fixture
def db_session_factory(tmp_path):
    db_file = tmp_path / "test_ecosystem.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    engine.dispose()


def test_ecosystem_event_contract_and_envelope() -> None:
    actor = EcosystemActor(
        actor_id="usr_owner_001",
        actor_type="user",
        roles=("club_owner", "board_member"),
        display_name="Sheikh Mansour",
    )
    subject = EcosystemSubject(
        subject_id="ply_regen_999",
        subject_type="player",
        title="Marcus Sterling",
        metadata={"position": "ST", "potential": 94},
    )
    club = EcosystemClubContext(
        club_id="club_gtex_fc",
        club_name="GTEX Athletic",
        division_id="div_premier",
    )
    evidence = EcosystemEvidence(
        source="ui_action",
        ip_address="192.168.1.1",
        metadata={"browser": "Chrome", "viewport": "desktop"},
    )

    event = EcosystemEvent(
        domain=EcosystemDomain.CLUB_MANAGEMENT,
        name="facility_upgrade_signed",
        payload={"facility_type": "youth_academy", "cost": 500000},
        actor=actor,
        subject=subject,
        club_context=club,
        evidence=evidence,
        idempotency_key="facility_upgrade:club_gtex_fc:level_4",
        priority=EcosystemEventPriority.HIGH,
        resolution_state=EcosystemResolutionStatus.OPEN,
    )

    assert event.event_type == "club_management.facility_upgrade_signed"

    envelope = event.envelope()
    assert envelope["event_id"] == event.event_id
    assert envelope["event_type"] == "club_management.facility_upgrade_signed"
    assert envelope["aggregate_id"] == "club_gtex_fc"
    assert envelope["aggregate_type"] == "club_management"
    assert envelope["headers"]["priority"] == "high"
    assert envelope["headers"]["idempotency_key"] == "facility_upgrade:club_gtex_fc:level_4"

    eco_meta = envelope["payload"]["__ecosystem__"]
    assert eco_meta["domain"] == "club_management"
    assert eco_meta["actor"]["actor_id"] == "usr_owner_001"
    assert eco_meta["actor"]["roles"] == ["club_owner", "board_member"]
    assert eco_meta["subject"]["title"] == "Marcus Sterling"
    assert eco_meta["club_context"]["club_name"] == "GTEX Athletic"
    assert eco_meta["resolution_state"] == "open"

    # Test conversion to domain event
    domain_event = event.to_domain_event()
    assert domain_event.name == "club_management.facility_upgrade_signed"
    assert domain_event.event_id == event.event_id


def test_non_bypass_invariants_strictly_enforced() -> None:
    # Attempting to bypass ledger throws UnauthorizedSettlementBypassError
    with pytest.raises(UnauthorizedSettlementBypassError, match="Direct ledger balance bypass is strictly forbidden"):
        EcosystemEvent(
            domain=EcosystemDomain.GIFTING_CELEBRATION,
            name="gift_sent",
            payload={"bypass_financial_ledger": True},
        )

    # Attempting to bypass 2D match engine throws UnauthorizedSettlementBypassError
    with pytest.raises(UnauthorizedSettlementBypassError, match="Authoritative 2D match simulation cannot be bypassed"):
        EcosystemEvent(
            domain=EcosystemDomain.MATCH_BROADCAST,
            name="match_completed",
            payload={"bypass_match_engine": True},
        )


def test_outbox_persistence_and_idempotent_deduplication(db_session_factory) -> None:
    bus = EcosystemEventBus()

    event = EcosystemEvent(
        domain=EcosystemDomain.ACADEMY_LIFE,
        name="wonderkid_graduated",
        payload={"player_id": "p-100", "ovr": 82},
        idempotency_key="wonderkid:p-100:2026",
    )

    with db_session_factory() as session:
        row1 = bus.publish(session, event)
        session.commit()

    with db_session_factory() as session:
        # Publish exact same event with same idempotency key
        row2 = bus.publish(session, event)
        session.commit()

        # Deduplication must return existing row and not create duplicate
        assert row1.id == row2.id
        assert row1.event_id == row2.event_id

        all_rows = session.scalars(select(EventOutbox)).all()
        assert len(all_rows) == 1
        assert all_rows[0].event_type == "academy_life.wonderkid_graduated"
        assert all_rows[0].headers_json["idempotency_key"] == "wonderkid:p-100:2026"


def test_consumer_registration_and_dispatch(db_session_factory) -> None:
    bus = EcosystemEventBus()
    consumed_events: list[EcosystemEvent] = []

    def handle_signing(ev: EcosystemEvent, sess: Session) -> None:
        consumed_events.append(ev)

    bus.register_consumer(
        name="cinema_walkout_projector",
        domains=[EcosystemDomain.RECRUITMENT_TRANSFER],
        event_types=["recruitment_transfer.contract_signed"],
        handler=handle_signing,
    )

    event = EcosystemEvent(
        domain=EcosystemDomain.RECRUITMENT_TRANSFER,
        name="contract_signed",
        payload={"player_name": "Erling Haaland", "wage_weekly": 450000},
        club_context=EcosystemClubContext(club_id="club-1"),
    )

    with db_session_factory() as session:
        bus.publish(session, event)
        session.commit()

    with db_session_factory() as session:
        dispatched = bus.dispatch_pending_events(session)
        session.commit()

        assert dispatched == 1
        assert len(consumed_events) == 1
        assert consumed_events[0].payload["player_name"] == "Erling Haaland"

        # Verify consumer state
        state = session.scalar(
            select(EventConsumerState).where(
                EventConsumerState.consumer_name == "cinema_walkout_projector",
                EventConsumerState.event_id == event.event_id,
            )
        )
        assert state is not None
        assert state.status == "processed"
        assert state.processed_at is not None

        # Verify outbox state
        outbox = session.scalar(select(EventOutbox).where(EventOutbox.event_id == event.event_id))
        assert outbox is not None
        assert outbox.status == "processed"


def test_permission_aware_distribution(db_session_factory) -> None:
    bus = EcosystemEventBus()
    executed = []

    def executive_decision_handler(ev: EcosystemEvent, sess: Session) -> None:
        executed.append(ev.event_id)

    bus.register_consumer(
        name="boardroom_executive_controller",
        domains=[EcosystemDomain.OWNER_DECISION],
        handler=executive_decision_handler,
        required_roles=["club_owner", "executive_board"],
    )

    # 1. Unauthorized actor (scout role only)
    unauthorized_event = EcosystemEvent(
        domain=EcosystemDomain.OWNER_DECISION,
        name="budget_allocation",
        payload={"budget": 10000000},
        actor=EcosystemActor(actor_id="u_scout", roles=("scout",)),
    )

    # 2. Authorized actor (club_owner)
    authorized_event = EcosystemEvent(
        domain=EcosystemDomain.OWNER_DECISION,
        name="budget_allocation",
        payload={"budget": 25000000},
        actor=EcosystemActor(actor_id="u_owner", roles=("club_owner",)),
    )

    with db_session_factory() as session:
        bus.publish(session, unauthorized_event)
        bus.publish(session, authorized_event)
        session.commit()

    with db_session_factory() as session:
        dispatched = bus.dispatch_pending_events(session)
        session.commit()

        # Only authorized event should have been dispatched to handler
        assert unauthorized_event.event_id not in executed
        assert authorized_event.event_id in executed

        # Check consumer state for unauthorized event
        unauth_state = session.scalar(
            select(EventConsumerState).where(
                EventConsumerState.consumer_name == "boardroom_executive_controller",
                EventConsumerState.event_id == unauthorized_event.event_id,
            )
        )
        assert unauth_state is not None
        assert unauth_state.status == "permission_denied"


def test_consumer_retry_budget_and_dead_letter_archival(db_session_factory) -> None:
    bus = EcosystemEventBus()
    fail_attempts = 0

    def failing_handler(ev: EcosystemEvent, sess: Session) -> None:
        nonlocal fail_attempts
        fail_attempts += 1
        raise RuntimeError("External advertising API timed out")

    bus.register_consumer(
        name="sponsor_ad_campaign_relay",
        domains=[EcosystemDomain.ADVERTISING_CAMPAIGN],
        handler=failing_handler,
        max_retries=2,
    )

    event = EcosystemEvent(
        domain=EcosystemDomain.ADVERTISING_CAMPAIGN,
        name="ad_campaign_launched",
        payload={"campaign_id": "camp-909", "brand": "Nike"},
    )

    with db_session_factory() as session:
        bus.publish(session, event)
        session.commit()

    # Attempt 1: Fails -> status="retry"
    with db_session_factory() as session:
        bus.dispatch_pending_events(session)
        session.commit()

        state = session.scalar(
            select(EventConsumerState).where(
                EventConsumerState.consumer_name == "sponsor_ad_campaign_relay",
                EventConsumerState.event_id == event.event_id,
            )
        )
        assert state is not None
        assert state.status == "retry"
        assert state.attempt_count == 1
        assert "External advertising API timed out" in state.last_error

    # Attempt 2: Exceeds max_retries (2) -> dead letter
    with db_session_factory() as session:
        bus.dispatch_pending_events(session)
        session.commit()

        state = session.scalar(
            select(EventConsumerState).where(
                EventConsumerState.consumer_name == "sponsor_ad_campaign_relay",
                EventConsumerState.event_id == event.event_id,
            )
        )
        assert state is not None
        assert state.status == "dead_letter"
        assert state.attempt_count == 2
        assert state.dead_lettered_at is not None

        # Check dead letter archive
        dl = session.scalar(
            select(EventDeadLetter).where(
                EventDeadLetter.consumer_name == "sponsor_ad_campaign_relay",
                EventDeadLetter.event_id == event.event_id,
            )
        )
        assert dl is not None
        assert dl.attempts == 2
        assert dl.event_type == "advertising_campaign.ad_campaign_launched"
        assert "External advertising API timed out" in dl.last_error


def test_event_version_adaptation() -> None:
    EcosystemEventVersionAdapter.clear()

    # Register transformer: v1 -> v2
    def upgrade_v1_to_v2(payload: dict, headers: dict):
        payload["converted_metric"] = payload.get("raw_rating", 0) * 10
        headers["migrated_by"] = "test_adapter"
        return payload, headers

    EcosystemEventVersionAdapter.register(
        event_type="academy_life.prodigy_evaluated",
        from_version=1,
        to_version=2,
        transform=upgrade_v1_to_v2,
    )

    event_v1 = EcosystemEvent(
        domain=EcosystemDomain.ACADEMY_LIFE,
        name="prodigy_evaluated",
        version=1,
        payload={"raw_rating": 8.5},
    )

    event_v2 = EcosystemEventVersionAdapter.adapt(event_v1, target_version=2)

    assert event_v2.version == 2
    assert event_v2.payload["converted_metric"] == 85.0
    assert event_v2.headers["migrated_by"] == "test_adapter"
    assert event_v2.event_id == event_v1.event_id
