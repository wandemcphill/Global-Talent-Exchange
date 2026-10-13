"""Regen endorsement deals for platform outbound sponsorship.

Revision ID: 20261013_0126_regen_endorsement_deals
Revises: 20260917_0125_legendary_catalogue_governance
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261013_0126_regen_endorsement_deals"
down_revision = "20260917_0125_legendary_catalogue_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regen_endorsement_deals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "player_id",
            sa.String(length=36),
            sa.ForeignKey("ingestion_players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sponsor_name", sa.String(length=120), nullable=False),
        sa.Column("brand_label", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="offered"),
        sa.Column("term_months", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("deal_value_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("owner_share_ratio", sa.Numeric(8, 4), nullable=False, server_default="0.6000"),
        sa.Column("platform_share_ratio", sa.Numeric(8, 4), nullable=False, server_default="0.4000"),
        sa.Column("badge_label", sa.String(length=80), nullable=False, server_default="Endorsed"),
        sa.Column("creative_url", sa.String(length=512), nullable=True),
        sa.Column(
            "offered_by_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
    )
    op.create_index("ix_regen_endorsement_deals_player_id", "regen_endorsement_deals", ["player_id"])
    op.create_index("ix_regen_endorsement_deals_owner_user_id", "regen_endorsement_deals", ["owner_user_id"])
    op.create_index("ix_regen_endorsement_deals_status", "regen_endorsement_deals", ["status"])


def downgrade() -> None:
    op.drop_index("ix_regen_endorsement_deals_status", table_name="regen_endorsement_deals")
    op.drop_index("ix_regen_endorsement_deals_owner_user_id", table_name="regen_endorsement_deals")
    op.drop_index("ix_regen_endorsement_deals_player_id", table_name="regen_endorsement_deals")
    op.drop_table("regen_endorsement_deals")
