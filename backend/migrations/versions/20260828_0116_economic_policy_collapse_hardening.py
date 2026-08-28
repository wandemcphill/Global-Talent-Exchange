"""Re-collapse active economic policies, preferring the normalized canonical row.

Revision ID: 20260828_0116_economic_policy_collapse_hardening
Revises: 20260828_0115_payout_request_idempotency

Migration 0114 collapsed duplicate active AdminRewardRule rows by keeping
whichever had the newest updated_at. Migration 0113 only normalized stale
10%/20% competition fees on rule_key='platform-economy-defaults'. On a database
where an operator had added a different active rule more recently, 0114 kept
that un-normalized row and deactivated the normalized one -- so a stale 10%/20%
competition default could survive the very migrations meant to remove it.

This repairs that end state:
  1. normalize the legacy 10%/20% competition defaults on EVERY active row, not
     just the canonical one, so whichever row survives cannot carry a stale fee;
  2. collapse to a single active row, preferring 'platform-economy-defaults'
     when it is active, and falling back to newest-updated otherwise.

Idempotent: on an already-correct database both statements are no-ops.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260828_0116_economic_policy_collapse_hardening"
down_revision = "20260828_0115_payout_request_idempotency"
branch_labels = None
depends_on = None

CANONICAL_RULE_KEY = "platform-economy-defaults"


def upgrade() -> None:
    connection = op.get_bind()

    connection.execute(sa.text("""
            UPDATE admin_reward_rules
            SET competition_platform_fee_bps = 3000
            WHERE active
              AND competition_platform_fee_bps IN (1000, 2000)
            """))

    survivor = connection.execute(
        sa.text("""
            SELECT id
            FROM admin_reward_rules
            WHERE active
            ORDER BY
                CASE WHEN rule_key = :canonical THEN 0 ELSE 1 END,
                updated_at DESC,
                id ASC
            LIMIT 1
            """),
        {"canonical": CANONICAL_RULE_KEY},
    ).first()

    if survivor is not None:
        connection.execute(
            sa.text("""
                UPDATE admin_reward_rules
                SET active = FALSE
                WHERE active AND id <> :survivor_id
                """),
            {"survivor_id": survivor[0]},
        )


def downgrade() -> None:
    # Reactivating rows this collapsed would recreate the multiple-active state
    # that resolve_economic_policy() deliberately fails closed on, and the 30%
    # value is the current constitutional default. No safe downgrade exists.
    pass
