from __future__ import annotations

from typing import Any, TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, JSON, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.common.enums.club_finance_account_type import ClubFinanceAccountType
from backend.app.common.enums.club_finance_entry_type import ClubFinanceEntryType
from backend.app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.club_finance_account import ClubFinanceAccount


class ClubFinanceLedgerEntry(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_finance_ledger_entries"

    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_finance_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_type: Mapped[ClubFinanceAccountType] = mapped_column(
        Enum(
            ClubFinanceAccountType,
            name="club_finance_account_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    entry_type: Mapped[ClubFinanceEntryType] = mapped_column(
        Enum(
            ClubFinanceEntryType,
            name="club_finance_entry_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    account: Mapped["ClubFinanceAccount"] = relationship(back_populates="ledger_entries")


@event.listens_for(ClubFinanceLedgerEntry, "before_update", propagate=True)
def _prevent_club_finance_ledger_updates(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Club finance ledger entries are append-only and cannot be updated.")


@event.listens_for(ClubFinanceLedgerEntry, "before_delete", propagate=True)
def _prevent_club_finance_ledger_deletes(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Club finance ledger entries are append-only and cannot be deleted.")


__all__ = ["ClubFinanceLedgerEntry"]
