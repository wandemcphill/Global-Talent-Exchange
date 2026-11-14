from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.community_engine import (
    CommunityReaction,
    CommunityUserBlock,
    CompetitionWatchlist,
    LiveThread,
    LiveThreadMessage,
    LiveThreadStatus,
    MessageVisibility,
    PrivateMessage,
    PrivateMessageParticipant,
    PrivateMessageThread,
    PrivateMessageThreadStatus,
)
from app.models.moderation_report import ModerationPriority, ModerationReport
from app.models.user import User


class CommunityEngineError(ValueError):
    pass


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


DISCUSSION_CATEGORIES: tuple[dict[str, str], ...] = (
    {"code": "real_transfer_news", "label": "Real Football Transfer News"},
    {"code": "real_matches", "label": "Real Football Matches"},
    {"code": "gtex_transfer_hub", "label": "GTEX Transfer Hub"},
    {"code": "gtex_competitions", "label": "GTEX Competitions"},
    {"code": "gtex_regens", "label": "GTEX Regens/Newgens"},
    {"code": "club_banter", "label": "Club Banter"},
    {"code": "tactics_room", "label": "Tactics Room"},
    {"code": "area_wars", "label": "Area Wars"},
    {"code": "national_teams", "label": "National Teams"},
    {"code": "player_market_talk", "label": "Player Market Talk"},
    {"code": "manager_room", "label": "Manager Room"},
    {"code": "new_user_help", "label": "Help / New User Questions"},
)


@dataclass(slots=True)
class CommunityEngineService:
    session: Session

    def add_watchlist(
        self,
        *,
        actor: User,
        competition_key: str,
        competition_title: str,
        competition_type: str,
        notify_on_story: bool,
        notify_on_launch: bool,
        metadata_json: dict[str, object],
    ) -> CompetitionWatchlist:
        existing = self.session.scalar(
            select(CompetitionWatchlist).where(
                CompetitionWatchlist.user_id == actor.id, CompetitionWatchlist.competition_key == competition_key
            )
        )
        if existing is not None:
            existing.competition_title = competition_title
            existing.competition_type = competition_type
            existing.notify_on_story = notify_on_story
            existing.notify_on_launch = notify_on_launch
            existing.metadata_json = metadata_json
            self.session.flush()
            return existing
        watch = CompetitionWatchlist(
            user_id=actor.id,
            competition_key=competition_key,
            competition_title=competition_title,
            competition_type=competition_type,
            notify_on_story=notify_on_story,
            notify_on_launch=notify_on_launch,
            metadata_json=metadata_json,
        )
        self.session.add(watch)
        self.session.flush()
        return watch

    def remove_watchlist(self, *, actor: User, competition_key: str) -> None:
        watch = self.session.scalar(
            select(CompetitionWatchlist).where(
                CompetitionWatchlist.user_id == actor.id, CompetitionWatchlist.competition_key == competition_key
            )
        )
        if watch is None:
            raise CommunityEngineError("Watchlist item was not found.")
        self.session.delete(watch)
        self.session.flush()

    def list_watchlist(self, *, actor: User) -> list[CompetitionWatchlist]:
        stmt = (
            select(CompetitionWatchlist)
            .where(CompetitionWatchlist.user_id == actor.id)
            .order_by(CompetitionWatchlist.updated_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def create_live_thread(
        self,
        *,
        actor: User,
        thread_key: str,
        competition_key: str | None,
        title: str,
        pinned: bool,
        metadata_json: dict[str, object],
    ) -> LiveThread:
        thread = LiveThread(
            thread_key=thread_key,
            thread_type="live_thread",
            competition_key=competition_key,
            title=title,
            created_by_user_id=actor.id,
            pinned=pinned,
            metadata_json=metadata_json,
        )
        self.session.add(thread)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise CommunityEngineError("A live thread with that key already exists.") from exc
        return thread

    def list_live_threads(
        self, *, competition_key: str | None = None, include_archived: bool = False
    ) -> list[LiveThread]:
        stmt = select(LiveThread)
        if competition_key:
            stmt = stmt.where(LiveThread.competition_key == competition_key)
        if not include_archived:
            stmt = stmt.where(LiveThread.status != LiveThreadStatus.ARCHIVED)
        stmt = stmt.order_by(
            LiveThread.pinned.desc(), LiveThread.last_message_at.desc().nullslast(), LiveThread.created_at.desc()
        )
        return list(self.session.scalars(stmt).all())

    def get_live_thread(self, *, thread_id: str) -> LiveThread:
        thread = self.session.get(LiveThread, thread_id)
        if thread is None:
            raise CommunityEngineError("Live thread was not found.")
        return thread

    def post_live_thread_message(
        self, *, actor: User, thread_id: str, body: str, metadata_json: dict[str, object]
    ) -> LiveThreadMessage:
        thread = self.get_live_thread(thread_id=thread_id)
        if thread.status != LiveThreadStatus.OPEN:
            raise CommunityEngineError("Live thread is not open for comments.")
        visibility = MessageVisibility.MOD_REVIEW if self._needs_review(body) else MessageVisibility.PUBLIC
        message = LiveThreadMessage(
            thread_id=thread.id,
            author_user_id=actor.id,
            body=body,
            message_type="message",
            visibility=visibility,
            metadata_json=metadata_json,
        )
        self.session.add(message)
        thread.last_message_at = datetime.now(UTC)
        self.session.flush()
        return message

    def list_live_thread_messages(self, *, thread_id: str) -> list[LiveThreadMessage]:
        self.get_live_thread(thread_id=thread_id)
        stmt = (
            select(LiveThreadMessage)
            .where(LiveThreadMessage.thread_id == thread_id, LiveThreadMessage.visibility != MessageVisibility.HIDDEN)
            .order_by(LiveThreadMessage.created_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def create_private_thread(
        self,
        *,
        actor: User,
        participant_user_ids: list[str],
        subject: str,
        initial_message: str,
        metadata_json: dict[str, object],
    ) -> PrivateMessageThread:
        participant_ids = sorted({item for item in participant_user_ids if item and item != actor.id})
        if not participant_ids:
            raise CommunityEngineError("At least one other participant is required.")
        missing = self._missing_user_ids(participant_ids)
        if missing:
            raise CommunityEngineError(f"Unknown participant user: {missing[0]}.")
        for user_id in participant_ids:
            if self._is_blocked_between(actor.id, user_id):
                raise CommunityEngineError("A participant has blocked this conversation.")
        thread = PrivateMessageThread(
            thread_key=f"pm-{actor.id[:6]}-{uuid4().hex[:12]}",
            created_by_user_id=actor.id,
            subject=subject,
            is_group=len(participant_ids) > 1,
            last_message_seq=1,
            metadata_json=metadata_json,
        )
        self.session.add(thread)
        self.session.flush()
        now = datetime.now(UTC)
        participants = [actor.id, *participant_ids]
        for user_id in participants:
            is_creator = user_id == actor.id
            self.session.add(
                PrivateMessageParticipant(
                    thread_id=thread.id,
                    user_id=user_id,
                    last_read_at=now if is_creator else None,
                    metadata_json=(
                        {"last_read_seq": 1, "last_read_seq_at": now.isoformat()}
                        if is_creator
                        else {"last_read_seq": 0}
                    ),
                )
            )
        message = PrivateMessage(
            thread_id=thread.id,
            seq=1,
            sender_user_id=actor.id,
            body=initial_message,
            created_at=now,
            metadata_json={"kind": "initial", **metadata_json},
        )
        self.session.add(message)
        thread.last_message_at = now
        self.session.flush()
        try:
            from app.realtime.service import RealtimeDispatch, get_global_realtime_hub

            hub = get_global_realtime_hub()
            if hub is not None:
                hub.publish_direct_sync(
                    RealtimeDispatch(
                        type="pm_thread_created",
                        topics=tuple(f"user:{uid}" for uid in participant_ids),
                        data={"thread_id": thread.id, "subject": thread.subject, "sender_user_id": actor.id},
                    )
                )
        except Exception:
            pass
        return thread

    def list_private_threads(self, *, actor: User) -> list[PrivateMessageThread]:
        stmt = (
            select(PrivateMessageThread)
            .join(PrivateMessageParticipant, PrivateMessageParticipant.thread_id == PrivateMessageThread.id)
            .where(
                PrivateMessageParticipant.user_id == actor.id,
                PrivateMessageParticipant.left_at.is_(None),
                PrivateMessageThread.status != PrivateMessageThreadStatus.ARCHIVED,
            )
            .order_by(PrivateMessageThread.last_message_at.desc().nullslast(), PrivateMessageThread.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def _require_active_participant(
        self, *, actor: User, thread_id: str
    ) -> tuple[PrivateMessageThread, PrivateMessageParticipant]:
        thread = self.session.get(PrivateMessageThread, thread_id)
        if thread is None:
            raise CommunityEngineError("Private thread was not found.")
        membership = self.session.scalar(
            select(PrivateMessageParticipant).where(
                PrivateMessageParticipant.thread_id == thread_id,
                PrivateMessageParticipant.user_id == actor.id,
            )
        )
        if membership is None:
            raise CommunityEngineError("You are not a participant in this thread.")
        if membership.left_at is not None:
            raise CommunityEngineError("You have left this conversation.")
        return thread, membership

    def _visible_thread_messages(self, *, thread_id: str) -> list[PrivateMessage]:
        stmt = (
            select(PrivateMessage)
            .where(PrivateMessage.thread_id == thread_id, PrivateMessage.visibility != MessageVisibility.HIDDEN)
            .order_by(PrivateMessage.seq.asc(), PrivateMessage.created_at.asc(), PrivateMessage.id.asc())
        )
        return list(self.session.scalars(stmt).all())

    def _effective_participant_read_seq(
        self,
        *,
        participant: PrivateMessageParticipant,
        messages: list[PrivateMessage] | None = None,
    ) -> int:
        meta = dict(participant.metadata_json or {})
        if "last_read_seq" in meta and meta["last_read_seq"] is not None:
            try:
                return max(0, int(meta["last_read_seq"]))
            except (TypeError, ValueError):
                pass
        if participant.last_read_at is None:
            return 0
        read_at = _as_utc(participant.last_read_at)
        if read_at is None:
            return 0
        visible = messages if messages is not None else self._visible_thread_messages(thread_id=participant.thread_id)
        max_seq = 0
        for msg in visible:
            msg_ts = _as_utc(msg.created_at)
            if msg_ts is not None and msg_ts <= read_at:
                max_seq = max(max_seq, int(msg.seq or 0))
        return max_seq

    def calculate_thread_unread_state(
        self,
        *,
        thread: PrivateMessageThread,
        actor_id: str,
    ) -> dict[str, object]:
        participant = self.session.scalar(
            select(PrivateMessageParticipant).where(
                PrivateMessageParticipant.thread_id == thread.id,
                PrivateMessageParticipant.user_id == actor_id,
            )
        )
        if participant is None or participant.left_at is not None:
            return {
                "unread_count": 0,
                "last_read_seq": int(participant.last_read_seq or 0) if participant is not None else 0,
                "last_read_at": participant.last_read_at if participant is not None else None,
            }
        messages = self._visible_thread_messages(thread_id=thread.id)
        read_seq = self._effective_participant_read_seq(participant=participant, messages=messages)
        unread_messages = [m for m in messages if m.sender_user_id != actor_id and int(m.seq or 0) > read_seq]
        return {
            "unread_count": int(len(unread_messages)),
            "last_read_seq": int(read_seq),
            "last_read_at": participant.last_read_at,
        }

    def get_private_thread(self, *, actor: User, thread_id: str) -> PrivateMessageThread:
        return self.mark_private_thread_read(actor=actor, thread_id=thread_id)

    def mark_private_thread_read(
        self,
        *,
        actor: User,
        thread_id: str,
        up_to_seq: int | None = None,
        up_to_message_id: str | None = None,
    ) -> PrivateMessageThread:
        thread, membership = self._require_active_participant(actor=actor, thread_id=thread_id)
        messages = self._visible_thread_messages(thread_id=thread_id)
        current_seq = self._effective_participant_read_seq(participant=membership, messages=messages)
        max_thread_seq = max((int(m.seq or 0) for m in messages), default=int(thread.last_message_seq or 0))

        target_seq: int
        if up_to_message_id is not None:
            target_msg = next((m for m in messages if m.id == up_to_message_id), None)
            if target_msg is None:
                msg_row = self.session.get(PrivateMessage, up_to_message_id)
                if msg_row is None or msg_row.thread_id != thread_id or msg_row.visibility == MessageVisibility.HIDDEN:
                    raise CommunityEngineError("Message was not found in this thread.")
                target_msg = msg_row
            target_seq = int(target_msg.seq or 0)
            if up_to_seq is not None:
                target_seq = min(target_seq, max(0, int(up_to_seq)))
        elif up_to_seq is not None:
            target_seq = min(max(0, int(up_to_seq)), max_thread_seq)
        else:
            target_seq = max_thread_seq

        new_seq = max(current_seq, target_seq)
        ack_msg = None
        for msg in messages:
            if int(msg.seq or 0) <= new_seq:
                ack_msg = msg

        has_explicit_seq = "last_read_seq" in dict(membership.metadata_json or {})
        if new_seq > current_seq or membership.last_read_at is None or not has_explicit_seq:
            membership.last_read_seq = new_seq
            if ack_msg is not None and ack_msg.created_at is not None:
                ack_ts = _as_utc(ack_msg.created_at) or datetime.now(UTC)
                if new_seq >= max_thread_seq and thread.last_message_at is not None:
                    thread_ts = _as_utc(thread.last_message_at)
                    if thread_ts is not None and thread_ts > ack_ts:
                        ack_ts = thread_ts
                current_read_at = _as_utc(membership.last_read_at)
                if current_read_at is None or current_read_at < ack_ts:
                    membership.last_read_at = ack_ts
            elif membership.last_read_at is None:
                membership.last_read_at = _as_utc(thread.last_message_at or thread.created_at) or datetime.now(UTC)
            self.session.flush()
            if new_seq > current_seq:
                try:
                    from app.realtime.service import RealtimeDispatch, get_global_realtime_hub

                    hub = get_global_realtime_hub()
                    if hub is not None:
                        hub.publish_direct_sync(
                            RealtimeDispatch(
                                type="pm_read",
                                topics=(f"user:{actor.id}",),
                                data={
                                    "thread_id": thread.id,
                                    "user_id": actor.id,
                                    "last_read_seq": new_seq,
                                    "last_read_at": (
                                        membership.last_read_at.isoformat() if membership.last_read_at else None
                                    ),
                                },
                            )
                        )
                except Exception:
                    pass
        return thread

    def mute_private_thread(self, *, actor: User, thread_id: str, muted: bool = True) -> PrivateMessageParticipant:
        _, participant = self._require_active_participant(actor=actor, thread_id=thread_id)
        participant.is_muted = muted
        self.session.flush()
        return participant

    def list_private_thread_participants(
        self, *, thread_id: str, active_only: bool = True
    ) -> list[PrivateMessageParticipant]:
        stmt = select(PrivateMessageParticipant).where(PrivateMessageParticipant.thread_id == thread_id)
        if active_only:
            stmt = stmt.where(PrivateMessageParticipant.left_at.is_(None))
        stmt = stmt.order_by(PrivateMessageParticipant.joined_at.asc())
        return list(self.session.scalars(stmt).all())

    def list_private_messages(self, *, actor: User, thread_id: str) -> list[PrivateMessage]:
        self._require_active_participant(actor=actor, thread_id=thread_id)
        return self._visible_thread_messages(thread_id=thread_id)

    def post_private_message(
        self, *, actor: User, thread_id: str, body: str, metadata_json: dict[str, object]
    ) -> PrivateMessage:
        thread, sender_membership = self._require_active_participant(actor=actor, thread_id=thread_id)
        if thread.status != PrivateMessageThreadStatus.ACTIVE:
            if thread.status == PrivateMessageThreadStatus.BLOCKED:
                raise CommunityEngineError("Private thread is blocked.")
            raise CommunityEngineError("Private thread is not active.")
        participants = self.list_private_thread_participants(thread_id=thread_id, active_only=True)
        for participant in participants:
            if participant.user_id != actor.id and self._is_blocked_between(actor.id, participant.user_id):
                raise CommunityEngineError("A participant has blocked this conversation.")
        prior_messages = self._visible_thread_messages(thread_id=thread_id)
        prior_read_seq = self._effective_participant_read_seq(participant=sender_membership, messages=prior_messages)
        has_unread_from_others = any(
            m.sender_user_id != actor.id and int(m.seq or 0) > prior_read_seq for m in prior_messages
        )
        now = datetime.now(UTC)
        next_seq = int(getattr(thread, "last_message_seq", 0) or 0) + 1
        message = PrivateMessage(
            thread_id=thread.id,
            seq=next_seq,
            sender_user_id=actor.id,
            body=body,
            created_at=now,
            metadata_json=metadata_json,
        )
        self.session.add(message)
        thread.last_message_seq = next_seq
        thread.last_message_at = now
        if not has_unread_from_others:
            sender_membership.last_read_seq = next_seq
            sender_membership.last_read_at = now
        self.session.flush()
        try:
            from app.realtime.service import RealtimeDispatch, get_global_realtime_hub

            hub = get_global_realtime_hub()
            if hub is not None:
                msg_data = {
                    "id": message.id,
                    "thread_id": thread.id,
                    "seq": next_seq,
                    "sender_user_id": actor.id,
                    "body": body,
                    "created_at": message.created_at.isoformat() if message.created_at else None,
                }
                hub.publish_direct_sync(
                    RealtimeDispatch(
                        type="pm_message",
                        topics=(
                            f"pm:{thread.id}",
                            *[f"user:{p.user_id}" for p in participants if p.user_id != actor.id],
                        ),
                        data=msg_data,
                    )
                )
        except Exception:
            pass
        return message

    def block_user(self, *, actor: User, target_user_id: str, reason: str | None = None) -> CommunityUserBlock:
        if target_user_id == actor.id:
            raise CommunityEngineError("You cannot block yourself.")
        if self.session.get(User, target_user_id) is None:
            raise CommunityEngineError("Blocked user was not found.")
        existing = self.session.scalar(
            select(CommunityUserBlock).where(
                CommunityUserBlock.blocker_user_id == actor.id,
                CommunityUserBlock.blocked_user_id == target_user_id,
            )
        )
        if existing is not None:
            return existing
        block = CommunityUserBlock(blocker_user_id=actor.id, blocked_user_id=target_user_id, reason=reason)
        self.session.add(block)
        self._block_dm_threads_between(actor.id, target_user_id)
        self.session.flush()
        return block

    def report_private_message(
        self,
        *,
        actor: User,
        message_id: str,
        reason_code: str,
        description: str,
    ) -> ModerationReport:
        message = self.session.get(PrivateMessage, message_id)
        if message is None:
            raise CommunityEngineError("Message was not found.")
        self._require_active_participant(actor=actor, thread_id=message.thread_id)
        return self._create_report(
            reporter=actor,
            target_type="chat_message",
            target_id=message.id,
            reason_code=reason_code,
            description=description,
            subject_user_id=message.sender_user_id,
        )

    def hide_private_message(self, *, message_id: str) -> PrivateMessage:
        message = self.session.get(PrivateMessage, message_id)
        if message is None:
            raise CommunityEngineError("Message was not found.")
        message.visibility = MessageVisibility.HIDDEN
        self.session.flush()
        return message

    def discussion_categories(self) -> list[dict[str, str]]:
        return list(DISCUSSION_CATEGORIES)

    def create_discussion_thread(
        self,
        *,
        actor: User,
        category: str,
        title: str,
        body: str,
        metadata_json: dict[str, object],
    ) -> LiveThread:
        self._validate_discussion_category(category)
        thread = LiveThread(
            thread_key=f"discussion-{uuid4().hex}",
            thread_type="discussion",
            category=category,
            title=title,
            body=body,
            created_by_user_id=actor.id,
            metadata_json=metadata_json,
        )
        self.session.add(thread)
        self.session.flush()
        return thread

    def list_discussion_threads(
        self,
        *,
        category: str | None = None,
        include_locked: bool = True,
    ) -> list[LiveThread]:
        stmt = select(LiveThread).where(
            LiveThread.thread_type == "discussion",
            LiveThread.status != LiveThreadStatus.ARCHIVED,
            LiveThread.moderation_status != "hidden",
        )
        if category:
            self._validate_discussion_category(category)
            stmt = stmt.where(LiveThread.category == category)
        if not include_locked:
            stmt = stmt.where(LiveThread.status == LiveThreadStatus.OPEN)
        stmt = stmt.order_by(
            LiveThread.pinned.desc(),
            LiveThread.trend_score.desc(),
            LiveThread.last_message_at.desc().nullslast(),
            LiveThread.created_at.desc(),
        )
        return list(self.session.scalars(stmt).all())

    def get_discussion_thread(self, *, thread_id: str) -> LiveThread:
        thread = self.get_live_thread(thread_id=thread_id)
        if thread.thread_type != "discussion" or thread.moderation_status == "hidden":
            raise CommunityEngineError("Discussion thread was not found.")
        return thread

    def list_discussion_replies(self, *, thread_id: str) -> list[LiveThreadMessage]:
        self.get_discussion_thread(thread_id=thread_id)
        stmt = (
            select(LiveThreadMessage)
            .where(
                LiveThreadMessage.thread_id == thread_id,
                LiveThreadMessage.visibility != MessageVisibility.HIDDEN,
                LiveThreadMessage.moderation_status != "hidden",
            )
            .order_by(LiveThreadMessage.created_at.asc(), LiveThreadMessage.id.asc())
        )
        return list(self.session.scalars(stmt).all())

    def post_discussion_reply(
        self,
        *,
        actor: User,
        thread_id: str,
        body: str,
        parent_reply_id: str | None,
        metadata_json: dict[str, object],
    ) -> LiveThreadMessage:
        thread = self.get_discussion_thread(thread_id=thread_id)
        if thread.status != LiveThreadStatus.OPEN:
            raise CommunityEngineError("Discussion thread is locked.")
        if parent_reply_id is not None:
            parent = self.session.get(LiveThreadMessage, parent_reply_id)
            if parent is None or parent.thread_id != thread_id:
                raise CommunityEngineError("Parent reply was not found.")
        visibility = MessageVisibility.MOD_REVIEW if self._needs_review(body) else MessageVisibility.PUBLIC
        reply = LiveThreadMessage(
            thread_id=thread.id,
            author_user_id=actor.id,
            parent_message_id=parent_reply_id,
            message_type="reply",
            body=body,
            visibility=visibility,
            metadata_json=metadata_json,
        )
        self.session.add(reply)
        thread.last_message_at = datetime.now(UTC)
        thread.trend_score += 1
        self.session.flush()
        if parent_reply_id is not None:
            parent = self.session.get(LiveThreadMessage, parent_reply_id)
            if parent is not None:
                parent.reply_count += 1
                self.session.flush()
        return reply

    def react_to_discussion_entity(
        self,
        *,
        actor: User,
        entity_type: str,
        entity_id: str,
        reaction_type: str,
    ) -> CommunityReaction:
        if entity_type not in {"thread", "reply"}:
            raise CommunityEngineError("Unsupported reaction target.")
        target = (
            self.get_discussion_thread(thread_id=entity_id)
            if entity_type == "thread"
            else self.session.get(LiveThreadMessage, entity_id)
        )
        if target is None:
            raise CommunityEngineError("Reaction target was not found.")
        if entity_type == "reply":
            self.get_discussion_thread(thread_id=target.thread_id)
        existing = self.session.scalar(
            select(CommunityReaction).where(
                CommunityReaction.entity_type == entity_type,
                CommunityReaction.entity_id == entity_id,
                CommunityReaction.user_id == actor.id,
                CommunityReaction.reaction_type == reaction_type,
            )
        )
        if existing is not None:
            return existing
        reaction = CommunityReaction(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=actor.id,
            reaction_type=reaction_type,
        )
        self.session.add(reaction)
        if entity_type == "reply":
            target.like_count += 1
            thread = self.session.get(LiveThread, target.thread_id)
            if thread is not None:
                thread.trend_score += 1
        else:
            target.trend_score += 1
        self.session.flush()
        return reaction

    def report_discussion_thread(
        self,
        *,
        actor: User,
        thread_id: str,
        reason_code: str,
        description: str,
    ) -> ModerationReport:
        thread = self.get_discussion_thread(thread_id=thread_id)
        return self._create_report(
            reporter=actor,
            target_type="discussion_thread",
            target_id=thread.id,
            reason_code=reason_code,
            description=description,
            subject_user_id=thread.created_by_user_id,
        )

    def report_discussion_reply(
        self,
        *,
        actor: User,
        reply_id: str,
        reason_code: str,
        description: str,
    ) -> ModerationReport:
        reply = self.session.get(LiveThreadMessage, reply_id)
        if reply is None:
            raise CommunityEngineError("Discussion reply was not found.")
        self.get_discussion_thread(thread_id=reply.thread_id)
        return self._create_report(
            reporter=actor,
            target_type="discussion_reply",
            target_id=reply.id,
            reason_code=reason_code,
            description=description,
            subject_user_id=reply.author_user_id,
        )

    def lock_discussion_thread(self, *, actor: User, thread_id: str) -> LiveThread:
        thread = self.get_discussion_thread(thread_id=thread_id)
        thread.status = LiveThreadStatus.LOCKED
        thread.locked_by_user_id = actor.id
        thread.locked_at = datetime.now(UTC)
        self.session.flush()
        return thread

    def hide_discussion_reply(self, *, reply_id: str) -> LiveThreadMessage:
        reply = self.session.get(LiveThreadMessage, reply_id)
        if reply is None:
            raise CommunityEngineError("Discussion reply was not found.")
        reply.visibility = MessageVisibility.HIDDEN
        reply.moderation_status = "hidden"
        self.session.flush()
        return reply

    def list_reports(self, *, target_types: set[str]) -> list[ModerationReport]:
        stmt = (
            select(ModerationReport)
            .where(ModerationReport.target_type.in_(target_types))
            .order_by(ModerationReport.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def digest(self, *, actor: User) -> dict[str, int]:
        watchlist_count = (
            self.session.scalar(
                select(func.count(CompetitionWatchlist.id)).where(CompetitionWatchlist.user_id == actor.id)
            )
            or 0
        )
        active_threads = self.list_private_threads(actor=actor)
        private_thread_count = len(active_threads)
        live_thread_count = (
            self.session.scalar(select(func.count(LiveThread.id)).where(LiveThread.status != LiveThreadStatus.ARCHIVED))
            or 0
        )
        unread_hint_count = sum(
            int(self.calculate_thread_unread_state(thread=thread, actor_id=actor.id)["unread_count"])
            for thread in active_threads
        )
        return {
            "watchlist_count": int(watchlist_count),
            "live_thread_count": int(live_thread_count),
            "private_thread_count": int(private_thread_count),
            "unread_hint_count": int(unread_hint_count),
        }

    def _missing_user_ids(self, user_ids: list[str]) -> list[str]:
        if not user_ids:
            return []
        existing = set(self.session.scalars(select(User.id).where(User.id.in_(user_ids))).all())
        return [user_id for user_id in user_ids if user_id not in existing]

    def _is_blocked_between(self, user_a_id: str, user_b_id: str) -> bool:
        block = self.session.scalar(
            select(CommunityUserBlock.id).where(
                or_(
                    (CommunityUserBlock.blocker_user_id == user_a_id)
                    & (CommunityUserBlock.blocked_user_id == user_b_id),
                    (CommunityUserBlock.blocker_user_id == user_b_id)
                    & (CommunityUserBlock.blocked_user_id == user_a_id),
                )
            )
        )
        return block is not None

    def _block_dm_threads_between(self, user_a_id: str, user_b_id: str) -> None:
        user_a_thread_ids = select(PrivateMessageParticipant.thread_id).where(
            PrivateMessageParticipant.user_id == user_a_id
        )
        user_b_thread_ids = select(PrivateMessageParticipant.thread_id).where(
            PrivateMessageParticipant.user_id == user_b_id,
            PrivateMessageParticipant.thread_id.in_(user_a_thread_ids),
        )
        threads = self.session.scalars(
            select(PrivateMessageThread).where(PrivateMessageThread.id.in_(user_b_thread_ids))
        ).all()
        for thread in threads:
            thread.status = PrivateMessageThreadStatus.BLOCKED

    def _create_report(
        self,
        *,
        reporter: User,
        target_type: str,
        target_id: str,
        reason_code: str,
        description: str,
        subject_user_id: str | None,
    ) -> ModerationReport:
        existing = self.session.scalar(
            select(ModerationReport).where(
                ModerationReport.reporter_user_id == reporter.id,
                ModerationReport.target_type == target_type,
                ModerationReport.target_id == target_id,
                ModerationReport.reason_code == reason_code,
            )
        )
        if existing is not None:
            existing.report_count_for_target += 1
            self.session.flush()
            return existing
        report = ModerationReport(
            reporter_user_id=reporter.id,
            subject_user_id=subject_user_id,
            target_type=target_type,
            target_id=target_id,
            reason_code=reason_code,
            description=description,
            priority=ModerationPriority.NORMAL,
        )
        self.session.add(report)
        self.session.flush()
        return report

    @staticmethod
    def _validate_discussion_category(category: str) -> None:
        if category not in {item["code"] for item in DISCUSSION_CATEGORIES}:
            raise CommunityEngineError("Unsupported discussion category.")

    @staticmethod
    def _needs_review(body: str) -> bool:
        lowered = body.lower()
        review_terms = ("fix match", "scam", "fraud", "rigged", "cashapp", "telegram")
        return any(term in lowered for term in review_terms)
