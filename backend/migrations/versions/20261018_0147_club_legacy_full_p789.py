"""Club Legacy full phases 7-9.

Revision ID: 20261018_0147_club_legacy_full_p789
Revises: 20261016_0131_encrypt_kyc_bank_fields

Adds manager terms, relationship events, trade reviews, distributions,
season runs, and the columns those records read. Upgrade is idempotent.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261018_0147_club_legacy_full_p789"
down_revision = "20261016_0131_encrypt_kyc_bank_fields"
branch_labels = None
depends_on = None


def _column_names(inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _index_names(inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {index["name"] for index in inspector.get_indexes(table)}


def _add_column(inspector, table: str, column: sa.Column) -> None:
    if column.name not in _column_names(inspector, table):
        op.add_column(table, column)


def _create_index(inspector, name: str, table: str, columns: list[str]) -> None:
    if name not in _index_names(inspector, table):
        op.create_index(name, table, columns)


def upgrade() -> None:
    bind = op.get_bind()
    from app.club_legacy.models import CLUB_LEGACY_FULL_TABLES

    for table in CLUB_LEGACY_FULL_TABLES:
        table.create(bind, checkfirst=True)

    inspector = sa.inspect(bind)
    offer_columns = (
        sa.Column("contract_length", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=40), nullable=True),
        sa.Column("parent_offer_id", sa.String(length=36), nullable=True),
        sa.Column("manager_id", sa.String(length=36), nullable=True),
        sa.Column("personality", sa.String(length=40), nullable=True),
        sa.Column("wage_expectation", sa.Numeric(20, 2), nullable=True),
        sa.Column("relationship_score", sa.Integer(), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=True),
        sa.Column("expectation_gap", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in offer_columns:
        _add_column(inspector, "club_legacy_manager_offers", column)
    inspector = sa.inspect(bind)
    _create_index(inspector, "ix_club_legacy_manager_offers_parent_offer_id", "club_legacy_manager_offers", ["parent_offer_id"])
    _create_index(inspector, "ix_club_legacy_manager_offers_manager_id", "club_legacy_manager_offers", ["manager_id"])
    _add_column(inspector, "club_legacy_promises", sa.Column("manager_id", sa.String(length=36), nullable=True))
    inspector = sa.inspect(bind)
    _create_index(inspector, "ix_club_legacy_promises_manager_id", "club_legacy_promises", ["manager_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ix_club_legacy_promises_manager_id" in _index_names(inspector, "club_legacy_promises"):
        op.drop_index("ix_club_legacy_promises_manager_id", table_name="club_legacy_promises")
    if "manager_id" in _column_names(inspector, "club_legacy_promises"):
        op.drop_column("club_legacy_promises", "manager_id")
    for index_name in (
        "ix_club_legacy_manager_offers_manager_id",
        "ix_club_legacy_manager_offers_parent_offer_id",
    ):
        if index_name in _index_names(inspector, "club_legacy_manager_offers"):
            op.drop_index(index_name, table_name="club_legacy_manager_offers")
    for name in (
        "created_at",
        "expectation_gap",
        "total_score",
        "relationship_score",
        "wage_expectation",
        "personality",
        "manager_id",
        "parent_offer_id",
        "role",
        "contract_length",
    ):
        if name in _column_names(inspector, "club_legacy_manager_offers"):
            op.drop_column("club_legacy_manager_offers", name)
    from app.club_legacy.models import CLUB_LEGACY_FULL_TABLES

    for table in reversed(CLUB_LEGACY_FULL_TABLES):
        table.drop(bind, checkfirst=True)
