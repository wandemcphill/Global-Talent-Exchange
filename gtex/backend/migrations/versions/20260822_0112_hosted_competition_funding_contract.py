"""Add explicit funding modes and Coin prize accounting to legacy hosted competitions.

Revision ID: 20260822_0112_hosted_competition_funding_contract
Revises: 20260822_0111_hosted_competition_template_fee_default
Create Date: 2026-08-22 14:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260822_0112_hosted_competition_funding_contract"
down_revision = "20260822_0111_hosted_competition_template_fee_default"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "competition_templates",
        sa.Column(
            "funding_mode",
            sa.String(length=40),
            nullable=False,
            server_default="fancoin_entry_pool",
        ),
    )
    op.add_column(
        "competition_templates",
        sa.Column("reward_pool_coin", sa.Numeric(18, 4), nullable=False, server_default="0"),
    )

    op.add_column(
        "user_hosted_competitions",
        sa.Column(
            "funding_mode",
            sa.String(length=40),
            nullable=False,
            server_default="fancoin_entry_pool",
        ),
    )
    op.add_column(
        "user_hosted_competitions",
        sa.Column("reward_pool_coin", sa.Numeric(18, 4), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_hosted_competitions",
        sa.Column("host_funding_required_coin", sa.Numeric(18, 4), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_hosted_competitions",
        sa.Column("host_funding_escrowed_coin", sa.Numeric(18, 4), nullable=False, server_default="0"),
    )

    op.add_column(
        "hosted_competition_settlements",
        sa.Column("currency", sa.String(length=12), nullable=False, server_default="credit"),
    )


def downgrade() -> None:
    op.drop_column("hosted_competition_settlements", "currency")
    op.drop_column("user_hosted_competitions", "host_funding_escrowed_coin")
    op.drop_column("user_hosted_competitions", "host_funding_required_coin")
    op.drop_column("user_hosted_competitions", "reward_pool_coin")
    op.drop_column("user_hosted_competitions", "funding_mode")
    op.drop_column("competition_templates", "reward_pool_coin")
    op.drop_column("competition_templates", "funding_mode")
