from __future__ import annotations

from alembic import command
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
import pytest

import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.matching.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
from app.auth.service import AuthService
from app.core.database import build_alembic_config
from app.ingestion.models import Player
from app.ledger.models import LedgerEventRecord, LedgerEventType
from app.ledger.service import LedgerEventService
from app.models.wallet import LedgerUnit
from app.orders.models import Order, OrderSide, OrderStatus


@pytest.fixture()
def migrated_session_factory(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'ledger_events.db').as_posix()}"
    command.upgrade(build_alembic_config(database_url), "head")
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield SessionLocal
    finally:
        engine.dispose()


def _create_user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
    )
    session.commit()
    return user


def _create_player(session, *, provider_external_id: str) -> Player:
    player = Player(
        source_provider="manual",
        provider_external_id=provider_external_id,
        full_name="Migrated Order Player",
        is_tradable=True,
    )
    session.add(player)
    session.commit()
    return player


def test_migrated_schema_accepts_all_runtime_order_lifecycle_events(migrated_session_factory) -> None:
    with migrated_session_factory() as session:
        table_sql = session.execute(
            text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'ledger_event_records'")
        ).scalar_one()
        for event_type in LedgerEventType:
            assert event_type.value in table_sql

        user = _create_user(
            session,
            email="ledger-events@example.com",
            username="ledgereventsuser",
        )
        service = LedgerEventService()

        for index, event_type in enumerate(LedgerEventType, start=1):
            service.append_event(
                session,
                aggregate_type="order",
                aggregate_id=f"order-{index}",
                user_id=user.id,
                event_type=event_type,
                payload={"sequence": index},
            )
        session.commit()

        persisted_events = session.scalars(
            select(LedgerEventRecord).order_by(LedgerEventRecord.aggregate_id.asc())
        ).all()

    assert [event.event_type.value for event in persisted_events] == [event_type.value for event_type in LedgerEventType]


def test_migrated_schema_round_trips_order_value_enums(migrated_session_factory) -> None:
    with migrated_session_factory() as session:
        user = _create_user(
            session,
            email="migrated-order-values@example.com",
            username="migratedordervaluesuser",
        )
        player = _create_player(session, provider_external_id="migrated-order-value-player")

        session.execute(
            text(
                """
                INSERT INTO exchange_orders (
                    id,
                    user_id,
                    player_id,
                    side,
                    quantity,
                    filled_quantity,
                    max_price,
                    currency,
                    reserved_amount,
                    status,
                    hold_transaction_id,
                    created_at,
                    updated_at
                ) VALUES (
                    :id,
                    :user_id,
                    :player_id,
                    :side,
                    :quantity,
                    :filled_quantity,
                    :max_price,
                    :currency,
                    :reserved_amount,
                    :status,
                    NULL,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": "order-value-roundtrip",
                "user_id": user.id,
                "player_id": player.id,
                "side": "buy",
                "quantity": 4,
                "filled_quantity": 0,
                "max_price": 12,
                "currency": "credit",
                "reserved_amount": 48,
                "status": "open",
            },
        )
        session.commit()

        order = session.get(Order, "order-value-roundtrip")

    assert order is not None
    assert order.side is OrderSide.BUY
    assert order.status is OrderStatus.OPEN
    assert order.currency is LedgerUnit.CREDIT


def test_ledger_event_records_remain_append_only(migrated_session_factory) -> None:
    with migrated_session_factory() as session:
        user = _create_user(
            session,
            email="ledger-append-only@example.com",
            username="ledgerappendonlyuser",
        )
        event_record = LedgerEventService().append_event(
            session,
            aggregate_type="order",
            aggregate_id="order-append-only",
            user_id=user.id,
            event_type=LedgerEventType.ORDER_ACCEPTED,
            payload={"status": "open"},
        )
        session.commit()

        event_record.payload_json = {"status": "tampered"}
        with pytest.raises(ValueError, match="append-only"):
            session.commit()
        session.rollback()

        persisted_event = session.get(LedgerEventRecord, event_record.id)
        assert persisted_event is not None
        session.delete(persisted_event)
        with pytest.raises(ValueError, match="append-only"):
            session.commit()
        session.rollback()

        assert session.get(LedgerEventRecord, event_record.id) is not None
