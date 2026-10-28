"""Add durable one-to-one mappings from owner-console competitions and fixtures to canonical GTEX lifecycle records.

Revision ID: 20261027_0151_owner_competition_lifecycle_mapping
Revises: 20261026_0150_world_clock_and_autonomous_fixtures

No legacy result, event, standing, ledger, or payout rows are migrated or rewritten.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261027_0151_owner_competition_lifecycle_mapping"
down_revision = "20261026_0150_world_clock_and_autonomous_fixtures"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "owner_competition_lifecycle_mappings" not in tables:
        op.create_table(
            "owner_competition_lifecycle_mappings",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("legacy_competition_id", sa.String(length=36), nullable=False),
            sa.Column("canonical_competition_id", sa.String(length=36), nullable=False),
            sa.Column("mapping_status", sa.String(length=24), server_default="active", nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["canonical_competition_id"],
                ["user_competitions.id"],
                name="fk_owner_comp_lifecycle_canonical_competition_user_competitions",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_owner_competition_lifecycle_mappings"),
            sa.UniqueConstraint(
                "legacy_competition_id",
                name="uq_owner_comp_lifecycle_legacy_competition",
            ),
            sa.UniqueConstraint(
                "canonical_competition_id",
                name="uq_owner_comp_lifecycle_canonical_competition",
            ),
            sa.UniqueConstraint(
                "id",
                "legacy_competition_id",
                name="uq_owner_comp_lifecycle_id_legacy_competition",
            ),
        )

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "owner_match_lifecycle_mappings" not in tables:
        op.create_table(
            "owner_match_lifecycle_mappings",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("legacy_match_id", sa.String(length=36), nullable=False),
            sa.Column("competition_mapping_id", sa.String(length=36), nullable=False),
            sa.Column("legacy_competition_id", sa.String(length=36), nullable=False),
            sa.Column("canonical_match_id", sa.String(length=36), nullable=False),
            sa.Column("mapping_status", sa.String(length=24), server_default="active", nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["canonical_match_id"],
                ["competition_matches.id"],
                name="fk_owner_match_lifecycle_canonical_match_competition_matches",
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["competition_mapping_id", "legacy_competition_id"],
                [
                    "owner_competition_lifecycle_mappings.id",
                    "owner_competition_lifecycle_mappings.legacy_competition_id",
                ],
                name="fk_owner_match_lifecycle_competition_map_legacy_competition",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_owner_match_lifecycle_mappings"),
            sa.UniqueConstraint("legacy_match_id", name="uq_owner_match_lifecycle_legacy_match"),
            sa.UniqueConstraint("canonical_match_id", name="uq_owner_match_lifecycle_canonical_match"),
        )

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("owner_match_lifecycle_mappings")}
    if "ix_owner_match_lifecycle_mappings_competition_mapping_id" not in indexes:
        op.create_index(
            "ix_owner_match_lifecycle_mappings_competition_mapping_id",
            "owner_match_lifecycle_mappings",
            ["competition_mapping_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # Only the mapping records are removed. Canonical and legacy source records
    # (including historical results and ledger entries) are intentionally untouched.
    if "owner_match_lifecycle_mappings" in tables:
        op.drop_table("owner_match_lifecycle_mappings")
    if "owner_competition_lifecycle_mappings" in tables:
        op.drop_table("owner_competition_lifecycle_mappings")
