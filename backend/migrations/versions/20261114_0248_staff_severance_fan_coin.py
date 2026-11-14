"""Track managerial severance paid in Fan Coin.

Revision ID: 20261114_0248_staff_severance_fan_coin
Revises: 20261114_0247_living_supporter_media_club_history
Create Date: 2026-11-14 19:25:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261114_0248_staff_severance_fan_coin"
down_revision = "20261114_0247_living_supporter_media_club_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "owner_club_managerial_tenures" not in set(inspector.get_table_names()):
        return

    columns = {column["name"] for column in inspector.get_columns("owner_club_managerial_tenures")}
    if "severance_paid_fan_coin" not in columns:
        op.add_column(
            "owner_club_managerial_tenures",
            sa.Column(
                "severance_paid_fan_coin",
                sa.Numeric(18, 2),
                nullable=False,
                server_default="0.00",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "owner_club_managerial_tenures" not in set(inspector.get_table_names()):
        return

    columns = {column["name"] for column in inspector.get_columns("owner_club_managerial_tenures")}
    if "severance_paid_fan_coin" in columns:
        op.drop_column("owner_club_managerial_tenures", "severance_paid_fan_coin")
