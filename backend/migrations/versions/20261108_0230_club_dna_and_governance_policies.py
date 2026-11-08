"""Add Club DNA policies and governance exceptions tables.

Revision ID: 20261108_0230_club_dna_and_governance_policies
Revises: 20261108_0229_merge_owner_world_and_commercial_heads
Create Date: 2026-11-08 20:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261108_0230_club_dna_and_governance_policies"
down_revision = "20261108_0229_merge_owner_world_and_commercial_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "club_dna_policies" not in table_names:
        op.create_table(
            "club_dna_policies",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("primary_philosophy", sa.String(length=64), server_default="balanced", nullable=False),
            sa.Column("secondary_philosophies", sa.JSON(), nullable=False),
            sa.Column("nationality_mode", sa.String(length=32), server_default="none", nullable=False),
            sa.Column("target_nationalities", sa.JSON(), nullable=False),
            sa.Column("allow_dual_nationality", sa.Boolean(), server_default="1", nullable=False),
            sa.Column("age_mode", sa.String(length=32), server_default="none", nullable=False),
            sa.Column("preferred_max_age", sa.Integer(), nullable=True),
            sa.Column("allow_age_exceptions", sa.Boolean(), server_default="1", nullable=False),
            sa.Column("transfer_strategy", sa.String(length=64), server_default="balanced", nullable=False),
            sa.Column("financial_philosophy", sa.String(length=64), server_default="balanced", nullable=False),
            sa.Column("club_vision_narrative", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
            ),
            sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("club_id", name="uq_club_dna_policies_club_id"),
        )
        op.create_index("ix_club_dna_policies_club_id", "club_dna_policies", ["club_id"])
        op.create_index("ix_club_dna_policies_primary_philosophy", "club_dna_policies", ["primary_philosophy"])
        op.create_index("ix_club_dna_policies_nationality_mode", "club_dna_policies", ["nationality_mode"])
        op.create_index("ix_club_dna_policies_age_mode", "club_dna_policies", ["age_mode"])

    if "club_governance_exceptions" not in table_names:
        op.create_table(
            "club_governance_exceptions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("policy_type", sa.String(length=32), nullable=False),
            sa.Column("player_id", sa.String(length=36), nullable=False),
            sa.Column("player_name", sa.String(length=160), nullable=False),
            sa.Column("player_nationality", sa.String(length=96), nullable=True),
            sa.Column("player_age", sa.Integer(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("approved_by_user_id", sa.String(length=36), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="approved", nullable=False),
            sa.Column(
                "approved_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
            ),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
            ),
            sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_club_governance_exceptions_club_id", "club_governance_exceptions", ["club_id"])
        op.create_index("ix_club_governance_exceptions_policy_type", "club_governance_exceptions", ["policy_type"])
        op.create_index("ix_club_governance_exceptions_player_id", "club_governance_exceptions", ["player_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "club_governance_exceptions" in table_names:
        op.drop_table("club_governance_exceptions")
    if "club_dna_policies" in table_names:
        op.drop_table("club_dna_policies")
