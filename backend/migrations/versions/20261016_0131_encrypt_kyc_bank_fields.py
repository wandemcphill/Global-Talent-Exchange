"""Encrypt KYC/bank identifier columns and add blind-index hashes.

Revision ID: 20261016_0131_encrypt_kyc_bank_fields
Revises: 20261013_0129_open_default_launch_flags

Widens the plaintext-identifier columns that now hold ``enc:v1:`` ciphertext,
drops the unusable nin/bvn indexes (ciphertext cannot be searched), and adds
HMAC blind-index columns for exact-match admin lookups. Existing rows are
left as plaintext; ``backend/scripts/encrypt_sensitive_fields.py`` backfills
them (read-through decrypt returns them unchanged until then).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261016_0131_encrypt_kyc_bank_fields"
down_revision = "20261016_0130_share_event_actor_fingerprint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("kyc_profiles") as batch:
        batch.drop_index("ix_kyc_profiles_nin")
        batch.drop_index("ix_kyc_profiles_bvn")
        batch.alter_column("nin", type_=sa.String(length=512), existing_nullable=True)
        batch.alter_column("bvn", type_=sa.String(length=512), existing_nullable=True)
        batch.add_column(sa.Column("nin_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("bvn_hash", sa.String(length=64), nullable=True))
        batch.create_index("ix_kyc_profiles_nin_hash", ["nin_hash"])
        batch.create_index("ix_kyc_profiles_bvn_hash", ["bvn_hash"])

    with op.batch_alter_table("user_bank_accounts") as batch:
        batch.alter_column("account_number", type_=sa.String(length=512), existing_nullable=False)

    with op.batch_alter_table("treasury_withdrawal_requests") as batch:
        batch.alter_column("bank_account_number", type_=sa.String(length=512), existing_nullable=False)
        batch.add_column(sa.Column("bank_account_number_hash", sa.String(length=64), nullable=True))
        batch.create_index(
            "ix_treasury_withdrawal_requests_bank_account_number_hash",
            ["bank_account_number_hash"],
        )


def downgrade() -> None:
    with op.batch_alter_table("treasury_withdrawal_requests") as batch:
        batch.drop_index("ix_treasury_withdrawal_requests_bank_account_number_hash")
        batch.drop_column("bank_account_number_hash")
        batch.alter_column("bank_account_number", type_=sa.String(length=32), existing_nullable=False)

    with op.batch_alter_table("user_bank_accounts") as batch:
        batch.alter_column("account_number", type_=sa.String(length=32), existing_nullable=False)

    with op.batch_alter_table("kyc_profiles") as batch:
        batch.drop_index("ix_kyc_profiles_bvn_hash")
        batch.drop_index("ix_kyc_profiles_nin_hash")
        batch.drop_column("bvn_hash")
        batch.drop_column("nin_hash")
        batch.alter_column("bvn", type_=sa.String(length=32), existing_nullable=True)
        batch.alter_column("nin", type_=sa.String(length=32), existing_nullable=True)
        batch.create_index("ix_kyc_profiles_nin", ["nin"])
        batch.create_index("ix_kyc_profiles_bvn", ["bvn"])
