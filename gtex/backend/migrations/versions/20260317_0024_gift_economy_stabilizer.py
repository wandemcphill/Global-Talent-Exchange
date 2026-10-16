"""Add gift economy stability controls and audit trail."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260317_0024_gift_economy_stabilizer"
down_revision = "20260317_0023_transfer_news_media_calendar"
branch_labels = None
depends_on = None

spending_control_decision = sa.Enum(
    "approved",
    "review",
    "blocked",
    name="spending_control_decision",
    native_enum=False,
)
ledger_unit = sa.Enum("coin", "credit", name="ledger_unit", native_enum=False)


def upgrade() -> None:
    with op.batch_alter_table("admin_reward_rules") as batch_op:
        batch_op.add_column(
            sa.Column(
                "stability_controls_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )

    op.create_table(
        "spending_control_audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("control_scope", sa.String(length=48), nullable=False),
        sa.Column("decision", spending_control_decision, nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("target_user_id", sa.String(length=36), nullable=True),
        sa.Column("reference_key", sa.String(length=160), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("ledger_unit", ledger_unit, nullable=False),
        sa.Column("primary_reason_code", sa.String(length=64), nullable=True),
        sa.Column("reason_detail", sa.Text(), nullable=True),
        sa.Column("triggered_rules_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_spending_control_audit_events"),
    )
    op.create_index(
        "ix_spending_control_audit_events_actor_created_at",
        "spending_control_audit_events",
        ["actor_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_spending_control_audit_events_target_created_at",
        "spending_control_audit_events",
        ["target_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_spending_control_audit_events_scope_decision",
        "spending_control_audit_events",
        ["control_scope", "decision"],
        unique=False,
    )
    op.create_index(
        "ix_spending_control_audit_events_reference_key",
        "spending_control_audit_events",
        ["reference_key"],
        unique=False,
    )
    op.create_index(
        "ix_spending_control_audit_events_event_type",
        "spending_control_audit_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_spending_control_audit_events_entity_id",
        "spending_control_audit_events",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_spending_control_audit_events_ledger_transaction_id",
        "spending_control_audit_events",
        ["ledger_transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_spending_control_audit_events_ledger_transaction_id", table_name="spending_control_audit_events")
    op.drop_index("ix_spending_control_audit_events_entity_id", table_name="spending_control_audit_events")
    op.drop_index("ix_spending_control_audit_events_event_type", table_name="spending_control_audit_events")
    op.drop_index("ix_spending_control_audit_events_reference_key", table_name="spending_control_audit_events")
    op.drop_index("ix_spending_control_audit_events_scope_decision", table_name="spending_control_audit_events")
    op.drop_index("ix_spending_control_audit_events_target_created_at", table_name="spending_control_audit_events")
    op.drop_index("ix_spending_control_audit_events_actor_created_at", table_name="spending_control_audit_events")
    op.drop_table("spending_control_audit_events")

    with op.batch_alter_table("admin_reward_rules") as batch_op:
        batch_op.drop_column("stability_controls_json")
