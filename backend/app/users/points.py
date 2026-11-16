from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_points import UserPointAccount, UserPointLedgerEntry
from app.users.schemas import UserPointBalanceView, UserPointLedgerEntryView

_POINT_QUANTUM = Decimal("0.0001")


def build_user_point_balance_view(
    session: Session,
    *,
    user_id: str,
    recent_limit: int = 20,
) -> UserPointBalanceView:
    """Load the user's isolated personal reward points balance and recent entries."""
    account = session.scalar(select(UserPointAccount).where(UserPointAccount.user_id == user_id))
    entries = list(
        session.scalars(
            select(UserPointLedgerEntry)
            .where(UserPointLedgerEntry.user_id == user_id)
            .order_by(UserPointLedgerEntry.created_at.desc(), UserPointLedgerEntry.id.desc())
            .limit(max(1, min(recent_limit, 100)))
        ).all()
    )
    balance = Decimal(account.balance).quantize(_POINT_QUANTUM) if account is not None else Decimal("0.0000")
    lifetime_earned = (
        Decimal(account.lifetime_earned).quantize(_POINT_QUANTUM) if account is not None else Decimal("0.0000")
    )
    lifetime_spent = (
        Decimal(account.lifetime_spent).quantize(_POINT_QUANTUM) if account is not None else Decimal("0.0000")
    )
    return UserPointBalanceView(
        user_id=user_id,
        account_id=account.id if account is not None else None,
        balance=balance,
        lifetime_earned=lifetime_earned,
        lifetime_spent=lifetime_spent,
        updated_at=account.updated_at if account is not None else None,
        recent_entries=[UserPointLedgerEntryView.model_validate(item) for item in entries],
    )
