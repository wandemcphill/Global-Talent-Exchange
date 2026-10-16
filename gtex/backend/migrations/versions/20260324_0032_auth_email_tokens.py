"""Add auth email tokens for signup confirmation and account recovery.

Revision ID: 20260324_0032_auth_email_tokens
Revises: 20260322_0031_merge_real_player_heads
Create Date: 2026-03-24 17:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260324_0032_auth_email_tokens"
down_revision = "20260322_0031_merge_real_player_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_email_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum(
                "signup_confirmation",
                "account_recovery",
                name="auth_email_token_purpose",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_auth_email_tokens_token_hash"),
    )
    op.create_index("ix_auth_email_tokens_user_id", "auth_email_tokens", ["user_id"], unique=False)
    op.create_index("ix_auth_email_tokens_purpose", "auth_email_tokens", ["purpose"], unique=False)
    op.create_index("ix_auth_email_tokens_token_hash", "auth_email_tokens", ["token_hash"], unique=False)
    op.create_index("ix_auth_email_tokens_expires_at", "auth_email_tokens", ["expires_at"], unique=False)
    op.create_index("ix_auth_email_tokens_used_at", "auth_email_tokens", ["used_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_email_tokens_used_at", table_name="auth_email_tokens")
    op.drop_index("ix_auth_email_tokens_expires_at", table_name="auth_email_tokens")
    op.drop_index("ix_auth_email_tokens_token_hash", table_name="auth_email_tokens")
    op.drop_index("ix_auth_email_tokens_purpose", table_name="auth_email_tokens")
    op.drop_index("ix_auth_email_tokens_user_id", table_name="auth_email_tokens")
    op.drop_table("auth_email_tokens")
