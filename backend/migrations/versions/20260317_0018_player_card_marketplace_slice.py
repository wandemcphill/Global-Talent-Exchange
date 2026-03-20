"""player card marketplace slice

Revision ID: 20260317_0018
Revises: 20260317_0017_merge_heads
Create Date: 2026-03-17 21:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260317_0018"
down_revision = "20260317_0017_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "player_card_listings",
        sa.Column("is_negotiable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_player_card_listings_status_price",
        "player_card_listings",
        ["status", "price_per_card_credits"],
        unique=False,
    )
    op.create_index(
        "ix_player_card_listings_status_negotiable",
        "player_card_listings",
        ["status", "is_negotiable"],
        unique=False,
    )

    op.add_column(
        "card_loan_listings",
        sa.Column("is_negotiable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "card_loan_listings",
        sa.Column("borrower_rights_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "card_loan_listings",
        sa.Column("lender_restrictions_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index(
        "ix_card_loan_listings_status_negotiable",
        "card_loan_listings",
        ["status", "is_negotiable"],
        unique=False,
    )
    op.create_index(
        "ix_card_loan_listings_status_fee_duration",
        "card_loan_listings",
        ["status", "loan_fee_credits", "duration_days"],
        unique=False,
    )

    op.create_table(
        "card_loan_negotiations",
        sa.Column("listing_id", sa.String(length=36), nullable=False),
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("borrower_user_id", sa.String(length=36), nullable=False),
        sa.Column("proposer_user_id", sa.String(length=36), nullable=False),
        sa.Column("counterparty_user_id", sa.String(length=36), nullable=False),
        sa.Column("proposed_duration_days", sa.Integer(), nullable=False),
        sa.Column("proposed_loan_fee_credits", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("supersedes_negotiation_id", sa.String(length=36), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_terms_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["borrower_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["counterparty_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["card_loan_listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supersedes_negotiation_id"], ["card_loan_negotiations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_loan_negotiations_listing_id", "card_loan_negotiations", ["listing_id"], unique=False)
    op.create_index("ix_card_loan_negotiations_borrower_user_id", "card_loan_negotiations", ["borrower_user_id"], unique=False)
    op.create_index("ix_card_loan_negotiations_proposer_user_id", "card_loan_negotiations", ["proposer_user_id"], unique=False)
    op.create_index("ix_card_loan_negotiations_status", "card_loan_negotiations", ["status"], unique=False)
    op.create_index("ix_card_loan_negotiations_supersedes", "card_loan_negotiations", ["supersedes_negotiation_id"], unique=False)

    with op.batch_alter_table("card_loan_contracts") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=24),
            type_=sa.String(length=32),
            existing_nullable=False,
            existing_server_default="active",
            server_default="accepted_pending_settlement",
        )
        batch_op.add_column(sa.Column("accepted_negotiation_id", sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column("requested_loan_fee_credits", sa.Numeric(18, 4), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("platform_fee_credits", sa.Numeric(18, 4), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("lender_net_credits", sa.Numeric(18, 4), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("platform_fee_bps", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("fee_floor_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch_op.add_column(sa.Column("loan_duration_days", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("settlement_reference", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("accepted_terms_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("borrower_rights_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("lender_rights_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(
            sa.Column("lender_restrictions_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
        )
        batch_op.create_foreign_key(
            "fk_card_loan_contract_accept_neg",
            "card_loan_negotiations",
            ["accepted_negotiation_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        "ix_card_loan_contracts_negotiation_id",
        "card_loan_contracts",
        ["accepted_negotiation_id"],
        unique=False,
    )
    op.create_index(
        "ix_card_loan_contracts_settlement_reference",
        "card_loan_contracts",
        ["settlement_reference"],
        unique=False,
    )

    op.create_table(
        "card_swap_listings",
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("requested_player_card_id", sa.String(length=36), nullable=True),
        sa.Column("requested_player_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("is_negotiable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("desired_filters_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("terms_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_player_card_id"], ["player_cards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_swap_listings_player_card_id", "card_swap_listings", ["player_card_id"], unique=False)
    op.create_index("ix_card_swap_listings_owner_user_id", "card_swap_listings", ["owner_user_id"], unique=False)
    op.create_index("ix_card_swap_listings_status", "card_swap_listings", ["status"], unique=False)
    op.create_index(
        "ix_card_swap_listings_requested_player_card_id",
        "card_swap_listings",
        ["requested_player_card_id"],
        unique=False,
    )

    op.create_table(
        "card_swap_executions",
        sa.Column("listing_id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("counterparty_user_id", sa.String(length=36), nullable=False),
        sa.Column("owner_player_card_id", sa.String(length=36), nullable=False),
        sa.Column("counterparty_player_card_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="executed"),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["counterparty_player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["counterparty_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["card_swap_listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("listing_id", name="uq_card_swap_executions_listing_id"),
    )
    op.create_index("ix_card_swap_executions_owner_user_id", "card_swap_executions", ["owner_user_id"], unique=False)
    op.create_index(
        "ix_card_swap_executions_counterparty_user_id",
        "card_swap_executions",
        ["counterparty_user_id"],
        unique=False,
    )
    op.create_index("ix_card_swap_executions_status", "card_swap_executions", ["status"], unique=False)

    op.create_table(
        "card_marketplace_audit_events",
        sa.Column("listing_type", sa.String(length=24), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("player_card_id", sa.String(length=36), nullable=True),
        sa.Column("listing_id", sa.String(length=36), nullable=True),
        sa.Column("loan_contract_id", sa.String(length=36), nullable=True),
        sa.Column("negotiation_id", sa.String(length=36), nullable=True),
        sa.Column("swap_execution_id", sa.String(length=36), nullable=True),
        sa.Column("status_from", sa.String(length=32), nullable=True),
        sa.Column("status_to", sa.String(length=32), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_card_marketplace_audit_events_listing_type",
        "card_marketplace_audit_events",
        ["listing_type"],
        unique=False,
    )
    op.create_index("ix_card_marketplace_audit_events_action", "card_marketplace_audit_events", ["action"], unique=False)
    op.create_index(
        "ix_card_marketplace_audit_events_actor_user_id",
        "card_marketplace_audit_events",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_card_marketplace_audit_events_player_card_id",
        "card_marketplace_audit_events",
        ["player_card_id"],
        unique=False,
    )
    op.create_index(
        "ix_card_marketplace_audit_events_listing_id",
        "card_marketplace_audit_events",
        ["listing_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_card_marketplace_audit_events_listing_id", table_name="card_marketplace_audit_events")
    op.drop_index("ix_card_marketplace_audit_events_player_card_id", table_name="card_marketplace_audit_events")
    op.drop_index("ix_card_marketplace_audit_events_actor_user_id", table_name="card_marketplace_audit_events")
    op.drop_index("ix_card_marketplace_audit_events_action", table_name="card_marketplace_audit_events")
    op.drop_index("ix_card_marketplace_audit_events_listing_type", table_name="card_marketplace_audit_events")
    op.drop_table("card_marketplace_audit_events")

    op.drop_index("ix_card_swap_executions_status", table_name="card_swap_executions")
    op.drop_index("ix_card_swap_executions_counterparty_user_id", table_name="card_swap_executions")
    op.drop_index("ix_card_swap_executions_owner_user_id", table_name="card_swap_executions")
    op.drop_table("card_swap_executions")

    op.drop_index("ix_card_swap_listings_requested_player_card_id", table_name="card_swap_listings")
    op.drop_index("ix_card_swap_listings_status", table_name="card_swap_listings")
    op.drop_index("ix_card_swap_listings_owner_user_id", table_name="card_swap_listings")
    op.drop_index("ix_card_swap_listings_player_card_id", table_name="card_swap_listings")
    op.drop_table("card_swap_listings")

    op.drop_index("ix_card_loan_contracts_settlement_reference", table_name="card_loan_contracts")
    op.drop_index("ix_card_loan_contracts_negotiation_id", table_name="card_loan_contracts")
    with op.batch_alter_table("card_loan_contracts") as batch_op:
        batch_op.drop_constraint(
            "fk_card_loan_contract_accept_neg",
            type_="foreignkey",
        )
        batch_op.drop_column("lender_restrictions_json")
        batch_op.drop_column("lender_rights_json")
        batch_op.drop_column("borrower_rights_json")
        batch_op.drop_column("accepted_terms_json")
        batch_op.drop_column("settlement_reference")
        batch_op.drop_column("settled_at")
        batch_op.drop_column("accepted_at")
        batch_op.drop_column("loan_duration_days")
        batch_op.drop_column("fee_floor_applied")
        batch_op.drop_column("platform_fee_bps")
        batch_op.drop_column("lender_net_credits")
        batch_op.drop_column("platform_fee_credits")
        batch_op.drop_column("requested_loan_fee_credits")
        batch_op.drop_column("accepted_negotiation_id")
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=32),
            type_=sa.String(length=24),
            existing_nullable=False,
            existing_server_default="accepted_pending_settlement",
            server_default="active",
        )

    op.drop_index("ix_card_loan_negotiations_supersedes", table_name="card_loan_negotiations")
    op.drop_index("ix_card_loan_negotiations_status", table_name="card_loan_negotiations")
    op.drop_index("ix_card_loan_negotiations_proposer_user_id", table_name="card_loan_negotiations")
    op.drop_index("ix_card_loan_negotiations_borrower_user_id", table_name="card_loan_negotiations")
    op.drop_index("ix_card_loan_negotiations_listing_id", table_name="card_loan_negotiations")
    op.drop_table("card_loan_negotiations")

    op.drop_index("ix_card_loan_listings_status_fee_duration", table_name="card_loan_listings")
    op.drop_index("ix_card_loan_listings_status_negotiable", table_name="card_loan_listings")
    op.drop_column("card_loan_listings", "lender_restrictions_json")
    op.drop_column("card_loan_listings", "borrower_rights_json")
    op.drop_column("card_loan_listings", "is_negotiable")

    op.drop_index("ix_player_card_listings_status_negotiable", table_name="player_card_listings")
    op.drop_index("ix_player_card_listings_status_price", table_name="player_card_listings")
    op.drop_column("player_card_listings", "is_negotiable")
