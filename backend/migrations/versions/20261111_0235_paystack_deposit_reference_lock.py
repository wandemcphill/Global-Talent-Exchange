"""Lock Paystack deposits to one provider reference.

Revision ID: 20261111_0235_paystack_deposit_reference_lock
Revises: 20261111_0235_flag_bearer_season_label_index
Create Date: 2026-11-11 10:40:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261111_0235_paystack_deposit_reference_lock"
down_revision = "20261111_0235_flag_bearer_season_label_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "owner_deposit_intents" in set(inspector.get_table_names()):
        return
    op.create_table(
        "owner_deposit_intents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("requested_amount_ngn", sa.Numeric(20, 2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("credited_amount_kobo", sa.Integer(), nullable=True),
        sa.Column("ledger_event_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "reference", name="uq_owner_deposit_intents_provider_reference"),
    )
    op.create_index("ix_owner_deposit_intents_user_id", "owner_deposit_intents", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "owner_deposit_intents" not in set(inspector.get_table_names()):
        return
    op.drop_index("ix_owner_deposit_intents_user_id", table_name="owner_deposit_intents")
    op.drop_table("owner_deposit_intents")
