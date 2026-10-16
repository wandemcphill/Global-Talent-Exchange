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
            metadata_json=metadata_json,
        )
        self.session.add(thread)
        self.session.flush()
        participants = [actor.id, *participant_ids]
        for user_id in participants:
            self.session.add(PrivateMessageParticipant(thread_id=thread.id, user_id=user_id))
        message = PrivateMessage(
            thread_id=thread.id,
            sender_user_id=actor.id,
            body=initial_message,
            metadata_json={"kind": "initial", **metadata_json},
        )
        self.session.add(message)
        thread.last_message_at = datetime.now(UTC)
        self.session.flush()
        return thread

    def list_private_threads(self, *, actor: User) -> list[PrivateMessageThread]:
        stmt = (
            select(PrivateMessageThread)
            .join(PrivateMessageParticipant, PrivateMessageParticipant.thread_id == PrivateMessageThread.id)
            .where(
                PrivateMessageParticipant.user_id == actor.id,
                PrivateMessageThread.status != PrivateMessageThreadStatus.ARCHIVED,
            )
            .order_by(PrivateMessageThread.last_message_at.desc().nullslast(), PrivateMessageThread.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_private_thread(self, *, actor: User, thread_id: str) -> PrivateMessageThread:
        thread = self.session.get(PrivateMessageThread, thread_id)
        if thread is None:
            raise CommunityEngineError("Private thread was not found.")
        membership = self.session.scalar(
            select(PrivateMessageParticipant).where(
                PrivateMessageParticipant.thread_id == thread_id, PrivateMessageParticipant.user_id == actor.id
            )
        )
        if membership is None:
            raise CommunityEngineError("You are not a participant in this thread.")
        membership.last_read_at = datetime.now(UTC)
        self.session.flush()
        return thread

    def mark_private_thread_read(self, *, actor: User, thread_id: str) -> PrivateMessageThread:
        return self.get_private_thread(actor=actor, thread_id=thread_id)

    def mute_private_thread(self, *, actor: User, thread_id: str, muted: bool = True) -> PrivateMessageParticipant:
        self.get_private_thread(actor=actor, thread_id=thread_id)
        participant = self.session.scalar(
            select(PrivateMessageParticipant).where(
                PrivateMessageParticipant.thread_id == thread_id,
                PrivateMessageParticipant.user_id == actor.id,
            )
        )
        if participant is None:
            raise CommunityEngineError("You are not a participant in this thread.")
        participant.is_muted = muted
        self.session.flush()
        return participant

    def list_private_thread_participants(self, *, thread_id: str) -> list[PrivateMessageParticipant]:
        stmt = (
            select(PrivateMessageParticipant)
            .where(PrivateMessageParticipant.thread_id == thread_id)
            .order_by(PrivateMessageParticipant.joined_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def list_private_messages(self, *, actor: User, thread_id: str) -> list[PrivateMessage]:
        self.get_private_thread(actor=actor, thread_id=thread_id)
        stmt = (
            select(PrivateMessage)
            .where(PrivateMessage.thread_id == thread_id, PrivateMessage.visibility != MessageVisibility.HIDDEN)
            .order_by(PrivateMessage.created_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def post_private_message(
        self, *, actor: User, thread_id: str, body: str, metadata_json: dict[str, object]
    ) -> PrivateMessage:
        thread = self.get_private_thread(actor=actor, thread_id=thread_id)
        if thread.status != PrivateMessageThreadStatus.ACTIVE:
            if thread.status == PrivateMessageThreadStatus.BLOCKED:
                raise CommunityEngineError("Private thread is blocked.")
            raise CommunityEngineError("Private thread is not active.")
        participants = self.list_private_thread_participants(thread_id=thread_id)
        for participant in participants:
            if participant.user_id != actor.id and self._is_blocked_between(actor.id, participant.user_id):
                raise CommunityEngineError("A participant has blocked this conversation.")
        message = PrivateMessage(thread_id=thread.id, sender_user_id=actor.id, body=body, metadata_json=metadata_json)
        self.session.add(message)
        thread.last_message_at = datetime.now(UTC)
        self.session.flush()
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
        self.get_private_thread(actor=actor, thread_id=message.thread_id)
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
        private_thread_count = (
            self.session.scalar(
                select(func.count(PrivateMessageParticipant.id)).where(PrivateMessageParticipant.user_id == actor.id)
            )
            or 0
        )
        live_thread_count = (
            self.session.scalar(select(func.count(LiveThread.id)).where(LiveThread.status != LiveThreadStatus.ARCHIVED))
            or 0
        )
        unread_hint_count = (
            self.session.scalar(
                select(func.count(PrivateMessageThread.id))
                .join(PrivateMessageParticipant, PrivateMessageParticipant.thread_id == PrivateMessageThread.id)
                .where(
                    PrivateMessageParticipant.user_id == actor.id,
                    or_(
                        PrivateMessageParticipant.last_read_at.is_(None),
                        PrivateMessageThread.last_message_at > PrivateMessageParticipant.last_read_at,
                    ),
                )
            )
            or 0
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
