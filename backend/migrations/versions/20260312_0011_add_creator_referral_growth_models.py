"""Add creator growth, share code, attribution, reward, and moderation tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from backend.app.common.enums.creator_profile_status import CreatorProfileStatus
from backend.app.common.enums.referral_event_type import ReferralEventType
from backend.app.common.enums.referral_reward_status import ReferralRewardStatus
from backend.app.common.enums.referral_reward_type import ReferralRewardType
from backend.app.common.enums.referral_source_channel import ReferralSourceChannel
from backend.app.common.enums.share_code_type import ShareCodeType

revision = "20260312_0011"
down_revision = "20260312_0010"
branch_labels = None
depends_on = None

_ATTRIBUTION_STATUSES = ("pending", "qualified", "blocked", "superseded")


def _enum_values(enum_type) -> tuple[str, ...]:
    return tuple(member.value for member in enum_type)


def _check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "creator_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("handle", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("tier", sa.String(length=32), server_default=sa.text("'community'"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'active'"), nullable=False),
        sa.Column("default_share_code", sa.String(length=32), nullable=True),
        sa.Column("default_competition_id", sa.String(length=36), nullable=True),
        sa.Column("revenue_share_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("payout_config_json", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            f"status IN ({_check_values(_enum_values(CreatorProfileStatus))})",
            name="creator_profile_status_allowed",
        ),
        sa.CheckConstraint(
            "revenue_share_percent IS NULL OR (revenue_share_percent >= 0 AND revenue_share_percent <= 100)",
            name="creator_profile_revshare_bounds",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_profiles"),
        sa.UniqueConstraint("user_id", name="uq_creator_profiles_user_id"),
        sa.UniqueConstraint("handle", name="uq_creator_profiles_handle"),
    )
    op.create_index("ix_creator_profiles_user_id", "creator_profiles", ["user_id"], unique=False)
    op.create_index("ix_creator_profiles_handle", "creator_profiles", ["handle"], unique=False)
    op.create_index("ix_creator_profiles_default_competition_id", "creator_profiles", ["default_competition_id"], unique=False)

    op.create_table(
        "share_codes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("vanity_code", sa.String(length=32), nullable=True),
        sa.Column("code_type", sa.String(length=24), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("owner_creator_id", sa.String(length=36), nullable=True),
        sa.Column("linked_competition_id", sa.String(length=36), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("current_uses", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            f"code_type IN ({_check_values(_enum_values(ShareCodeType))})",
            name="share_code_type_allowed",
        ),
        sa.CheckConstraint("current_uses >= 0", name="share_code_current_uses_non_negative"),
        sa.CheckConstraint("max_uses IS NULL OR max_uses > 0", name="share_code_max_uses_positive"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_creator_id"], ["creator_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_share_codes"),
        sa.UniqueConstraint("code", name="uq_share_codes_code"),
        sa.UniqueConstraint("vanity_code", name="uq_share_codes_vanity_code"),
    )
    op.create_index("ix_share_codes_code", "share_codes", ["code"], unique=False)
    op.create_index("ix_share_codes_vanity_code", "share_codes", ["vanity_code"], unique=False)
    op.create_index("ix_share_codes_owner_user_id", "share_codes", ["owner_user_id"], unique=False)
    op.create_index("ix_share_codes_owner_creator_id", "share_codes", ["owner_creator_id"], unique=False)
    op.create_index("ix_share_codes_linked_competition_id", "share_codes", ["linked_competition_id"], unique=False)

    op.create_table(
        "creator_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("share_code_id", sa.String(length=36), nullable=True),
        sa.Column("linked_competition_id", sa.String(length=36), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["share_code_id"], ["share_codes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_campaigns"),
        sa.UniqueConstraint("creator_profile_id", "name", name="uq_creator_campaigns_creator_name"),
    )
    op.create_index("ix_creator_campaigns_creator_profile_id", "creator_campaigns", ["creator_profile_id"], unique=False)
    op.create_index("ix_creator_campaigns_share_code_id", "creator_campaigns", ["share_code_id"], unique=False)
    op.create_index("ix_creator_campaigns_linked_competition_id", "creator_campaigns", ["linked_competition_id"], unique=False)

    op.create_table(
        "referral_attributions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("referred_user_id", sa.String(length=36), nullable=False),
        sa.Column("referrer_user_id", sa.String(length=36), nullable=True),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=True),
        sa.Column("share_code_id", sa.String(length=36), nullable=True),
        sa.Column("source_channel", sa.String(length=32), nullable=False),
        sa.Column("first_touch_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("attribution_status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("campaign_name", sa.String(length=120), nullable=True),
        sa.Column("linked_competition_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            f"source_channel IN ({_check_values(_enum_values(ReferralSourceChannel))})",
            name="referral_attribution_source_channel_allowed",
        ),
        sa.CheckConstraint(
            f"attribution_status IN ({_check_values(_ATTRIBUTION_STATUSES)})",
            name="referral_attribution_status_allowed",
        ),
        sa.ForeignKeyConstraint(["referred_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["referrer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["share_code_id"], ["share_codes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_referral_attributions"),
        sa.UniqueConstraint("referred_user_id", name="uq_referral_attributions_referred_user_id"),
    )
    op.create_index("ix_referral_attributions_referred_user_id", "referral_attributions", ["referred_user_id"], unique=False)
    op.create_index("ix_referral_attributions_referrer_user_id", "referral_attributions", ["referrer_user_id"], unique=False)
    op.create_index("ix_referral_attributions_creator_profile_id", "referral_attributions", ["creator_profile_id"], unique=False)
    op.create_index("ix_referral_attributions_share_code_id", "referral_attributions", ["share_code_id"], unique=False)
    op.create_index("ix_referral_attributions_linked_competition_id", "referral_attributions", ["linked_competition_id"], unique=False)

    op.create_table(
        "referral_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("event_key", sa.String(length=96), nullable=False),
        sa.Column("referral_attribution_id", sa.String(length=36), nullable=True),
        sa.Column("referred_user_id", sa.String(length=36), nullable=False),
        sa.Column("referrer_user_id", sa.String(length=36), nullable=True),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=True),
        sa.Column("share_code_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("source_channel", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("manual_review_requested", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("fraud_suspected", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("event_payload_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            f"event_type IN ({_check_values(_enum_values(ReferralEventType))})",
            name="referral_event_type_allowed",
        ),
        sa.CheckConstraint(
            f"source_channel IN ({_check_values(_enum_values(ReferralSourceChannel))})",
            name="referral_event_source_channel_allowed",
        ),
        sa.ForeignKeyConstraint(["referral_attribution_id"], ["referral_attributions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["referred_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["referrer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["share_code_id"], ["share_codes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_referral_events"),
        sa.UniqueConstraint("event_key", name="uq_referral_events_event_key"),
    )
    op.create_index("ix_referral_events_event_key", "referral_events", ["event_key"], unique=False)
    op.create_index("ix_referral_events_referral_attribution_id", "referral_events", ["referral_attribution_id"], unique=False)
    op.create_index("ix_referral_events_referred_user_id", "referral_events", ["referred_user_id"], unique=False)
    op.create_index("ix_referral_events_referrer_user_id", "referral_events", ["referrer_user_id"], unique=False)
    op.create_index("ix_referral_events_creator_profile_id", "referral_events", ["creator_profile_id"], unique=False)
    op.create_index("ix_referral_events_share_code_id", "referral_events", ["share_code_id"], unique=False)

    op.create_table(
        "referral_rewards",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("reward_key", sa.String(length=128), nullable=False),
        sa.Column("referral_attribution_id", sa.String(length=36), nullable=True),
        sa.Column("reward_source_event_id", sa.String(length=36), nullable=True),
        sa.Column("referred_user_id", sa.String(length=36), nullable=False),
        sa.Column("beneficiary_user_id", sa.String(length=36), nullable=True),
        sa.Column("beneficiary_creator_id", sa.String(length=36), nullable=True),
        sa.Column("trigger_event_type", sa.String(length=48), nullable=False),
        sa.Column("reward_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("reward_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("reward_unit", sa.String(length=24), nullable=True),
        sa.Column("reward_reference", sa.String(length=64), nullable=True),
        sa.Column("hold_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_reason", sa.String(length=255), nullable=True),
        sa.Column("reward_payload_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            f"trigger_event_type IN ({_check_values(_enum_values(ReferralEventType))})",
            name="referral_reward_trigger_event_allowed",
        ),
        sa.CheckConstraint(
            f"reward_type IN ({_check_values(_enum_values(ReferralRewardType))})",
            name="referral_reward_type_allowed",
        ),
        sa.CheckConstraint(
            f"status IN ({_check_values(_enum_values(ReferralRewardStatus))})",
            name="referral_reward_status_allowed",
        ),
        sa.ForeignKeyConstraint(["referral_attribution_id"], ["referral_attributions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reward_source_event_id"], ["referral_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["referred_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["beneficiary_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["beneficiary_creator_id"], ["creator_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_referral_rewards"),
        sa.UniqueConstraint("reward_key", name="uq_referral_rewards_reward_key"),
    )
    op.create_index("ix_referral_rewards_reward_key", "referral_rewards", ["reward_key"], unique=False)
    op.create_index("ix_referral_rewards_referral_attribution_id", "referral_rewards", ["referral_attribution_id"], unique=False)
    op.create_index("ix_referral_rewards_reward_source_event_id", "referral_rewards", ["reward_source_event_id"], unique=False)
    op.create_index("ix_referral_rewards_referred_user_id", "referral_rewards", ["referred_user_id"], unique=False)
    op.create_index("ix_referral_rewards_beneficiary_user_id", "referral_rewards", ["beneficiary_user_id"], unique=False)
    op.create_index("ix_referral_rewards_beneficiary_creator_id", "referral_rewards", ["beneficiary_creator_id"], unique=False)

    op.create_table(
        "referral_reward_ledger",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("entry_key", sa.String(length=128), nullable=False),
        sa.Column("reward_id", sa.String(length=36), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("unit", sa.String(length=24), nullable=True),
        sa.Column("status_after", sa.String(length=24), nullable=False),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            f"status_after IN ({_check_values(_enum_values(ReferralRewardStatus))})",
            name="referral_reward_ledger_status_allowed",
        ),
        sa.ForeignKeyConstraint(["reward_id"], ["referral_rewards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_referral_reward_ledger"),
        sa.UniqueConstraint("entry_key", name="uq_referral_reward_ledger_entry_key"),
    )
    op.create_index("ix_referral_reward_ledger_entry_key", "referral_reward_ledger", ["entry_key"], unique=False)
    op.create_index("ix_referral_reward_ledger_reward_id", "referral_reward_ledger", ["reward_id"], unique=False)
    op.create_index("ix_referral_reward_ledger_reference_id", "referral_reward_ledger", ["reference_id"], unique=False)

    op.create_table(
        "referral_flags",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("flag_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("subject_kind", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'open'"), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_referral_flags"),
    )
    op.create_index("ix_referral_flags_flag_type", "referral_flags", ["flag_type"], unique=False)
    op.create_index("ix_referral_flags_severity", "referral_flags", ["severity"], unique=False)
    op.create_index("ix_referral_flags_subject_kind", "referral_flags", ["subject_kind"], unique=False)
    op.create_index("ix_referral_flags_subject_id", "referral_flags", ["subject_id"], unique=False)

    op.create_table(
        "referral_analytics_daily",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("analytics_date", sa.Date(), nullable=False),
        sa.Column("scope", sa.String(length=24), nullable=False),
        sa.Column("scope_id", sa.String(length=36), nullable=True),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=True),
        sa.Column("share_code_id", sa.String(length=36), nullable=True),
        sa.Column("signups_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("qualified_users_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("retained_day_7_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("retained_day_30_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("reward_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("blocked_reward_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("approved_reward_amount", sa.Numeric(20, 4), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["share_code_id"], ["share_codes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_referral_analytics_daily"),
        sa.UniqueConstraint("analytics_date", "scope", "scope_id", name="uq_referral_analytics_daily_scope"),
    )
    op.create_index("ix_referral_analytics_daily_analytics_date", "referral_analytics_daily", ["analytics_date"], unique=False)
    op.create_index("ix_referral_analytics_daily_scope", "referral_analytics_daily", ["scope"], unique=False)
    op.create_index("ix_referral_analytics_daily_scope_id", "referral_analytics_daily", ["scope_id"], unique=False)
    op.create_index("ix_referral_analytics_daily_creator_profile_id", "referral_analytics_daily", ["creator_profile_id"], unique=False)
    op.create_index("ix_referral_analytics_daily_share_code_id", "referral_analytics_daily", ["share_code_id"], unique=False)

    op.create_table(
        "creator_leaderboard_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("scope", sa.String(length=24), server_default=sa.text("'global'"), nullable=False),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(20, 4), nullable=False),
        sa.Column("total_signups", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("qualified_joins", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("active_participants", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("retained_users", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("approved_reward_amount", sa.Numeric(20, 4), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_leaderboard_snapshots"),
        sa.UniqueConstraint("snapshot_date", "scope", "rank", name="uq_creator_leaderboard_snapshot_rank"),
    )
    op.create_index("ix_creator_leaderboard_snapshots_snapshot_date", "creator_leaderboard_snapshots", ["snapshot_date"], unique=False)
    op.create_index("ix_creator_leaderboard_snapshots_creator_profile_id", "creator_leaderboard_snapshots", ["creator_profile_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_creator_leaderboard_snapshots_creator_profile_id", table_name="creator_leaderboard_snapshots")
    op.drop_index("ix_creator_leaderboard_snapshots_snapshot_date", table_name="creator_leaderboard_snapshots")
    op.drop_table("creator_leaderboard_snapshots")

    op.drop_index("ix_referral_analytics_daily_share_code_id", table_name="referral_analytics_daily")
    op.drop_index("ix_referral_analytics_daily_creator_profile_id", table_name="referral_analytics_daily")
    op.drop_index("ix_referral_analytics_daily_scope_id", table_name="referral_analytics_daily")
    op.drop_index("ix_referral_analytics_daily_scope", table_name="referral_analytics_daily")
    op.drop_index("ix_referral_analytics_daily_analytics_date", table_name="referral_analytics_daily")
    op.drop_table("referral_analytics_daily")

    op.drop_index("ix_referral_flags_subject_id", table_name="referral_flags")
    op.drop_index("ix_referral_flags_subject_kind", table_name="referral_flags")
    op.drop_index("ix_referral_flags_severity", table_name="referral_flags")
    op.drop_index("ix_referral_flags_flag_type", table_name="referral_flags")
    op.drop_table("referral_flags")

    op.drop_index("ix_referral_reward_ledger_reference_id", table_name="referral_reward_ledger")
    op.drop_index("ix_referral_reward_ledger_reward_id", table_name="referral_reward_ledger")
    op.drop_index("ix_referral_reward_ledger_entry_key", table_name="referral_reward_ledger")
    op.drop_table("referral_reward_ledger")

    op.drop_index("ix_referral_rewards_beneficiary_creator_id", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_beneficiary_user_id", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_referred_user_id", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_reward_source_event_id", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_referral_attribution_id", table_name="referral_rewards")
    op.drop_index("ix_referral_rewards_reward_key", table_name="referral_rewards")
    op.drop_table("referral_rewards")

    op.drop_index("ix_referral_events_share_code_id", table_name="referral_events")
    op.drop_index("ix_referral_events_creator_profile_id", table_name="referral_events")
    op.drop_index("ix_referral_events_referrer_user_id", table_name="referral_events")
    op.drop_index("ix_referral_events_referred_user_id", table_name="referral_events")
    op.drop_index("ix_referral_events_referral_attribution_id", table_name="referral_events")
    op.drop_index("ix_referral_events_event_key", table_name="referral_events")
    op.drop_table("referral_events")

    op.drop_index("ix_referral_attributions_linked_competition_id", table_name="referral_attributions")
    op.drop_index("ix_referral_attributions_share_code_id", table_name="referral_attributions")
    op.drop_index("ix_referral_attributions_creator_profile_id", table_name="referral_attributions")
    op.drop_index("ix_referral_attributions_referrer_user_id", table_name="referral_attributions")
    op.drop_index("ix_referral_attributions_referred_user_id", table_name="referral_attributions")
    op.drop_table("referral_attributions")

    op.drop_index("ix_creator_campaigns_linked_competition_id", table_name="creator_campaigns")
    op.drop_index("ix_creator_campaigns_share_code_id", table_name="creator_campaigns")
    op.drop_index("ix_creator_campaigns_creator_profile_id", table_name="creator_campaigns")
    op.drop_table("creator_campaigns")

    op.drop_index("ix_share_codes_linked_competition_id", table_name="share_codes")
    op.drop_index("ix_share_codes_owner_creator_id", table_name="share_codes")
    op.drop_index("ix_share_codes_owner_user_id", table_name="share_codes")
    op.drop_index("ix_share_codes_vanity_code", table_name="share_codes")
    op.drop_index("ix_share_codes_code", table_name="share_codes")
    op.drop_table("share_codes")

    op.drop_index("ix_creator_profiles_default_competition_id", table_name="creator_profiles")
    op.drop_index("ix_creator_profiles_handle", table_name="creator_profiles")
    op.drop_index("ix_creator_profiles_user_id", table_name="creator_profiles")
    op.drop_table("creator_profiles")
