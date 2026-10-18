"""Post a Club Legacy money movement through the canonical wallet ledger."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.wallet import LedgerEntryReason, LedgerSourceTag
from app.wallets.service import LedgerPosting, WalletService

_wallet = WalletService()


def post_club_legacy_transfer(
    session: Session,
    *,
    idempotency_key: str,
    source,
    destination,
    amount: Decimal,
    actor=None,
    description: str = "Club Legacy transfer",
) -> list:
    """Debit source and credit destination once for this idempotency key."""
    gross = Decimal(amount).quantize(Decimal("0.0001"))
    if gross <= 0:
        raise ValueError("amount_must_be_positive")
    return _wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=source, amount=-gross),
            LedgerPosting(account=destination, amount=gross),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        idempotency_key=idempotency_key,
        description=description[:255],
        actor=actor,
        metadata={"domain": "club_legacy"},
    )
