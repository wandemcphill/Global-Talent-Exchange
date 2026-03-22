"""Add richer living-market value engine persistence surfaces."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260313_0017"
down_revision = "20260312_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("player_value_snapshots") as batch_op:
        batch_op.add_column(
            sa.Column("snapshot_type", sa.String(length=32), nullable=False, server_default=sa.text("'intraday'"))
        )
        batch_op.add_column(
            sa.Column("scouting_signal_value_credits", sa.Float(), nullable=False, server_default=sa.text("0"))
        )
        batch_op.add_column(
            sa.Column("egame_signal_value_credits", sa.Float(), nullable=False, server_default=sa.text("0"))
        )
        batch_op.add_column(sa.Column("confidence_score", sa.Float(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(
            sa.Column("confidence_tier", sa.String(length=32), nullable=False, server_default=sa.text("'low'"))
        )
        batch_op.add_column(
            sa.Column("liquidity_tier", sa.String(length=32), nullable=False, server_default=sa.text("'default'"))
        )
        batch_op.add_column(
            sa.Column("market_integrity_score", sa.Float(), nullable=False, server_default=sa.text("0"))
        )
        batch_op.add_column(sa.Column("signal_trust_score", sa.Float(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("trend_7d_pct", sa.Float(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("trend_30d_pct", sa.Float(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(
            sa.Column("trend_direction", sa.String(length=16), nullable=False, server_default=sa.text("'flat'"))
        )
        batch_op.add_column(sa.Column("trend_confidence", sa.Float(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(
            sa.Column("config_version", sa.String(length=64), nullable=False, server_default=sa.text("'baseline-v1'"))
        )
        batch_op.add_column(
            sa.Column("reason_codes_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )

    op.execute(
        sa.text(
            """
            UPDATE player_value_snapshots
            SET snapshot_type = 'intraday',
                scouting_signal_value_credits = 0,
                egame_signal_value_credits = 0,
                confidence_score = 0,
                confidence_tier = 'low',
                liquidity_tier = 'default',
                market_integrity_score = 0,
                signal_trust_score = 0,
                trend_7d_pct = 0,
                trend_30d_pct = 0,
                trend_direction = 'flat',
                trend_confidence = 0,
                config_version = 'baseline-v1',
                reason_codes_json = '[]'
            """
        )
    )

    with op.batch_alter_table("player_value_snapshots") as batch_op:
        batch_op.drop_constraint("uq_player_value_snapshots_player_as_of", type_="unique")
        batch_op.create_unique_constraint(
            "uq_player_value_snapshots_player_as_of_type",
            ["player_id", "as_of", "snapshot_type"],
        )
        batch_op.create_index("ix_player_value_snapshots_snapshot_type", ["snapshot_type"], unique=False)
        batch_op.create_index("ix_player_value_snapshots_confidence_tier", ["confidence_tier"], unique=False)
        batch_op.create_index("ix_player_value_snapshots_liquidity_tier", ["liquidity_tier"], unique=False)
        batch_op.create_index("ix_player_value_snapshots_confidence_score", ["confidence_score"], unique=False)

    op.create_table(
        "player_value_daily_closes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("close_date", sa.Date(), nullable=False),
        sa.Column("close_credits", sa.Float(), nullable=False),
        sa.Column("football_truth_value_credits", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("market_signal_value_credits", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("scouting_signal_value_credits", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("egame_signal_value_credits", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("confidence_tier", sa.String(length=32), nullable=False, server_default=sa.text("'low'")),
        sa.Column("liquidity_tier", sa.String(length=32), nullable=False, server_default=sa.text("'default'")),
        sa.Column("trend_7d_pct", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("trend_30d_pct", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("trend_direction", sa.String(length=16), nullable=False, server_default=sa.text("'flat'")),
        sa.Column("trend_confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("reason_codes_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("breakdown_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_player_value_daily_closes"),
        sa.UniqueConstraint("player_id", "close_date", name="uq_player_value_daily_closes_player_date"),
    )
    op.create_index("ix_player_value_daily_closes_player_id", "player_value_daily_closes", ["player_id"], unique=False)
    op.create_index("ix_player_value_daily_closes_close_date", "player_value_daily_closes", ["close_date"], unique=False)
    op.create_index(
        "ix_player_value_daily_closes_confidence_tier",
        "player_value_daily_closes",
        ["confidence_tier"],
        unique=False,
    )
    op.create_index(
        "ix_player_value_daily_closes_liquidity_tier",
        "player_value_daily_closes",
        ["liquidity_tier"],
        unique=False,
    )

    op.create_table(
        "player_value_recompute_candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("requested_tempo", sa.String(length=24), nullable=False, server_default=sa.text("'hourly'")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("trigger_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("signal_delta_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_eligible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("reason_codes_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_player_value_recompute_candidates"),
        sa.UniqueConstraint("player_id", name="uq_player_value_recompute_candidates_player_id"),
    )
    op.create_index(
        "ix_player_value_recompute_candidates_player_id",
        "player_value_recompute_candidates",
        ["player_id"],
        unique=False,
    )
    op.create_index(
        "ix_player_value_recompute_candidates_status",
        "player_value_recompute_candidates",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_player_value_recompute_candidates_requested_tempo",
        "player_value_recompute_candidates",
        ["requested_tempo"],
        unique=False,
    )
    op.create_index(
        "ix_player_value_recompute_candidates_priority",
        "player_value_recompute_candidates",
        ["priority"],
        unique=False,
    )
    op.create_index(
        "ix_player_value_recompute_candidates_last_event_at",
        "player_value_recompute_candidates",
        ["last_event_at"],
        unique=False,
    )
    op.create_index(
        "ix_player_value_recompute_candidates_next_eligible_at",
        "player_value_recompute_candidates",
        ["next_eligible_at"],
        unique=False,
    )

    op.create_table(
        "player_value_run_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("config_version", sa.String(length=64), nullable=False, server_default=sa.text("'baseline-v1'")),
        sa.Column("triggered_by", sa.String(length=32), nullable=False, server_default=sa.text("'system'")),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("snapshot_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_player_value_run_records"),
    )
    op.create_index("ix_player_value_run_records_run_type", "player_value_run_records", ["run_type"], unique=False)
    op.create_index("ix_player_value_run_records_status", "player_value_run_records", ["status"], unique=False)
    op.create_index("ix_player_value_run_records_as_of", "player_value_run_records", ["as_of"], unique=False)
    op.create_index(
        "ix_player_value_run_records_config_version",
        "player_value_run_records",
        ["config_version"],
        unique=False,
    )
    op.create_index(
        "ix_player_value_run_records_actor_user_id",
        "player_value_run_records",
        ["actor_user_id"],
        unique=False,
    )

    op.create_table(
        "player_value_admin_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=48), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=True),
        sa.Column("config_version", sa.String(length=64), nullable=True),
        sa.Column("target_player_id", sa.String(length=36), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_override", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_player_value_admin_audits"),
    )
    op.create_index(
        "ix_player_value_admin_audits_action_type",
        "player_value_admin_audits",
        ["action_type"],
        unique=False,
    )
    op.create_index(
        "ix_player_value_admin_audits_actor_user_id",
        "player_value_admin_audits",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_player_value_admin_audits_config_version",
        "player_value_admin_audits",
        ["config_version"],
        unique=False,
    )
    op.create_index(
        "ix_player_value_admin_audits_target_player_id",
        "player_value_admin_audits",
        ["target_player_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_player_value_admin_audits_target_player_id", table_name="player_value_admin_audits")
    op.drop_index("ix_player_value_admin_audits_config_version", table_name="player_value_admin_audits")
    op.drop_index("ix_player_value_admin_audits_actor_user_id", table_name="player_value_admin_audits")
    op.drop_index("ix_player_value_admin_audits_action_type", table_name="player_value_admin_audits")
    op.drop_table("player_value_admin_audits")

    op.drop_index("ix_player_value_run_records_actor_user_id", table_name="player_value_run_records")
    op.drop_index("ix_player_value_run_records_config_version", table_name="player_value_run_records")
    op.drop_index("ix_player_value_run_records_as_of", table_name="player_value_run_records")
    op.drop_index("ix_player_value_run_records_status", table_name="player_value_run_records")
    op.drop_index("ix_player_value_run_records_run_type", table_name="player_value_run_records")
    op.drop_table("player_value_run_records")

    op.drop_index(
        "ix_player_value_recompute_candidates_next_eligible_at",
        table_name="player_value_recompute_candidates",
    )
    op.drop_index(
        "ix_player_value_recompute_candidates_last_event_at",
        table_name="player_value_recompute_candidates",
    )
    op.drop_index("ix_player_value_recompute_candidates_priority", table_name="player_value_recompute_candidates")
    op.drop_index(
        "ix_player_value_recompute_candidates_requested_tempo",
        table_name="player_value_recompute_candidates",
    )
    op.drop_index("ix_player_value_recompute_candidates_status", table_name="player_value_recompute_candidates")
    op.drop_index("ix_player_value_recompute_candidates_player_id", table_name="player_value_recompute_candidates")
    op.drop_table("player_value_recompute_candidates")

    op.drop_index("ix_player_value_daily_closes_liquidity_tier", table_name="player_value_daily_closes")
    op.drop_index("ix_player_value_daily_closes_confidence_tier", table_name="player_value_daily_closes")
    op.drop_index("ix_player_value_daily_closes_close_date", table_name="player_value_daily_closes")
    op.drop_index("ix_player_value_daily_closes_player_id", table_name="player_value_daily_closes")
    op.drop_table("player_value_daily_closes")

    with op.batch_alter_table("player_value_snapshots") as batch_op:
        batch_op.drop_index("ix_player_value_snapshots_confidence_score")
        batch_op.drop_index("ix_player_value_snapshots_liquidity_tier")
        batch_op.drop_index("ix_player_value_snapshots_confidence_tier")
        batch_op.drop_index("ix_player_value_snapshots_snapshot_type")
        batch_op.drop_constraint("uq_player_value_snapshots_player_as_of_type", type_="unique")
        batch_op.create_unique_constraint("uq_player_value_snapshots_player_as_of", ["player_id", "as_of"])
        batch_op.drop_column("reason_codes_json")
        batch_op.drop_column("config_version")
        batch_op.drop_column("trend_confidence")
        batch_op.drop_column("trend_direction")
        batch_op.drop_column("trend_30d_pct")
        batch_op.drop_column("trend_7d_pct")
        batch_op.drop_column("signal_trust_score")
        batch_op.drop_column("market_integrity_score")
        batch_op.drop_column("liquidity_tier")
        batch_op.drop_column("confidence_tier")
        batch_op.drop_column("confidence_score")
        batch_op.drop_column("egame_signal_value_credits")
        batch_op.drop_column("scouting_signal_value_credits")
        batch_op.drop_column("snapshot_type")
