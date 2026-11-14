"""Add missing single-column indexes on living institution tables.

Revision ID: 20261114_0248_living_institution_index_coverage
Revises: 20261114_0247_living_supporter_media_club_history
Create Date: 2026-11-14 18:25:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261114_0248_living_institution_index_coverage"
down_revision = "20261114_0247_living_supporter_media_club_history"
branch_labels = None
depends_on = None

INDEX_SPECS: tuple[tuple[str, str, list[str]], ...] = (
    ("owner_supporter_events", "ix_owner_supporter_events_created_at", ["created_at"]),
    ("owner_media_stories", "ix_owner_media_stories_outlet_key", ["outlet_key"]),
    ("owner_media_stories", "ix_owner_media_stories_created_at", ["created_at"]),
    ("owner_club_history_entries", "ix_owner_club_history_entries_season_number", ["season_number"]),
    ("owner_club_history_entries", "ix_owner_club_history_entries_event_type", ["event_type"]),
    ("owner_club_history_entries", "ix_owner_club_history_entries_is_major_milestone", ["is_major_milestone"]),
    ("owner_club_history_entries", "ix_owner_club_history_entries_created_at", ["created_at"]),
    ("owner_club_season_archives", "ix_owner_club_season_archives_season_number", ["season_number"]),
    ("owner_club_season_archives", "ix_owner_club_season_archives_created_at", ["created_at"]),
    ("owner_club_managerial_tenures", "ix_owner_club_managerial_tenures_manager_id", ["manager_id"]),
    ("owner_club_transfer_records", "ix_owner_club_transfer_records_player_id", ["player_id"]),
    ("owner_club_transfer_records", "ix_owner_club_transfer_records_world_day", ["world_day"]),
    ("owner_club_transfer_records", "ix_owner_club_transfer_records_created_at", ["created_at"]),
    ("owner_club_academy_graduates", "ix_owner_club_academy_graduates_status", ["status"]),
    ("owner_club_rivalries", "ix_owner_club_rivalries_rival_club_id", ["rival_club_id"]),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    indexes_by_table: dict[str, set[str]] = {}

    for table_name, index_name, columns in INDEX_SPECS:
        if table_name not in existing_tables:
            continue
        if table_name not in indexes_by_table:
            indexes_by_table[table_name] = {
                str(idx.get("name")) for idx in inspector.get_indexes(table_name) if idx.get("name")
            }
        if index_name not in indexes_by_table[table_name]:
            op.create_index(index_name, table_name, columns)
            indexes_by_table[table_name].add(index_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    indexes_by_table: dict[str, set[str]] = {}

    for table_name, index_name, _columns in reversed(INDEX_SPECS):
        if table_name not in existing_tables:
            continue
        if table_name not in indexes_by_table:
            indexes_by_table[table_name] = {
                str(idx.get("name")) for idx in inspector.get_indexes(table_name) if idx.get("name")
            }
        if index_name in indexes_by_table[table_name]:
            op.drop_index(index_name, table_name=table_name)
            indexes_by_table[table_name].discard(index_name)
