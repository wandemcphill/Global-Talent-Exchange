"""GTEX Commercial Network & Advertising Engine schema upgrade.

Revision ID: 20261107_0227_gtex_commercial_network
Revises: 20261105_0226_phase2_4_relationship_pair_uniqueness
Create Date: 2026-11-07 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.models.brand_ad_campaign import BrandAdCampaign
from app.models.commercial_network import (
    AdPlacementSpec,
    AdPricingPackage,
    AdvertiserClientBrand,
    AdvertiserInvoice,
    AdvertiserMediaAsset,
    AdvertiserPaymentRecord,
    AdvertiserRefundRecord,
    AdvertiserSubscription,
    AdvertiserWebhookEvent,
    AdvertiserWorkspace,
    AdvertiserWorkspaceMember,
    CommercialAuditLog,
)

revision = "20261107_0228_gtex_commercial_network"
down_revision = "20261106_0227_owner_club_delegation_and_authority_engine"
branch_labels = None
depends_on = None


_NEW_TABLES = (
    AdvertiserWorkspace.__table__,
    AdvertiserWorkspaceMember.__table__,
    AdvertiserClientBrand.__table__,
    AdPlacementSpec.__table__,
    AdPricingPackage.__table__,
    AdvertiserMediaAsset.__table__,
    AdvertiserPaymentRecord.__table__,
    AdvertiserInvoice.__table__,
    AdvertiserSubscription.__table__,
    AdvertiserRefundRecord.__table__,
    AdvertiserWebhookEvent.__table__,
    CommercialAuditLog.__table__,
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table in _NEW_TABLES:
        if table.name not in existing_tables:
            table.create(bind=bind, checkfirst=True)

    if "advertiser_media_assets" in existing_tables:
        media_cols = {col["name"] for col in inspector.get_columns("advertiser_media_assets")}
        media_new_cols = [
            (
                "storage_provider",
                sa.Column("storage_provider", sa.String(64), nullable=False, server_default="local_object_storage"),
            ),
            ("storage_key", sa.Column("storage_key", sa.String(512), nullable=True)),
            (
                "access_classification",
                sa.Column("access_classification", sa.String(32), nullable=False, server_default="public"),
            ),
        ]
        for col_name, col_def in media_new_cols:
            if col_name not in media_cols:
                op.add_column("advertiser_media_assets", col_def)
        if "data" in media_cols and bind.dialect.name == "postgresql":
            op.alter_column("advertiser_media_assets", "data", nullable=True)

    if "brand_ad_campaigns" not in existing_tables:
        BrandAdCampaign.__table__.create(bind=bind, checkfirst=True)
    else:
        existing_cols = {col["name"] for col in inspector.get_columns("brand_ad_campaigns")}
        new_columns = [
            ("workspace_id", sa.Column("workspace_id", sa.String(length=36), nullable=True)),
            ("client_brand_id", sa.Column("client_brand_id", sa.String(length=36), nullable=True)),
            ("package_id", sa.Column("package_id", sa.String(length=36), nullable=True)),
            ("contact_email", sa.Column("contact_email", sa.String(length=320), nullable=True)),
            ("contact_phone", sa.Column("contact_phone", sa.String(length=64), nullable=True)),
            ("contact_name", sa.Column("contact_name", sa.String(length=160), nullable=True)),
            ("website_url", sa.Column("website_url", sa.String(length=2048), nullable=True)),
            ("placements_json", sa.Column("placements_json", sa.JSON(), nullable=False, server_default="[]")),
            ("logo_asset_id", sa.Column("logo_asset_id", sa.String(length=36), nullable=True)),
            ("creative_asset_id", sa.Column("creative_asset_id", sa.String(length=36), nullable=True)),
            ("creative_media_type", sa.Column("creative_media_type", sa.String(length=64), nullable=True)),
            (
                "is_silent_creative",
                sa.Column("is_silent_creative", sa.Boolean(), nullable=False, server_default=sa.true()),
            ),
            ("duration_days", sa.Column("duration_days", sa.Integer(), nullable=False, server_default="7")),
            (
                "payment_status",
                sa.Column("payment_status", sa.String(length=32), nullable=False, server_default="unpaid"),
            ),
            ("payment_reference", sa.Column("payment_reference", sa.String(length=120), nullable=True)),
            (
                "price_minor_ngn",
                sa.Column(
                    "price_minor_ngn",
                    sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                    nullable=False,
                    server_default="0",
                ),
            ),
            ("is_subscription", sa.Column("is_subscription", sa.Boolean(), nullable=False, server_default=sa.false())),
            ("music_audio_asset_id", sa.Column("music_audio_asset_id", sa.String(length=36), nullable=True)),
            ("music_artwork_asset_id", sa.Column("music_artwork_asset_id", sa.String(length=36), nullable=True)),
            ("music_audio_url", sa.Column("music_audio_url", sa.String(length=2048), nullable=True)),
            ("music_artwork_url", sa.Column("music_artwork_url", sa.String(length=2048), nullable=True)),
            (
                "music_explicit_content",
                sa.Column("music_explicit_content", sa.Boolean(), nullable=False, server_default=sa.false()),
            ),
            (
                "music_rights_declaration_accepted",
                sa.Column("music_rights_declaration_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
            ),
            (
                "music_rights_declaration_at",
                sa.Column("music_rights_declaration_at", sa.DateTime(timezone=True), nullable=True),
            ),
        ]
        for col_name, col_def in new_columns:
            if col_name not in existing_cols:
                op.add_column("brand_ad_campaigns", col_def)

        if bind.dialect.name == "postgresql":
            for constraint_name in ("valid_placement", "valid_status", "valid_pricing_model"):
                op.execute(f"ALTER TABLE brand_ad_campaigns DROP CONSTRAINT IF EXISTS {constraint_name}")
            op.alter_column("brand_ad_campaigns", "status", type_=sa.String(length=32))
            op.alter_column("brand_ad_campaigns", "pricing_model", type_=sa.String(length=24))
            if "brand_ad_events" in existing_tables:
                op.alter_column("brand_ad_events", "event_type", type_=sa.String(length=32))
            if "brand_ad_review_events" in existing_tables:
                op.alter_column("brand_ad_review_events", "action", type_=sa.String(length=32))
                op.alter_column("brand_ad_review_events", "from_status", type_=sa.String(length=32))
                op.alter_column("brand_ad_review_events", "to_status", type_=sa.String(length=32))

    # The legacy brand_ad_campaigns table predates this migration. When it
    # already exists, create the workspace lookup index added to the model.
    # Keep this idempotent because upgraded environments may already have it.
    if "brand_ad_campaigns" in sa.inspect(bind).get_table_names():
        campaign_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("brand_ad_campaigns")}
        if "ix_brand_ad_campaigns_workspace" not in campaign_indexes:
            op.create_index(
                "ix_brand_ad_campaigns_workspace",
                "brand_ad_campaigns",
                ["workspace_id", "status"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(_NEW_TABLES):
        table.drop(bind=bind, checkfirst=True)
