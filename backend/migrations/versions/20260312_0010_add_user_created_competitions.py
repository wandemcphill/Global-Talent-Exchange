"""Add user-created skill contest competition tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from backend.app.config.competition_constants import (
    USER_COMPETITION_MAX_ENTRY_FEE_MINOR,
    USER_COMPETITION_MAX_HOST_CREATION_FEE_MINOR,
    USER_COMPETITION_MAX_PARTICIPANTS,
    USER_COMPETITION_MAX_PLATFORM_FEE_BPS,
    USER_COMPETITION_MIN_PARTICIPANTS,
)

revision = "20260312_0010"
down_revision = "20260312_0009"
branch_labels = None
depends_on = None

_COMPETITION_FORMATS = ("league", "cup")
_VISIBILITIES = ("public", "private", "invite_only")
_STATUSES = (
    "draft",
    "published",
    "open_for_join",
    "filled",
    "locked",
    "in_progress",
    "completed",
    "cancelled",
    "refunded",
    "disputed",
)
_START_MODES = ("scheduled", "when_full", "manual_after_min")
_PAYOUT_MODES = ("winner_take_all", "top_n", "custom_percent")


def _as_check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "user_competitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("host_user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("format", sa.String(length=24), nullable=False),
        sa.Column("visibility", sa.String(length=24), server_default=sa.text("'public'"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("start_mode", sa.String(length=24), server_default=sa.text("'scheduled'"), nullable=False),
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("currency", sa.String(length=12), nullable=False),
        sa.Column("entry_fee_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("platform_fee_bps", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("host_creation_fee_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("gross_pool_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("net_prize_pool_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint(
            f"format IN ({_as_check_values(_COMPETITION_FORMATS)})",
            name="competition_format_allowed",
        ),
        sa.CheckConstraint(
            f"visibility IN ({_as_check_values(_VISIBILITIES)})",
            name="competition_visibility_allowed",
        ),
        sa.CheckConstraint(
            f"status IN ({_as_check_values(_STATUSES)})",
            name="competition_status_allowed",
        ),
        sa.CheckConstraint(
            f"start_mode IN ({_as_check_values(_START_MODES)})",
            name="competition_start_mode_allowed",
        ),
        sa.CheckConstraint(
            f"entry_fee_minor >= 0 AND entry_fee_minor <= {USER_COMPETITION_MAX_ENTRY_FEE_MINOR}",
            name="competition_entry_fee_bounds",
        ),
        sa.CheckConstraint(
            f"platform_fee_bps >= 0 AND platform_fee_bps <= {USER_COMPETITION_MAX_PLATFORM_FEE_BPS}",
            name="competition_platform_fee_bounds",
        ),
        sa.CheckConstraint(
            "host_creation_fee_minor >= 0 "
            f"AND host_creation_fee_minor <= {USER_COMPETITION_MAX_HOST_CREATION_FEE_MINOR}",
            name="competition_host_fee_bounds",
        ),
        sa.CheckConstraint("gross_pool_minor >= 0", name="competition_gross_pool_non_negative"),
        sa.CheckConstraint("net_prize_pool_minor >= 0", name="competition_net_pool_non_negative"),
        sa.PrimaryKeyConstraint("id", name="pk_user_competitions"),
    )
    op.create_index("ix_user_competitions_host_user_id", "user_competitions", ["host_user_id"], unique=False)
    op.create_index("ix_user_competitions_status", "user_competitions", ["status"], unique=False)

    op.create_table(
        "competition_rule_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("format", sa.String(length=24), nullable=False),
        sa.Column("min_participants", sa.Integer(), nullable=False),
        sa.Column("max_participants", sa.Integer(), nullable=False),
        sa.Column("league_win_points", sa.Integer(), nullable=True),
        sa.Column("league_draw_points", sa.Integer(), nullable=True),
        sa.Column("league_loss_points", sa.Integer(), nullable=True),
        sa.Column("league_tie_break_order", sa.JSON(), nullable=False),
        sa.Column("league_home_away", sa.Boolean(), nullable=True),
        sa.Column("cup_single_elimination", sa.Boolean(), nullable=True),
        sa.Column("cup_two_leg_tie", sa.Boolean(), nullable=True),
        sa.Column("cup_extra_time", sa.Boolean(), nullable=True),
        sa.Column("cup_penalties", sa.Boolean(), nullable=True),
        sa.Column("cup_allowed_participant_sizes", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            f"format IN ({_as_check_values(_COMPETITION_FORMATS)})",
            name="rule_set_format_allowed",
        ),
        sa.CheckConstraint(
            f"min_participants >= {USER_COMPETITION_MIN_PARTICIPANTS}",
            name="rule_set_min_participants_floor",
        ),
        sa.CheckConstraint(
            f"max_participants <= {USER_COMPETITION_MAX_PARTICIPANTS}",
            name="rule_set_max_participants_ceiling",
        ),
        sa.CheckConstraint("min_participants <= max_participants", name="rule_set_min_lte_max"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_rule_sets"),
        sa.UniqueConstraint("competition_id", name="uq_competition_rule_sets_competition_id"),
    )
    op.create_index("ix_competition_rule_sets_competition_id", "competition_rule_sets", ["competition_id"], unique=False)

    op.create_table(
        "competition_prize_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("payout_mode", sa.String(length=24), nullable=False),
        sa.Column("top_n", sa.Integer(), nullable=True),
        sa.Column("payout_percentages", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            f"payout_mode IN ({_as_check_values(_PAYOUT_MODES)})",
            name="prize_rule_payout_mode_allowed",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_competition_prize_rules"),
        sa.UniqueConstraint("competition_id", name="uq_competition_prize_rules_competition_id"),
    )
    op.create_index("ix_competition_prize_rules_competition_id", "competition_prize_rules", ["competition_id"], unique=False)

    op.create_table(
        "competition_participants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'joined'"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("paid_entry_fee_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("paid_entry_fee_minor >= 0", name="participant_paid_fee_non_negative"),
        sa.PrimaryKeyConstraint("id", name="pk_competition_participants"),
        sa.UniqueConstraint("competition_id", "club_id", name="uq_competition_participants_competition_club"),
    )
    op.create_index("ix_competition_participants_competition_id", "competition_participants", ["competition_id"], unique=False)
    op.create_index("ix_competition_participants_club_id", "competition_participants", ["club_id"], unique=False)

    op.create_table(
        "competition_invites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("invited_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_competition_invites"),
        sa.UniqueConstraint("competition_id", "club_id", name="uq_competition_invites_competition_club"),
    )
    op.create_index("ix_competition_invites_competition_id", "competition_invites", ["competition_id"], unique=False)
    op.create_index("ix_competition_invites_club_id", "competition_invites", ["club_id"], unique=False)

    op.create_table(
        "competition_wallet_ledger",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=12), nullable=False),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_competition_wallet_ledger"),
    )
    op.create_index("ix_competition_wallet_ledger_competition_id", "competition_wallet_ledger", ["competition_id"], unique=False)
    op.create_index("ix_competition_wallet_ledger_entry_type", "competition_wallet_ledger", ["entry_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_competition_wallet_ledger_entry_type", table_name="competition_wallet_ledger")
    op.drop_index("ix_competition_wallet_ledger_competition_id", table_name="competition_wallet_ledger")
    op.drop_table("competition_wallet_ledger")

    op.drop_index("ix_competition_invites_club_id", table_name="competition_invites")
    op.drop_index("ix_competition_invites_competition_id", table_name="competition_invites")
    op.drop_table("competition_invites")

    op.drop_index("ix_competition_participants_club_id", table_name="competition_participants")
    op.drop_index("ix_competition_participants_competition_id", table_name="competition_participants")
    op.drop_table("competition_participants")

    op.drop_index("ix_competition_prize_rules_competition_id", table_name="competition_prize_rules")
    op.drop_table("competition_prize_rules")

    op.drop_index("ix_competition_rule_sets_competition_id", table_name="competition_rule_sets")
    op.drop_table("competition_rule_sets")

    op.drop_index("ix_user_competitions_status", table_name="user_competitions")
    op.drop_index("ix_user_competitions_host_user_id", table_name="user_competitions")
    op.drop_table("user_competitions")
