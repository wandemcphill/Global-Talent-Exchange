"""Add unique constraint to reward_settlements for idempotency.

Revision ID: 20261019_0148_reward_settlement_idempotency_guard
Revises: 20261018_0147_club_legacy_full_p789

Adds unique constraint uq_reward_settlements_comp_user_source to reward_settlements
table to prevent double-crediting under concurrent requests.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261019_0148_reward_settlement_idempotency_guard"
down_revision = "20261018_0147_club_legacy_full_p789"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraint_name = "uq_reward_settlements_comp_user_source"
    constraints = {
        c["name"] for c in inspector.get_unique_constraints("reward_settlements")
    }
    if constraint_name not in constraints:
        # Never silently delete or rewrite existing financial settlement history.
        duplicates = bind.execute(
            sa.text(
                """
                SELECT competition_key, user_id, reward_source, COUNT(*) AS duplicate_count
                FROM reward_settlements
                GROUP BY competition_key, user_id, reward_source
                HAVING COUNT(*) > 1
                ORDER BY duplicate_count DESC
                LIMIT 10
                """
            )
        ).mappings().all()
        if duplicates:
            examples = "; ".join(
                f"competition_key={row['competition_key']!r}, user_id={row['user_id']!r}, "
                f"reward_source={row['reward_source']!r}, rows={row['duplicate_count']}"
                for row in duplicates
            )
            raise RuntimeError(
                "Cannot add reward-settlement idempotency constraint: duplicate financial "
                "settlement rows already exist. Reconcile them through the audited financial "
                f"process before retrying this migration. Examples: {examples}"
            )
        op.create_unique_constraint(
            constraint_name,
            "reward_settlements",
            ["competition_key", "user_id", "reward_source"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {c["name"] for c in inspector.get_unique_constraints("reward_settlements")}
    if "uq_reward_settlements_comp_user_source" in constraints:
        op.drop_constraint(
            "uq_reward_settlements_comp_user_source",
            "reward_settlements",
            type_="unique",
        )
