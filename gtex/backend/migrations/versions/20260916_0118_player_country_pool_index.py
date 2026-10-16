"""Index canonical player nationality for national-team pool filtering.

Revision ID: 20260916_0118_player_country_pool_index
Revises: 20260902_0117_player_match_performance
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260916_0118_player_country_pool_index"
down_revision = "20260902_0117_player_match_performance"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_ingestion_players_country_id"
TABLE_NAME = "ingestion_players"


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE_NAME):
        return
    existing = {index["name"] for index in sa.inspect(bind).get_indexes(TABLE_NAME)}
    if INDEX_NAME not in existing:
        op.create_index(INDEX_NAME, TABLE_NAME, ["country_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table(TABLE_NAME):
        existing = {index["name"] for index in sa.inspect(bind).get_indexes(TABLE_NAME)}
        if INDEX_NAME in existing:
            op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
