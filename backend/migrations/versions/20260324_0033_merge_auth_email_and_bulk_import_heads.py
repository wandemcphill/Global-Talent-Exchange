"""Merge auth email token and bulk import staging heads.

Revision ID: 20260324_0033_merge_auth_email_and_bulk_import_heads
Revises: 20260323_0032_real_player_import_staging_foundation, 20260324_0032_auth_email_tokens
Create Date: 2026-03-24 18:05:00.000000
"""

from __future__ import annotations


revision = "20260324_0033_merge_auth_email_and_bulk_import_heads"
down_revision = (
    "20260323_0032_real_player_import_staging_foundation",
    "20260324_0032_auth_email_tokens",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
