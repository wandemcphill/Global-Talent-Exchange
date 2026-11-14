"""Community platform overhaul and durable Owner Inbox communications tables.

Revision ID: 20261113_0243_community_and_owner_comms_overhaul
Revises: 20261113_0242_missing_all_time_legends
Create Date: 2026-11-13 21:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session

revision = "20261113_0243_community_and_owner_comms_overhaul"
down_revision = "20261113_0242_missing_all_time_legends"
branch_labels = None
depends_on = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name) if idx.get("name")}


def upgrade() -> None:
    from app.models.community_social import (
        CommunityBookmark,
        CommunityChannel,
        CommunityChannelMessage,
        CommunityCompetitionApplication,
        CommunityPollVote,
        CommunityPost,
        CommunityPostComment,
        CommunityUserMute,
    )
    from app.owner_console.models import (
        OwnerClubAnnouncement,
        OwnerClubConversation,
        OwnerClubMeeting,
        OwnerClubMessage,
        OwnerClubState,
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for model in (
        CommunityChannel,
        CommunityChannelMessage,
        CommunityPost,
        CommunityPostComment,
        CommunityBookmark,
        CommunityPollVote,
        CommunityUserMute,
        CommunityCompetitionApplication,
        OwnerClubConversation,
        OwnerClubMessage,
        OwnerClubMeeting,
        OwnerClubAnnouncement,
    ):
        model.__table__.create(bind, checkfirst=True)

    # Extend existing private_message_* tables safely
    pm_thread_cols = _column_names(inspector, "private_message_threads")
    if pm_thread_cols:
        with op.batch_alter_table("private_message_threads") as batch_op:
            if "is_group" not in pm_thread_cols:
                batch_op.add_column(sa.Column("is_group", sa.Boolean(), nullable=False, server_default=sa.false()))
            if "last_message_seq" not in pm_thread_cols:
                batch_op.add_column(sa.Column("last_message_seq", sa.Integer(), nullable=False, server_default="0"))

    pm_part_cols = _column_names(inspector, "private_message_participants")
    if pm_part_cols and "left_at" not in pm_part_cols:
        with op.batch_alter_table("private_message_participants") as batch_op:
            batch_op.add_column(sa.Column("left_at", sa.DateTime(timezone=True), nullable=True))

    pm_cols = _column_names(inspector, "private_messages")
    if pm_cols:
        with op.batch_alter_table("private_messages") as batch_op:
            if "seq" not in pm_cols:
                batch_op.add_column(sa.Column("seq", sa.Integer(), nullable=False, server_default="0"))
            if "reply_to_message_id" not in pm_cols:
                batch_op.add_column(sa.Column("reply_to_message_id", sa.String(length=36), nullable=True))
            if "mentions_json" not in pm_cols:
                batch_op.add_column(
                    sa.Column("mentions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
                )
        inspector = sa.inspect(bind)
        if "ix_private_messages_thread_seq" not in _index_names(inspector, "private_messages"):
            op.create_index("ix_private_messages_thread_seq", "private_messages", ["thread_id", "seq"], unique=False)

    # Idempotent data backfill inside ORM session
    session = Session(bind=bind)
    try:
        from app.models.community_engine import PrivateMessage, PrivateMessageParticipant, PrivateMessageThread
        from app.owner_console.comms_persistence import backfill_legacy_club_communications

        threads = list(session.scalars(sa.select(PrivateMessageThread)).all())
        for thread in threads:
            part_count = int(
                session.scalar(
                    sa.select(sa.func.count(PrivateMessageParticipant.id)).where(
                        PrivateMessageParticipant.thread_id == thread.id
                    )
                )
                or 0
            )
            if part_count > 2:
                thread.is_group = True
            msgs = list(
                session.scalars(
                    sa.select(PrivateMessage)
                    .where(PrivateMessage.thread_id == thread.id)
                    .order_by(PrivateMessage.created_at.asc(), PrivateMessage.id.asc())
                ).all()
            )
            seq_num = 0
            for msg in msgs:
                seq_num += 1
                if int(msg.seq or 0) == 0:
                    msg.seq = seq_num
                else:
                    seq_num = max(seq_num, int(msg.seq))
            thread.last_message_seq = max(int(thread.last_message_seq or 0), seq_num)

        if inspector.has_table("owner_club_states"):
            states = list(session.scalars(sa.select(OwnerClubState)).all())
            for st in states:
                backfill_legacy_club_communications(session, st)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def downgrade() -> None:
    from app.models.community_social import (
        CommunityBookmark,
        CommunityChannel,
        CommunityChannelMessage,
        CommunityCompetitionApplication,
        CommunityPollVote,
        CommunityPost,
        CommunityPostComment,
        CommunityUserMute,
    )
    from app.owner_console.models import (
        OwnerClubAnnouncement,
        OwnerClubConversation,
        OwnerClubMeeting,
        OwnerClubMessage,
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "ix_private_messages_thread_seq" in _index_names(inspector, "private_messages"):
        op.drop_index("ix_private_messages_thread_seq", table_name="private_messages")

    pm_cols = _column_names(inspector, "private_messages")
    if pm_cols:
        with op.batch_alter_table("private_messages") as batch_op:
            for col in ("mentions_json", "reply_to_message_id", "seq"):
                if col in pm_cols:
                    batch_op.drop_column(col)

    pm_part_cols = _column_names(inspector, "private_message_participants")
    if pm_part_cols and "left_at" in pm_part_cols:
        with op.batch_alter_table("private_message_participants") as batch_op:
            batch_op.drop_column("left_at")

    pm_thread_cols = _column_names(inspector, "private_message_threads")
    if pm_thread_cols:
        with op.batch_alter_table("private_message_threads") as batch_op:
            for col in ("last_message_seq", "is_group"):
                if col in pm_thread_cols:
                    batch_op.drop_column(col)

    for model in (
        OwnerClubAnnouncement,
        OwnerClubMeeting,
        OwnerClubMessage,
        OwnerClubConversation,
        CommunityCompetitionApplication,
        CommunityUserMute,
        CommunityPollVote,
        CommunityBookmark,
        CommunityPostComment,
        CommunityPost,
        CommunityChannelMessage,
        CommunityChannel,
    ):
        model.__table__.drop(bind, checkfirst=True)
