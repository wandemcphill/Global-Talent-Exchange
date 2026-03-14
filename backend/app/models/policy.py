from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow

if TYPE_CHECKING:
    from backend.app.models.user import User


class PolicyDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "policy_documents"

    document_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    versions: Mapped[list["PolicyDocumentVersion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="PolicyDocumentVersion.published_at.desc()",
    )


class PolicyDocumentVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "policy_document_versions"
    __table_args__ = (
        UniqueConstraint("policy_document_id", "version_label", name="uq_policy_document_versions_document_version"),
    )

    policy_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("policy_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_label: Mapped[str] = mapped_column(String(32), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    document: Mapped[PolicyDocument] = relationship(back_populates="versions")
    acceptance_records: Mapped[list["PolicyAcceptanceRecord"]] = relationship(
        back_populates="document_version",
        cascade="all, delete-orphan",
    )


class PolicyAcceptanceRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "policy_acceptance_records"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "policy_document_version_id",
            name="uq_policy_acceptance_records_user_version",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_document_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("policy_document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    document_version: Mapped[PolicyDocumentVersion] = relationship(back_populates="acceptance_records")
    user: Mapped["User"] = relationship()


class CountryFeaturePolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "country_feature_policies"
    __table_args__ = (
        UniqueConstraint("country_code", "bucket_type", name="uq_country_feature_policies_country_bucket"),
    )

    country_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    bucket_type: Mapped[str] = mapped_column(String(32), nullable=False, default="default", server_default="default")
    deposits_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    market_trading_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    platform_reward_withdrawals_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    user_hosted_gift_withdrawals_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    gtex_competition_gift_withdrawals_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    national_reward_withdrawals_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    one_time_region_change_after_days: Mapped[int] = mapped_column(Integer, nullable=False, default=180, server_default="180")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
