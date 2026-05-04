"""Allow per-user national team rental entries.

Revision ID: 20260501_0089_national_team_rental_owners
Revises: 20260424_0088_regen_universe_story_and_seed_awards
Create Date: 2026-05-01 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260501_0089_national_team_rental_owners"
down_revision = "20260424_0088_regen_universe_story_and_seed_awards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("national_team_entries") as batch_op:
        batch_op.add_column(sa.Column("entry_owner_user_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_national_team_entries_entry_owner_user_id_users",
            "users",
            ["entry_owner_user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_constraint("uq_national_team_entries_competition_country", type_="unique")
        batch_op.create_unique_constraint(
            "uq_national_team_entries_competition_country_owner",
            ["competition_id", "country_code", "entry_owner_user_id"],
        )
    op.create_index(
        "ix_national_team_entries_entry_owner_user_id",
        "national_team_entries",
        ["entry_owner_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_national_team_entries_entry_owner_user_id", table_name="national_team_entries")
    with op.batch_alter_table("national_team_entries") as batch_op:
        batch_op.drop_constraint("uq_national_team_entries_competition_country_owner", type_="unique")
        batch_op.create_unique_constraint(
            "uq_national_team_entries_competition_country",
            ["competition_id", "country_code"],
        )
        batch_op.drop_constraint("fk_national_team_entries_entry_owner_user_id_users", type_="foreignkey")
        batch_op.drop_column("entry_owner_user_id")
