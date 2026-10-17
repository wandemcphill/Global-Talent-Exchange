"""Trigram indexes so player-name ILIKE search stays fast with the national regen cohort.

Revision ID: 20261017_0132_player_name_trgm_indexes
Revises: 20261016_0131_normalize_wallet_enum_values
"""

from __future__ import annotations

from alembic import op

revision = "20261017_0132_player_name_trgm_indexes"
down_revision = "20261016_0131_normalize_wallet_enum_values"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ingestion_players_full_name_trgm ON ingestion_players USING gin (full_name gin_trgm_ops)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ingestion_players_display_name_trgm "
        "ON ingestion_players USING gin (canonical_display_name gin_trgm_ops)"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS ix_ingestion_players_display_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_ingestion_players_full_name_trgm")
