"""Add explicit released supply for player-share markets.

Revision ID: 20260911_0118_released_share_supply
Revises: 20260902_0117_player_match_performance

Released supply is distinct from lifetime total supply and circulating ownership.
Legacy rows remain NULL until explicitly reconciled rather than being assigned
an invented historical release amount.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260911_0118_released_share_supply"
down_revision = "20260902_0117_player_match_performance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.add_column(
        "player_share_markets",
        sa.Column("released_shares", sa.Integer(), nullable=True),
    )
    if bind.dialect.name != "sqlite":
        op.create_check_constraint(
            "ck_player_share_markets_released_shares_nonnegative",
            "player_share_markets",
            "released_shares IS NULL OR released_shares >= 0",
        )
        op.create_check_constraint(
            "ck_player_share_markets_released_not_below_circulating",
            "player_share_markets",
            "released_shares IS NULL OR released_shares >= circulating_shares",
        )
        op.create_check_constraint(
            "ck_player_share_markets_released_not_above_total",
            "player_share_markets",
            "released_shares IS NULL OR released_shares <= total_shares",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_constraint("ck_player_share_markets_released_not_above_total", "player_share_markets", type_="check")
        op.drop_constraint("ck_player_share_markets_released_not_below_circulating", "player_share_markets", type_="check")
        op.drop_constraint("ck_player_share_markets_released_shares_nonnegative", "player_share_markets", type_="check")
    op.drop_column("player_share_markets", "released_shares")
