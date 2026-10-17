"""Club Legacy desk: gift settlement columns, sponsor delivery, and auction bids.

Revision ID: 20261017_0138_club_legacy_desk
Revises: 20261017_0137_club_legacy_phases
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261017_0138_club_legacy_desk"
down_revision = "20261017_0137_club_legacy_phases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    settlement_cols = {column["name"] for column in inspector.get_columns("club_legacy_preseason_settlements")}
    if "gift_platform_amount" not in settlement_cols:
        op.add_column(
            "club_legacy_preseason_settlements",
            sa.Column("gift_platform_amount", sa.Numeric(20, 2), nullable=False, server_default="0"),
        )
        op.add_column(
            "club_legacy_preseason_settlements",
            sa.Column("gift_club_amount", sa.Numeric(20, 2), nullable=False, server_default="0"),
        )
    contract_cols = {column["name"] for column in inspector.get_columns("club_legacy_sponsor_contracts")}
    if "delivery_report" not in contract_cols:
        op.add_column("club_legacy_sponsor_contracts", sa.Column("delivery_report", sa.Text(), nullable=True))
        op.add_column("club_legacy_sponsor_contracts", sa.Column("impressions", sa.Integer(), nullable=True))
        op.add_column(
            "club_legacy_sponsor_contracts", sa.Column("renewed_from_id", sa.String(length=36), nullable=True)
        )
    from app.club_legacy.models import ClubLegacyBid

    ClubLegacyBid.__table__.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    from app.club_legacy.models import ClubLegacyBid

    ClubLegacyBid.__table__.drop(bind, checkfirst=True)
    op.drop_column("club_legacy_sponsor_contracts", "renewed_from_id")
    op.drop_column("club_legacy_sponsor_contracts", "impressions")
    op.drop_column("club_legacy_sponsor_contracts", "delivery_report")
    op.drop_column("club_legacy_preseason_settlements", "gift_club_amount")
    op.drop_column("club_legacy_preseason_settlements", "gift_platform_amount")
