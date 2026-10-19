from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.owner_console import ledger


def fund_club_treasury(session: Session, club_id: str, amount: Decimal | str = "10000000") -> None:
    """Seed a club's GTEX Coin treasury the way an owner capital injection would."""
    ledger.record(
        session,
        event_type="owner_capital_injection",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(club_id),
        currency=ledger.GTEX,
        gross=amount,
        club_id=club_id,
        memo="Test treasury funding",
        check_funds=False,
    )
    session.commit()
