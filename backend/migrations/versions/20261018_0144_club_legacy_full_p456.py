"""Club Legacy phases 4-6: provenance, pre-season rules, and sponsor zones.

Revision ID: 20261018_0144_club_legacy_full_p456
Revises: 20261016_0131_encrypt_kyc_bank_fields
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261018_0144_club_legacy_full_p456"
down_revision = "20261016_0131_encrypt_kyc_bank_fields"
branch_labels = None
depends_on = None

ASSET_EDITION_CONSTRAINT = "uq_club_legacy_assets_catalogue_edition"


def _names(items) -> set[str]:
    return {item.get("name") for item in items if item.get("name")}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    from app.club_legacy.models import CLUB_LEGACY_FULL_TABLES

    for table in CLUB_LEGACY_FULL_TABLES:
        table.create(bind, checkfirst=True)

    inspector = sa.inspect(bind)
    if inspector.has_table("club_legacy_preseason_settlements"):
        columns = {column["name"] for column in inspector.get_columns("club_legacy_preseason_settlements")}
        if "rule_version" not in columns:
            op.add_column(
                "club_legacy_preseason_settlements",
                sa.Column("rule_version", sa.Integer(), nullable=False, server_default="1"),
            )
    if inspector.has_table("club_legacy_assets"):
        present = _names(inspector.get_unique_constraints("club_legacy_assets")) | _names(
            inspector.get_indexes("club_legacy_assets")
        )
        if ASSET_EDITION_CONSTRAINT not in present:
            with op.batch_alter_table("club_legacy_assets") as batch:
                batch.create_unique_constraint(ASSET_EDITION_CONSTRAINT, ["catalogue_id", "edition_number"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("club_legacy_assets"):
        present = _names(inspector.get_unique_constraints("club_legacy_assets")) | _names(
            inspector.get_indexes("club_legacy_assets")
        )
        if ASSET_EDITION_CONSTRAINT in present:
            with op.batch_alter_table("club_legacy_assets") as batch:
                batch.drop_constraint(ASSET_EDITION_CONSTRAINT, type_="unique")
    if inspector.has_table("club_legacy_preseason_settlements"):
        columns = {column["name"] for column in inspector.get_columns("club_legacy_preseason_settlements")}
        if "rule_version" in columns:
            op.drop_column("club_legacy_preseason_settlements", "rule_version")
    from app.club_legacy.models import CLUB_LEGACY_FULL_TABLES

    for table in reversed(CLUB_LEGACY_FULL_TABLES):
        table.drop(bind, checkfirst=True)
