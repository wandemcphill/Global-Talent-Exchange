"""Add competition engine backbone tables and lifecycle fields."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260314_0036"
down_revision = "20260314_0035"
branch_labels = None
depends_on = None

_COMPETITION_STATUSES = (
    "draft",
    "open",
    "seeded",
    "live",
    "published",
    "open_for_join",
    "filled",
    "locked",
    "in_progress",
    "completed",
    "settled",
    "cancelled",
    "refunded",
    "disputed",
)
_VISIBILITIES = ("public", "private", "invite_only", "gated")


def _as_check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    with op.batch_alter_table("user_competitions") as batch_op:
        batch_op.add_column(sa.Column("competition_type", sa.String(length=32), nullable=False, server_default=sa.text("'league'")))
        batch_op.add_column(sa.Column("source_type", sa.String(length=48), nullable=True))
        batch_op.add_column(sa.Column("source_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("seeded_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("launched_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("stage", sa.String(length=32), nullable=False, server_default=sa.text("'registration'")))
        batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("host_fee_bps", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.drop_constraint("competition_visibility_allowed", type_="check")
        batch_op.create_check_constraint(
            "competition_visibility_allowed",
            f"visibility IN ({_as_check_values(_VISIBILITIES)})",
        )
        batch_op.drop_constraint("competition_status_allowed", type_="check")
        batch_op.create_check_constraint(
            "competition_status_allowed",
            f"status IN ({_as_check_values(_COMPETITION_STATUSES)})",
        )

    op.create_index("ix_user_competitions_competition_type", "user_competitions", ["competition_type"], unique=False)
    op.create_index("ix_user_competitions_source_type", "user_competitions", ["source_type"], unique=False)
    op.create_index("ix_user_competitions_source_id", "user_competitions", ["source_id"], unique=False)
    op.create_index("ix_user_competitions_stage", "user_competitions", ["stage"], unique=False)

    with op.batch_alter_table("competition_rule_sets") as batch_op:
        batch_op.add_column(sa.Column("group_stage_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("group_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("group_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("group_advance_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("knockout_bracket_size", sa.Integer(), nullable=True))

    with op.batch_alter_table("competition_participants") as batch_op:
        batch_op.add_column(sa.Column("entry_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("seed", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("seed_locked", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("group_key", sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column("played", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("wins", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("draws", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("losses", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("goals_for", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("goals_against", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("goal_diff", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("points", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("advanced", sa.Boolean(), nullable=False, server_default=sa.text("0")))

    op.create_index("ix_competition_participants_entry_id", "competition_participants", ["entry_id"], unique=False)
    op.create_index("ix_competition_participants_group_key", "competition_participants", ["group_key"], unique=False)

    with op.batch_alter_table("competition_invites") as batch_op:
        batch_op.add_column(sa.Column("invite_code", sa.String(length=32), nullable=False, server_default=sa.text("'invite'")))
        batch_op.add_column(sa.Column("max_uses", sa.Integer(), nullable=False, server_default=sa.text("1")))
        batch_op.add_column(sa.Column("uses", sa.Integer(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.alter_column("club_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.create_unique_constraint("uq_competition_invites_invite_code", ["invite_code"])

    op.create_index("ix_competition_invites_invite_code", "competition_invites", ["invite_code"], unique=False)

    op.create_table(
        "competition_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("entry_type", sa.String(length=24), server_default=sa.text("'direct'"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("invite_id", sa.String(length=36), nullable=True),
        sa.Column("seed_preference", sa.Integer(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], name="fk_competition_entries_competition_id_user_competitions", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invite_id"], ["competition_invites.id"], name="fk_competition_entries_invite_id_competition_invites", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_entries"),
        sa.UniqueConstraint("competition_id", "club_id", name="uq_competition_entries_competition_club"),
    )
    op.create_index("ix_competition_entries_competition_id", "competition_entries", ["competition_id"], unique=False)
    op.create_index("ix_competition_entries_club_id", "competition_entries", ["club_id"], unique=False)
    op.create_index("ix_competition_entries_user_id", "competition_entries", ["user_id"], unique=False)
    op.create_index("ix_competition_entries_invite_id", "competition_entries", ["invite_id"], unique=False)

    op.create_table(
        "competition_rounds",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=32), server_default=sa.text("'league'"), nullable=False),
        sa.Column("group_key", sa.String(length=24), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'scheduled'"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], name="fk_competition_rounds_competition_id_user_competitions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_rounds"),
        sa.UniqueConstraint(
            "competition_id",
            "round_number",
            "group_key",
            "stage",
            name="uq_competition_rounds_competition_round_group_stage",
        ),
    )
    op.create_index("ix_competition_rounds_competition_id", "competition_rounds", ["competition_id"], unique=False)
    op.create_index("ix_competition_rounds_group_key", "competition_rounds", ["group_key"], unique=False)
    op.create_index("ix_competition_rounds_status", "competition_rounds", ["status"], unique=False)

    op.create_table(
        "competition_matches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("round_id", sa.String(length=36), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=32), server_default=sa.text("'league'"), nullable=False),
        sa.Column("group_key", sa.String(length=24), nullable=True),
        sa.Column("home_club_id", sa.String(length=36), nullable=False),
        sa.Column("away_club_id", sa.String(length=36), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("match_date", sa.Date(), nullable=True),
        sa.Column("window", sa.String(length=32), nullable=True),
        sa.Column("slot_sequence", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'scheduled'"), nullable=False),
        sa.Column("home_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("away_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("winner_club_id", sa.String(length=36), nullable=True),
        sa.Column("decided_by_penalties", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("requires_winner", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("stats_applied", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], name="fk_competition_matches_competition_id_user_competitions", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["round_id"], ["competition_rounds.id"], name="fk_competition_matches_round_id_competition_rounds", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_matches"),
        sa.UniqueConstraint(
            "competition_id",
            "round_id",
            "home_club_id",
            "away_club_id",
            name="uq_competition_matches_round_clubs",
        ),
    )
    op.create_index("ix_competition_matches_competition_id", "competition_matches", ["competition_id"], unique=False)
    op.create_index("ix_competition_matches_round_id", "competition_matches", ["round_id"], unique=False)
    op.create_index("ix_competition_matches_match_date", "competition_matches", ["match_date"], unique=False)
    op.create_index("ix_competition_matches_status", "competition_matches", ["status"], unique=False)
    op.create_index("ix_competition_matches_group_key", "competition_matches", ["group_key"], unique=False)
    op.create_index("ix_competition_matches_home_club_id", "competition_matches", ["home_club_id"], unique=False)
    op.create_index("ix_competition_matches_away_club_id", "competition_matches", ["away_club_id"], unique=False)

    op.create_table(
        "competition_match_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=True),
        sa.Column("added_time", sa.Integer(), nullable=True),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=True),
        sa.Column("secondary_player_id", sa.String(length=36), nullable=True),
        sa.Column("card_type", sa.String(length=16), nullable=True),
        sa.Column("highlight", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], name="fk_competition_match_events_competition_id_user_competitions", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], name="fk_competition_match_events_match_id_competition_matches", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_match_events"),
    )
    op.create_index("ix_competition_match_events_competition_id", "competition_match_events", ["competition_id"], unique=False)
    op.create_index("ix_competition_match_events_match_id", "competition_match_events", ["match_id"], unique=False)
    op.create_index("ix_competition_match_events_event_type", "competition_match_events", ["event_type"], unique=False)
    op.create_index("ix_competition_match_events_club_id", "competition_match_events", ["club_id"], unique=False)
    op.create_index("ix_competition_match_events_player_id", "competition_match_events", ["player_id"], unique=False)

    op.create_table(
        "competition_reward_pools",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("pool_type", sa.String(length=32), server_default=sa.text("'entry_fee'"), nullable=False),
        sa.Column("currency", sa.String(length=12), nullable=False),
        sa.Column("amount_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'planned'"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], name="fk_competition_reward_pools_competition_id_user_competitions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_reward_pools"),
    )
    op.create_index("ix_competition_reward_pools_competition_id", "competition_reward_pools", ["competition_id"], unique=False)
    op.create_index("ix_competition_reward_pools_status", "competition_reward_pools", ["status"], unique=False)

    op.create_table(
        "competition_rewards",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("reward_pool_id", sa.String(length=36), nullable=True),
        sa.Column("participant_id", sa.String(length=36), nullable=True),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("placement", sa.Integer(), nullable=True),
        sa.Column("reward_type", sa.String(length=32), server_default=sa.text("'prize'"), nullable=False),
        sa.Column("currency", sa.String(length=12), nullable=False),
        sa.Column("amount_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], name="fk_competition_rewards_competition_id_user_competitions", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reward_pool_id"], ["competition_reward_pools.id"], name="fk_competition_rewards_reward_pool_id_competition_reward_pools", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["participant_id"], ["competition_participants.id"], name="fk_competition_rewards_participant_id_competition_participants", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_rewards"),
    )
    op.create_index("ix_competition_rewards_competition_id", "competition_rewards", ["competition_id"], unique=False)
    op.create_index("ix_competition_rewards_reward_pool_id", "competition_rewards", ["reward_pool_id"], unique=False)
    op.create_index("ix_competition_rewards_participant_id", "competition_rewards", ["participant_id"], unique=False)
    op.create_index("ix_competition_rewards_club_id", "competition_rewards", ["club_id"], unique=False)
    op.create_index("ix_competition_rewards_status", "competition_rewards", ["status"], unique=False)

    op.create_table(
        "competition_seed_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("seed_method", sa.String(length=24), server_default=sa.text("'random'"), nullable=False),
        sa.Column("seed_source", sa.String(length=32), server_default=sa.text("'rating'"), nullable=False),
        sa.Column("allow_admin_override", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("lock_after_seed", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], name="fk_competition_seed_rules_competition_id_user_competitions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_seed_rules"),
        sa.UniqueConstraint("competition_id", name="uq_competition_seed_rules_competition_id"),
    )
    op.create_index("ix_competition_seed_rules_competition_id", "competition_seed_rules", ["competition_id"], unique=False)

    op.create_table(
        "competition_visibility_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("rule_payload", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], name="fk_competition_visibility_rules_competition_id_user_competitions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_visibility_rules"),
    )
    op.create_index("ix_competition_visibility_rules_competition_id", "competition_visibility_rules", ["competition_id"], unique=False)

    op.create_table(
        "competition_playoffs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("round_id", sa.String(length=36), nullable=True),
        sa.Column("slot_index", sa.Integer(), nullable=True),
        sa.Column("home_seed", sa.Integer(), nullable=True),
        sa.Column("away_seed", sa.Integer(), nullable=True),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("winner_club_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], name="fk_competition_playoffs_competition_id_user_competitions", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["round_id"], ["competition_rounds.id"], name="fk_competition_playoffs_round_id_competition_rounds", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], name="fk_competition_playoffs_match_id_competition_matches", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_playoffs"),
    )
    op.create_index("ix_competition_playoffs_competition_id", "competition_playoffs", ["competition_id"], unique=False)
    op.create_index("ix_competition_playoffs_round_id", "competition_playoffs", ["round_id"], unique=False)
    op.create_index("ix_competition_playoffs_match_id", "competition_playoffs", ["match_id"], unique=False)

    op.create_table(
        "competition_autofill_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_payload", sa.JSON(), nullable=False),
        sa.Column("min_fill", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_fill", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], name="fk_competition_autofill_rules_competition_id_user_competitions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_autofill_rules"),
    )
    op.create_index("ix_competition_autofill_rules_competition_id", "competition_autofill_rules", ["competition_id"], unique=False)

    op.create_table(
        "competition_schedule_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'planned'"), nullable=False),
        sa.Column("requested_start_on", sa.Date(), nullable=True),
        sa.Column("requested_dates_json", sa.JSON(), nullable=False),
        sa.Column("assigned_dates_json", sa.JSON(), nullable=False),
        sa.Column("schedule_plan_json", sa.JSON(), nullable=False),
        sa.Column("preview_only", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("alignment_group", sa.String(length=64), nullable=True),
        sa.Column("alignment_week", sa.Integer(), nullable=True),
        sa.Column("alignment_year", sa.Integer(), nullable=True),
        sa.Column("requires_exclusive_windows", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], name="fk_competition_schedule_jobs_competition_id_user_competitions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_schedule_jobs"),
    )
    op.create_index("ix_competition_schedule_jobs_competition_id", "competition_schedule_jobs", ["competition_id"], unique=False)
    op.create_index("ix_competition_schedule_jobs_status", "competition_schedule_jobs", ["status"], unique=False)
    op.create_index("ix_competition_schedule_jobs_alignment_group", "competition_schedule_jobs", ["alignment_group"], unique=False)
    op.create_index("ix_competition_schedule_jobs_created_by_user_id", "competition_schedule_jobs", ["created_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_competition_schedule_jobs_created_by_user_id", table_name="competition_schedule_jobs")
    op.drop_index("ix_competition_schedule_jobs_alignment_group", table_name="competition_schedule_jobs")
    op.drop_index("ix_competition_schedule_jobs_status", table_name="competition_schedule_jobs")
    op.drop_index("ix_competition_schedule_jobs_competition_id", table_name="competition_schedule_jobs")
    op.drop_table("competition_schedule_jobs")

    op.drop_index("ix_competition_autofill_rules_competition_id", table_name="competition_autofill_rules")
    op.drop_table("competition_autofill_rules")

    op.drop_index("ix_competition_playoffs_match_id", table_name="competition_playoffs")
    op.drop_index("ix_competition_playoffs_round_id", table_name="competition_playoffs")
    op.drop_index("ix_competition_playoffs_competition_id", table_name="competition_playoffs")
    op.drop_table("competition_playoffs")

    op.drop_index("ix_competition_visibility_rules_competition_id", table_name="competition_visibility_rules")
    op.drop_table("competition_visibility_rules")

    op.drop_index("ix_competition_seed_rules_competition_id", table_name="competition_seed_rules")
    op.drop_table("competition_seed_rules")

    op.drop_index("ix_competition_rewards_status", table_name="competition_rewards")
    op.drop_index("ix_competition_rewards_club_id", table_name="competition_rewards")
    op.drop_index("ix_competition_rewards_participant_id", table_name="competition_rewards")
    op.drop_index("ix_competition_rewards_reward_pool_id", table_name="competition_rewards")
    op.drop_index("ix_competition_rewards_competition_id", table_name="competition_rewards")
    op.drop_table("competition_rewards")

    op.drop_index("ix_competition_reward_pools_status", table_name="competition_reward_pools")
    op.drop_index("ix_competition_reward_pools_competition_id", table_name="competition_reward_pools")
    op.drop_table("competition_reward_pools")

    op.drop_index("ix_competition_match_events_player_id", table_name="competition_match_events")
    op.drop_index("ix_competition_match_events_club_id", table_name="competition_match_events")
    op.drop_index("ix_competition_match_events_event_type", table_name="competition_match_events")
    op.drop_index("ix_competition_match_events_match_id", table_name="competition_match_events")
    op.drop_index("ix_competition_match_events_competition_id", table_name="competition_match_events")
    op.drop_table("competition_match_events")

    op.drop_index("ix_competition_matches_away_club_id", table_name="competition_matches")
    op.drop_index("ix_competition_matches_home_club_id", table_name="competition_matches")
    op.drop_index("ix_competition_matches_group_key", table_name="competition_matches")
    op.drop_index("ix_competition_matches_status", table_name="competition_matches")
    op.drop_index("ix_competition_matches_match_date", table_name="competition_matches")
    op.drop_index("ix_competition_matches_round_id", table_name="competition_matches")
    op.drop_index("ix_competition_matches_competition_id", table_name="competition_matches")
    op.drop_table("competition_matches")

    op.drop_index("ix_competition_rounds_status", table_name="competition_rounds")
    op.drop_index("ix_competition_rounds_group_key", table_name="competition_rounds")
    op.drop_index("ix_competition_rounds_competition_id", table_name="competition_rounds")
    op.drop_table("competition_rounds")

    op.drop_index("ix_competition_entries_invite_id", table_name="competition_entries")
    op.drop_index("ix_competition_entries_user_id", table_name="competition_entries")
    op.drop_index("ix_competition_entries_club_id", table_name="competition_entries")
    op.drop_index("ix_competition_entries_competition_id", table_name="competition_entries")
    op.drop_table("competition_entries")

    op.drop_index("ix_competition_invites_invite_code", table_name="competition_invites")
    with op.batch_alter_table("competition_invites") as batch_op:
        batch_op.drop_constraint("uq_competition_invites_invite_code", type_="unique")
        batch_op.alter_column("club_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("expires_at")
        batch_op.drop_column("uses")
        batch_op.drop_column("max_uses")
        batch_op.drop_column("invite_code")

    op.drop_index("ix_competition_participants_group_key", table_name="competition_participants")
    op.drop_index("ix_competition_participants_entry_id", table_name="competition_participants")
    with op.batch_alter_table("competition_participants") as batch_op:
        batch_op.drop_column("advanced")
        batch_op.drop_column("points")
        batch_op.drop_column("goal_diff")
        batch_op.drop_column("goals_against")
        batch_op.drop_column("goals_for")
        batch_op.drop_column("losses")
        batch_op.drop_column("draws")
        batch_op.drop_column("wins")
        batch_op.drop_column("played")
        batch_op.drop_column("group_key")
        batch_op.drop_column("seed_locked")
        batch_op.drop_column("seed")
        batch_op.drop_column("entry_id")

    with op.batch_alter_table("competition_rule_sets") as batch_op:
        batch_op.drop_column("knockout_bracket_size")
        batch_op.drop_column("group_advance_count")
        batch_op.drop_column("group_size")
        batch_op.drop_column("group_count")
        batch_op.drop_column("group_stage_enabled")

    op.drop_index("ix_user_competitions_stage", table_name="user_competitions")
    op.drop_index("ix_user_competitions_source_id", table_name="user_competitions")
    op.drop_index("ix_user_competitions_source_type", table_name="user_competitions")
    op.drop_index("ix_user_competitions_competition_type", table_name="user_competitions")
    with op.batch_alter_table("user_competitions") as batch_op:
        batch_op.drop_constraint("competition_status_allowed", type_="check")
        batch_op.create_check_constraint(
            "competition_status_allowed",
            "status IN ('draft', 'published', 'open_for_join', 'filled', 'locked', 'in_progress', 'completed', 'cancelled', 'refunded', 'disputed')",
        )
        batch_op.drop_constraint("competition_visibility_allowed", type_="check")
        batch_op.create_check_constraint(
            "competition_visibility_allowed",
            "visibility IN ('public', 'private', 'invite_only')",
        )
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("stage")
        batch_op.drop_column("settled_at")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("launched_at")
        batch_op.drop_column("seeded_at")
        batch_op.drop_column("opened_at")
        batch_op.drop_column("source_id")
        batch_op.drop_column("source_type")
        batch_op.drop_column("host_fee_bps")
        batch_op.drop_column("competition_type")
