"""award gifts phase 3

Revision ID: 20260517_0099_award_gifts_phase3
Revises: 20260517_0098_social_phase2_chat_discussions
Create Date: 2026-05-17 13:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260517_0099_award_gifts_phase3"
down_revision = "20260517_0098_social_phase2_chat_discussions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gift_catalog", sa.Column("fallback_display_name", sa.String(length=160), nullable=True))
    op.add_column("gift_catalog", sa.Column("rarity", sa.String(length=32), nullable=False, server_default="common"))
    op.add_column("gift_catalog", sa.Column("currency", sa.String(length=16), nullable=False, server_default="credit"))
    op.add_column("gift_catalog", sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="2500"))
    op.add_column(
        "gift_catalog", sa.Column("legal_status", sa.String(length=32), nullable=False, server_default="safe")
    )
    op.add_column("gift_catalog", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("gift_catalog", sa.Column("is_award_pack", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column("gift_transactions", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column(
        "gift_transactions", sa.Column("recipient_type", sa.String(length=32), nullable=False, server_default="user")
    )
    op.add_column("gift_transactions", sa.Column("recipient_entity_id", sa.String(length=64), nullable=True))
    op.add_column("gift_transactions", sa.Column("chat_thread_id", sa.String(length=36), nullable=True))
    op.add_column("gift_transactions", sa.Column("discussion_thread_id", sa.String(length=36), nullable=True))
    op.add_column("gift_transactions", sa.Column("discussion_reply_id", sa.String(length=36), nullable=True))
    op.add_column("gift_transactions", sa.Column("match_id", sa.String(length=64), nullable=True))
    op.add_column("gift_transactions", sa.Column("competition_id", sa.String(length=64), nullable=True))
    op.add_column("gift_transactions", sa.Column("wallet_debit_ledger_id", sa.String(length=36), nullable=True))
    op.add_column("gift_transactions", sa.Column("wallet_credit_ledger_id", sa.String(length=36), nullable=True))
    op.add_column("gift_transactions", sa.Column("platform_fee_ledger_id", sa.String(length=36), nullable=True))
    op.add_column("gift_transactions", sa.Column("animation_key", sa.String(length=64), nullable=True))
    op.add_column("gift_transactions", sa.Column("sound_key", sa.String(length=64), nullable=True))
    op.add_column(
        "gift_transactions", sa.Column("abuse_status", sa.String(length=32), nullable=False, server_default="clean")
    )
    op.add_column("gift_transactions", sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"))
    op.create_index("uq_gift_transactions_idempotency_key", "gift_transactions", ["idempotency_key"], unique=True)
    op.create_index(
        op.f("ix_gift_transactions_recipient_entity_id"), "gift_transactions", ["recipient_entity_id"], unique=False
    )
    op.create_index(op.f("ix_gift_transactions_chat_thread_id"), "gift_transactions", ["chat_thread_id"], unique=False)
    op.create_index(
        op.f("ix_gift_transactions_discussion_thread_id"), "gift_transactions", ["discussion_thread_id"], unique=False
    )
    op.create_index(
        op.f("ix_gift_transactions_discussion_reply_id"), "gift_transactions", ["discussion_reply_id"], unique=False
    )
    op.create_index(op.f("ix_gift_transactions_match_id"), "gift_transactions", ["match_id"], unique=False)
    op.create_index(op.f("ix_gift_transactions_competition_id"), "gift_transactions", ["competition_id"], unique=False)
    op.create_index(
        op.f("ix_gift_transactions_wallet_debit_ledger_id"),
        "gift_transactions",
        ["wallet_debit_ledger_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gift_transactions_wallet_credit_ledger_id"),
        "gift_transactions",
        ["wallet_credit_ledger_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gift_transactions_platform_fee_ledger_id"),
        "gift_transactions",
        ["platform_fee_ledger_id"],
        unique=False,
    )

    op.create_table(
        "gift_stats",
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("total_gifts_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_fan_coin_received", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
        sa.Column("total_unique_senders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("top_gift_code", sa.String(length=64), nullable=True),
        sa.Column("mythic_gifts_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", name="uq_gift_stats_entity"),
    )
    op.create_index(op.f("ix_gift_stats_entity_type"), "gift_stats", ["entity_type"], unique=False)
    op.create_index(op.f("ix_gift_stats_entity_id"), "gift_stats", ["entity_id"], unique=False)

    op.create_table(
        "gift_abuse_flags",
        sa.Column("flag_key", sa.String(length=160), nullable=False),
        sa.Column("sender_user_id", sa.String(length=36), nullable=False),
        sa.Column("recipient_type", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("recipient_id", sa.String(length=64), nullable=False),
        sa.Column("gift_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("flag_type", sa.String(length=48), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["gift_transaction_id"], ["gift_transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flag_key", name="uq_gift_abuse_flags_flag_key"),
    )
    op.create_index(op.f("ix_gift_abuse_flags_flag_key"), "gift_abuse_flags", ["flag_key"], unique=False)
    op.create_index(op.f("ix_gift_abuse_flags_sender_user_id"), "gift_abuse_flags", ["sender_user_id"], unique=False)
    op.create_index(op.f("ix_gift_abuse_flags_recipient_id"), "gift_abuse_flags", ["recipient_id"], unique=False)
    op.create_index(
        op.f("ix_gift_abuse_flags_gift_transaction_id"), "gift_abuse_flags", ["gift_transaction_id"], unique=False
    )
    op.create_index(op.f("ix_gift_abuse_flags_flag_type"), "gift_abuse_flags", ["flag_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_gift_abuse_flags_flag_type"), table_name="gift_abuse_flags")
    op.drop_index(op.f("ix_gift_abuse_flags_gift_transaction_id"), table_name="gift_abuse_flags")
    op.drop_index(op.f("ix_gift_abuse_flags_recipient_id"), table_name="gift_abuse_flags")
    op.drop_index(op.f("ix_gift_abuse_flags_sender_user_id"), table_name="gift_abuse_flags")
    op.drop_index(op.f("ix_gift_abuse_flags_flag_key"), table_name="gift_abuse_flags")
    op.drop_table("gift_abuse_flags")

    op.drop_index(op.f("ix_gift_stats_entity_id"), table_name="gift_stats")
    op.drop_index(op.f("ix_gift_stats_entity_type"), table_name="gift_stats")
    op.drop_table("gift_stats")

    op.drop_index(op.f("ix_gift_transactions_platform_fee_ledger_id"), table_name="gift_transactions")
    op.drop_index(op.f("ix_gift_transactions_wallet_credit_ledger_id"), table_name="gift_transactions")
    op.drop_index(op.f("ix_gift_transactions_wallet_debit_ledger_id"), table_name="gift_transactions")
    op.drop_index(op.f("ix_gift_transactions_competition_id"), table_name="gift_transactions")
    op.drop_index(op.f("ix_gift_transactions_match_id"), table_name="gift_transactions")
    op.drop_index(op.f("ix_gift_transactions_discussion_reply_id"), table_name="gift_transactions")
    op.drop_index(op.f("ix_gift_transactions_discussion_thread_id"), table_name="gift_transactions")
    op.drop_index(op.f("ix_gift_transactions_chat_thread_id"), table_name="gift_transactions")
    op.drop_index(op.f("ix_gift_transactions_recipient_entity_id"), table_name="gift_transactions")
    op.drop_index("uq_gift_transactions_idempotency_key", table_name="gift_transactions")
    op.drop_column("gift_transactions", "metadata_json")
    op.drop_column("gift_transactions", "abuse_status")
    op.drop_column("gift_transactions", "sound_key")
    op.drop_column("gift_transactions", "animation_key")
    op.drop_column("gift_transactions", "platform_fee_ledger_id")
    op.drop_column("gift_transactions", "wallet_credit_ledger_id")
    op.drop_column("gift_transactions", "wallet_debit_ledger_id")
    op.drop_column("gift_transactions", "competition_id")
    op.drop_column("gift_transactions", "match_id")
    op.drop_column("gift_transactions", "discussion_reply_id")
    op.drop_column("gift_transactions", "discussion_thread_id")
    op.drop_column("gift_transactions", "chat_thread_id")
    op.drop_column("gift_transactions", "recipient_entity_id")
    op.drop_column("gift_transactions", "recipient_type")
    op.drop_column("gift_transactions", "idempotency_key")

    op.drop_column("gift_catalog", "is_award_pack")
    op.drop_column("gift_catalog", "sort_order")
    op.drop_column("gift_catalog", "legal_status")
    op.drop_column("gift_catalog", "duration_ms")
    op.drop_column("gift_catalog", "currency")
    op.drop_column("gift_catalog", "rarity")
    op.drop_column("gift_catalog", "fallback_display_name")
