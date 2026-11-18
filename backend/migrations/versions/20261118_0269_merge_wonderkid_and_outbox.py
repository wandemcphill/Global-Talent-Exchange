"""Join the wonderkid roster chain with the event outbox widening.

Revision ID: 20261118_0269_merge_wonderkid_and_outbox
Revises: 20261118_0266_widen_event_outbox_event_id, 20261118_0268_fair_wonderkid_ratings
Create Date: 2026-11-18 02:40:00.000000
"""

revision = "20261118_0269_merge_wonderkid_and_outbox"
down_revision = (
    "20261118_0266_widen_event_outbox_event_id",
    "20261118_0268_fair_wonderkid_ratings",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
