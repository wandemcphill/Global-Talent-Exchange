from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, JSON, String
from sqlalchemy import event
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class CompetitionWalletLedger(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "competition_wallet_ledger"

    competition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(12), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


@event.listens_for(CompetitionWalletLedger, "before_update", propagate=True)
def _prevent_competition_wallet_ledger_updates(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Competition wallet ledger entries are append-only and cannot be updated.")


@event.listens_for(CompetitionWalletLedger, "before_delete", propagate=True)
def _prevent_competition_wallet_ledger_deletes(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Competition wallet ledger entries are append-only and cannot be deleted.")
