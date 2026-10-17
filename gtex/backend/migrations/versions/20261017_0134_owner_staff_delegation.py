"""Club Legacy Slice A: GM / HoYD staff, delegation policies, delegated actions and showroom links.

Revision ID: 20261017_0134_owner_staff_delegation
Revises: 20261017_0133_player_share_price_snapshots
"""

from __future__ import annotations

from alembic import op

revision = "20261017_0134_owner_staff_delegation"
down_revision = "20261017_0133_player_share_price_snapshots"
branch_labels = None
depends_on = None


def _tables():
    from app.owner_console.staff_models import OwnerClubStaff, OwnerDelegatedAction, OwnerDelegationPolicy, OwnerShowroomLink

    return [OwnerClubStaff.__table__, OwnerDelegationPolicy.__table__, OwnerDelegatedAction.__table__, OwnerShowroomLink.__table__]


def upgrade() -> None:
    for table in _tables():
        table.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    for table in reversed(_tables()):
        table.drop(op.get_bind(), checkfirst=True)
