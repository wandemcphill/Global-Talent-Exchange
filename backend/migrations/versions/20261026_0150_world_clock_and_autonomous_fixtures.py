"""World clock persistence, season virtual-age backfill, and autonomous fixtures schema.

Revision ID: 20261026_0150_world_clock_and_autonomous_fixtures
Revises: 20261020_0149_event_storytelling_and_club_management

Adds:
- world_clock_state: durable singleton for persistent virtual-world time
- backfill of virtual_age_month_index on existing regen_universe_seasons
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "20261026_0150_world_clock_and_autonomous_fixtures"
down_revision = "20261020_0149_event_storytelling_and_club_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. world_clock_state table
    if "world_clock_state" not in tables:
        op.create_table(
            "world_clock_state",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("epoch_real_utc", sa.DateTime(timezone=True), nullable=False),
            sa.Column("virtual_start_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("progression_rate", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("is_paused", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("paused_at_virtual_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("virtual_months_per_season", sa.Integer(), nullable=False, server_default="12"),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    # 2. Backfill virtual_age_month_index on existing regen_universe_seasons rows if table exists
    if "regen_universe_seasons" in tables:
        connection = op.get_bind()
        result = connection.execute(
            sa.text("SELECT id, season_number, metadata_json FROM regen_universe_seasons")
        ).fetchall()
        for row in result:
            row_id = row[0]
            season_num = row[1] or 1
            raw_meta = row[2]
            meta = {}
            if isinstance(raw_meta, str):
                try:
                    meta = json.loads(raw_meta)
                except Exception:
                    meta = {}
            elif isinstance(raw_meta, dict):
                meta = dict(raw_meta)

            if "virtual_age_month_index" not in meta:
                meta["virtual_age_month_index"] = max(0, (season_num - 1) * 12)
                connection.execute(
                    sa.text(
                        "UPDATE regen_universe_seasons SET metadata_json = :meta WHERE id = :id"
                    ),
                    {"meta": json.dumps(meta), "id": row_id},
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "world_clock_state" in tables:
        op.drop_table("world_clock_state")
