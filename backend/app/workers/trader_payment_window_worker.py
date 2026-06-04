from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.wallets.rail_service import (
    TRADER_DISPUTE_ESCALATION_HOURS,
    TRADER_PAYMENT_WINDOW_MINUTES,
    WalletRailService,
)


@dataclass(slots=True)
class TraderPaymentWindowWorker:
    session: Session

    def expire_payment_windows(
        self,
        *,
        reference_time: datetime | None = None,
        payment_window_minutes: int = TRADER_PAYMENT_WINDOW_MINUTES,
        dispute_escalation_hours: int = TRADER_DISPUTE_ESCALATION_HOURS,
        limit: int = 200,
    ) -> dict[str, Any]:
        result = WalletRailService(self.session).expire_trader_payment_windows(
            reference_time=reference_time,
            payment_window_minutes=payment_window_minutes,
            dispute_escalation_hours=dispute_escalation_hours,
            limit=limit,
        )
        self.session.flush()
        return result


__all__ = ["TraderPaymentWindowWorker"]
