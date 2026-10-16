from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.wallet import LedgerAccount, LedgerEntryReason, LedgerSourceTag, LedgerTransaction
from app.wallets.service import LedgerError, LedgerPosting, WalletService


@dataclass(frozen=True, slots=True)
class WalletTransactionPosting:
    wallet_id: str
    amount: Decimal
    source_tag: LedgerSourceTag | None = None


@dataclass(frozen=True, slots=True)
class WalletTransactionResult:
    transaction_id: str
    entry_ids: tuple[str, ...]
    reason: LedgerEntryReason
    reference: str | None
    external_reference: str | None
    idempotency_key: str | None


class WalletTransactionService:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        wallet_service: WalletService | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.wallet_service = wallet_service or WalletService()

    def post_transaction(
        self,
        *,
        postings: list[WalletTransactionPosting],
        reason: LedgerEntryReason,
        source_tag: LedgerSourceTag | None = None,
        reference: str | None = None,
        description: str | None = None,
        external_reference: str | None = None,
        actor_user_id: str | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WalletTransactionResult:
        with self.session_factory() as session:
            with session.begin():
                actor = self._resolve_actor(session, actor_user_id)
                resolved_postings = self._resolve_postings(session, postings)
                entries = self.wallet_service.append_transaction(
                    session,
                    postings=resolved_postings,
                    reason=reason,
                    source_tag=source_tag,
                    reference=reference,
                    description=description,
                    external_reference=external_reference,
                    actor=actor,
                    idempotency_key=idempotency_key,
                    metadata=metadata,
                )
                transaction = session.get(LedgerTransaction, entries[0].transaction_id)
                if transaction is None:
                    raise LedgerError("Wallet transaction header was not persisted.")
            return WalletTransactionResult(
                transaction_id=transaction.id,
                entry_ids=tuple(entry.id for entry in entries),
                reason=transaction.reason,
                reference=transaction.reference,
                external_reference=transaction.external_reference,
                idempotency_key=transaction.idempotency_key,
            )

    def _resolve_postings(
        self,
        session: Session,
        postings: list[WalletTransactionPosting],
    ) -> list[LedgerPosting]:
        wallet_ids = list(dict.fromkeys(posting.wallet_id for posting in postings))
        if not wallet_ids:
            raise LedgerError("Wallet transactions require at least one wallet posting.")

        statement = select(LedgerAccount).where(LedgerAccount.id.in_(wallet_ids))
        if self.wallet_service._supports_row_locks(session):
            statement = statement.with_for_update()
        wallets = {
            wallet.id: wallet
            for wallet in session.scalars(statement).all()
        }
        missing_wallet_ids = [wallet_id for wallet_id in wallet_ids if wallet_id not in wallets]
        if missing_wallet_ids:
            raise LedgerError(f"Unknown wallet id(s): {', '.join(missing_wallet_ids)}")

        return [
            LedgerPosting(
                account=wallets[posting.wallet_id],
                amount=posting.amount,
                source_tag=posting.source_tag,
            )
            for posting in postings
        ]

    @staticmethod
    def _resolve_actor(session: Session, actor_user_id: str | None):
        if actor_user_id is None:
            return None
        from app.models.user import User

        actor = session.get(User, actor_user_id)
        if actor is None:
            raise LedgerError(f"Unknown actor user id: {actor_user_id}")
        return actor


__all__ = [
    "WalletService",
    "WalletTransactionPosting",
    "WalletTransactionResult",
    "WalletTransactionService",
]
