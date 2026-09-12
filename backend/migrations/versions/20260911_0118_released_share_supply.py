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
    with op.batch_alter_table("player_share_markets") as batch_op:
        batch_op.add_column(sa.Column("released_shares", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_player_share_markets_released_shares_nonnegative",
            "released_shares IS NULL OR released_shares >= 0",
        )
        batch_op.create_check_constraint(
            "ck_player_share_markets_released_not_below_circulating",
            "released_shares IS NULL OR released_shares >= circulating_shares",
        )
        batch_op.create_check_constraint(
            "ck_player_share_markets_released_not_above_total",
            "released_shares IS NULL OR released_shares <= total_shares",
        )


def downgrade() -> None:
    with op.batch_alter_table("player_share_markets") as batch_op:
        batch_op.drop_constraint("ck_player_share_markets_released_not_above_total", type_="check")
        batch_op.drop_constraint("ck_player_share_markets_released_not_below_circulating", type_="check")
        batch_op.drop_constraint("ck_player_share_markets_released_shares_nonnegative", type_="check")
        batch_op.drop_column("released_shares")
