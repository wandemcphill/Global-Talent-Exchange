"""Daily player share price snapshots for the scouting-drawer price history chart.

Revision ID: 20261017_0133_player_share_price_snapshots
Revises: 20261017_0132_player_name_trgm_indexes
"""

from __future__ import annotations

from alembic import op

revision = "20261017_0133_player_share_price_snapshots"
down_revision = "20261017_0132_player_name_trgm_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.models.player_token_market import PlayerSharePriceSnapshot

    PlayerSharePriceSnapshot.__table__.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    from app.models.player_token_market import PlayerSharePriceSnapshot

    PlayerSharePriceSnapshot.__table__.drop(op.get_bind(), checkfirst=True)
