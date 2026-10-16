"""Add provenance, editorial governance, and date of birth to legendary profiles."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260917_0125_legendary_catalogue_governance"
down_revision = "20260915_0124_legendary_player_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("legendary_player_profiles", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column(
        "legendary_player_profiles",
        sa.Column("source_evidence_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "legendary_player_profiles",
        sa.Column("football_evidence_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "legendary_player_profiles",
        sa.Column("editorial_status", sa.String(length=32), nullable=False, server_default="sourced"),
    )
    op.add_column(
        "legendary_player_profiles",
        sa.Column("rights_status", sa.String(length=32), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "legendary_player_profiles",
        sa.Column("catalogue_status", sa.String(length=32), nullable=False, server_default="staged"),
    )
    op.create_index("ix_legendary_player_profiles_editorial_status", "legendary_player_profiles", ["editorial_status"])
    op.create_index("ix_legendary_player_profiles_rights_status", "legendary_player_profiles", ["rights_status"])
    op.create_index("ix_legendary_player_profiles_catalogue_status", "legendary_player_profiles", ["catalogue_status"])


def downgrade() -> None:
    op.drop_index("ix_legendary_player_profiles_catalogue_status", table_name="legendary_player_profiles")
    op.drop_index("ix_legendary_player_profiles_rights_status", table_name="legendary_player_profiles")
    op.drop_index("ix_legendary_player_profiles_editorial_status", table_name="legendary_player_profiles")
    op.drop_column("legendary_player_profiles", "catalogue_status")
    op.drop_column("legendary_player_profiles", "rights_status")
    op.drop_column("legendary_player_profiles", "editorial_status")
    op.drop_column("legendary_player_profiles", "football_evidence_json")
    op.drop_column("legendary_player_profiles", "source_evidence_json")
    op.drop_column("legendary_player_profiles", "date_of_birth")
