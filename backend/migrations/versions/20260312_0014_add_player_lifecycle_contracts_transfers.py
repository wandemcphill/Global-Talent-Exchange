"""Add player lifecycle, contract, injury, and transfer window tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260312_0014"
down_revision = "20260312_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_career_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("club_name", sa.String(length=160), nullable=False),
        sa.Column("season_label", sa.String(length=80), nullable=False),
        sa.Column("squad_role", sa.String(length=64), nullable=True),
        sa.Column("appearances", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("goals", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("assists", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("average_rating", sa.Integer(), nullable=True),
        sa.Column("honours_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("start_on", sa.Date(), nullable=True),
        sa.Column("end_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_player_career_entries"),
    )
    op.create_index("ix_player_career_entries_player_id", "player_career_entries", ["player_id"], unique=False)
    op.create_index("ix_player_career_entries_club_id", "player_career_entries", ["club_id"], unique=False)
    op.create_index("ix_player_career_entries_season_label", "player_career_entries", ["season_label"], unique=False)

    op.create_table(
        "player_contracts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'active'"), nullable=False),
        sa.Column("wage_amount", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("bonus_terms", sa.String(length=255), nullable=True),
        sa.Column("release_clause_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("signed_on", sa.Date(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("extension_option_until", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_player_contracts"),
    )
    op.create_index("ix_player_contracts_player_id", "player_contracts", ["player_id"], unique=False)
    op.create_index("ix_player_contracts_club_id", "player_contracts", ["club_id"], unique=False)
    op.create_index("ix_player_contracts_status", "player_contracts", ["status"], unique=False)
    op.create_index("ix_player_contracts_ends_on", "player_contracts", ["ends_on"], unique=False)

    op.create_table(
        "player_injury_cases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("severity", sa.String(length=24), server_default=sa.text("'minor'"), nullable=False),
        sa.Column("injury_type", sa.String(length=80), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("expected_return_on", sa.Date(), nullable=True),
        sa.Column("recovered_on", sa.Date(), nullable=True),
        sa.Column("source_match_id", sa.String(length=36), nullable=True),
        sa.Column("recovery_days", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_availability_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_player_injury_cases"),
    )
    op.create_index("ix_player_injury_cases_player_id", "player_injury_cases", ["player_id"], unique=False)
    op.create_index("ix_player_injury_cases_club_id", "player_injury_cases", ["club_id"], unique=False)
    op.create_index("ix_player_injury_cases_severity", "player_injury_cases", ["severity"], unique=False)
    op.create_index("ix_player_injury_cases_occurred_on", "player_injury_cases", ["occurred_on"], unique=False)

    op.create_table(
        "transfer_windows",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("territory_code", sa.String(length=16), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'upcoming'"), nullable=False),
        sa.Column("opens_on", sa.Date(), nullable=False),
        sa.Column("closes_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_transfer_windows"),
    )
    op.create_index("ix_transfer_windows_territory_code", "transfer_windows", ["territory_code"], unique=False)
    op.create_index("ix_transfer_windows_status", "transfer_windows", ["status"], unique=False)
    op.create_index("ix_transfer_windows_opens_on", "transfer_windows", ["opens_on"], unique=False)
    op.create_index("ix_transfer_windows_closes_on", "transfer_windows", ["closes_on"], unique=False)

    op.create_table(
        "transfer_bids",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("window_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("selling_club_id", sa.String(length=36), nullable=True),
        sa.Column("buying_club_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("bid_amount", sa.Numeric(12, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("wage_offer_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("sell_on_clause_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("structured_terms_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["buying_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selling_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["window_id"], ["transfer_windows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_transfer_bids"),
    )
    op.create_index("ix_transfer_bids_window_id", "transfer_bids", ["window_id"], unique=False)
    op.create_index("ix_transfer_bids_player_id", "transfer_bids", ["player_id"], unique=False)
    op.create_index("ix_transfer_bids_selling_club_id", "transfer_bids", ["selling_club_id"], unique=False)
    op.create_index("ix_transfer_bids_buying_club_id", "transfer_bids", ["buying_club_id"], unique=False)
    op.create_index("ix_transfer_bids_status", "transfer_bids", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transfer_bids_status", table_name="transfer_bids")
    op.drop_index("ix_transfer_bids_buying_club_id", table_name="transfer_bids")
    op.drop_index("ix_transfer_bids_selling_club_id", table_name="transfer_bids")
    op.drop_index("ix_transfer_bids_player_id", table_name="transfer_bids")
    op.drop_index("ix_transfer_bids_window_id", table_name="transfer_bids")
    op.drop_table("transfer_bids")
    op.drop_index("ix_transfer_windows_closes_on", table_name="transfer_windows")
    op.drop_index("ix_transfer_windows_opens_on", table_name="transfer_windows")
    op.drop_index("ix_transfer_windows_status", table_name="transfer_windows")
    op.drop_index("ix_transfer_windows_territory_code", table_name="transfer_windows")
    op.drop_table("transfer_windows")
    op.drop_index("ix_player_injury_cases_occurred_on", table_name="player_injury_cases")
    op.drop_index("ix_player_injury_cases_severity", table_name="player_injury_cases")
    op.drop_index("ix_player_injury_cases_club_id", table_name="player_injury_cases")
    op.drop_index("ix_player_injury_cases_player_id", table_name="player_injury_cases")
    op.drop_table("player_injury_cases")
    op.drop_index("ix_player_contracts_ends_on", table_name="player_contracts")
    op.drop_index("ix_player_contracts_status", table_name="player_contracts")
    op.drop_index("ix_player_contracts_club_id", table_name="player_contracts")
    op.drop_index("ix_player_contracts_player_id", table_name="player_contracts")
    op.drop_table("player_contracts")
    op.drop_index("ix_player_career_entries_season_label", table_name="player_career_entries")
    op.drop_index("ix_player_career_entries_club_id", table_name="player_career_entries")
    op.drop_index("ix_player_career_entries_player_id", table_name="player_career_entries")
    op.drop_table("player_career_entries")
