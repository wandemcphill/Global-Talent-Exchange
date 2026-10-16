"""Add lifecycle events and managed club linkage for persistent player state."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260312_0015"
down_revision = "20260312_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ingestion_players") as batch_op:
        batch_op.add_column(
            sa.Column("current_club_profile_id", sa.String(length=36), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_ingestion_players_current_club_profile_id",
            "club_profiles",
            ["current_club_profile_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_ingestion_players_current_club_profile_id",
            ["current_club_profile_id"],
            unique=False,
        )

    op.create_table(
        "player_lifecycle_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("event_status", sa.String(length=24), server_default=sa.text("'recorded'"), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("related_entity_type", sa.String(length=48), nullable=True),
        sa.Column("related_entity_id", sa.String(length=36), nullable=True),
        sa.Column("summary", sa.String(length=200), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_player_lifecycle_events"),
    )
    op.create_index("ix_player_lifecycle_events_player_id", "player_lifecycle_events", ["player_id"], unique=False)
    op.create_index("ix_player_lifecycle_events_club_id", "player_lifecycle_events", ["club_id"], unique=False)
    op.create_index("ix_player_lifecycle_events_event_type", "player_lifecycle_events", ["event_type"], unique=False)
    op.create_index("ix_player_lifecycle_events_event_status", "player_lifecycle_events", ["event_status"], unique=False)
    op.create_index("ix_player_lifecycle_events_occurred_on", "player_lifecycle_events", ["occurred_on"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_player_lifecycle_events_occurred_on", table_name="player_lifecycle_events")
    op.drop_index("ix_player_lifecycle_events_event_status", table_name="player_lifecycle_events")
    op.drop_index("ix_player_lifecycle_events_event_type", table_name="player_lifecycle_events")
    op.drop_index("ix_player_lifecycle_events_club_id", table_name="player_lifecycle_events")
    op.drop_index("ix_player_lifecycle_events_player_id", table_name="player_lifecycle_events")
    op.drop_table("player_lifecycle_events")

    with op.batch_alter_table("ingestion_players") as batch_op:
        batch_op.drop_index("ix_ingestion_players_current_club_profile_id")
        batch_op.drop_constraint("fk_ingestion_players_current_club_profile_id", type_="foreignkey")
        batch_op.drop_column("current_club_profile_id")
