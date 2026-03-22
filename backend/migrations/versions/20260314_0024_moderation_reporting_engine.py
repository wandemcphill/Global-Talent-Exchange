"""Add moderation reporting engine."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260314_0024"
down_revision = "20260314_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "moderation_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("reporter_user_id", sa.String(length=36), nullable=False),
        sa.Column("subject_user_id", sa.String(length=36), nullable=True),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=48), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'open'")),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default=sa.text("'normal'")),
        sa.Column("assigned_admin_user_id", sa.String(length=36), nullable=True),
        sa.Column("resolution_action", sa.String(length=32), nullable=False, server_default=sa.text("'none'")),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("report_count_for_target", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], name="fk_moderation_reports_reporter_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_user_id"], ["users.id"], name="fk_moderation_reports_subject_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_admin_user_id"], ["users.id"], name="fk_moderation_reports_assigned_admin_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], name="fk_moderation_reports_resolved_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_moderation_reports"),
    )
    op.create_index("ix_moderation_reports_reporter_user_id", "moderation_reports", ["reporter_user_id"], unique=False)
    op.create_index("ix_moderation_reports_subject_user_id", "moderation_reports", ["subject_user_id"], unique=False)
    op.create_index("ix_moderation_reports_target_type", "moderation_reports", ["target_type"], unique=False)
    op.create_index("ix_moderation_reports_target_id", "moderation_reports", ["target_id"], unique=False)
    op.create_index("ix_moderation_reports_reason_code", "moderation_reports", ["reason_code"], unique=False)
    op.create_index("ix_moderation_reports_assigned_admin_user_id", "moderation_reports", ["assigned_admin_user_id"], unique=False)
    op.create_index("ix_moderation_reports_resolved_by_user_id", "moderation_reports", ["resolved_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_moderation_reports_resolved_by_user_id", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_assigned_admin_user_id", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_reason_code", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_target_id", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_target_type", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_subject_user_id", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_reporter_user_id", table_name="moderation_reports")
    op.drop_table("moderation_reports")
