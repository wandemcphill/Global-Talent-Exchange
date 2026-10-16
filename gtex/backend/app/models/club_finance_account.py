from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.club_finance_account_type import ClubFinanceAccountType
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.club_finance_ledger_entry import ClubFinanceLedgerEntry


class ClubFinanceAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_finance_accounts"
    __table_args__ = (
        UniqueConstraint("club_id", "account_type", name="uq_club_finance_accounts_club_account_type"),
    )

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    account_type: Mapped[ClubFinanceAccountType] = mapped_column(
        Enum(
            ClubFinanceAccountType,
            name="club_finance_account_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    balance_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    allow_negative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    ledger_entries: Mapped[list["ClubFinanceLedgerEntry"]] = relationship(back_populates="account")


__all__ = ["ClubFinanceAccount"]
