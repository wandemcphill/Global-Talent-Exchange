"""Keep public matches on 2D and clear unedited user-hosted play prices.

Revision ID: 20261112_0237_two_d_launch_and_play_prices
Revises: 20261111_0236_world_clock_official_start

Official GTEX competitions stay free. This only inserts the 3D gameplay
switch, off, and sets user-hosted play prices that an admin has not edited
back to 0.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "20261112_0237_two_d_launch_and_play_prices"
down_revision = "20261111_0236_world_clock_official_start"
branch_labels = None
depends_on = None

_PLAY_PRICE_KEYS = ("tournament-entry", "fast-match-entry", "competitive-match-entry")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    now = datetime.now(timezone.utc)

    if "admin_feature_flags" in tables:
        flags = sa.table(
            "admin_feature_flags",
            sa.column("id", sa.String),
            sa.column("feature_key", sa.String),
            sa.column("title", sa.String),
            sa.column("description", sa.Text),
            sa.column("enabled", sa.Boolean),
            sa.column("audience", sa.String),
            sa.column("launch_state", sa.String),
            sa.column("allowed_roles_json", sa.JSON),
            sa.column("allowed_regions_json", sa.JSON),
            sa.column("beta_only", sa.Boolean),
            sa.column("kill_switch_enabled", sa.Boolean),
            sa.column("metadata_json", sa.JSON),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        )
        existing = bind.execute(
            sa.select(flags.c.feature_key).where(flags.c.feature_key == "match_3d_gameplay")
        ).first()
        if existing is None:
            op.execute(
                flags.insert().values(
                    id=str(uuid4()),
                    feature_key="match_3d_gameplay",
                    title="3D gameplay",
                    description="Public matches stay on the 2D pitch until an admin turns 3D gameplay on.",
                    enabled=False,
                    audience="global",
                    launch_state="public",
                    allowed_roles_json=[],
                    allowed_regions_json=[],
                    beta_only=False,
                    kill_switch_enabled=False,
                    metadata_json={"route": "/app/match"},
                    created_at=now,
                    updated_at=now,
                )
            )

    if "service_pricing_rules" in tables:
        rules = sa.table(
            "service_pricing_rules",
            sa.column("service_key", sa.String),
            sa.column("price_coin", sa.Numeric),
            sa.column("price_fancoin_equivalent", sa.Numeric),
            sa.column("updated_by_user_id", sa.String),
            sa.column("updated_at", sa.DateTime),
        )
        op.execute(
            rules.update()
            .where(rules.c.service_key.in_(_PLAY_PRICE_KEYS))
            .where(rules.c.updated_by_user_id.is_(None))
            .values(price_coin=0, price_fancoin_equivalent=0, updated_at=now)
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "admin_feature_flags" not in set(inspector.get_table_names()):
        return
    flags = sa.table(
        "admin_feature_flags",
        sa.column("feature_key", sa.String),
        sa.column("updated_by_user_id", sa.String),
    )
    op.execute(
        flags.delete().where(flags.c.feature_key == "match_3d_gameplay").where(flags.c.updated_by_user_id.is_(None))
    )
