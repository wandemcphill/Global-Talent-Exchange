"""Create owner living club world tables: events, relationships, relationship history, and directives.

Revision ID: 20261105_0225_phase2_4_living_club_world_events_relationships
Revises: 20261104_0224_canonical_player_identity_resolution_and_consolidation
Create Date: 2026-11-05 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261105_0225_phase2_4_living_club_world_events_relationships"
down_revision = "20261104_0224_canonical_player_identity_resolution_and_consolidation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "owner_club_events" not in tables:
        op.create_table(
            "owner_club_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("club_id", sa.String(36), nullable=False),
            sa.Column("category", sa.String(32), nullable=False),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("severity", sa.String(16), nullable=False, server_default="routine"),
            sa.Column("status", sa.String(24), nullable=False, server_default="active"),
            sa.Column("source_type", sa.String(32), nullable=False, server_default="system"),
            sa.Column("source_id", sa.String(64), nullable=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("participants_json", sa.JSON(), nullable=False),
            sa.Column("world_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("consequences_json", sa.JSON(), nullable=False),
            sa.Column("idempotency_key", sa.String(128), nullable=True),
            sa.Column("actions_json", sa.JSON(), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolution_action", sa.String(64), nullable=True),
            sa.Column("resolution_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_owner_club_events_club_id", "owner_club_events", ["club_id"])
        op.create_index("ix_owner_club_events_category", "owner_club_events", ["category"])
        op.create_index("ix_owner_club_events_event_type", "owner_club_events", ["event_type"])
        op.create_index("ix_owner_club_events_status", "owner_club_events", ["status"])
        op.create_index("ix_owner_club_events_source_id", "owner_club_events", ["source_id"])
        op.create_index("ix_owner_club_events_world_day", "owner_club_events", ["world_day"])
        op.create_index("ix_owner_club_events_idempotency_key", "owner_club_events", ["idempotency_key"], unique=True)

    if "owner_club_relationships" not in tables:
        op.create_table(
            "owner_club_relationships",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("club_id", sa.String(36), nullable=False),
            sa.Column("pairing_key", sa.String(160), nullable=False),
            sa.Column("participant_a_type", sa.String(32), nullable=False),
            sa.Column("participant_a_id", sa.String(64), nullable=False),
            sa.Column("participant_a_name", sa.String(160), nullable=False),
            sa.Column("participant_b_type", sa.String(32), nullable=False),
            sa.Column("participant_b_id", sa.String(64), nullable=False),
            sa.Column("participant_b_name", sa.String(160), nullable=False),
            sa.Column("trust", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("respect", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("affinity", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("tension", sa.Integer(), nullable=False, server_default="20"),
            sa.Column("status", sa.String(24), nullable=False, server_default="active"),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("club_id", "pairing_key", name="uq_owner_club_relationships_club_pairing"),
        )
        op.create_index("ix_owner_club_relationships_club_id", "owner_club_relationships", ["club_id"])
        op.create_index("ix_owner_club_relationships_pairing_key", "owner_club_relationships", ["pairing_key"])
        op.create_index(
            "uq_owner_club_relationships_club_pairing_idx",
            "owner_club_relationships",
            ["club_id", "pairing_key"],
            unique=True,
        )
        op.create_index(
            "ix_owner_club_relationships_participant_a_id", "owner_club_relationships", ["participant_a_id"]
        )
        op.create_index(
            "ix_owner_club_relationships_participant_b_id", "owner_club_relationships", ["participant_b_id"]
        )

    if "owner_club_relationship_history" not in tables:
        op.create_table(
            "owner_club_relationship_history",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("relationship_id", sa.String(36), nullable=False),
            sa.Column("club_id", sa.String(36), nullable=False),
            sa.Column("world_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("reason", sa.String(255), nullable=False),
            sa.Column("source_event_id", sa.String(36), nullable=True),
            sa.Column("delta_trust", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("delta_respect", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("delta_affinity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("delta_tension", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("snapshot_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_owner_club_rel_hist_rel_id", "owner_club_relationship_history", ["relationship_id"])
        op.create_index("ix_owner_club_rel_hist_club_id", "owner_club_relationship_history", ["club_id"])
        op.create_index("ix_owner_club_rel_hist_world_day", "owner_club_relationship_history", ["world_day"])
        op.create_index("ix_owner_club_rel_hist_src_event_id", "owner_club_relationship_history", ["source_event_id"])

    if "owner_club_directives" not in tables:
        op.create_table(
            "owner_club_directives",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("club_id", sa.String(36), nullable=False),
            sa.Column("department", sa.String(32), nullable=False),
            sa.Column("directive_key", sa.String(64), nullable=False),
            sa.Column("title", sa.String(160), nullable=False),
            sa.Column("instruction", sa.Text(), nullable=False),
            sa.Column("target_scope", sa.String(64), nullable=True),
            sa.Column("target_scope_id", sa.String(64), nullable=True),
            sa.Column("status", sa.String(24), nullable=False, server_default="active"),
            sa.Column("issued_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("deadline_day", sa.Integer(), nullable=True),
            sa.Column("acknowledged_by", sa.String(120), nullable=True),
            sa.Column("acknowledgement_text", sa.Text(), nullable=True),
            sa.Column("consequences_json", sa.JSON(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_owner_club_directives_club_id", "owner_club_directives", ["club_id"])
        op.create_index("ix_owner_club_directives_department", "owner_club_directives", ["department"])
        op.create_index("ix_owner_club_directives_directive_key", "owner_club_directives", ["directive_key"])
        op.create_index("ix_owner_club_directives_status", "owner_club_directives", ["status"])
        op.create_index("ix_owner_club_directives_issued_day", "owner_club_directives", ["issued_day"])


def downgrade() -> None:
    op.drop_table("owner_club_directives")
    op.drop_table("owner_club_relationship_history")
    op.drop_table("owner_club_relationships")
    op.drop_table("owner_club_events")
