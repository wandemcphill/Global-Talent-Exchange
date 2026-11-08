from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AdvertiserWorkspace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Independent commercial workspace for Business, Agency, or Music advertisers."""

    __tablename__ = "advertiser_workspaces"
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('business', 'agency', 'music')",
            name="ck_advertiser_workspaces_account_type",
        ),
        CheckConstraint(
            "status IN ('active', 'suspended', 'pending_verification')",
            name="ck_advertiser_workspaces_status",
        ),
        Index("ix_advertiser_workspaces_owner", "owner_user_id"),
        Index("ix_advertiser_workspaces_type_status", "account_type", "status"),
    )

    owner_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    account_type: Mapped[str] = mapped_column(
        String(24), nullable=False, default="business", server_default="business"
    )
    company_name: Mapped[str] = mapped_column(String(180), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(320), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    website_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    logo_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    stage_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    label_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", server_default="active"
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="NGN", server_default="NGN"
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AdvertiserWorkspaceMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Authorised team member within an advertiser or agency workspace."""

    __tablename__ = "advertiser_workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "invited_email", name="uq_advertiser_workspace_member_email"),
        CheckConstraint(
            "role IN ('owner', 'admin', 'campaign_manager', 'billing', 'analyst')",
            name="ck_advertiser_workspace_members_role",
        ),
        CheckConstraint(
            "status IN ('active', 'invited', 'revoked')",
            name="ck_advertiser_workspace_members_status",
        ),
        Index("ix_advertiser_workspace_members_workspace", "workspace_id", "status"),
        Index("ix_advertiser_workspace_members_user", "user_id"),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("advertiser_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    invited_email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="campaign_manager", server_default="campaign_manager"
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="active", server_default="active"
    )
    permissions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    invited_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AdvertiserClientBrand(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Client brand managed by an advertising agency workspace."""

    __tablename__ = "advertiser_client_brands"
    __table_args__ = (
        Index("ix_advertiser_client_brands_workspace", "workspace_id", "is_active"),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("advertiser_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    brand_name: Mapped[str] = mapped_column(String(180), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    logo_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())


class AdPlacementSpec(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Central registry of GTEX commercial advertising placements."""

    __tablename__ = "ad_placement_specs"
    __table_args__ = (
        UniqueConstraint("placement_key", name="uq_ad_placement_specs_key"),
        Index("ix_ad_placement_specs_enabled", "division", "is_enabled", "delivery_surface_ready"),
    )

    placement_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    division: Mapped[str] = mapped_column(String(16), nullable=False, default="brand", server_default="brand")
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    supported_media_types_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    aspect_ratio: Mapped[str] = mapped_column(String(32), nullable=False, default="16:9", server_default="16:9")
    recommended_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommended_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_file_size_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=26214400, server_default="26214400"
    )
    max_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_silent_media: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    # Nullable minor NGN (kobo) rate: None means pricing is not yet configured by an administrator.
    weekly_rate_minor_ngn: Mapped[int | None] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    delivery_surface_ready: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    frequency_cap_per_session: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10, server_default="10"
    )
    rotation_interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    priority_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    device_compatibility_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class AdPricingPackage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Admin-configurable NGN commercial pricing package or duration tier."""

    __tablename__ = "ad_pricing_packages"
    __table_args__ = (
        UniqueConstraint("package_code", name="uq_ad_pricing_packages_code"),
        CheckConstraint("currency = 'NGN'", name="ck_ad_pricing_packages_ngn_only"),
        CheckConstraint("duration_days >= 7", name="ck_ad_pricing_packages_min_duration"),
        Index("ix_ad_pricing_packages_division_active", "division", "is_active", "sort_order"),
    )

    package_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    division: Mapped[str] = mapped_column(String(16), nullable=False, default="brand", server_default="brand")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7, server_default="7")
    placement_keys_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_bundle: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    is_subscription: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    billing_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Nullable minor NGN (kobo) price: None indicates an explicit unconfigured pricing state.
    price_minor_ngn: Mapped[int | None] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN", server_default="NGN")
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AdvertiserMediaAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Uploaded creative image, silent video, logo, audio track, or cover artwork."""

    __tablename__ = "advertiser_media_assets"
    __table_args__ = (
        CheckConstraint(
            "asset_kind IN ('logo', 'brand_image', 'brand_video', 'music_audio', 'music_artwork')",
            name="ck_advertiser_media_assets_kind",
        ),
        CheckConstraint(
            "validation_status IN ('valid', 'rejected', 'quarantined')",
            name="ck_advertiser_media_assets_validation",
        ),
        Index("ix_advertiser_media_assets_workspace", "workspace_id", "asset_kind"),
        Index("ix_advertiser_media_assets_hash", "sha256_hash"),
    )

    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("advertiser_workspaces.id", ondelete="CASCADE"), nullable=True
    )
    uploaded_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    asset_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sanitized_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_audio_track: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    is_silent_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    validation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="valid", server_default="valid"
    )
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_provider: Mapped[str] = mapped_column(
        String(64), nullable=False, default="local_object_storage", server_default="local_object_storage"
    )
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    access_classification: Mapped[str] = mapped_column(
        String(32), nullable=False, default="public", server_default="public"
    )
    data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AdvertiserPaymentRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """NGN payment record for advertising campaigns and subscriptions."""

    __tablename__ = "advertiser_payment_records"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_advertiser_payment_records_reference"),
        UniqueConstraint("idempotency_key", name="uq_advertiser_payment_records_idempotency"),
        CheckConstraint("currency = 'NGN'", name="ck_advertiser_payment_records_ngn_only"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'paid', 'failed', 'cancelled', 'refunded', 'partially_refunded', 'reversed', 'flagged_overpayment')",
            name="ck_advertiser_payment_records_status",
        ),
        Index("ix_advertiser_payment_records_workspace", "workspace_id", "status"),
        Index("ix_advertiser_payment_records_campaign", "campaign_id", "status"),
    )

    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("advertiser_workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    campaign_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("brand_ad_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    subscription_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    initiated_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="paystack", server_default="paystack")
    provider_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    amount_minor_ngn: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN", server_default="NGN")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default="pending"
    )
    checkout_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    pricing_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    provider_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AdvertiserInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Official NGN invoice and receipt record for an advertiser transaction."""

    __tablename__ = "advertiser_invoices"
    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_advertiser_invoices_number"),
        CheckConstraint("currency = 'NGN'", name="ck_advertiser_invoices_ngn_only"),
        Index("ix_advertiser_invoices_workspace", "workspace_id", "status"),
    )

    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("advertiser_workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payment_record_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("advertiser_payment_records.id", ondelete="SET NULL"), nullable=True
    )
    subtotal_minor_ngn: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), nullable=False
    )
    tax_minor_ngn: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), nullable=False, default=0, server_default="0"
    )
    discount_minor_ngn: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), nullable=False, default=0, server_default="0"
    )
    total_minor_ngn: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN", server_default="NGN")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="issued", server_default="issued")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    line_items_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    billing_details_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AdvertiserSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Recurring NGN monthly subscription for a brand or music campaign."""

    __tablename__ = "advertiser_subscriptions"
    __table_args__ = (
        CheckConstraint("currency = 'NGN'", name="ck_advertiser_subscriptions_ngn_only"),
        CheckConstraint(
            "status IN ('pending_consent', 'active', 'past_due', 'grace_period', 'paused', 'cancelled', 'expired')",
            name="ck_advertiser_subscriptions_status",
        ),
        Index("ix_advertiser_subscriptions_workspace", "workspace_id", "status"),
        Index("ix_advertiser_subscriptions_campaign", "campaign_id", "status"),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("advertiser_workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    campaign_id: Mapped[str] = mapped_column(String(36), nullable=False)
    package_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="paystack", server_default="paystack")
    provider_authorization_code: Mapped[str | None] = mapped_column(String(160), nullable=True)
    amount_minor_ngn: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN", server_default="NGN")
    billing_interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30, server_default="30")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_consent", server_default="pending_consent"
    )
    consent_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    consent_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_terms_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_billing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class AdvertiserRefundRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Finance-admin authorised refund record."""

    __tablename__ = "advertiser_refund_records"
    __table_args__ = (
        CheckConstraint("currency = 'NGN'", name="ck_advertiser_refund_records_ngn_only"),
        Index("ix_advertiser_refund_records_payment", "payment_record_id"),
        Index("ix_advertiser_refund_records_workspace", "workspace_id"),
    )

    payment_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("advertiser_payment_records.id", ondelete="RESTRICT"), nullable=False
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("advertiser_workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    amount_minor_ngn: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN", server_default="NGN")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="completed", server_default="completed"
    )
    approved_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    provider_refund_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)


class AdvertiserWebhookEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Idempotent webhook ingestion ledger for Nigerian payment providers."""

    __tablename__ = "advertiser_webhook_events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_advertiser_webhook_events_event_id"),
        Index("ix_advertiser_webhook_events_reference", "payment_reference"),
    )

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payment_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    signature_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CommercialAuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable audit log for advertiser accounts, campaigns, pricing, moderation, and finance actions."""

    __tablename__ = "commercial_audit_logs"
    __table_args__ = (
        Index("ix_commercial_audit_logs_workspace", "workspace_id", "created_at"),
        Index("ix_commercial_audit_logs_campaign", "campaign_id", "created_at"),
        Index("ix_commercial_audit_logs_entity", "entity_type", "entity_id", "created_at"),
    )

    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "AdPlacementSpec",
    "AdPricingPackage",
    "AdvertiserClientBrand",
    "AdvertiserInvoice",
    "AdvertiserMediaAsset",
    "AdvertiserPaymentRecord",
    "AdvertiserRefundRecord",
    "AdvertiserSubscription",
    "AdvertiserWebhookEvent",
    "AdvertiserWorkspace",
    "AdvertiserWorkspaceMember",
    "CommercialAuditLog",
]
