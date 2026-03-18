from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import re

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from backend.app.common.enums.match_status import MatchStatus
from backend.app.models.club_infra import ClubSupporterHolding
from backend.app.models.club_profile import ClubProfile
from backend.app.models.club_social import RivalryProfile
from backend.app.models.competition import Competition
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.creator_fan_engagement import (
    CreatorClubFollow,
    CreatorFanCompetition,
    CreatorFanCompetitionEntry,
    CreatorFanCompetitionStatus,
    CreatorFanGroup,
    CreatorFanGroupMembership,
    CreatorFanWallEvent,
    CreatorMatchChatMessage,
    CreatorMatchChatMessageVisibility,
    CreatorMatchChatRoom,
    CreatorMatchChatRoomStatus,
    CreatorMatchTacticalAdvice,
    CreatorRivalrySignalOutput,
    CreatorRivalrySignalStatus,
    CreatorRivalrySignalSurface,
    CreatorTacticalAdviceStatus,
    CreatorTacticalAdviceType,
)
from backend.app.models.creator_monetization import CreatorBroadcastPurchase, CreatorMatchGiftEvent, CreatorSeasonPass
from backend.app.models.creator_provisioning import CreatorSquad
from backend.app.models.creator_share_market import CreatorClubShareHolding
from backend.app.models.media_engine import MatchView, PremiumVideoPurchase
from backend.app.models.user import User, UserRole
from backend.app.services.creator_broadcast_service import CreatorBroadcastError, CreatorBroadcastService

CHAT_OPEN_BEFORE_EVENT = timedelta(hours=1)
CHAT_CLOSE_AFTER_MATCH = timedelta(minutes=15)
RIVALRY_SIGNAL_THRESHOLD = 60
CHAT_MESSAGE_COOLDOWN = timedelta(seconds=8)
CHAT_MESSAGE_BURST_WINDOW = timedelta(minutes=2)
CHAT_MESSAGE_BURST_LIMIT = 5
TACTICAL_ADVICE_COOLDOWN = timedelta(seconds=30)
TACTICAL_ADVICE_MATCH_LIMIT = 3
LAYOUT_HINTS = {
    "preferred_container": "collapsible_side_panel",
    "alternate_container": "bottom_sheet",
    "avoid_video_overlay": True,
    "pin_to_match_video_edge": True,
}


class CreatorFanEngagementError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(frozen=True, slots=True)
class CreatorFanAccessState:
    can_comment: bool
    reason: str | None
    shareholder: bool
    supporter_share_balance: int
    creator_share_balance: int
    creator_shareholder: bool
    season_pass_holder: bool
    paying_viewer: bool
    visibility_priority: int
    has_cosmetic_voting_rights: bool
    cosmetic_vote_power: int
    followed_club_ids: tuple[str, ...]
    fan_group_ids: tuple[str, ...]
    fan_competition_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CreatorMatchChatWindow:
    status: CreatorMatchChatRoomStatus
    phase: str
    opens_at: datetime | None
    closes_at: datetime | None
    is_open: bool


@dataclass(slots=True)
class CreatorFanEngagementService:
    session: Session
    broadcast_service: CreatorBroadcastService | None = None

    def __post_init__(self) -> None:
        if self.broadcast_service is None:
            self.broadcast_service = CreatorBroadcastService(self.session)

    def get_chat_room(self, *, actor: User, match_id: str, now: datetime | None = None) -> dict[str, object]:
        context = self._get_match_context(match_id)
        room = self._ensure_chat_room(match_id=match_id, now=now)
        window = self._chat_window(match=context.match, now=now)
        access = self._fan_access_state(actor=actor, match=context.match, season_id=context.season.id)
        message_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorMatchChatMessage)
                .where(CreatorMatchChatMessage.room_id == room.id)
            )
            or 0
        )
        return {
            "id": room.id,
            "season_id": room.season_id,
            "competition_id": room.competition_id,
            "match_id": room.match_id,
            "room_key": room.room_key,
            "status": room.status,
            "phase": window.phase,
            "opens_at": room.opens_at,
            "closes_at": room.closes_at,
            "is_open": window.is_open,
            "message_count": message_count,
            "layout_hints_json": room.layout_hints_json or dict(LAYOUT_HINTS),
            "metadata_json": room.metadata_json or {},
            "access": self._serialize_access_state(access),
            "created_at": room.created_at,
            "updated_at": room.updated_at,
        }

    def list_chat_messages(self, *, match_id: str, limit: int = 50) -> list[CreatorMatchChatMessage]:
        room = self._ensure_chat_room(match_id=match_id)
        stmt = (
            select(CreatorMatchChatMessage)
            .where(
                CreatorMatchChatMessage.room_id == room.id,
                CreatorMatchChatMessage.visibility != CreatorMatchChatMessageVisibility.HIDDEN,
            )
            .order_by(
                CreatorMatchChatMessage.visibility_priority.desc(),
                CreatorMatchChatMessage.created_at.desc(),
            )
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def post_chat_message(
        self,
        *,
        actor: User,
        match_id: str,
        body: str,
        supported_club_id: str | None,
        metadata_json: dict[str, object],
        now: datetime | None = None,
    ) -> CreatorMatchChatMessage:
        context = self._get_match_context(match_id)
        room = self._ensure_chat_room(match_id=match_id, now=now)
        window = self._chat_window(match=context.match, now=now)
        if not window.is_open:
            raise CreatorFanEngagementError("Creator match fan chat is closed.", reason="chat_room_closed")
        access = self._fan_access_state(actor=actor, match=context.match, season_id=context.season.id)
        if not access.can_comment:
            raise CreatorFanEngagementError("Creator match fan chat requires season-pass or paid-viewer access.", reason=access.reason)
        normalized_body = body.strip()
        self._enforce_chat_safety(
            actor=actor,
            room_id=room.id,
            message_body=normalized_body,
        )
        club_id = self._resolve_supported_club_id(supported_club_id=supported_club_id, context=context, access=access)
        message = CreatorMatchChatMessage(
            room_id=room.id,
            author_user_id=actor.id,
            supported_club_id=club_id,
            body=normalized_body,
            visibility=CreatorMatchChatMessageVisibility.VISIBLE,
            visibility_priority=access.visibility_priority,
            shareholder=access.shareholder,
            season_pass_holder=access.season_pass_holder,
            paying_viewer=access.paying_viewer,
            metadata_json=metadata_json,
        )
        self.session.add(message)
        self.session.flush()
        return message

    def create_tactical_advice(
        self,
        *,
        actor: User,
        match_id: str,
        advice_type: CreatorTacticalAdviceType | str,
        suggestion_text: str,
        supported_club_id: str | None,
        metadata_json: dict[str, object],
        now: datetime | None = None,
    ) -> CreatorMatchTacticalAdvice:
        context = self._get_match_context(match_id)
        room = self._ensure_chat_room(match_id=match_id, now=now)
        window = self._chat_window(match=context.match, now=now)
        if not window.is_open or room.status != CreatorMatchChatRoomStatus.OPEN:
            raise CreatorFanEngagementError("Creator tactical advice is only available while fan chat is open.", reason="chat_room_closed")
        access = self._fan_access_state(actor=actor, match=context.match, season_id=context.season.id)
        if not access.can_comment:
            raise CreatorFanEngagementError("Creator tactical advice requires season-pass or paid-viewer access.", reason=access.reason)
        normalized_text = suggestion_text.strip()
        self._enforce_tactical_advice_safety(
            actor=actor,
            match_id=context.match.id,
        )
        club_id = self._resolve_supported_club_id(supported_club_id=supported_club_id, context=context, access=access)
        normalized_advice_type = (
            advice_type if isinstance(advice_type, CreatorTacticalAdviceType) else CreatorTacticalAdviceType(str(advice_type))
        )
        advice = CreatorMatchTacticalAdvice(
            season_id=context.season.id,
            competition_id=context.competition.id,
            match_id=context.match.id,
            author_user_id=actor.id,
            supported_club_id=club_id,
            advice_type=normalized_advice_type,
            suggestion_text=normalized_text,
            visibility_priority=access.visibility_priority,
            status=CreatorTacticalAdviceStatus.ACTIVE,
            metadata_json={"authority": "advisory_only", **metadata_json},
        )
        self.session.add(advice)
        self.session.flush()
        self._record_wall_event(
            club_id=club_id,
            match_id=context.match.id,
            actor_user_id=actor.id,
            event_kind="tactical_advice",
            headline=f"{self._display_name(actor)} suggested: {advice.suggestion_text}",
            body="Advice is advisory only and cannot directly control creator match actions.",
            reference_type="tactical_advice",
            reference_id=advice.id,
            prominence=70,
            metadata_json={"advice_type": normalized_advice_type.value, "authority": "advisory_only"},
        )
        return advice

    def list_tactical_advice(self, *, match_id: str, limit: int = 50) -> list[CreatorMatchTacticalAdvice]:
        stmt = (
            select(CreatorMatchTacticalAdvice)
            .where(
                CreatorMatchTacticalAdvice.match_id == match_id,
                CreatorMatchTacticalAdvice.status == CreatorTacticalAdviceStatus.ACTIVE,
            )
            .order_by(
                CreatorMatchTacticalAdvice.visibility_priority.desc(),
                CreatorMatchTacticalAdvice.created_at.desc(),
            )
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def follow_creator_club(
        self,
        *,
        actor: User,
        club_id: str,
        metadata_json: dict[str, object],
    ) -> CreatorClubFollow:
        club = self._require_creator_club(club_id)
        follow = self.session.scalar(
            select(CreatorClubFollow).where(
                CreatorClubFollow.club_id == club_id,
                CreatorClubFollow.user_id == actor.id,
            )
        )
        if follow is None:
            follow = CreatorClubFollow(
                club_id=club_id,
                user_id=actor.id,
                metadata_json=metadata_json,
            )
            self.session.add(follow)
            self.session.flush()
            self._record_wall_event(
                club_id=club_id,
                match_id=None,
                actor_user_id=actor.id,
                event_kind="follow",
                headline=f"{self._display_name(actor)} followed {club.club_name}",
                body=None,
                reference_type="follow",
                reference_id=follow.id,
                prominence=35,
                metadata_json={},
            )
        else:
            follow.metadata_json = metadata_json
            self.session.flush()
        return follow

    def unfollow_creator_club(self, *, actor: User, club_id: str) -> None:
        follow = self.session.scalar(
            select(CreatorClubFollow).where(
                CreatorClubFollow.club_id == club_id,
                CreatorClubFollow.user_id == actor.id,
            )
        )
        if follow is None:
            raise CreatorFanEngagementError("Creator club follow was not found.", reason="creator_follow_not_found")
        self.session.delete(follow)
        self.session.flush()

    def list_fan_groups(self, *, club_id: str) -> list[dict[str, object]]:
        self._require_creator_club(club_id)
        groups = list(
            self.session.scalars(
                select(CreatorFanGroup)
                .where(CreatorFanGroup.club_id == club_id)
                .order_by(CreatorFanGroup.is_official.desc(), CreatorFanGroup.created_at.asc())
            ).all()
        )
        counts = self._fan_group_counts(group_ids=tuple(group.id for group in groups))
        return [self._serialize_fan_group(group, member_count=counts.get(group.id, 0)) for group in groups]

    def create_fan_group(
        self,
        *,
        actor: User,
        club_id: str,
        name: str,
        description: str | None,
        identity_label: str | None,
        is_official: bool,
        metadata_json: dict[str, object],
    ) -> dict[str, object]:
        club = self._require_creator_club(club_id)
        slug = self._slugify(name)
        existing = self.session.scalar(
            select(CreatorFanGroup).where(
                CreatorFanGroup.club_id == club_id,
                CreatorFanGroup.slug == slug,
            )
        )
        if existing is not None:
            return self._serialize_fan_group(existing, member_count=self._fan_group_counts((existing.id,)).get(existing.id, 0))
        group = CreatorFanGroup(
            club_id=club_id,
            created_by_user_id=actor.id,
            slug=slug,
            name=name.strip(),
            description=description,
            identity_label=identity_label,
            is_official=is_official,
            metadata_json=metadata_json,
        )
        self.session.add(group)
        self.session.flush()
        self.join_fan_group(
            actor=actor,
            group_id=group.id,
            fan_identity_label=identity_label,
            metadata_json={"auto_join": True},
        )
        self._record_wall_event(
            club_id=club_id,
            match_id=None,
            actor_user_id=actor.id,
            event_kind="fan_group_launch",
            headline=f"{self._display_name(actor)} started {group.name}",
            body=f"New fan identity for {club.club_name}",
            reference_type="fan_group",
            reference_id=group.id,
            prominence=45,
            metadata_json={},
        )
        return self._serialize_fan_group(group, member_count=1)

    def join_fan_group(
        self,
        *,
        actor: User,
        group_id: str,
        fan_identity_label: str | None,
        metadata_json: dict[str, object],
    ) -> CreatorFanGroupMembership:
        group = self.session.get(CreatorFanGroup, group_id)
        if group is None:
            raise CreatorFanEngagementError("Creator fan group was not found.", reason="fan_group_not_found")
        membership = self.session.scalar(
            select(CreatorFanGroupMembership).where(
                CreatorFanGroupMembership.group_id == group_id,
                CreatorFanGroupMembership.user_id == actor.id,
            )
        )
        if membership is None:
            membership = CreatorFanGroupMembership(
                group_id=group_id,
                user_id=actor.id,
                club_id=group.club_id,
                fan_identity_label=fan_identity_label or group.identity_label,
                metadata_json=metadata_json,
            )
            self.session.add(membership)
            self.session.flush()
            self._record_wall_event(
                club_id=group.club_id,
                match_id=None,
                actor_user_id=actor.id,
                event_kind="fan_group_join",
                headline=f"{self._display_name(actor)} joined {group.name}",
                body=membership.fan_identity_label,
                reference_type="fan_group_membership",
                reference_id=membership.id,
                prominence=30,
                metadata_json={},
            )
        else:
            membership.fan_identity_label = fan_identity_label or membership.fan_identity_label
            membership.metadata_json = metadata_json
            self.session.flush()
        return membership

    def list_fan_competitions(self, *, club_id: str, match_id: str | None = None) -> list[dict[str, object]]:
        self._require_creator_club(club_id)
        stmt = select(CreatorFanCompetition).where(CreatorFanCompetition.club_id == club_id)
        if match_id is not None:
            stmt = stmt.where(CreatorFanCompetition.match_id == match_id)
        competitions = list(
            self.session.scalars(stmt.order_by(CreatorFanCompetition.created_at.desc())).all()
        )
        counts = self._fan_competition_counts(tuple(item.id for item in competitions))
        return [
            self._serialize_fan_competition(item, entry_count=counts.get(item.id, 0))
            for item in competitions
        ]

    def create_fan_competition(
        self,
        *,
        actor: User,
        club_id: str,
        title: str,
        description: str | None,
        match_id: str | None,
        starts_at: datetime | None,
        ends_at: datetime | None,
        metadata_json: dict[str, object],
    ) -> dict[str, object]:
        club = self._require_creator_club(club_id)
        if match_id is not None:
            context = self._get_match_context(match_id)
            if club_id not in {context.match.home_club_id, context.match.away_club_id}:
                raise CreatorFanEngagementError("Fan competition club must belong to the creator match.", reason="supported_club_not_in_match")
        competition = CreatorFanCompetition(
            club_id=club_id,
            created_by_user_id=actor.id,
            match_id=match_id,
            title=title.strip(),
            description=description,
            status=CreatorFanCompetitionStatus.ACTIVE,
            starts_at=starts_at,
            ends_at=ends_at,
            metadata_json=metadata_json,
        )
        self.session.add(competition)
        self.session.flush()
        self._record_wall_event(
            club_id=club_id,
            match_id=match_id,
            actor_user_id=actor.id,
            event_kind="fan_competition_launch",
            headline=f"{self._display_name(actor)} launched {competition.title}",
            body=f"Fan competition for {club.club_name}",
            reference_type="fan_competition",
            reference_id=competition.id,
            prominence=50,
            metadata_json={},
        )
        return self._serialize_fan_competition(competition, entry_count=0)

    def join_fan_competition(
        self,
        *,
        actor: User,
        fan_competition_id: str,
        fan_group_id: str | None,
        metadata_json: dict[str, object],
    ) -> CreatorFanCompetitionEntry:
        competition = self.session.get(CreatorFanCompetition, fan_competition_id)
        if competition is None:
            raise CreatorFanEngagementError("Creator fan competition was not found.", reason="fan_competition_not_found")
        if competition.status != CreatorFanCompetitionStatus.ACTIVE:
            raise CreatorFanEngagementError("Creator fan competition is closed.", reason="fan_competition_closed")
        if fan_group_id is not None:
            group = self.session.get(CreatorFanGroup, fan_group_id)
            if group is None or group.club_id != competition.club_id:
                raise CreatorFanEngagementError("Fan group does not belong to this creator club.", reason="fan_group_not_found")
        entry = self.session.scalar(
            select(CreatorFanCompetitionEntry).where(
                CreatorFanCompetitionEntry.fan_competition_id == fan_competition_id,
                CreatorFanCompetitionEntry.user_id == actor.id,
            )
        )
        if entry is None:
            entry = CreatorFanCompetitionEntry(
                fan_competition_id=fan_competition_id,
                user_id=actor.id,
                club_id=competition.club_id,
                fan_group_id=fan_group_id,
                metadata_json=metadata_json,
            )
            self.session.add(entry)
            self.session.flush()
            self._record_wall_event(
                club_id=competition.club_id,
                match_id=competition.match_id,
                actor_user_id=actor.id,
                event_kind="fan_competition_join",
                headline=f"{self._display_name(actor)} joined {competition.title}",
                body=None,
                reference_type="fan_competition_entry",
                reference_id=entry.id,
                prominence=35,
                metadata_json={},
            )
        else:
            entry.fan_group_id = fan_group_id
            entry.metadata_json = metadata_json
            self.session.flush()
        return entry

    def get_fan_state(self, *, actor: User, club_id: str, match_id: str | None = None) -> dict[str, object]:
        self._require_creator_club(club_id)
        follow = self.session.scalar(
            select(CreatorClubFollow).where(
                CreatorClubFollow.club_id == club_id,
                CreatorClubFollow.user_id == actor.id,
            )
        )
        holding = self.session.scalar(
            select(ClubSupporterHolding).where(
                ClubSupporterHolding.club_id == club_id,
                ClubSupporterHolding.user_id == actor.id,
            )
        )
        creator_share_holding = self._creator_share_holding_for_club(actor_id=actor.id, club_id=club_id)
        season_pass_holder = self.session.scalar(
            select(CreatorSeasonPass.id).where(
                CreatorSeasonPass.club_id == club_id,
                CreatorSeasonPass.user_id == actor.id,
            )
        ) is not None
        paying_viewer = False
        can_comment = False
        visibility_priority = 0
        if match_id is not None:
            context = self._get_match_context(match_id)
            access = self._fan_access_state(actor=actor, match=context.match, season_id=context.season.id)
            paying_viewer = access.paying_viewer
            can_comment = access.can_comment
            visibility_priority = access.visibility_priority
        fan_group_ids = [
            item.group_id
            for item in self.session.scalars(
                select(CreatorFanGroupMembership).where(
                    CreatorFanGroupMembership.user_id == actor.id,
                    CreatorFanGroupMembership.club_id == club_id,
                )
            ).all()
        ]
        fan_competition_ids = [
            item.fan_competition_id
            for item in self.session.scalars(
                select(CreatorFanCompetitionEntry).where(
                    CreatorFanCompetitionEntry.user_id == actor.id,
                    CreatorFanCompetitionEntry.club_id == club_id,
                )
            ).all()
        ]
        gifts_query = select(func.count()).select_from(CreatorMatchGiftEvent).where(
            CreatorMatchGiftEvent.sender_user_id == actor.id,
            CreatorMatchGiftEvent.club_id == club_id,
        )
        if match_id is not None:
            gifts_query = gifts_query.where(CreatorMatchGiftEvent.match_id == match_id)
        gifts_sent_count = int(self.session.scalar(gifts_query) or 0)
        supporter_share_balance = int(holding.token_balance if holding is not None else 0)
        creator_share_balance = int(creator_share_holding.share_count if creator_share_holding is not None else 0)
        creator_shareholder = creator_share_balance > 0
        shareholder = creator_shareholder or bool(
            holding is not None and (int(holding.token_balance) > 0 or int(holding.influence_points) > 0)
        )
        return {
            "club_id": club_id,
            "match_id": match_id,
            "following": follow is not None,
            "shareholder": shareholder,
            "supporter_share_balance": supporter_share_balance,
            "creator_share_balance": creator_share_balance,
            "creator_shareholder": creator_shareholder,
            "season_pass_holder": season_pass_holder,
            "paying_viewer": paying_viewer,
            "can_comment": can_comment,
            "visibility_priority": visibility_priority,
            "has_cosmetic_voting_rights": creator_shareholder,
            "cosmetic_vote_power": creator_share_balance,
            "fan_group_ids": fan_group_ids,
            "fan_competition_ids": fan_competition_ids,
            "gifts_sent_count": gifts_sent_count,
        }

    def get_fan_wall(self, *, match_id: str, limit: int = 50) -> dict[str, object]:
        context = self._get_match_context(match_id)
        club_ids = (context.match.home_club_id, context.match.away_club_id)
        wall_events = list(
            self.session.scalars(
                select(CreatorFanWallEvent)
                .where(
                    or_(
                        CreatorFanWallEvent.match_id == match_id,
                        and_(
                            CreatorFanWallEvent.match_id.is_(None),
                            CreatorFanWallEvent.club_id.in_(club_ids),
                        ),
                    )
                )
                .order_by(CreatorFanWallEvent.created_at.desc())
                .limit(limit * 2)
            ).all()
        )
        items: list[dict[str, object]] = [
            {
                "item_id": event.id,
                "item_type": event.event_kind,
                "club_id": event.club_id,
                "match_id": event.match_id,
                "headline": event.headline,
                "body": event.body,
                "prominence": event.prominence,
                "created_at": event.created_at,
                "reference_type": event.reference_type,
                "reference_id": event.reference_id,
                "metadata_json": event.metadata_json or {},
            }
            for event in wall_events
        ]
        gifts = list(
            self.session.scalars(
                select(CreatorMatchGiftEvent)
                .where(CreatorMatchGiftEvent.match_id == match_id)
                .order_by(CreatorMatchGiftEvent.created_at.desc())
                .limit(limit)
            ).all()
        )
        for gift in gifts:
            items.append(
                {
                    "item_id": gift.id,
                    "item_type": "gift",
                    "club_id": gift.club_id,
                    "match_id": gift.match_id,
                    "headline": f"{gift.gift_label} sent to creator club",
                    "body": gift.note,
                    "prominence": min(95, 60 + int(gift.gross_amount_coin)),
                    "created_at": gift.created_at,
                    "reference_type": "creator_match_gift",
                    "reference_id": gift.id,
                    "metadata_json": {
                        "gross_amount_coin": str(gift.gross_amount_coin),
                        "recipient_creator_user_id": gift.recipient_creator_user_id,
                    },
                }
            )
        items.sort(key=lambda item: (int(item["prominence"]), item["created_at"]), reverse=True)
        return {
            "match_id": match_id,
            "layout_hints_json": dict(LAYOUT_HINTS),
            "items": items[:limit],
        }

    def refresh_rivalry_signals(self, *, match_id: str) -> list[CreatorRivalrySignalOutput]:
        context = self._get_match_context(match_id)
        match = context.match
        home_club = context.home_club
        away_club = context.away_club
        completed_matches = self._creator_pair_matches(home_club_id=match.home_club_id, away_club_id=match.away_club_id)
        close_results = sum(1 for item in completed_matches if abs(int(item.home_score) - int(item.away_score)) <= 1)
        frequent_matches_score = min(30, len(completed_matches) * 10)
        close_results_score = min(20, close_results * 8)
        room = self.session.scalar(select(CreatorMatchChatRoom).where(CreatorMatchChatRoom.match_id == match.id))
        chat_count = 0
        if room is not None:
            chat_count = int(
                self.session.scalar(
                    select(func.count())
                    .select_from(CreatorMatchChatMessage)
                    .where(CreatorMatchChatMessage.room_id == room.id)
                )
                or 0
            )
        tactical_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorMatchTacticalAdvice)
                .where(CreatorMatchTacticalAdvice.match_id == match.id)
            )
            or 0
        )
        gift_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorMatchGiftEvent)
                .where(CreatorMatchGiftEvent.match_id == match.id)
            )
            or 0
        )
        current_view_count = int(
            self.session.scalar(
                select(func.count()).select_from(MatchView).where(MatchView.match_key == match.id)
            )
            or 0
        )
        fan_engagement_score = min(25, (chat_count * 3) + (tactical_count * 4) + (gift_count * 5))
        viewership_spike_score = self._viewership_spike_score(match_id=match.id, current_view_count=current_view_count)
        rivalry_profile = self._find_rivalry_profile(home_club_id=match.home_club_id, away_club_id=match.away_club_id)
        existing_bonus = min(10, int(rivalry_profile.intensity_score) // 10) if rivalry_profile is not None else 0
        total_score = min(
            100,
            frequent_matches_score + close_results_score + fan_engagement_score + viewership_spike_score + existing_bonus,
        )
        active = total_score >= RIVALRY_SIGNAL_THRESHOLD
        target_user_ids = self._target_user_ids_for_rivalry(
            home_club_id=match.home_club_id,
            away_club_id=match.away_club_id,
        )
        headline_base = f"{home_club.club_name if home_club else match.home_club_id} vs {away_club.club_name if away_club else match.away_club_id}"
        rationale = {
            "frequent_matches": len(completed_matches),
            "close_results": close_results,
            "chat_messages": chat_count,
            "tactical_advice": tactical_count,
            "gift_events": gift_count,
            "view_count": current_view_count,
            "frequent_matches_score": frequent_matches_score,
            "close_results_score": close_results_score,
            "fan_engagement_score": fan_engagement_score,
            "viewership_spike_score": viewership_spike_score,
            "club_social_bonus": existing_bonus,
        }
        outputs: list[CreatorRivalrySignalOutput] = []
        surface_payloads = (
            (
                CreatorRivalrySignalSurface.HOMEPAGE_PROMOTION,
                f"{headline_base} is trending",
                "Fan engagement and close creator-match results have pushed this matchup into homepage promotion range.",
            ),
            (
                CreatorRivalrySignalSurface.NOTIFICATION,
                f"Rivalry alert: {headline_base}",
                "Trigger notification delivery for highly engaged followers, season-pass holders, and supporter shareholders.",
            ),
        )
        for surface, headline, message in surface_payloads:
            output = self.session.scalar(
                select(CreatorRivalrySignalOutput).where(
                    CreatorRivalrySignalOutput.match_id == match.id,
                    CreatorRivalrySignalOutput.surface == surface,
                )
            )
            if output is None:
                output = CreatorRivalrySignalOutput(
                    match_id=match.id,
                    home_club_id=match.home_club_id,
                    away_club_id=match.away_club_id,
                    surface=surface,
                    headline=headline,
                    message=message,
                    rationale_json={},
                    metadata_json={},
                )
                self.session.add(output)
            output.home_club_id = match.home_club_id
            output.away_club_id = match.away_club_id
            output.club_social_rivalry_id = rivalry_profile.id if rivalry_profile is not None else None
            output.signal_status = (
                CreatorRivalrySignalStatus.ACTIVE if active else CreatorRivalrySignalStatus.INACTIVE
            )
            output.score = total_score
            output.headline = headline
            output.message = message
            output.target_user_count = len(target_user_ids)
            output.rationale_json = rationale
            output.metadata_json = {"target_user_ids": sorted(target_user_ids)}
            self.session.flush()
            outputs.append(output)
        return outputs

    def list_rivalry_signals(self, *, match_id: str) -> list[CreatorRivalrySignalOutput]:
        self.refresh_rivalry_signals(match_id=match_id)
        return list(
            self.session.scalars(
                select(CreatorRivalrySignalOutput)
                .where(CreatorRivalrySignalOutput.match_id == match_id)
                .order_by(CreatorRivalrySignalOutput.surface.asc())
            ).all()
        )

    def _get_match_context(self, match_id: str):
        try:
            return self.broadcast_service.get_match_context(match_id)
        except CreatorBroadcastError as exc:
            reason = exc.reason or "creator_match_not_found"
            mapped_reason = "creator_match_not_found" if reason in {"match_not_found", "creator_league_only"} else reason
            raise CreatorFanEngagementError(exc.detail, reason=mapped_reason) from exc

    def _require_creator_club(self, club_id: str) -> ClubProfile:
        club = self.session.scalar(
            select(ClubProfile)
            .join(CreatorSquad, CreatorSquad.club_id == ClubProfile.id)
            .where(ClubProfile.id == club_id)
        )
        if club is None:
            raise CreatorFanEngagementError("Creator club was not found.", reason="creator_club_not_found")
        return club

    def _ensure_chat_room(self, *, match_id: str, now: datetime | None = None) -> CreatorMatchChatRoom:
        context = self._get_match_context(match_id)
        window = self._chat_window(match=context.match, now=now)
        room = self.session.scalar(select(CreatorMatchChatRoom).where(CreatorMatchChatRoom.match_id == match_id))
        if room is None:
            room = CreatorMatchChatRoom(
                season_id=context.season.id,
                competition_id=context.competition.id,
                match_id=context.match.id,
                room_key=f"creator-match:{context.match.id}",
                layout_hints_json=dict(LAYOUT_HINTS),
                metadata_json={"video_safe": True},
            )
            self.session.add(room)
        room.season_id = context.season.id
        room.competition_id = context.competition.id
        room.opens_at = window.opens_at
        room.closes_at = window.closes_at
        room.status = window.status
        room.layout_hints_json = dict(LAYOUT_HINTS)
        self.session.flush()
        return room

    def _chat_window(self, *, match: CompetitionMatch, now: datetime | None = None) -> CreatorMatchChatWindow:
        clock = self._ensure_aware(now or datetime.now(UTC))
        start_at = self._ensure_aware(match.scheduled_at)
        completed_at = self._ensure_aware(
            match.completed_at or (match.updated_at if match.status == MatchStatus.COMPLETED.value else None)
        )
        opens_at = start_at - CHAT_OPEN_BEFORE_EVENT if start_at is not None else None
        closes_at = completed_at + CHAT_CLOSE_AFTER_MATCH if completed_at is not None else None
        if match.status in {MatchStatus.CANCELLED.value, MatchStatus.POSTPONED.value}:
            return CreatorMatchChatWindow(CreatorMatchChatRoomStatus.CLOSED, "closed", opens_at, closes_at, False)
        if match.status in {MatchStatus.IN_PROGRESS.value, MatchStatus.PAUSED.value}:
            return CreatorMatchChatWindow(CreatorMatchChatRoomStatus.OPEN, "live", opens_at, closes_at, True)
        if match.status == MatchStatus.COMPLETED.value:
            is_open = closes_at is not None and clock <= closes_at
            return CreatorMatchChatWindow(
                CreatorMatchChatRoomStatus.OPEN if is_open else CreatorMatchChatRoomStatus.CLOSED,
                "post_match" if is_open else "closed",
                opens_at,
                closes_at,
                is_open,
            )
        if opens_at is not None and clock >= opens_at:
            return CreatorMatchChatWindow(CreatorMatchChatRoomStatus.OPEN, "pre_match", opens_at, closes_at, True)
        return CreatorMatchChatWindow(CreatorMatchChatRoomStatus.SCHEDULED, "closed", opens_at, closes_at, False)

    def _fan_access_state(self, *, actor: User, match: CompetitionMatch, season_id: str) -> CreatorFanAccessState:
        club_ids = (match.home_club_id, match.away_club_id)
        if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return CreatorFanAccessState(
                can_comment=True,
                reason=None,
                shareholder=False,
                supporter_share_balance=0,
                creator_share_balance=0,
                creator_shareholder=False,
                season_pass_holder=True,
                paying_viewer=True,
                visibility_priority=400,
                has_cosmetic_voting_rights=False,
                cosmetic_vote_power=0,
                followed_club_ids=(),
                fan_group_ids=(),
                fan_competition_ids=(),
            )
        holdings = list(
            self.session.scalars(
                select(ClubSupporterHolding).where(
                    ClubSupporterHolding.user_id == actor.id,
                    ClubSupporterHolding.club_id.in_(club_ids),
                )
            ).all()
        )
        creator_share_holdings = self._creator_share_holdings_for_match(actor_id=actor.id, club_ids=club_ids)
        creator_share_balance = sum(int(item.share_count) for item in creator_share_holdings)
        creator_shareholder = creator_share_balance > 0
        shareholder = creator_shareholder or any(
            int(item.token_balance) > 0 or int(item.influence_points) > 0 for item in holdings
        )
        supporter_share_balance = sum(int(item.token_balance) for item in holdings)
        season_passes = list(
            self.session.scalars(
                select(CreatorSeasonPass).where(
                    CreatorSeasonPass.user_id == actor.id,
                    CreatorSeasonPass.season_id == season_id,
                    CreatorSeasonPass.club_id.in_(club_ids),
                )
            ).all()
        )
        season_pass_holder = bool(season_passes)
        creator_purchase = self.session.scalar(
            select(CreatorBroadcastPurchase).where(
                CreatorBroadcastPurchase.user_id == actor.id,
                CreatorBroadcastPurchase.match_id == match.id,
            )
        )
        premium_purchase = self.session.scalar(
            select(PremiumVideoPurchase).where(
                PremiumVideoPurchase.user_id == actor.id,
                PremiumVideoPurchase.match_key == match.id,
            )
        )
        paying_viewer = creator_purchase is not None or premium_purchase is not None
        followed_club_ids = tuple(
            item.club_id
            for item in self.session.scalars(
                select(CreatorClubFollow).where(
                    CreatorClubFollow.user_id == actor.id,
                    CreatorClubFollow.club_id.in_(club_ids),
                )
            ).all()
        )
        fan_group_ids = tuple(
            item.group_id
            for item in self.session.scalars(
                select(CreatorFanGroupMembership).where(
                    CreatorFanGroupMembership.user_id == actor.id,
                    CreatorFanGroupMembership.club_id.in_(club_ids),
                )
            ).all()
        )
        fan_competition_ids = tuple(
            item.fan_competition_id
            for item in self.session.scalars(
                select(CreatorFanCompetitionEntry).where(
                    CreatorFanCompetitionEntry.user_id == actor.id,
                    CreatorFanCompetitionEntry.club_id.in_(club_ids),
                )
            ).all()
        )
        can_comment = season_pass_holder or paying_viewer
        visibility_priority = 0
        if season_pass_holder:
            visibility_priority = 200
        elif paying_viewer:
            visibility_priority = 100
        if visibility_priority > 0 and creator_shareholder:
            visibility_priority += 100
        elif season_pass_holder and supporter_share_balance > 0:
            visibility_priority += 100
        return CreatorFanAccessState(
            can_comment=can_comment,
            reason=None if can_comment else "fan_chat_access_denied",
            shareholder=shareholder,
            supporter_share_balance=supporter_share_balance,
            creator_share_balance=creator_share_balance,
            creator_shareholder=creator_shareholder,
            season_pass_holder=season_pass_holder,
            paying_viewer=paying_viewer,
            visibility_priority=visibility_priority,
            has_cosmetic_voting_rights=creator_shareholder,
            cosmetic_vote_power=creator_share_balance,
            followed_club_ids=followed_club_ids,
            fan_group_ids=fan_group_ids,
            fan_competition_ids=fan_competition_ids,
        )

    def _enforce_chat_safety(self, *, actor: User, room_id: str, message_body: str) -> None:
        if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return
        now = datetime.now(UTC)
        latest_message = self.session.scalar(
            select(CreatorMatchChatMessage)
            .where(
                CreatorMatchChatMessage.room_id == room_id,
                CreatorMatchChatMessage.author_user_id == actor.id,
            )
            .order_by(CreatorMatchChatMessage.created_at.desc(), CreatorMatchChatMessage.id.desc())
        )
        if latest_message is not None and latest_message.created_at is not None:
            latest_created_at = self._ensure_aware(latest_message.created_at) or latest_message.created_at
            elapsed = now - latest_created_at
            if elapsed < CHAT_MESSAGE_COOLDOWN:
                raise CreatorFanEngagementError(
                    "Creator match fan chat is temporarily rate limited for this user.",
                    reason="fan_chat_rate_limited",
                )
            if elapsed < CHAT_MESSAGE_BURST_WINDOW and latest_message.body.strip().casefold() == message_body.casefold():
                raise CreatorFanEngagementError(
                    "Duplicate creator match fan chat messages are temporarily blocked.",
                    reason="fan_chat_rate_limited",
                )

        burst_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorMatchChatMessage)
                .where(
                    CreatorMatchChatMessage.room_id == room_id,
                    CreatorMatchChatMessage.author_user_id == actor.id,
                    CreatorMatchChatMessage.created_at >= now - CHAT_MESSAGE_BURST_WINDOW,
                )
            )
            or 0
        )
        if burst_count >= CHAT_MESSAGE_BURST_LIMIT:
            raise CreatorFanEngagementError(
                "Creator match fan chat is temporarily rate limited for this user.",
                reason="fan_chat_rate_limited",
            )

    def _enforce_tactical_advice_safety(self, *, actor: User, match_id: str) -> None:
        if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return
        now = datetime.now(UTC)
        latest_advice = self.session.scalar(
            select(CreatorMatchTacticalAdvice)
            .where(
                CreatorMatchTacticalAdvice.match_id == match_id,
                CreatorMatchTacticalAdvice.author_user_id == actor.id,
            )
            .order_by(CreatorMatchTacticalAdvice.created_at.desc(), CreatorMatchTacticalAdvice.id.desc())
        )
        if latest_advice is not None and latest_advice.created_at is not None:
            latest_created_at = self._ensure_aware(latest_advice.created_at) or latest_advice.created_at
            if now - latest_created_at < TACTICAL_ADVICE_COOLDOWN:
                raise CreatorFanEngagementError(
                    "Creator tactical advice is temporarily rate limited for this user.",
                    reason="tactical_advice_rate_limited",
                )

        advice_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorMatchTacticalAdvice)
                .where(
                    CreatorMatchTacticalAdvice.match_id == match_id,
                    CreatorMatchTacticalAdvice.author_user_id == actor.id,
                    CreatorMatchTacticalAdvice.status == CreatorTacticalAdviceStatus.ACTIVE,
                )
            )
            or 0
        )
        if advice_count >= TACTICAL_ADVICE_MATCH_LIMIT:
            raise CreatorFanEngagementError(
                "Creator tactical advice is temporarily rate limited for this user.",
                reason="tactical_advice_rate_limited",
            )

    def _creator_share_holdings_for_match(
        self,
        *,
        actor_id: str,
        club_ids: tuple[str | None, str | None],
    ) -> list[CreatorClubShareHolding]:
        try:
            return list(
                self.session.scalars(
                    select(CreatorClubShareHolding).where(
                        CreatorClubShareHolding.user_id == actor_id,
                        CreatorClubShareHolding.club_id.in_(club_ids),
                        CreatorClubShareHolding.share_count > 0,
                    )
                ).all()
            )
        except OperationalError:
            # Some lightweight setups create only fan-engagement tables and intentionally omit share-market tables.
            return []

    def _creator_share_holding_for_club(
        self,
        *,
        actor_id: str,
        club_id: str,
    ) -> CreatorClubShareHolding | None:
        try:
            return self.session.scalar(
                select(CreatorClubShareHolding).where(
                    CreatorClubShareHolding.club_id == club_id,
                    CreatorClubShareHolding.user_id == actor_id,
                )
            )
        except OperationalError:
            return None

    def _serialize_access_state(self, access: CreatorFanAccessState) -> dict[str, object]:
        return {
            "can_comment": access.can_comment,
            "reason": access.reason,
            "shareholder": access.shareholder,
            "supporter_share_balance": access.supporter_share_balance,
            "creator_share_balance": access.creator_share_balance,
            "creator_shareholder": access.creator_shareholder,
            "season_pass_holder": access.season_pass_holder,
            "paying_viewer": access.paying_viewer,
            "visibility_priority": access.visibility_priority,
            "has_cosmetic_voting_rights": access.has_cosmetic_voting_rights,
            "cosmetic_vote_power": access.cosmetic_vote_power,
            "followed_club_ids": list(access.followed_club_ids),
            "fan_group_ids": list(access.fan_group_ids),
            "fan_competition_ids": list(access.fan_competition_ids),
        }

    def _resolve_supported_club_id(self, *, supported_club_id: str | None, context, access: CreatorFanAccessState) -> str | None:
        if supported_club_id is None:
            return context.match.home_club_id if access.followed_club_ids else None
        if supported_club_id not in {context.match.home_club_id, context.match.away_club_id}:
            raise CreatorFanEngagementError("Supported club must belong to this creator match.", reason="supported_club_not_in_match")
        return supported_club_id

    def _record_wall_event(
        self,
        *,
        club_id: str | None,
        match_id: str | None,
        actor_user_id: str | None,
        event_kind: str,
        headline: str,
        body: str | None,
        reference_type: str | None,
        reference_id: str | None,
        prominence: int,
        metadata_json: dict[str, object],
    ) -> CreatorFanWallEvent:
        event = CreatorFanWallEvent(
            club_id=club_id,
            match_id=match_id,
            actor_user_id=actor_user_id,
            event_kind=event_kind,
            headline=headline,
            body=body,
            reference_type=reference_type,
            reference_id=reference_id,
            prominence=prominence,
            metadata_json=metadata_json,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def _fan_group_counts(self, group_ids: tuple[str, ...]) -> dict[str, int]:
        if not group_ids:
            return {}
        rows = self.session.execute(
            select(CreatorFanGroupMembership.group_id, func.count(CreatorFanGroupMembership.id))
            .where(CreatorFanGroupMembership.group_id.in_(group_ids))
            .group_by(CreatorFanGroupMembership.group_id)
        ).all()
        return {str(group_id): int(count) for group_id, count in rows}

    def _fan_competition_counts(self, competition_ids: tuple[str, ...]) -> dict[str, int]:
        if not competition_ids:
            return {}
        rows = self.session.execute(
            select(CreatorFanCompetitionEntry.fan_competition_id, func.count(CreatorFanCompetitionEntry.id))
            .where(CreatorFanCompetitionEntry.fan_competition_id.in_(competition_ids))
            .group_by(CreatorFanCompetitionEntry.fan_competition_id)
        ).all()
        return {str(competition_id): int(count) for competition_id, count in rows}

    def _serialize_fan_group(self, group: CreatorFanGroup, *, member_count: int) -> dict[str, object]:
        return {
            "id": group.id,
            "club_id": group.club_id,
            "created_by_user_id": group.created_by_user_id,
            "slug": group.slug,
            "name": group.name,
            "description": group.description,
            "identity_label": group.identity_label,
            "is_official": group.is_official,
            "metadata_json": group.metadata_json or {},
            "created_at": group.created_at,
            "updated_at": group.updated_at,
            "member_count": member_count,
        }

    def _serialize_fan_competition(self, competition: CreatorFanCompetition, *, entry_count: int) -> dict[str, object]:
        return {
            "id": competition.id,
            "club_id": competition.club_id,
            "created_by_user_id": competition.created_by_user_id,
            "match_id": competition.match_id,
            "title": competition.title,
            "description": competition.description,
            "status": competition.status,
            "starts_at": competition.starts_at,
            "ends_at": competition.ends_at,
            "metadata_json": competition.metadata_json or {},
            "created_at": competition.created_at,
            "updated_at": competition.updated_at,
            "entry_count": entry_count,
        }

    def _creator_pair_matches(self, *, home_club_id: str, away_club_id: str) -> list[CompetitionMatch]:
        stmt = (
            select(CompetitionMatch)
            .join(Competition, Competition.id == CompetitionMatch.competition_id)
            .where(
                Competition.source_type == "creator_league",
                CompetitionMatch.status == MatchStatus.COMPLETED.value,
                or_(
                    and_(CompetitionMatch.home_club_id == home_club_id, CompetitionMatch.away_club_id == away_club_id),
                    and_(CompetitionMatch.home_club_id == away_club_id, CompetitionMatch.away_club_id == home_club_id),
                ),
            )
            .order_by(CompetitionMatch.completed_at.desc().nullslast(), CompetitionMatch.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def _viewership_spike_score(self, *, match_id: str, current_view_count: int) -> int:
        counts = [
            int(row[1])
            for row in self.session.execute(
                select(MatchView.match_key, func.count(MatchView.id))
                .join(CompetitionMatch, CompetitionMatch.id == MatchView.match_key)
                .join(Competition, Competition.id == CompetitionMatch.competition_id)
                .where(Competition.source_type == "creator_league")
                .group_by(MatchView.match_key)
            ).all()
            if row[0] != match_id
        ]
        if not counts:
            return 15 if current_view_count >= 5 else 0
        baseline = sum(counts) / len(counts)
        if current_view_count >= max(5, int(baseline * 2)):
            return 25
        if current_view_count >= max(4, int(baseline * 1.5)):
            return 15
        return 0

    def _find_rivalry_profile(self, *, home_club_id: str, away_club_id: str) -> RivalryProfile | None:
        return self.session.scalar(
            select(RivalryProfile).where(
                or_(
                    and_(RivalryProfile.club_a_id == home_club_id, RivalryProfile.club_b_id == away_club_id),
                    and_(RivalryProfile.club_a_id == away_club_id, RivalryProfile.club_b_id == home_club_id),
                )
            )
        )

    def _target_user_ids_for_rivalry(self, *, home_club_id: str, away_club_id: str) -> set[str]:
        club_ids = (home_club_id, away_club_id)
        user_ids = set(
            self.session.scalars(select(CreatorClubFollow.user_id).where(CreatorClubFollow.club_id.in_(club_ids))).all()
        )
        user_ids.update(
            self.session.scalars(select(CreatorSeasonPass.user_id).where(CreatorSeasonPass.club_id.in_(club_ids))).all()
        )
        user_ids.update(
            self.session.scalars(
                select(ClubSupporterHolding.user_id).where(
                    ClubSupporterHolding.club_id.in_(club_ids),
                    or_(ClubSupporterHolding.token_balance > 0, ClubSupporterHolding.influence_points > 0),
                )
            ).all()
        )
        return {str(user_id) for user_id in user_ids}

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "fan-group"

    @staticmethod
    def _display_name(actor: User) -> str:
        return actor.display_name or actor.full_name or actor.username

    @staticmethod
    def _ensure_aware(value: datetime | None) -> datetime | None:
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=UTC)


__all__ = [
    "CreatorFanAccessState",
    "CreatorFanEngagementError",
    "CreatorFanEngagementService",
]
