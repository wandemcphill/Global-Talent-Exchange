from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.community_engine import (
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
from backend.app.models.user import User


class CommunityEngineError(ValueError):
    pass


@dataclass(slots=True)
class CommunityEngineService:
    session: Session

    def add_watchlist(self, *, actor: User, competition_key: str, competition_title: str, competition_type: str, notify_on_story: bool, notify_on_launch: bool, metadata_json: dict[str, object]) -> CompetitionWatchlist:
        existing = self.session.scalar(select(CompetitionWatchlist).where(CompetitionWatchlist.user_id == actor.id, CompetitionWatchlist.competition_key == competition_key))
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
        watch = self.session.scalar(select(CompetitionWatchlist).where(CompetitionWatchlist.user_id == actor.id, CompetitionWatchlist.competition_key == competition_key))
        if watch is None:
            raise CommunityEngineError('Watchlist item was not found.')
        self.session.delete(watch)
        self.session.flush()

    def list_watchlist(self, *, actor: User) -> list[CompetitionWatchlist]:
        stmt = select(CompetitionWatchlist).where(CompetitionWatchlist.user_id == actor.id).order_by(CompetitionWatchlist.updated_at.desc())
        return list(self.session.scalars(stmt).all())

    def create_live_thread(self, *, actor: User, thread_key: str, competition_key: str | None, title: str, pinned: bool, metadata_json: dict[str, object]) -> LiveThread:
        thread = LiveThread(thread_key=thread_key, competition_key=competition_key, title=title, created_by_user_id=actor.id, pinned=pinned, metadata_json=metadata_json)
        self.session.add(thread)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise CommunityEngineError('A live thread with that key already exists.') from exc
        return thread

    def list_live_threads(self, *, competition_key: str | None = None, include_archived: bool = False) -> list[LiveThread]:
        stmt = select(LiveThread)
        if competition_key:
            stmt = stmt.where(LiveThread.competition_key == competition_key)
        if not include_archived:
            stmt = stmt.where(LiveThread.status != LiveThreadStatus.ARCHIVED)
        stmt = stmt.order_by(LiveThread.pinned.desc(), LiveThread.last_message_at.desc().nullslast(), LiveThread.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def get_live_thread(self, *, thread_id: str) -> LiveThread:
        thread = self.session.get(LiveThread, thread_id)
        if thread is None:
            raise CommunityEngineError('Live thread was not found.')
        return thread

    def post_live_thread_message(self, *, actor: User, thread_id: str, body: str, metadata_json: dict[str, object]) -> LiveThreadMessage:
        thread = self.get_live_thread(thread_id=thread_id)
        if thread.status != LiveThreadStatus.OPEN:
            raise CommunityEngineError('Live thread is not open for comments.')
        visibility = MessageVisibility.MOD_REVIEW if self._needs_review(body) else MessageVisibility.PUBLIC
        message = LiveThreadMessage(thread_id=thread.id, author_user_id=actor.id, body=body, visibility=visibility, metadata_json=metadata_json)
        self.session.add(message)
        thread.last_message_at = datetime.now(UTC)
        self.session.flush()
        return message

    def list_live_thread_messages(self, *, thread_id: str) -> list[LiveThreadMessage]:
        self.get_live_thread(thread_id=thread_id)
        stmt = select(LiveThreadMessage).where(LiveThreadMessage.thread_id == thread_id, LiveThreadMessage.visibility != MessageVisibility.HIDDEN).order_by(LiveThreadMessage.created_at.asc())
        return list(self.session.scalars(stmt).all())

    def create_private_thread(self, *, actor: User, participant_user_ids: list[str], subject: str, initial_message: str, metadata_json: dict[str, object]) -> PrivateMessageThread:
        participant_ids = sorted({item for item in participant_user_ids if item and item != actor.id})
        if not participant_ids:
            raise CommunityEngineError('At least one other participant is required.')
        thread = PrivateMessageThread(thread_key=f'pm-{actor.id[:6]}-{int(datetime.now(UTC).timestamp())}', created_by_user_id=actor.id, subject=subject, metadata_json=metadata_json)
        self.session.add(thread)
        self.session.flush()
        participants = [actor.id, *participant_ids]
        for user_id in participants:
            self.session.add(PrivateMessageParticipant(thread_id=thread.id, user_id=user_id))
        message = PrivateMessage(thread_id=thread.id, sender_user_id=actor.id, body=initial_message, metadata_json={"kind": "initial", **metadata_json})
        self.session.add(message)
        thread.last_message_at = datetime.now(UTC)
        self.session.flush()
        return thread

    def list_private_threads(self, *, actor: User) -> list[PrivateMessageThread]:
        stmt = (
            select(PrivateMessageThread)
            .join(PrivateMessageParticipant, PrivateMessageParticipant.thread_id == PrivateMessageThread.id)
            .where(PrivateMessageParticipant.user_id == actor.id, PrivateMessageThread.status != PrivateMessageThreadStatus.ARCHIVED)
            .order_by(PrivateMessageThread.last_message_at.desc().nullslast(), PrivateMessageThread.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_private_thread(self, *, actor: User, thread_id: str) -> PrivateMessageThread:
        thread = self.session.get(PrivateMessageThread, thread_id)
        if thread is None:
            raise CommunityEngineError('Private thread was not found.')
        membership = self.session.scalar(select(PrivateMessageParticipant).where(PrivateMessageParticipant.thread_id == thread_id, PrivateMessageParticipant.user_id == actor.id))
        if membership is None:
            raise CommunityEngineError('You are not a participant in this thread.')
        membership.last_read_at = datetime.now(UTC)
        self.session.flush()
        return thread

    def list_private_thread_participants(self, *, thread_id: str) -> list[PrivateMessageParticipant]:
        stmt = select(PrivateMessageParticipant).where(PrivateMessageParticipant.thread_id == thread_id).order_by(PrivateMessageParticipant.joined_at.asc())
        return list(self.session.scalars(stmt).all())

    def list_private_messages(self, *, actor: User, thread_id: str) -> list[PrivateMessage]:
        self.get_private_thread(actor=actor, thread_id=thread_id)
        stmt = select(PrivateMessage).where(PrivateMessage.thread_id == thread_id).order_by(PrivateMessage.created_at.asc())
        return list(self.session.scalars(stmt).all())

    def post_private_message(self, *, actor: User, thread_id: str, body: str, metadata_json: dict[str, object]) -> PrivateMessage:
        thread = self.get_private_thread(actor=actor, thread_id=thread_id)
        if thread.status != PrivateMessageThreadStatus.ACTIVE:
            raise CommunityEngineError('Private thread is not active.')
        message = PrivateMessage(thread_id=thread.id, sender_user_id=actor.id, body=body, metadata_json=metadata_json)
        self.session.add(message)
        thread.last_message_at = datetime.now(UTC)
        self.session.flush()
        return message

    def digest(self, *, actor: User) -> dict[str, int]:
        watchlist_count = self.session.scalar(select(func.count(CompetitionWatchlist.id)).where(CompetitionWatchlist.user_id == actor.id)) or 0
        private_thread_count = self.session.scalar(select(func.count(PrivateMessageParticipant.id)).where(PrivateMessageParticipant.user_id == actor.id)) or 0
        live_thread_count = self.session.scalar(select(func.count(LiveThread.id)).where(LiveThread.status != LiveThreadStatus.ARCHIVED)) or 0
        unread_hint_count = self.session.scalar(
            select(func.count(PrivateMessageThread.id))
            .join(PrivateMessageParticipant, PrivateMessageParticipant.thread_id == PrivateMessageThread.id)
            .where(
                PrivateMessageParticipant.user_id == actor.id,
                or_(PrivateMessageParticipant.last_read_at.is_(None), PrivateMessageThread.last_message_at > PrivateMessageParticipant.last_read_at),
            )
        ) or 0
        return {
            'watchlist_count': int(watchlist_count),
            'live_thread_count': int(live_thread_count),
            'private_thread_count': int(private_thread_count),
            'unread_hint_count': int(unread_hint_count),
        }

    @staticmethod
    def _needs_review(body: str) -> bool:
        lowered = body.lower()
        review_terms = ('fix match', 'scam', 'fraud', 'rigged', 'cashapp', 'telegram')
        return any(term in lowered for term in review_terms)
