"""Add admin-managed referral partners for first-deposit affiliate campaigns.

Revision ID: 20261117_0261_admin_referral_partners
Revises: 20261116_0260_first_500_club_grant_amount
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20261117_0261_admin_referral_partners"
down_revision = "20261116_0260_first_500_club_grant_amount"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referral_partners",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("contact_email", sa.String(length=320), nullable=True),
        sa.Column("social_handle", sa.String(length=120), nullable=True),
        sa.Column("campaign_name", sa.String(length=120), nullable=True),
        sa.Column("payout_method", sa.String(length=32), server_default="manual", nullable=False),
        sa.Column("payout_destination_reference", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referral_partners_contact_email", "referral_partners", ["contact_email"])
    op.create_index("ix_referral_partners_created_by_user_id", "referral_partners", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_referral_partners_created_by_user_id", table_name="referral_partners")
    op.drop_index("ix_referral_partners_contact_email", table_name="referral_partners")
    op.drop_table("referral_partners")
