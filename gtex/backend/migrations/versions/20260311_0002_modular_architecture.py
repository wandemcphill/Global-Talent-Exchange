"""Add persisted read models for modular architecture."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260311_0002"
down_revision = "20260311_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_value_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_credits", sa.Float(), nullable=False),
        sa.Column("target_credits", sa.Float(), nullable=False),
        sa.Column("movement_pct", sa.Float(), nullable=False),
        sa.Column("breakdown_json", sa.JSON(), nullable=False),
        sa.Column("drivers_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], name="fk_player_value_snapshots_player_id_ingestion_players", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_player_value_snapshots"),
        sa.UniqueConstraint("player_id", "as_of", name="uq_player_value_snapshots_player_as_of"),
    )
    op.create_index("ix_player_value_snapshots_player_id", "player_value_snapshots", ["player_id"], unique=False)
    op.create_index("ix_player_value_snapshots_as_of", "player_value_snapshots", ["as_of"], unique=False)

    op.create_table(
        "player_summary_read_models",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("current_club_id", sa.String(length=36), nullable=True),
        sa.Column("current_club_name", sa.String(length=160), nullable=True),
        sa.Column("current_competition_id", sa.String(length=36), nullable=True),
        sa.Column("current_competition_name", sa.String(length=160), nullable=True),
        sa.Column("last_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("last_snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_value_credits", sa.Float(), nullable=False),
        sa.Column("previous_value_credits", sa.Float(), nullable=False),
        sa.Column("movement_pct", sa.Float(), nullable=False),
        sa.Column("average_rating", sa.Float(), nullable=True),
        sa.Column("market_interest_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], name="fk_player_summary_read_models_player_id_ingestion_players", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("player_id", name="pk_player_summary_read_models"),
    )

    op.create_table(
        "market_summary_read_models",
        sa.Column("asset_id", sa.String(length=128), nullable=False),
        sa.Column("open_listing_id", sa.String(length=32), nullable=True),
        sa.Column("open_listing_type", sa.String(length=32), nullable=True),
        sa.Column("seller_user_id", sa.String(length=36), nullable=True),
        sa.Column("ask_price", sa.Integer(), nullable=True),
        sa.Column("pending_offer_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("best_offer_price", sa.Integer(), nullable=True),
        sa.Column("active_trade_intent_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("asset_id", name="pk_market_summary_read_models"),
    )


def downgrade() -> None:
    op.drop_table("market_summary_read_models")
    op.drop_table("player_summary_read_models")
    op.drop_index("ix_player_value_snapshots_as_of", table_name="player_value_snapshots")
    op.drop_index("ix_player_value_snapshots_player_id", table_name="player_value_snapshots")
    op.drop_table("player_value_snapshots")
