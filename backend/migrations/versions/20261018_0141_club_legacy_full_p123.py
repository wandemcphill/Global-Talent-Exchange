"""Club Legacy full phases 1-3: settings, contracts, and recommendation detail.

Revision ID: 20261018_0141_club_legacy_full_p123
Revises: 20261016_0131_encrypt_kyc_bank_fields
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261018_0141_club_legacy_full_p123"
down_revision = "20261016_0131_encrypt_kyc_bank_fields"
branch_labels = None
depends_on = None


def _columns(inspector: sa.Inspector, table: str) -> set[str]:
    tables = set(inspector.get_table_names())
    if table not in tables:
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _has_unique_idempotency(inspector: sa.Inspector) -> bool:
    if "club_legacy_audit_events" not in set(inspector.get_table_names()):
        return False
    for index in inspector.get_indexes("club_legacy_audit_events"):
        columns = index.get("column_names") or []
        if index.get("unique") and "idempotency_key" in columns:
            return True
    for constraint in inspector.get_unique_constraints("club_legacy_audit_events"):
        if "idempotency_key" in (constraint.get("column_names") or []):
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    from app.club_legacy.models import ClubLegacySettings

    ClubLegacySettings.__table__.create(bind, checkfirst=True)

    inspector = sa.inspect(bind)
    executive_columns = _columns(inspector, "club_legacy_executives")
    if "contract_months" not in executive_columns:
        op.add_column(
            "club_legacy_executives",
            sa.Column("contract_months", sa.Integer(), nullable=False, server_default="24"),
        )
    if "authority" not in executive_columns:
        op.add_column(
            "club_legacy_executives",
            sa.Column("authority", sa.String(length=64), nullable=False, server_default="limited"),
        )

    inspector = sa.inspect(bind)
    recommendation_columns = _columns(inspector, "club_legacy_recommendations")
    if "reason" not in recommendation_columns:
        op.add_column("club_legacy_recommendations", sa.Column("reason", sa.Text(), nullable=True))
    if "confidence" not in recommendation_columns:
        op.add_column("club_legacy_recommendations", sa.Column("confidence", sa.Integer(), nullable=True))
    if "consequence" not in recommendation_columns:
        op.add_column("club_legacy_recommendations", sa.Column("consequence", sa.Text(), nullable=True))

    inspector = sa.inspect(bind)
    audit_columns = _columns(inspector, "club_legacy_audit_events")
    if "idempotency_key" not in audit_columns:
        op.add_column("club_legacy_audit_events", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    inspector = sa.inspect(bind)
    if not _has_unique_idempotency(inspector):
        op.create_index(
            "uq_club_legacy_audit_idempotency",
            "club_legacy_audit_events",
            ["idempotency_key"],
            unique=True,
        )

    from sqlalchemy.orm import Session

    from app.club_legacy.full.phase1 import DEFAULT_INVENTORY_CAPS, DEFAULT_PRESEASON_SHARES, DEFAULT_TRANSFER_FEE_RATE

    session = Session(bind=bind)
    try:
        existing = session.scalar(sa.select(ClubLegacySettings).where(ClubLegacySettings.settings_key == "current"))
        if existing is None:
            session.add(
                ClubLegacySettings(
                    settings_key="current",
                    transfer_fee_rate=DEFAULT_TRANSFER_FEE_RATE,
                    inventory_caps_json=dict(DEFAULT_INVENTORY_CAPS),
                    preseason_shares_json=dict(DEFAULT_PRESEASON_SHARES),
                )
            )
            session.commit()
    finally:
        session.close()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_unique_idempotency(inspector):
        try:
            op.drop_index("uq_club_legacy_audit_idempotency", table_name="club_legacy_audit_events")
        except Exception:
            pass
    for table, column in (
        ("club_legacy_audit_events", "idempotency_key"),
        ("club_legacy_recommendations", "consequence"),
        ("club_legacy_recommendations", "confidence"),
        ("club_legacy_recommendations", "reason"),
        ("club_legacy_executives", "authority"),
        ("club_legacy_executives", "contract_months"),
    ):
        if column in _columns(inspector, table):
            op.drop_column(table, column)
        inspector = sa.inspect(bind)
    if "club_legacy_settings" in set(inspector.get_table_names()):
        op.drop_table("club_legacy_settings")
