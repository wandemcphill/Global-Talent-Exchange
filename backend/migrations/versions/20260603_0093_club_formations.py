"""Add club formation drafts and publish history."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260603_0093_club_formations"
down_revision = "20260531_0092_auth_trust_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_formations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("scheme", sa.String(length=24), server_default="4-3-3", nullable=False),
        sa.Column("status", sa.String(length=24), server_default="draft", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("slots_json", sa.JSON(), nullable=False),
        sa.Column("chemistry_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("warnings_json", sa.JSON(), nullable=False),
        sa.Column("validation_blockers_json", sa.JSON(), nullable=False),
        sa.Column("source_formation_id", sa.String(length=36), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("audit_ref", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_club_formations_club_id", "club_formations", ["club_id"], unique=False)
    op.create_index("ix_club_formations_club_status", "club_formations", ["club_id", "status"], unique=False)
    op.create_index("ix_club_formations_published_at", "club_formations", ["published_at"], unique=False)
    op.create_index("ix_club_formations_status", "club_formations", ["status"], unique=False)
    op.create_table(
        "club_formation_audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("formation_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["formation_id"], ["club_formations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_club_formation_audit_events_action", "club_formation_audit_events", ["action"], unique=False)
    op.create_index("ix_club_formation_audit_events_club_created", "club_formation_audit_events", ["club_id", "created_at"], unique=False)
    op.create_index("ix_club_formation_audit_events_club_id", "club_formation_audit_events", ["club_id"], unique=False)
    op.create_index(
        "ix_club_formation_audit_events_formation_created",
        "club_formation_audit_events",
        ["formation_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_club_formation_audit_events_formation_id", "club_formation_audit_events", ["formation_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_club_formation_audit_events_formation_id", table_name="club_formation_audit_events")
    op.drop_index("ix_club_formation_audit_events_formation_created", table_name="club_formation_audit_events")
    op.drop_index("ix_club_formation_audit_events_club_id", table_name="club_formation_audit_events")
    op.drop_index("ix_club_formation_audit_events_club_created", table_name="club_formation_audit_events")
    op.drop_index("ix_club_formation_audit_events_action", table_name="club_formation_audit_events")
    op.drop_table("club_formation_audit_events")
    op.drop_index("ix_club_formations_status", table_name="club_formations")
    op.drop_index("ix_club_formations_published_at", table_name="club_formations")
    op.drop_index("ix_club_formations_club_status", table_name="club_formations")
    op.drop_index("ix_club_formations_club_id", table_name="club_formations")
    op.drop_table("club_formations")
