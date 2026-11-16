"""Merge the club crest persistence and launch cleanup migration heads.

Revision ID: 20261116_0257_merge_crest_and_test_account_cleanup_heads
Revises: 20261116_0256_club_crest_asset_ref_text, 20261116_0256_remove_test_accounts_and_seeded_owner_competitions
Create Date: 2026-11-16
"""

from __future__ import annotations

revision = "20261116_0257_merge_crest_and_test_account_cleanup_heads"
down_revision = (
    "20261116_0256_club_crest_asset_ref_text",
    "20261116_0256_remove_test_accounts_and_seeded_owner_competitions",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
