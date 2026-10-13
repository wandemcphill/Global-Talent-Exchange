"""Open untouched product launch flags to the public seed.

Revision ID: 20261013_0129_open_default_launch_flags
Revises: 20261013_0128_story_feed_moderation

Rows an admin has edited, and rows with a kill switch, are left alone.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261013_0129_open_default_launch_flags"
down_revision = "20261013_0128_story_feed_moderation"
branch_labels = None
depends_on = None

_PUBLIC_FEATURE_KEYS = (
    "national-team-engine",
    "club_lifecycle",
    "academy_pipeline",
    "transfer_hub",
    "coin_traders",
    "fan_coin",
    "gtex_coin",
    "gifting",
    "newgen_portraits",
    "club_shares",
    "create_a_son",
    "ticketing",
    "broadcast",
    "player_card_marketplace",
    "club_sale_market",
    "staff_marketplace",
    "sponsorships",
    "federations",
    "fan_wars",
    "predictions",
    "story-feed",
    "daily-challenges",
)


def upgrade() -> None:
    flags = sa.table(
        "admin_feature_flags",
        sa.column("feature_key", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("audience", sa.String),
        sa.column("launch_state", sa.String),
        sa.column("allowed_roles_json", sa.JSON),
        sa.column("beta_only", sa.Boolean),
        sa.column("kill_switch_enabled", sa.Boolean),
        sa.column("updated_by_user_id", sa.String),
    )
    op.execute(
        flags.update()
        .where(flags.c.feature_key.in_(_PUBLIC_FEATURE_KEYS))
        .where(flags.c.updated_by_user_id.is_(None))
        .where(flags.c.kill_switch_enabled.is_(False))
        .values(
            enabled=True,
            audience="global",
            launch_state="public",
            allowed_roles_json=[],
            beta_only=False,
        )
    )


def downgrade() -> None:
    flags = sa.table(
        "admin_feature_flags",
        sa.column("feature_key", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("launch_state", sa.String),
        sa.column("kill_switch_enabled", sa.Boolean),
        sa.column("updated_by_user_id", sa.String),
    )
    closed = tuple(key for key in _PUBLIC_FEATURE_KEYS if key not in {"story-feed", "daily-challenges"})
    op.execute(
        flags.update()
        .where(flags.c.feature_key.in_(closed))
        .where(flags.c.updated_by_user_id.is_(None))
        .where(flags.c.kill_switch_enabled.is_(False))
        .values(enabled=False, launch_state="internal")
    )
