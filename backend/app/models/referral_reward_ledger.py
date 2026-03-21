from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import Enum, ForeignKey, JSON, Numeric, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums.referral_reward_status import ReferralRewardStatus
from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ReferralRewardLedger(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "referral_reward_ledger"

    entry_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    reward_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("referral_rewards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    status_after: Mapped[ReferralRewardStatus] = mapped_column(
        Enum(
            ReferralRewardStatus,
            name="referral_reward_status",
            native_enum=False,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


@event.listens_for(ReferralRewardLedger, "before_update", propagate=True)
def _prevent_referral_reward_ledger_updates(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Referral reward ledger entries are append-only and cannot be updated.")


@event.listens_for(ReferralRewardLedger, "before_delete", propagate=True)
def _prevent_referral_reward_ledger_deletes(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Referral reward ledger entries are append-only and cannot be deleted.")
