"""Add risk signal/action and social viral persistence.

Revision ID: 20260328_0053_thread_de_risk_social_core
Revises: 20260327_0052_wallet_transaction_classification
Create Date: 2026-03-28 07:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0053_thread_de_risk_social_core"
down_revision = "20260327_0052_wallet_transaction_classification"
branch_labels = None
depends_on = None


risk_signal_type = sa.Enum(
    "device_id",
    "ip_address",
    "transaction_pattern",
    "match_behavior",
    name="risk_signal_type",
    native_enum=False,
)

risk_action_type = sa.Enum(
    "freeze_wallet",
    "block_withdrawal",
    "manual_review",
    "block_trading",
    name="risk_action_type",
    native_enum=False,
)

risk_action_status = sa.Enum(
    "active",
    "released",
    "expired",
    name="risk_action_status",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    risk_signal_type.create(bind, checkfirst=True)
    risk_action_type.create(bind, checkfirst=True)
    risk_action_status.create(bind, checkfirst=True)

    op.create_table(
        "risk_signals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("signal_type", risk_signal_type, nullable=False),
        sa.Column("signal_key", sa.String(length=64), nullable=False, server_default="signal"),
        sa.Column("signal_value", sa.String(length=255), nullable=True),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=48), nullable=False, server_default="manual"),
        sa.Column("confidence_score", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_signals_user_id"), "risk_signals", ["user_id"], unique=False)
    op.create_index(op.f("ix_risk_signals_signal_value"), "risk_signals", ["signal_value"], unique=False)
    op.create_index(op.f("ix_risk_signals_device_id"), "risk_signals", ["device_id"], unique=False)
    op.create_index(op.f("ix_risk_signals_ip_address"), "risk_signals", ["ip_address"], unique=False)
    op.create_index(op.f("ix_risk_signals_source"), "risk_signals", ["source"], unique=False)
    op.create_index(op.f("ix_risk_signals_occurred_at"), "risk_signals", ["occurred_at"], unique=False)

    op.create_table(
        "risk_actions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("action_type", risk_action_type, nullable=False),
        sa.Column("status", risk_action_status, nullable=False, server_default="active"),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("source_rule_key", sa.String(length=96), nullable=False, server_default="manual"),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("released_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("fraud_case_id", sa.String(length=36), nullable=True),
        sa.Column("release_note", sa.Text(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fraud_case_id"], ["fraud_cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["released_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_actions_user_id"), "risk_actions", ["user_id"], unique=False)
    op.create_index(op.f("ix_risk_actions_action_type"), "risk_actions", ["action_type"], unique=False)
    op.create_index(op.f("ix_risk_actions_status"), "risk_actions", ["status"], unique=False)
    op.create_index(op.f("ix_risk_actions_source_rule_key"), "risk_actions", ["source_rule_key"], unique=False)
    op.create_index(op.f("ix_risk_actions_created_by_user_id"), "risk_actions", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_risk_actions_released_by_user_id"), "risk_actions", ["released_by_user_id"], unique=False)
    op.create_index(op.f("ix_risk_actions_fraud_case_id"), "risk_actions", ["fraud_case_id"], unique=False)
    op.create_index(op.f("ix_risk_actions_expires_at"), "risk_actions", ["expires_at"], unique=False)

    op.create_table(
        "social_follows",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("target_key", sa.String(length=96), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "target_key", name="uq_social_follows_user_target"),
    )
    op.create_index(op.f("ix_social_follows_user_id"), "social_follows", ["user_id"], unique=False)
    op.create_index(op.f("ix_social_follows_target_key"), "social_follows", ["target_key"], unique=False)
    op.create_index(op.f("ix_social_follows_target_type"), "social_follows", ["target_type"], unique=False)
    op.create_index(op.f("ix_social_follows_club_id"), "social_follows", ["club_id"], unique=False)
    op.create_index(op.f("ix_social_follows_player_id"), "social_follows", ["player_id"], unique=False)

    op.create_table(
        "match_share_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("challenge_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("share_code", sa.String(length=40), nullable=False),
        sa.Column("share_text", sa.Text(), nullable=False),
        sa.Column("web_path", sa.String(length=255), nullable=False),
        sa.Column("deep_link_path", sa.String(length=255), nullable=False),
        sa.Column("reward_amount_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["club_challenges.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_code", name="uq_match_share_links_share_code"),
    )
    op.create_index(op.f("ix_match_share_links_match_id"), "match_share_links", ["match_id"], unique=False)
    op.create_index(op.f("ix_match_share_links_challenge_id"), "match_share_links", ["challenge_id"], unique=False)
    op.create_index(op.f("ix_match_share_links_created_by_user_id"), "match_share_links", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_match_share_links_share_code"), "match_share_links", ["share_code"], unique=False)

    op.create_table(
        "match_share_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("share_link_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("source_platform", sa.String(length=48), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["share_link_id"], ["match_share_links.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_match_share_events_share_link_id"), "match_share_events", ["share_link_id"], unique=False)
    op.create_index(op.f("ix_match_share_events_actor_user_id"), "match_share_events", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_match_share_events_event_type"), "match_share_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_match_share_events_source_platform"), "match_share_events", ["source_platform"], unique=False)

    op.create_table(
        "match_live_reactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("reaction_type", sa.String(length=32), nullable=False),
        sa.Column("reaction_label", sa.String(length=80), nullable=False),
        sa.Column("intensity_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_match_live_reactions_match_id"), "match_live_reactions", ["match_id"], unique=False)
    op.create_index(op.f("ix_match_live_reactions_user_id"), "match_live_reactions", ["user_id"], unique=False)
    op.create_index(op.f("ix_match_live_reactions_club_id"), "match_live_reactions", ["club_id"], unique=False)
    op.create_index(op.f("ix_match_live_reactions_reaction_type"), "match_live_reactions", ["reaction_type"], unique=False)

    op.create_table(
        "match_chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(length=24), nullable=False, server_default="public"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_match_chat_messages_match_id"), "match_chat_messages", ["match_id"], unique=False)
    op.create_index(op.f("ix_match_chat_messages_user_id"), "match_chat_messages", ["user_id"], unique=False)
    op.create_index(op.f("ix_match_chat_messages_club_id"), "match_chat_messages", ["club_id"], unique=False)
    op.create_index(op.f("ix_match_chat_messages_visibility"), "match_chat_messages", ["visibility"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_match_chat_messages_visibility"), table_name="match_chat_messages")
    op.drop_index(op.f("ix_match_chat_messages_club_id"), table_name="match_chat_messages")
    op.drop_index(op.f("ix_match_chat_messages_user_id"), table_name="match_chat_messages")
    op.drop_index(op.f("ix_match_chat_messages_match_id"), table_name="match_chat_messages")
    op.drop_table("match_chat_messages")

    op.drop_index(op.f("ix_match_live_reactions_reaction_type"), table_name="match_live_reactions")
    op.drop_index(op.f("ix_match_live_reactions_club_id"), table_name="match_live_reactions")
    op.drop_index(op.f("ix_match_live_reactions_user_id"), table_name="match_live_reactions")
    op.drop_index(op.f("ix_match_live_reactions_match_id"), table_name="match_live_reactions")
    op.drop_table("match_live_reactions")

    op.drop_index(op.f("ix_match_share_events_source_platform"), table_name="match_share_events")
    op.drop_index(op.f("ix_match_share_events_event_type"), table_name="match_share_events")
    op.drop_index(op.f("ix_match_share_events_actor_user_id"), table_name="match_share_events")
    op.drop_index(op.f("ix_match_share_events_share_link_id"), table_name="match_share_events")
    op.drop_table("match_share_events")

    op.drop_index(op.f("ix_match_share_links_share_code"), table_name="match_share_links")
    op.drop_index(op.f("ix_match_share_links_created_by_user_id"), table_name="match_share_links")
    op.drop_index(op.f("ix_match_share_links_challenge_id"), table_name="match_share_links")
    op.drop_index(op.f("ix_match_share_links_match_id"), table_name="match_share_links")
    op.drop_table("match_share_links")

    op.drop_index(op.f("ix_social_follows_player_id"), table_name="social_follows")
    op.drop_index(op.f("ix_social_follows_club_id"), table_name="social_follows")
    op.drop_index(op.f("ix_social_follows_target_type"), table_name="social_follows")
    op.drop_index(op.f("ix_social_follows_target_key"), table_name="social_follows")
    op.drop_index(op.f("ix_social_follows_user_id"), table_name="social_follows")
    op.drop_table("social_follows")

    op.drop_index(op.f("ix_risk_actions_expires_at"), table_name="risk_actions")
    op.drop_index(op.f("ix_risk_actions_fraud_case_id"), table_name="risk_actions")
    op.drop_index(op.f("ix_risk_actions_released_by_user_id"), table_name="risk_actions")
    op.drop_index(op.f("ix_risk_actions_created_by_user_id"), table_name="risk_actions")
    op.drop_index(op.f("ix_risk_actions_source_rule_key"), table_name="risk_actions")
    op.drop_index(op.f("ix_risk_actions_status"), table_name="risk_actions")
    op.drop_index(op.f("ix_risk_actions_action_type"), table_name="risk_actions")
    op.drop_index(op.f("ix_risk_actions_user_id"), table_name="risk_actions")
    op.drop_table("risk_actions")

    op.drop_index(op.f("ix_risk_signals_occurred_at"), table_name="risk_signals")
    op.drop_index(op.f("ix_risk_signals_source"), table_name="risk_signals")
    op.drop_index(op.f("ix_risk_signals_ip_address"), table_name="risk_signals")
    op.drop_index(op.f("ix_risk_signals_device_id"), table_name="risk_signals")
    op.drop_index(op.f("ix_risk_signals_signal_value"), table_name="risk_signals")
    op.drop_index(op.f("ix_risk_signals_user_id"), table_name="risk_signals")
    op.drop_table("risk_signals")

    risk_action_status.drop(op.get_bind(), checkfirst=True)
    risk_action_type.drop(op.get_bind(), checkfirst=True)
    risk_signal_type.drop(op.get_bind(), checkfirst=True)
