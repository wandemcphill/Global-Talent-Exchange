from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_visibility import CompetitionVisibility
from app.core.events import InMemoryEventPublisher
from app.models.admin_rules import AdminRewardRule
from app.models.base import Base
from app.models.competition import Competition
from app.models.competition_participant import CompetitionParticipant
from app.services.competition_orchestrator import CompetitionOrchestrator
from backend.tests.support.economic_policy import seed_economic_policy


def test_competition_orchestrator_publishes_realtime_event_payload() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(
        engine,
        tables=[
            # Inserting a priced competition runs the Admin fee listener, which
            # resolves the active economic policy.
            AdminRewardRule.__table__,
            Competition.__table__,
            CompetitionParticipant.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    try:
        with session_factory() as session:
            seed_economic_policy(session)
            session.commit()
            competition = Competition(
                id="competition-1",
                host_user_id="host-1",
                name="Realtime Test Cup",
                description="Competition realtime event coverage.",
                competition_type=CompetitionFormat.CUP.value,
                format=CompetitionFormat.CUP.value,
                visibility=CompetitionVisibility.PUBLIC.value,
                status=CompetitionStatus.OPEN.value,
                start_mode=CompetitionStartMode.SCHEDULED.value,
                stage="registration",
                currency="credit",
                entry_fee_minor=2500,
                platform_fee_bps=1000,
                host_fee_bps=0,
                host_creation_fee_minor=0,
                gross_pool_minor=10_000,
                net_prize_pool_minor=9_000,
            )
            session.add(competition)
            session.add_all(
                [
                    CompetitionParticipant(
                        competition_id=competition.id,
                        club_id="club-1",
                        status="joined",
                    ),
                    CompetitionParticipant(
                        competition_id=competition.id,
                        club_id="club-2",
                        status="joined",
                    ),
                ]
            )
            session.commit()

            publisher = InMemoryEventPublisher()
            orchestrator = CompetitionOrchestrator(
                session,
                event_publisher=publisher,
            )
            orchestrator._publish_competition_update(
                event_name="competition.updated",
                competition=competition,
                extra={"source_type": "user_created"},
            )

            assert [event.name for event in publisher.published_events] == ["competition.updated"]
            event = publisher.published_events[0]
            assert event.aggregate_id == competition.id
            assert event.aggregate_type == "competition"
            assert event.payload == {
                "competition_id": competition.id,
                "status": CompetitionStatus.OPEN.value,
                "stage": "registration",
                "participant_count": 2,
                "source_type": "user_created",
            }
    finally:
        engine.dispose()
