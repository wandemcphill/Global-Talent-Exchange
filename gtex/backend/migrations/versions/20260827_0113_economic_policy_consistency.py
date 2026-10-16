"""Normalize Phase A competition fee defaults to the 30% economic constitution.

Revision ID: 20260827_0113_economic_policy_consistency
Revises: 20260823_0107_talent_exchange_foundation
Create Date: 2026-08-27 00:00:00.000000

The AdminRewardRule model and constitutional policy already define 30% as the
competition default. Older seeded rows and legacy template snapshots could
still carry 10% or 20%. Normalize those known legacy defaults without changing
an explicitly customized Admin policy.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260827_0113_economic_policy_consistency"
down_revision = "20260823_0107_talent_exchange_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    admin_exists = connection.execute(
        sa.text("SELECT 1 FROM admin_reward_rules WHERE rule_key = :rule_key LIMIT 1"),
        {"rule_key": "platform-economy-defaults"},
    ).first()
    if admin_exists is None:
        connection.execute(
            sa.text(
                """
                INSERT INTO admin_reward_rules (
                    id,
                    rule_key,
                    title,
                    description,
                    trading_fee_bps,
                    gift_platform_rake_bps,
                    withdrawal_fee_bps,
                    minimum_withdrawal_fee_credits,
                    competition_platform_fee_bps,
                    stability_controls_json,
                    active
                ) VALUES (
                    :id,
                    :rule_key,
                    :title,
                    :description,
                    :trading_fee_bps,
                    :gift_platform_rake_bps,
                    :withdrawal_fee_bps,
                    :minimum_withdrawal_fee_credits,
                    :competition_platform_fee_bps,
                    :stability_controls_json,
                    :active
                )
                """
            ),
            {
                "id": "system-platform-economy-defaults",
                "rule_key": "platform-economy-defaults",
                "title": "Platform Economy Defaults",
                "description": "Canonical Admin fee and rake policy for GTEX economic flows.",
                "trading_fee_bps": 2000,
                "gift_platform_rake_bps": 3000,
                "withdrawal_fee_bps": 1000,
                "minimum_withdrawal_fee_credits": 5,
                "competition_platform_fee_bps": 3000,
                "stability_controls_json": "{}",
                "active": True,
            },
        )
    else:
        connection.execute(
            sa.text(
                """
                UPDATE admin_reward_rules
                SET competition_platform_fee_bps = 3000
                WHERE rule_key = :rule_key
                  AND active
                  AND competition_platform_fee_bps IN (1000, 2000)
                """
            ),
            {"rule_key": "platform-economy-defaults"},
        )

    # Legacy template values are snapshots only. Normalize known product
    # defaults so newly-created templates and admin displays cannot advertise
    # stale 10%/20% economics.
    connection.execute(
        sa.text(
            """
            UPDATE competition_templates
            SET platform_fee_bps = 3000
            WHERE platform_fee_bps IN (1000, 2000)
            """
        )
    )


def downgrade() -> None:
    # The 30% value is the current constitutional default. There is no safe
    # downgrade that can distinguish stale legacy defaults from an intentional
    # historical change, so the downgrade is intentionally a no-op.
    pass
