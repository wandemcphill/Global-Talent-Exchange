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
    constraints = {c["name"] for c in inspector.get_unique_constraints("reward_settlements")}
    if "uq_reward_settlements_comp_user_source" not in constraints:
        op.create_unique_constraint(
            "uq_reward_settlements_comp_user_source",
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
