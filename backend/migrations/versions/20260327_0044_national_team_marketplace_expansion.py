"""Add national team rental tournaments and club marketplace ops hooks.

Revision ID: 20260327_0044_national_team_marketplace_expansion
Revises: 20260327_0043_merge_parallel_0042_heads
Create Date: 2026-03-27 23:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0044_national_team_marketplace_expansion"
down_revision = "20260327_0043_merge_parallel_0042_heads"
branch_labels = None
depends_on = None


rental_contract_status_enum = sa.Enum(
    "active",
    "expired",
    "released",
    name="national_team_rental_contract_status",
    native_enum=False,
)
story_event_type_enum = sa.Enum(
    "underdog_run",
    "giant_killing",
    "revenge_match",
    "star_breakout",
    name="tournament_story_event_type",
    native_enum=False,
)
stadium_ad_placement_enum = sa.Enum(
    "billboard",
    "sideline",
    "digital_screen",
    name="stadium_ad_placement",
    native_enum=False,
)


def upgrade() -> None:
    with op.batch_alter_table("national_team_competitions", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("linked_competition_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("entry_opens_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("entry_closes_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.create_foreign_key(
            "fk_nt_competitions_linked_competition_id_user_competitions",
            "user_competitions",
            ["linked_competition_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_national_team_competitions_linked_competition_id", ["linked_competition_id"], unique=False)

    op.create_table(
        "national_team_rental_contracts",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("tournament_id", sa.String(length=36), nullable=False),
        sa.Column("entry_id", sa.String(length=36), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("loan_price_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("is_free_player", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("free_player_tier", sa.String(length=16), nullable=True),
        sa.Column("status", rental_contract_status_enum, nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["entry_id"], ["national_team_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tournament_id"], ["national_team_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_national_team_rental_contracts")),
    )
    op.create_index("ix_national_team_rental_contracts_tournament_id", "national_team_rental_contracts", ["tournament_id"], unique=False)
    op.create_index("ix_national_team_rental_contracts_entry_id", "national_team_rental_contracts", ["entry_id"], unique=False)
    op.create_index("ix_national_team_rental_contracts_user_id", "national_team_rental_contracts", ["user_id"], unique=False)
    op.create_index("ix_national_team_rental_contracts_player_id", "national_team_rental_contracts", ["player_id"], unique=False)
    op.create_index("ix_national_team_rental_contracts_status", "national_team_rental_contracts", ["status"], unique=False)

    op.create_table(
        "national_team_rental_squad_members",
        sa.Column("entry_id", sa.String(length=36), nullable=False),
        sa.Column("rental_contract_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("overall_rating", sa.Integer(), nullable=False),
        sa.Column("shirt_number", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=16), nullable=False, server_default="rental"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="selected"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["entry_id"], ["national_team_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rental_contract_id"], ["national_team_rental_contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_national_team_rental_squad_members")),
        sa.UniqueConstraint("entry_id", "player_id", name="uq_national_team_rental_squad_members_entry_player"),
        sa.UniqueConstraint("rental_contract_id", name="uq_national_team_rental_squad_members_contract"),
    )
    op.create_index("ix_national_team_rental_squad_members_entry_id", "national_team_rental_squad_members", ["entry_id"], unique=False)

    op.create_table(
        "tournament_story_events",
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("type", story_event_type_enum, nullable=False),
        sa.Column("entities", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("narrative_text", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["competition_id"], ["national_team_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tournament_story_events")),
    )
    op.create_index("ix_tournament_story_events_competition_id", "tournament_story_events", ["competition_id"], unique=False)
    op.create_index("ix_tournament_story_events_match_id", "tournament_story_events", ["match_id"], unique=False)
    op.create_index("ix_tournament_story_events_type", "tournament_story_events", ["type"], unique=False)

    op.create_table(
        "tournament_themes",
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("video_asset_url", sa.String(length=255), nullable=True),
        sa.Column("audio_theme_url", sa.String(length=255), nullable=True),
        sa.Column("visual_style", sa.String(length=64), nullable=False, server_default="gtex_default"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["competition_id"], ["national_team_competitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tournament_themes")),
        sa.UniqueConstraint("competition_id", name="uq_tournament_themes_competition_id"),
    )
    op.create_index("ix_tournament_themes_competition_id", "tournament_themes", ["competition_id"], unique=False)

    op.create_table(
        "stadium_ads",
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("asset_url", sa.String(length=255), nullable=False),
        sa.Column("placement", stadium_ad_placement_enum, nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("rotation_interval_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["competition_id"], ["national_team_competitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stadium_ads")),
    )
    op.create_index("ix_stadium_ads_competition_id", "stadium_ads", ["competition_id"], unique=False)
    op.create_index("ix_stadium_ads_placement", "stadium_ads", ["placement"], unique=False)
    op.create_index("ix_stadium_ads_priority", "stadium_ads", ["priority"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_stadium_ads_priority", table_name="stadium_ads")
    op.drop_index("ix_stadium_ads_placement", table_name="stadium_ads")
    op.drop_index("ix_stadium_ads_competition_id", table_name="stadium_ads")
    op.drop_table("stadium_ads")

    op.drop_index("ix_tournament_themes_competition_id", table_name="tournament_themes")
    op.drop_table("tournament_themes")

    op.drop_index("ix_tournament_story_events_type", table_name="tournament_story_events")
    op.drop_index("ix_tournament_story_events_match_id", table_name="tournament_story_events")
    op.drop_index("ix_tournament_story_events_competition_id", table_name="tournament_story_events")
    op.drop_table("tournament_story_events")

    op.drop_index("ix_national_team_rental_squad_members_entry_id", table_name="national_team_rental_squad_members")
    op.drop_table("national_team_rental_squad_members")

    op.drop_index("ix_national_team_rental_contracts_status", table_name="national_team_rental_contracts")
    op.drop_index("ix_national_team_rental_contracts_player_id", table_name="national_team_rental_contracts")
    op.drop_index("ix_national_team_rental_contracts_user_id", table_name="national_team_rental_contracts")
    op.drop_index("ix_national_team_rental_contracts_entry_id", table_name="national_team_rental_contracts")
    op.drop_index("ix_national_team_rental_contracts_tournament_id", table_name="national_team_rental_contracts")
    op.drop_table("national_team_rental_contracts")

    with op.batch_alter_table("national_team_competitions", recreate="auto") as batch_op:
        batch_op.drop_index("ix_national_team_competitions_linked_competition_id")
        batch_op.drop_constraint("fk_nt_competitions_linked_competition_id_user_competitions", type_="foreignkey")
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("kickoff_at")
        batch_op.drop_column("entry_closes_at")
        batch_op.drop_column("entry_opens_at")
        batch_op.drop_column("linked_competition_id")
