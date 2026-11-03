"""Create owner showroom assets table.

Revision ID: 20261103_0218_create_owner_showroom_assets
Revises: 20261103_0217_backfill_player_attributes_positions_and_tradeability
Create Date: 2026-11-03 09:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261103_0218_create_owner_showroom_assets"
down_revision = "20261103_0217_backfill_player_attributes_positions_and_tradeability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "owner_showroom_assets" not in tables:
        op.create_table(
            "owner_showroom_assets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("club_id", sa.String(36), nullable=False),
            sa.Column("owner_user_id", sa.String(36), nullable=False),
            sa.Column("catalog_key", sa.String(64), nullable=False),
            sa.Column("custom_name", sa.String(160), nullable=False),
            sa.Column("category", sa.String(48), nullable=False),
            sa.Column("model", sa.String(120), nullable=True),
            sa.Column("image_url", sa.String(255), nullable=True),
            sa.Column("purchase_price_gtex", sa.Numeric(20, 4), nullable=False),
            sa.Column("gifted_to_player_id", sa.String(36), nullable=True),
            sa.Column("gifted_to_player_name", sa.String(120), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("ledger_event_id", sa.String(36), nullable=True),
            sa.Column("idempotency_key", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_owner_showroom_assets_club_id", "owner_showroom_assets", ["club_id"])
        op.create_index("ix_owner_showroom_assets_owner_user_id", "owner_showroom_assets", ["owner_user_id"])
        op.create_index("ix_owner_showroom_assets_catalog_key", "owner_showroom_assets", ["catalog_key"])
        op.create_index("ix_owner_showroom_assets_category", "owner_showroom_assets", ["category"])
        op.create_index(
            "ix_owner_showroom_assets_gifted_to_player_id", "owner_showroom_assets", ["gifted_to_player_id"]
        )
        op.create_index("ix_owner_showroom_assets_status", "owner_showroom_assets", ["status"])
        op.create_index("ix_owner_showroom_assets_ledger_event_id", "owner_showroom_assets", ["ledger_event_id"])
        op.create_index("ix_owner_showroom_assets_idempotency_key", "owner_showroom_assets", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("owner_showroom_assets")
