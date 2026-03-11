from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class MarketSummaryReadModel(TimestampMixin, Base):
    __tablename__ = "market_summary_read_models"

    asset_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    open_listing_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    open_listing_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    seller_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ask_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pending_offer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    best_offer_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_trade_intent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
