"""Let unfiled club scores stay empty.

Revision ID: 20261121_0274_optional_unfiled_club_scores
Revises: 20261120_0273_staff_contract_demands

Supporter, media, and recruitment scores were stored with numeric defaults.
A club that has not filed a score now keeps the column empty.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261121_0274_optional_unfiled_club_scores"
down_revision = "20261120_0273_staff_contract_demands"
branch_labels = None
depends_on = None

_OPTIONAL_COLUMNS: dict[str, tuple[tuple[str, sa.types.TypeEngine, str], ...]] = {
    "owner_supporter_profiles": (
        ("supporter_culture_label", sa.String(length=120), "'Community & Youth Traditionalists'"),
        ("overall_sentiment", sa.Integer(), "65"),
        ("confidence_in_owner", sa.Integer(), "65"),
        ("confidence_in_manager", sa.Integer(), "68"),
        ("loyalty_index", sa.Integer(), "72"),
        ("matchday_enthusiasm", sa.Integer(), "66"),
        ("ticket_price_tier", sa.String(length=24), "'standard'"),
        ("matchday_experience_rating", sa.Integer(), "62"),
        ("owner_credibility_score", sa.Integer(), "72"),
    ),
    "owner_supporter_segments": (
        ("population_share_pct", sa.Integer(), "16"),
        ("member_count", sa.Integer(), "200"),
        ("sentiment", sa.Integer(), "65"),
        ("loyalty", sa.Integer(), "70"),
        ("enthusiasm", sa.Integer(), "65"),
        ("owner_approval", sa.Integer(), "65"),
    ),
    "owner_media_outlets": (("credibility_score", sa.Integer(), "88"),),
    "owner_recruitment_assignments": (
        ("min_gsi", sa.Integer(), "80"),
        ("max_gsi", sa.Integer(), "85"),
    ),
}


def _relax(table: str, column: str, column_type: sa.types.TypeEngine, previous_default: str) -> None:
    with op.batch_alter_table(table) as batch_op:
        batch_op.alter_column(
            column,
            existing_type=column_type,
            nullable=True,
            server_default=None,
            existing_server_default=sa.text(previous_default),
        )


def _restore(table: str, column: str, column_type: sa.types.TypeEngine, previous_default: str) -> None:
    op.execute(sa.text(f"UPDATE {table} SET {column} = {previous_default} WHERE {column} IS NULL"))
    with op.batch_alter_table(table) as batch_op:
        batch_op.alter_column(
            column,
            existing_type=column_type,
            nullable=False,
            server_default=sa.text(previous_default),
            existing_nullable=True,
        )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table, columns in _OPTIONAL_COLUMNS.items():
        if table not in tables:
            continue
        present = {column["name"] for column in inspector.get_columns(table)}
        for name, column_type, previous_default in columns:
            if name not in present:
                continue
            _relax(table, name, column_type, previous_default)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table, columns in _OPTIONAL_COLUMNS.items():
        if table not in tables:
            continue
        present = {column["name"] for column in inspector.get_columns(table)}
        for name, column_type, previous_default in columns:
            if name not in present:
                continue
            _restore(table, name, column_type, previous_default)
