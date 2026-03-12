from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TransferBid(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transfer_bids"

    window_id: Mapped[str] = mapped_column(String(36), ForeignKey("transfer_windows.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False, index=True)
    selling_club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    buying_club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default="draft", index=True)
    bid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    wage_offer_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    sell_on_clause_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    structured_terms_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
