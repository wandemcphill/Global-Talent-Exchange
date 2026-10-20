"""Event storytelling, AI newsroom, luxury showroom, and club management schema.

Revision ID: 20261020_0149_event_storytelling_and_club_management
Revises: 20261019_0148_reward_settlement_idempotency_guard

Adds:
- owner_broadcast_events: durable verified global announcements (jets, facility upgrades, player gifts)
- owner_newsroom_articles: AI grounded football newsroom dispatches
- owner_scouting_watchlists: confidential owner scouting dossiers
- owner_inbox_items column extensions: save_context_id, category, is_read, read_at, archived_at, deadline_at
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261020_0149_event_storytelling_and_club_management"
down_revision = "20261019_0148_reward_settlement_idempotency_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. owner_inbox_items columns
    if "owner_inbox_items" in tables:
        inbox_cols = {col["name"] for col in inspector.get_columns("owner_inbox_items")}
        if "save_context_id" not in inbox_cols:
            op.add_column("owner_inbox_items", sa.Column("save_context_id", sa.String(64), nullable=True, index=True))
        if "category" not in inbox_cols:
            op.add_column("owner_inbox_items", sa.Column("category", sa.String(40), nullable=False, server_default="requests", index=True))
        if "is_read" not in inbox_cols:
            op.add_column("owner_inbox_items", sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        if "read_at" not in inbox_cols:
            op.add_column("owner_inbox_items", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
        if "archived_at" not in inbox_cols:
            op.add_column("owner_inbox_items", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True, index=True))
        if "deadline_at" not in inbox_cols:
            op.add_column("owner_inbox_items", sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True, index=True))

    # 2. owner_broadcast_events table
    if "owner_broadcast_events" not in tables:
        op.create_table(
            "owner_broadcast_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("save_context_id", sa.String(64), nullable=False, index=True),
            sa.Column("club_id", sa.String(36), nullable=False, index=True),
            sa.Column("club_name", sa.String(120), nullable=False),
            sa.Column("club_crest_url", sa.String(255), nullable=True),
            sa.Column("owner_user_id", sa.String(36), nullable=False, index=True),
            sa.Column("owner_display_name", sa.String(120), nullable=False),
            sa.Column("event_type", sa.String(48), nullable=False, index=True),
            sa.Column("item_name", sa.String(160), nullable=False),
            sa.Column("item_model", sa.String(120), nullable=True),
            sa.Column("item_image_url", sa.String(255), nullable=True),
            sa.Column("player_id", sa.String(36), nullable=True),
            sa.Column("player_name", sa.String(120), nullable=True),
            sa.Column("player_portrait_url", sa.String(255), nullable=True),
            sa.Column("verified_price_gtex", sa.Numeric(20, 4), nullable=True),
            sa.Column("currency", sa.String(16), nullable=False, server_default="GTEX"),
            sa.Column("status", sa.String(20), nullable=False, server_default="active", index=True),
            sa.Column("headline", sa.String(200), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("ledger_event_id", sa.String(36), nullable=True, index=True),
            sa.Column("idempotency_key", sa.String(128), nullable=True, unique=True, index=True),
            sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    # 3. owner_newsroom_articles table
    if "owner_newsroom_articles" not in tables:
        op.create_table(
            "owner_newsroom_articles",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("save_context_id", sa.String(64), nullable=False, index=True),
            sa.Column("club_id", sa.String(36), nullable=True, index=True),
            sa.Column("visibility", sa.String(16), nullable=False, server_default="global", index=True),
            sa.Column("category", sa.String(40), nullable=False, server_default="editorial", index=True),
            sa.Column("headline", sa.String(220), nullable=False),
            sa.Column("subheadline", sa.String(255), nullable=False, server_default=""),
            sa.Column("hero_image_url", sa.String(255), nullable=True),
            sa.Column("club_crest_url", sa.String(255), nullable=True),
            sa.Column("player_portrait_url", sa.String(255), nullable=True),
            sa.Column("established_facts_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("editorial_narration", sa.Text(), nullable=False),
            sa.Column("grounding_report_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("verified_price_gtex", sa.Numeric(20, 4), nullable=True),
            sa.Column("source_event_id", sa.String(36), nullable=True, index=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="published", index=True),
            sa.Column("idempotency_key", sa.String(128), nullable=True, unique=True, index=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    # 4. owner_scouting_watchlists table
    if "owner_scouting_watchlists" not in tables:
        op.create_table(
            "owner_scouting_watchlists",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("club_id", sa.String(36), nullable=False, index=True),
            sa.Column("save_context_id", sa.String(64), nullable=False, index=True),
            sa.Column("player_id", sa.String(36), nullable=True, index=True),
            sa.Column("player_name", sa.String(120), nullable=False),
            sa.Column("position", sa.String(16), nullable=False, server_default="MID"),
            sa.Column("age", sa.Integer(), nullable=False, server_default="18"),
            sa.Column("current_rating", sa.Integer(), nullable=False, server_default="65"),
            sa.Column("potential_rating", sa.Integer(), nullable=False, server_default="80"),
            sa.Column("estimated_value_gtex", sa.Numeric(20, 4), nullable=False, server_default="100"),
            sa.Column("priority", sa.String(16), nullable=False, server_default="medium"),
            sa.Column("scout_notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("recommendation", sa.String(120), nullable=False, server_default="Monitor"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "owner_scouting_watchlists" in tables:
        op.drop_table("owner_scouting_watchlists")
    if "owner_newsroom_articles" in tables:
        op.drop_table("owner_newsroom_articles")
    if "owner_broadcast_events" in tables:
        op.drop_table("owner_broadcast_events")

    if "owner_inbox_items" in tables:
        inbox_cols = {col["name"] for col in inspector.get_columns("owner_inbox_items")}
        for col in ("deadline_at", "archived_at", "read_at", "is_read", "category", "save_context_id"):
            if col in inbox_cols:
                op.drop_column("owner_inbox_items", col)
