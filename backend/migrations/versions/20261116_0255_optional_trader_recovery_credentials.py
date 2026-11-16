"""Allow authenticator-based trader security without extra signup credentials.

Revision ID: 20261116_0255_optional_trader_recovery_credentials
Revises: 20261116_0254_normalize_mutable_treasury_wallet_enum_casing
Create Date: 2026-11-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261116_0255_optional_trader_recovery_credentials"
down_revision = "20261116_0254_normalize_mutable_treasury_wallet_enum_casing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The authenticator plus password protects the trader account. Recovery phrase
    # and a second PIN are optional recovery conveniences, not signup prerequisites.
    with op.batch_alter_table("trader_security") as batch_op:
        batch_op.alter_column(
            "recovery_phrase_hash",
            existing_type=sa.String(length=255),
            nullable=True,
        )
        batch_op.alter_column(
            "security_pin_hash",
            existing_type=sa.String(length=255),
            nullable=True,
        )


def downgrade() -> None:
    # Older application versions require non-null columns. Mark unset values as
    # legacy placeholders; users must configure their own recovery values before
    # those older recovery paths can validate them.
    op.execute(
        sa.text(
            "UPDATE trader_security SET recovery_phrase_hash = 'legacy-unset' "
            "WHERE recovery_phrase_hash IS NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE trader_security SET security_pin_hash = 'legacy-unset' "
            "WHERE security_pin_hash IS NULL"
        )
    )
    with op.batch_alter_table("trader_security") as batch_op:
        batch_op.alter_column(
            "recovery_phrase_hash",
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.alter_column(
            "security_pin_hash",
            existing_type=sa.String(length=255),
            nullable=False,
        )
