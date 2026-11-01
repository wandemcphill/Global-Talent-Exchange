"""Add first club entitlement tracking and historical reconciliation.

Revision ID: 20261101_0155_first_club_grant_and_funding_provenance
Revises: 20261101_0154_brand_music_rights_and_budget_pacing
"""

from __future__ import annotations

import uuid
from alembic import op
import sqlalchemy as sa


revision = "20261101_0155_first_club_grant_and_funding_provenance"
down_revision = "20261101_0154_brand_music_rights_and_budget_pacing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "first_club_entitlements" not in tables:
        op.create_table(
            "first_club_entitlements",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("club_id", sa.String(36), nullable=False),
            sa.Column("gtex_grant_amount", sa.Numeric(18, 4), nullable=False, server_default="100000.0000"),
            sa.Column("fan_grant_amount", sa.Numeric(18, 4), nullable=False, server_default="1000.0000"),
            sa.Column("gtex_ledger_event_id", sa.String(36), nullable=True),
            sa.Column("fan_ledger_event_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", name="uq_first_club_entitlements_user_id"),
        )
        op.create_index(
            "ix_first_club_entitlements_user_id",
            "first_club_entitlements",
            ["user_id"],
        )
        op.create_index(
            "ix_first_club_entitlements_club_id",
            "first_club_entitlements",
            ["club_id"],
        )

    # Safe idempotent historical reconciliation:
    # Any user who already created/owned a club in owner_club_states must be registered
    # as having claimed their first-club entitlement so they cannot receive another grant.
    if "owner_club_states" in tables:
        # Fetch existing owners with their earliest club
        rows = bind.execute(
            sa.text(
                """
                SELECT owner_user_id, club_id
                FROM owner_club_states
                ORDER BY created_at ASC
                """
            )
        ).fetchall()

        seen_users = set()
        for row in rows:
            user_id = str(row[0])
            club_id = str(row[1])
            if user_id in seen_users:
                continue
            seen_users.add(user_id)

            # Check if entitlement already recorded
            existing = bind.execute(
                sa.text(
                    "SELECT id FROM first_club_entitlements WHERE user_id = :uid"
                ),
                {"uid": user_id},
            ).fetchone()
            if existing:
                continue

            # Look up any historical launch_grant ledger event for this club
            gtex_event_id = None
            if "owner_ledger_events" in tables:
                event_row = bind.execute(
                    sa.text(
                        """
                        SELECT id FROM owner_ledger_events
                        WHERE destination_account = :acct AND event_type = 'launch_grant'
                        ORDER BY created_at ASC LIMIT 1
                        """
                    ),
                    {"acct": f"club:{club_id}"},
                ).fetchone()
                if event_row:
                    gtex_event_id = str(event_row[0])

            # Backfill record without duplicating or clawing back funds
            bind.execute(
                sa.text(
                    """
                    INSERT INTO first_club_entitlements (
                        id, user_id, club_id, gtex_grant_amount, fan_grant_amount,
                        gtex_ledger_event_id, fan_ledger_event_id, created_at, updated_at
                    ) VALUES (
                        :id, :user_id, :club_id, 100000.0000, 1000.0000,
                        :gtex_event_id, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "club_id": club_id,
                    "gtex_event_id": gtex_event_id,
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "first_club_entitlements" in tables:
        op.drop_table("first_club_entitlements")
