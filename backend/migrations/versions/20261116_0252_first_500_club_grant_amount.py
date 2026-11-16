"""Set the default first-club campaign grant to 2,500 GTX.

Revision ID: 20261116_0252_first_500_club_grant_amount
Revises: 20261115_0251_abdelkarim_ozhianvuna_odegbami_camara_calibration
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261116_0252_first_500_club_grant_amount"
down_revision = "20261115_0251_abdelkarim_ozhianvuna_odegbami_camara_calibration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing entitlement amounts are intentionally preserved. Only the
    # server default for newly-created entitlement rows changes.
    op.alter_column(
        "first_club_entitlements",
        "gtex_grant_amount",
        existing_type=sa.Numeric(18, 4),
        existing_nullable=False,
        server_default="2500.0000",
    )


def downgrade() -> None:
    op.alter_column(
        "first_club_entitlements",
        "gtex_grant_amount",
        existing_type=sa.Numeric(18, 4),
        existing_nullable=False,
        server_default="100000.0000",
    )
