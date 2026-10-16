"""Add streamer tournament engine tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260317_0016_streamer"
down_revision = "20260317_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tournament_type = sa.Enum(
        "creator_invitation",
        "fan_qualifier",
        "creator_vs_fan",
        name="streamertournamenttype",
    )
    tournament_status = sa.Enum(
        "draft",
        "pending_approval",
        "published",
        "live",
        "completed",
        "cancelled",
        name="streamertournamentstatus",
    )
    approval_status = sa.Enum(
        "not_required",
        "pending",
        "approved",
        "rejected",
        name="streamertournamentapprovalstatus",
    )
    invite_status = sa.Enum("pending", "accepted", "declined", "revoked", name="streamertournamentinvitestatus")
    qualification_type = sa.Enum("invite", "playoffs", "season_pass", "top_gifter", name="streamertournamentqualificationtype")
    entry_status = sa.Enum(
        "confirmed",
        "eliminated",
        "completed",
        "declined",
        "withdrawn",
        "disqualified",
        name="streamertournamententrystatus",
    )
    reward_type = sa.Enum("gtex_coin", "fan_coin", "exclusive_cosmetic", name="streamertournamentrewardtype")
    risk_status = sa.Enum("open", "resolved", "dismissed", name="streamertournamentriskstatus")
    grant_status = sa.Enum("pending", "settled", "failed", "cancelled", name="streamertournamentrewardgrantstatus")

    op.create_table(
        "streamer_tournament_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("policy_key", sa.String(length=64), server_default=sa.text("'default'"), nullable=False),
        sa.Column("reward_coin_approval_limit", sa.Numeric(18, 4), server_default=sa.text("500.0000"), nullable=False),
        sa.Column("reward_credit_approval_limit", sa.Numeric(18, 4), server_default=sa.text("5000.0000"), nullable=False),
        sa.Column("max_cosmetic_rewards_without_review", sa.Integer(), server_default=sa.text("10"), nullable=False),
        sa.Column("max_reward_slots", sa.Integer(), server_default=sa.text("12"), nullable=False),
        sa.Column("max_invites_per_tournament", sa.Integer(), server_default=sa.text("64"), nullable=False),
        sa.Column("top_gifter_rank_limit", sa.Integer(), server_default=sa.text("25"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_streamer_tournament_policies"),
        sa.UniqueConstraint("policy_key", name="uq_streamer_tournament_policies_policy_key"),
    )

    op.create_table(
        "streamer_tournaments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("host_user_id", sa.String(length=36), nullable=False),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("creator_club_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=True),
        sa.Column("linked_competition_id", sa.String(length=36), nullable=True),
        sa.Column("playoff_source_competition_id", sa.String(length=36), nullable=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tournament_type", tournament_type, nullable=False),
        sa.Column("status", tournament_status, server_default=sa.text("'draft'"), nullable=False),
        sa.Column("approval_status", approval_status, server_default=sa.text("'not_required'"), nullable=False),
        sa.Column("max_participants", sa.Integer(), server_default=sa.text("8"), nullable=False),
        sa.Column("requires_admin_approval", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("high_reward_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("rejected_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("submission_notes", sa.Text(), nullable=True),
        sa.Column("approval_notes", sa.Text(), nullable=True),
        sa.Column("entry_rules_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creator_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_competition_id"], ["user_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["playoff_source_competition_id"], ["user_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rejected_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_streamer_tournaments"),
        sa.UniqueConstraint("creator_profile_id", "slug", name="uq_streamer_tournaments_creator_slug"),
    )
    op.create_index("ix_streamer_tournaments_host_user_id", "streamer_tournaments", ["host_user_id"], unique=False)
    op.create_index("ix_streamer_tournaments_creator_profile_id", "streamer_tournaments", ["creator_profile_id"], unique=False)
    op.create_index("ix_streamer_tournaments_creator_club_id", "streamer_tournaments", ["creator_club_id"], unique=False)
    op.create_index("ix_streamer_tournaments_season_id", "streamer_tournaments", ["season_id"], unique=False)
    op.create_index("ix_streamer_tournaments_linked_competition_id", "streamer_tournaments", ["linked_competition_id"], unique=False)
    op.create_index("ix_streamer_tournaments_playoff_source_competition_id", "streamer_tournaments", ["playoff_source_competition_id"], unique=False)

    op.create_table(
        "streamer_tournament_invites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("tournament_id", sa.String(length=36), nullable=False),
        sa.Column("invited_user_id", sa.String(length=36), nullable=False),
        sa.Column("invited_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("status", invite_status, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tournament_id"], ["streamer_tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_streamer_tournament_invites"),
        sa.UniqueConstraint("tournament_id", "invited_user_id", name="uq_streamer_tournament_invites_tournament_user"),
    )
    op.create_index("ix_streamer_tournament_invites_tournament_id", "streamer_tournament_invites", ["tournament_id"], unique=False)
    op.create_index("ix_streamer_tournament_invites_invited_user_id", "streamer_tournament_invites", ["invited_user_id"], unique=False)
    op.create_index("ix_streamer_tournament_invites_invited_by_user_id", "streamer_tournament_invites", ["invited_by_user_id"], unique=False)

    op.create_table(
        "streamer_tournament_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("tournament_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("invite_id", sa.String(length=36), nullable=True),
        sa.Column("entry_role", sa.String(length=32), server_default=sa.text("'participant'"), nullable=False),
        sa.Column("qualification_source", qualification_type, nullable=False),
        sa.Column("qualification_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("status", entry_status, server_default=sa.text("'confirmed'"), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("placement", sa.Integer(), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["invite_id"], ["streamer_tournament_invites.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tournament_id"], ["streamer_tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_streamer_tournament_entries"),
        sa.UniqueConstraint("tournament_id", "user_id", name="uq_streamer_tournament_entries_tournament_user"),
    )
    op.create_index("ix_streamer_tournament_entries_tournament_id", "streamer_tournament_entries", ["tournament_id"], unique=False)
    op.create_index("ix_streamer_tournament_entries_user_id", "streamer_tournament_entries", ["user_id"], unique=False)
    op.create_index("ix_streamer_tournament_entries_invite_id", "streamer_tournament_entries", ["invite_id"], unique=False)

    op.create_table(
        "streamer_tournament_rewards",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("tournament_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("reward_type", reward_type, nullable=False),
        sa.Column("placement_start", sa.Integer(), nullable=False),
        sa.Column("placement_end", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("cosmetic_sku", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["streamer_tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_streamer_tournament_rewards"),
    )
    op.create_index("ix_streamer_tournament_rewards_tournament_id", "streamer_tournament_rewards", ["tournament_id"], unique=False)

    op.create_table(
        "streamer_tournament_risk_signals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("tournament_id", sa.String(length=36), nullable=False),
        sa.Column("signal_key", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), server_default=sa.text("'low'"), nullable=False),
        sa.Column("status", risk_status, server_default=sa.text("'open'"), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tournament_id"], ["streamer_tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_streamer_tournament_risk_signals"),
        sa.UniqueConstraint("tournament_id", "signal_key", name="uq_streamer_tournament_risk_signals_tournament_signal"),
    )
    op.create_index("ix_streamer_tournament_risk_signals_tournament_id", "streamer_tournament_risk_signals", ["tournament_id"], unique=False)

    op.create_table(
        "streamer_tournament_reward_grants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("tournament_id", sa.String(length=36), nullable=False),
        sa.Column("reward_id", sa.String(length=36), nullable=False),
        sa.Column("entry_id", sa.String(length=36), nullable=True),
        sa.Column("recipient_user_id", sa.String(length=36), nullable=False),
        sa.Column("placement", sa.Integer(), nullable=True),
        sa.Column("reward_type", reward_type, nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("cosmetic_sku", sa.String(length=120), nullable=True),
        sa.Column("settlement_status", grant_status, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("reward_settlement_id", sa.String(length=36), nullable=True),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("settled_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["entry_id"], ["streamer_tournament_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reward_id"], ["streamer_tournament_rewards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reward_settlement_id"], ["reward_settlements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tournament_id"], ["streamer_tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_streamer_tournament_reward_grants"),
    )
    op.create_index("ix_streamer_tournament_reward_grants_tournament_id", "streamer_tournament_reward_grants", ["tournament_id"], unique=False)
    op.create_index("ix_streamer_tournament_reward_grants_reward_id", "streamer_tournament_reward_grants", ["reward_id"], unique=False)
    op.create_index("ix_streamer_tournament_reward_grants_entry_id", "streamer_tournament_reward_grants", ["entry_id"], unique=False)
    op.create_index("ix_streamer_tournament_reward_grants_recipient_user_id", "streamer_tournament_reward_grants", ["recipient_user_id"], unique=False)
    op.create_index("ix_streamer_tournament_reward_grants_reward_settlement_id", "streamer_tournament_reward_grants", ["reward_settlement_id"], unique=False)
    op.create_index("ix_streamer_tournament_reward_grants_ledger_transaction_id", "streamer_tournament_reward_grants", ["ledger_transaction_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_streamer_tournament_reward_grants_ledger_transaction_id", table_name="streamer_tournament_reward_grants")
    op.drop_index("ix_streamer_tournament_reward_grants_reward_settlement_id", table_name="streamer_tournament_reward_grants")
    op.drop_index("ix_streamer_tournament_reward_grants_recipient_user_id", table_name="streamer_tournament_reward_grants")
    op.drop_index("ix_streamer_tournament_reward_grants_entry_id", table_name="streamer_tournament_reward_grants")
    op.drop_index("ix_streamer_tournament_reward_grants_reward_id", table_name="streamer_tournament_reward_grants")
    op.drop_index("ix_streamer_tournament_reward_grants_tournament_id", table_name="streamer_tournament_reward_grants")
    op.drop_table("streamer_tournament_reward_grants")

    op.drop_index("ix_streamer_tournament_risk_signals_tournament_id", table_name="streamer_tournament_risk_signals")
    op.drop_table("streamer_tournament_risk_signals")

    op.drop_index("ix_streamer_tournament_rewards_tournament_id", table_name="streamer_tournament_rewards")
    op.drop_table("streamer_tournament_rewards")

    op.drop_index("ix_streamer_tournament_entries_invite_id", table_name="streamer_tournament_entries")
    op.drop_index("ix_streamer_tournament_entries_user_id", table_name="streamer_tournament_entries")
    op.drop_index("ix_streamer_tournament_entries_tournament_id", table_name="streamer_tournament_entries")
    op.drop_table("streamer_tournament_entries")

    op.drop_index("ix_streamer_tournament_invites_invited_by_user_id", table_name="streamer_tournament_invites")
    op.drop_index("ix_streamer_tournament_invites_invited_user_id", table_name="streamer_tournament_invites")
    op.drop_index("ix_streamer_tournament_invites_tournament_id", table_name="streamer_tournament_invites")
    op.drop_table("streamer_tournament_invites")

    op.drop_index("ix_streamer_tournaments_playoff_source_competition_id", table_name="streamer_tournaments")
    op.drop_index("ix_streamer_tournaments_linked_competition_id", table_name="streamer_tournaments")
    op.drop_index("ix_streamer_tournaments_season_id", table_name="streamer_tournaments")
    op.drop_index("ix_streamer_tournaments_creator_club_id", table_name="streamer_tournaments")
    op.drop_index("ix_streamer_tournaments_creator_profile_id", table_name="streamer_tournaments")
    op.drop_index("ix_streamer_tournaments_host_user_id", table_name="streamer_tournaments")
    op.drop_table("streamer_tournaments")

    op.drop_table("streamer_tournament_policies")
