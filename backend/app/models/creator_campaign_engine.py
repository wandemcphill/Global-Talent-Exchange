from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorCampaignMetricSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_campaign_metric_snapshots"
    __table_args__ = (
        UniqueConstraint("campaign_id", "snapshot_date", name="uq_campaign_metric_snapshots_campaign_date"),
    )

    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    clicks: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    attributed_signups: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    verified_signups: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    qualified_joins: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    gifts_generated: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    gift_volume_minor: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    rewards_generated: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    reward_volume_minor: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    competition_entries: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(nullable=False, default=dict)


__all__ = ["CreatorCampaignMetricSnapshot"]
