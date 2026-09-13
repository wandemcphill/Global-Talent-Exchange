"""Persist explicit recipient-club context without changing profile identity.

Revision ID: 20260913_0121_gift_profile_club_identity
Revises: 20260912_0120_personal_manager

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260913_0121_gift_profile_club_identity"
down_revision = "20260912_0120_personal_manager"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gift_transactions",
        sa.Column("recipient_club_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_gift_transactions_recipient_club_id"),
        "gift_transactions",
        ["recipient_club_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_gift_transactions_recipient_club_id",
        "gift_transactions",
        "club_profiles",
        ["recipient_club_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_gift_transactions_recipient_club_id",
        "gift_transactions",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_gift_transactions_recipient_club_id"), table_name="gift_transactions")
    op.drop_column("gift_transactions", "recipient_club_id")
