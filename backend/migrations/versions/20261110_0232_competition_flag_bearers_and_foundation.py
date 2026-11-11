"""Competition flag bearers, result memory, scoped rankings, foundation divisions.

Revision ID: 20261110_0232_competition_flag_bearers_and_foundation
Revises: 20261109_0231_neymar_legend_dedup_and_authentic_legend_portraits
Create Date: 2026-11-10 15:10:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261110_0232_competition_flag_bearers_and_foundation"
down_revision = "20261109_0231_neymar_legend_dedup_and_authentic_legend_portraits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "national_team_country_rankings" in tables:
        columns = {column["name"] for column in inspector.get_columns("national_team_country_rankings")}
        if "age_band" not in columns:
            op.add_column(
                "national_team_country_rankings",
                sa.Column("age_band", sa.String(length=16), server_default="senior", nullable=False),
            )
        if "competition_family" not in columns:
            op.add_column(
                "national_team_country_rankings",
                sa.Column("competition_family", sa.String(length=32), server_default="all", nullable=False),
            )
        indexes = {index["name"] for index in inspector.get_indexes("national_team_country_rankings")}
        uniques = {
            constraint["name"] for constraint in inspector.get_unique_constraints("national_team_country_rankings")
        }
        if (
            "uq_national_team_country_rankings_country_code" in uniques
            or "uq_national_team_country_rankings_country_code" in indexes
        ):
            with op.batch_alter_table("national_team_country_rankings") as batch:
                batch.drop_constraint("uq_national_team_country_rankings_country_code", type_="unique")
        uniques = {
            constraint["name"]
            for constraint in sa.inspect(bind).get_unique_constraints("national_team_country_rankings")
        }
        if "uq_national_team_country_rankings_scope" not in uniques:
            # SQLite cannot ALTER in a unique constraint. Batch mode copies the table.
            with op.batch_alter_table("national_team_country_rankings") as batch:
                batch.create_unique_constraint(
                    "uq_national_team_country_rankings_scope",
                    ["country_code", "age_band", "competition_family"],
                )

    if "owner_club_states" in tables:
        columns = {column["name"] for column in inspector.get_columns("owner_club_states")}
        if "division_level" not in columns:
            op.add_column(
                "owner_club_states",
                sa.Column("division_level", sa.String(length=32), server_default="foundation", nullable=False),
            )

    if "national_team_flag_bearers" not in tables:
        op.create_table(
            "national_team_flag_bearers",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("season_label", sa.String(length=64), nullable=False),
            sa.Column("age_band", sa.String(length=16), nullable=False),
            sa.Column("competition_family", sa.String(length=32), nullable=False),
            sa.Column("country_code", sa.String(length=8), nullable=False),
            sa.Column("country_name", sa.String(length=120), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("entry_id", sa.String(length=36), nullable=True),
            sa.Column("source_competition_id", sa.String(length=36), nullable=False),
            sa.Column("target_key", sa.String(length=96), nullable=False),
            sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "season_label",
                "age_band",
                "target_key",
                "country_code",
                name="uq_national_team_flag_bearers_slot",
            ),
        )
        op.create_index("ix_national_team_flag_bearers_country_code", "national_team_flag_bearers", ["country_code"])
        op.create_index("ix_national_team_flag_bearers_target_key", "national_team_flag_bearers", ["target_key"])
        op.create_index(
            "ix_national_team_flag_bearers_source_competition_id",
            "national_team_flag_bearers",
            ["source_competition_id"],
        )
        op.create_index(
            "ix_national_team_flag_bearers_season_label",
            "national_team_flag_bearers",
            ["season_label"],
        )

    if "national_team_result_memories" not in tables:
        op.create_table(
            "national_team_result_memories",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("competition_id", sa.String(length=36), nullable=False),
            sa.Column("season_label", sa.String(length=64), nullable=False),
            sa.Column("age_band", sa.String(length=16), nullable=False),
            sa.Column("competition_family", sa.String(length=32), nullable=False),
            sa.Column("stage", sa.String(length=32), nullable=False),
            sa.Column("match_key", sa.String(length=80), nullable=False),
            sa.Column("home_entry_id", sa.String(length=36), nullable=True),
            sa.Column("away_entry_id", sa.String(length=36), nullable=True),
            sa.Column("home_user_id", sa.String(length=36), nullable=True),
            sa.Column("away_user_id", sa.String(length=36), nullable=True),
            sa.Column("home_country_code", sa.String(length=8), nullable=False),
            sa.Column("away_country_code", sa.String(length=8), nullable=False),
            sa.Column("home_score", sa.Integer(), server_default="0", nullable=False),
            sa.Column("away_score", sa.Integer(), server_default="0", nullable=False),
            sa.Column("winner_user_id", sa.String(length=36), nullable=True),
            sa.Column("winner_entry_id", sa.String(length=36), nullable=True),
            sa.Column("same_country_playoff", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("competition_id", "match_key", name="uq_national_team_result_memories_match"),
        )
        op.create_index(
            "ix_national_team_result_memories_competition_id", "national_team_result_memories", ["competition_id"]
        )
        op.create_index(
            "ix_national_team_result_memories_competition_family",
            "national_team_result_memories",
            ["competition_family"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "national_team_result_memories" in tables:
        op.drop_table("national_team_result_memories")
    if "national_team_flag_bearers" in tables:
        op.drop_table("national_team_flag_bearers")
