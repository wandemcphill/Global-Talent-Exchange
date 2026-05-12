from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base, utcnow
from app.models.notification_record import NotificationRecord
from app.models.ticketing import StadiumEvent
from app.models.user import User, UserRole
from app.models.wallet import LedgerSourceTag, LedgerUnit
from app.ticketing.service import TicketingService
from app.wallets.service import WalletService


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return session_local()


def test_ticket_purchase_publishes_matrix_notification() -> None:
    session = _session()
    try:
        buyer = User(
            id="ticket-buyer",
            email="ticket-buyer@example.com",
            username="ticket-buyer",
            password_hash="x",
            role=UserRole.USER,
        )
        now = utcnow()
        event = StadiumEvent(
            id="stadium-event-notify",
            stadium_id="stadium-notify",
            match_id="match-ticket-notify",
            title="Lagos Stars vs Abuja Meteors",
            venue_name="GTEX Matchday Arena",
            event_type="league",
            event_status="on_sale",
            capacity=120,
            tier_distribution_json={"regular": 100, "premium": 18, "vip": 2},
            base_price_json={"regular": "12.0000", "premium": "28.0000", "vip": "80.0000"},
            public_sales_starts_at=now - timedelta(hours=1),
            sales_close_at=now + timedelta(hours=4),
            metadata_json={},
        )
        session.add_all([buyer, event])
        session.commit()

        wallet = WalletService()
        wallet.credit_trade_proceeds(
            session,
            user=buyer,
            amount=Decimal("100.0000"),
            unit=LedgerUnit.CREDIT,
            reference="seed-ticket-buyer",
            description="Seed ticket buyer credits",
            external_reference="seed-ticket-buyer",
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        )
        session.commit()

        response = TicketingService(session, wallet_service=wallet).buy_ticket(
            user=buyer,
            match_id=event.match_id,
            seat_tier="regular",
        )
        session.commit()

        notification = session.scalar(
            select(NotificationRecord).where(
                NotificationRecord.user_id == buyer.id,
                NotificationRecord.resource_id == response.ticket.ticket_id,
            )
        )
        assert notification is not None
        assert notification.template_key == "ticket.purchased"
        assert notification.resource_type == "ticket_purchased"
        assert notification.metadata_json["match_id"] == event.match_id
        assert notification.metadata_json["route"] == "/app/play"
    finally:
        bind = session.get_bind()
        session.close()
        bind.dispose()
