"""Add canonical live match execution tables and event versioning columns.

Revision ID: 20261115_0251_canonical_live_match_execution
Revises: 20261115_0250_academy_first_team_minutes
Create Date: 2026-11-15 18:50:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261115_0251_canonical_live_match_execution"
down_revision = "20261115_0250_academy_first_team_minutes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "competition_match_executions" not in existing_tables:
        op.create_table(
            "competition_match_executions",
            sa.Column("match_id", sa.String(length=36), nullable=False),
            sa.Column("competition_id", sa.String(length=36), nullable=False),
            sa.Column("execution_status", sa.String(length=24), nullable=False, server_default="scheduled"),
            sa.Column("execution_revision", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("current_minute", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("target_end_minute", sa.Integer(), nullable=False, server_default="90"),
            sa.Column("step_sequence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_event_sequence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("clock_phase", sa.String(length=32), nullable=False, server_default="pre_match"),
            sa.Column("broadcast_category", sa.String(length=32), nullable=False, server_default="regular"),
            sa.Column("assigned_duration_seconds", sa.Integer(), nullable=False, server_default="600"),
            sa.Column("elapsed_broadcast_seconds", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("paused_reason", sa.String(length=64), nullable=True),
            sa.Column("halftime_resume_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("next_step_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("lease_owner", sa.String(length=128), nullable=True),
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("simulation_request_json", sa.JSON(), nullable=False),
            sa.Column("checkpoint_json", sa.JSON(), nullable=False),
            sa.Column("home_tactics_json", sa.JSON(), nullable=False),
            sa.Column("away_tactics_json", sa.JSON(), nullable=False),
            sa.Column("committed_events_json", sa.JSON(), nullable=False),
            sa.Column("projected_tail_events_json", sa.JSON(), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["competition_id"],
                ["user_competitions.id"],
                name=op.f("fk_competition_match_executions_competition_id_user_competitions"),
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["match_id"],
                ["competition_matches.id"],
                name=op.f("fk_competition_match_executions_match_id_competition_matches"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_competition_match_executions")),
            sa.UniqueConstraint("match_id", name=op.f("uq_competition_match_executions_match_id")),
        )
        op.create_index(
            op.f("ix_competition_match_executions_competition_id"),
            "competition_match_executions",
            ["competition_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_competition_match_executions_execution_status"),
            "competition_match_executions",
            ["execution_status"],
            unique=False,
        )
        op.create_index(
            "ix_competition_match_executions_status_next_step",
            "competition_match_executions",
            ["execution_status", "next_step_at"],
            unique=False,
        )

    if "competition_match_tactical_commands" not in existing_tables:
        op.create_table(
            "competition_match_tactical_commands",
            sa.Column("match_id", sa.String(length=36), nullable=False),
            sa.Column("execution_id", sa.String(length=36), nullable=False),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("side", sa.String(length=16), nullable=False),
            sa.Column("actor_user_id", sa.String(length=36), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("expected_revision", sa.Integer(), nullable=False),
            sa.Column("resulting_revision", sa.Integer(), nullable=True),
            sa.Column("submitted_at_minute", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("effective_minute", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="accepted"),
            sa.Column("rejection_reason", sa.String(length=255), nullable=True),
            sa.Column("command_payload_json", sa.JSON(), nullable=False),
            sa.Column("response_payload_json", sa.JSON(), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["execution_id"],
                ["competition_match_executions.id"],
                name=op.f("fk_competition_match_tactical_commands_execution_id_competition_match_executions"),
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["match_id"],
                ["competition_matches.id"],
                name=op.f("fk_competition_match_tactical_commands_match_id_competition_matches"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_competition_match_tactical_commands")),
            sa.UniqueConstraint(
                "match_id",
                "idempotency_key",
                name="uq_competition_match_tactical_commands_idempotency",
            ),
        )
        op.create_index(
            op.f("ix_competition_match_tactical_commands_match_id"),
            "competition_match_tactical_commands",
            ["match_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_competition_match_tactical_commands_execution_id"),
            "competition_match_tactical_commands",
            ["execution_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_competition_match_tactical_commands_club_id"),
            "competition_match_tactical_commands",
            ["club_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_competition_match_tactical_commands_actor_user_id"),
            "competition_match_tactical_commands",
            ["actor_user_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_competition_match_tactical_commands_status"),
            "competition_match_tactical_commands",
            ["status"],
            unique=False,
        )

    if "competition_match_events" in existing_tables:
        columns = {item["name"] for item in inspector.get_columns("competition_match_events")}
        indexes = {item["name"] for item in inspector.get_indexes("competition_match_events")}
        unique_constraints = {
            item["name"]
            for item in inspector.get_unique_constraints("competition_match_events")
            if item.get("name")
        }
        with op.batch_alter_table("competition_match_events", schema=None) as batch_op:
            if "sequence" not in columns:
                batch_op.add_column(sa.Column("sequence", sa.Integer(), nullable=True))
            if "execution_revision" not in columns:
                batch_op.add_column(sa.Column("execution_revision", sa.Integer(), nullable=False, server_default="1"))
            if "event_key" not in columns:
                batch_op.add_column(sa.Column("event_key", sa.String(length=128), nullable=True))
            if "uq_competition_match_events_match_event_key" not in unique_constraints:
                batch_op.create_unique_constraint(
                    "uq_competition_match_events_match_event_key",
                    ["match_id", "event_key"],
                )
        if op.f("ix_competition_match_events_sequence") not in indexes:
            op.create_index(
                op.f("ix_competition_match_events_sequence"),
                "competition_match_events",
                ["sequence"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "competition_match_events" in existing_tables:
        columns = {item["name"] for item in inspector.get_columns("competition_match_events")}
        indexes = {item["name"] for item in inspector.get_indexes("competition_match_events")}
        unique_constraints = {
            item["name"]
            for item in inspector.get_unique_constraints("competition_match_events")
            if item.get("name")
        }
        sequence_ix = op.f("ix_competition_match_events_sequence")
        if sequence_ix in indexes:
            op.drop_index(sequence_ix, table_name="competition_match_events")
        with op.batch_alter_table("competition_match_events", schema=None) as batch_op:
            if "uq_competition_match_events_match_event_key" in unique_constraints:
                batch_op.drop_constraint("uq_competition_match_events_match_event_key", type_="unique")
            if "event_key" in columns:
                batch_op.drop_column("event_key")
            if "execution_revision" in columns:
                batch_op.drop_column("execution_revision")
            if "sequence" in columns:
                batch_op.drop_column("sequence")

    if "competition_match_tactical_commands" in existing_tables:
        op.drop_table("competition_match_tactical_commands")

    if "competition_match_executions" in existing_tables:
        op.drop_table("competition_match_executions")
