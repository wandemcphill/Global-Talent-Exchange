"""Create f_unaccent function, GIN trigram search indexes, and unique real player profile constraint.

Revision ID: 20261103_0219_search_performance_and_unaccent_indexes
Revises: 20261103_0218_create_owner_showroom_assets
Create Date: 2026-11-03 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261103_0219_search_performance_and_unaccent_indexes"
down_revision = "20261103_0218_create_owner_showroom_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    # 1. Deduplicate real_player_profiles keeping latest
    op.execute(sa.text("""
        DELETE FROM real_player_profiles
        WHERE id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (
                    PARTITION BY gtex_player_id 
                    ORDER BY source_last_refreshed_at DESC NULLS LAST, updated_at DESC, id DESC
                ) as rn
                FROM real_player_profiles
            ) sub
            WHERE rn > 1
        );
    """))

    # 2. Create unique index on gtex_player_id
    op.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_real_player_profiles_gtex_player_id 
        ON real_player_profiles (gtex_player_id);
    """))

    # 3. Create immutable f_unaccent function for indexing
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION f_unaccent(text)
          RETURNS text AS
        $func$
        SELECT public.unaccent('public.unaccent', $1)
        $func$ LANGUAGE sql IMMUTABLE PARALLEL SAFE;
    """))

    # 4. GIN trigram indexes on f_unaccent(full_name) and f_unaccent(canonical_display_name)
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_ingestion_players_f_unaccent_full_name_trgm 
        ON ingestion_players USING gin (f_unaccent(full_name) gin_trgm_ops);
    """))
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_ingestion_players_f_unaccent_display_name_trgm 
        ON ingestion_players USING gin (f_unaccent(canonical_display_name) gin_trgm_ops);
    """))

    # 5. Composite index for fast discovery ordering and count
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_ingestion_players_val_name_id 
        ON ingestion_players (current_market_reference_value DESC NULLS LAST, full_name ASC, id ASC) 
        WHERE is_real_player IS TRUE AND is_tradable IS TRUE;
    """))
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_ingestion_players_mkt_val_active 
        ON ingestion_players (current_market_reference_value DESC NULLS LAST, id ASC) 
        WHERE is_real_player IS TRUE AND is_tradable IS TRUE;
    """))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute(sa.text("DROP INDEX IF EXISTS ix_ingestion_players_mkt_val_active;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_ingestion_players_val_name_id;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_ingestion_players_f_unaccent_display_name_trgm;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_ingestion_players_f_unaccent_full_name_trgm;"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS f_unaccent(text);"))
    op.execute(sa.text("DROP INDEX IF EXISTS uq_real_player_profiles_gtex_player_id;"))
