from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Integer, String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.ingestion.models import Country, Player
from app.models.agent_marketplace import (
    AgentAskingType,
    AgentMarketplaceListing,
    ConversationParticipantRole,
    PlayerConversation,
    PlayerConversationMessage,
    PlayerConversationParticipant,
    PlayerConversationStatus,
)
from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.models.real_player_profile import RealPlayerProfile
from app.models.user import User
from app.players.read_models import PlayerSummaryReadModel


class MarketplaceError(Exception):
    pass


class MarketplaceNotFoundError(MarketplaceError):
    pass


class MarketplacePermissionError(MarketplaceError):
    pass


class MarketplaceConflictError(MarketplaceError):
    pass


class MarketplaceValidationError(MarketplaceError):
    pass


MARKETPLACE_SORTS = frozenset({"recent", "name", "market_interest"})


@dataclass(slots=True)
class AgentMarketplaceService:
    session: Session
    today: date | None = None

    def __post_init__(self) -> None:
        if self.today is None:
            self.today = date.today()

    def list_players(
        self,
        *,
        limit: int = 20,
        cursor: str | None = None,
        offset: int = 0,
        search: str | None = None,
        position: str | None = None,
        country: str | None = None,
        nationality: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        availability: str | None = None,
        sort: str = "recent",
        include_unavailable: bool = False,
        agent_user_id: str | None = None,
    ) -> dict[str, object]:
        effective_offset = self._resolve_offset(cursor=cursor, offset=offset)
        normalized_country = self._clean(country) or self._clean(nationality)
        normalized_sort = self._clean(sort) or "recent"
        if normalized_sort not in MARKETPLACE_SORTS:
            raise MarketplaceValidationError(f"sort must be one of {sorted(MARKETPLACE_SORTS)}")
        if min_age is not None and max_age is not None and min_age > max_age:
            raise MarketplaceValidationError("min_age cannot exceed max_age")
        if limit < 1 or limit > 100:
            raise MarketplaceValidationError("limit must be between 1 and 100")
        if effective_offset < 0:
            raise MarketplaceValidationError("offset cannot be negative")

        statement = self._marketplace_player_statement(
            include_unavailable=include_unavailable,
            agent_user_id=agent_user_id,
        )
        statement = self._apply_player_filters(
            statement,
            search=search,
            position=position,
            country=normalized_country,
            min_age=min_age,
            max_age=max_age,
            availability=availability,
        )

        total = int(self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        rows = self.session.execute(
            statement.order_by(*self._order_by(sort=normalized_sort)).offset(effective_offset).limit(limit)
        ).all()
        items = [self._build_marketplace_player_view(*row) for row in rows]
        next_offset = effective_offset + len(items)
        has_more = next_offset < total
        return {
            "items": items,
            "limit": limit,
            "next_cursor": str(next_offset) if has_more else None,
            "has_more": has_more,
            "total": total,
        }

    def get_player(self, player_id: str) -> dict[str, object]:
        row = self.session.execute(
            self._marketplace_player_statement(include_unavailable=True).where(Player.id == player_id)
        ).first()
        if row is None:
            raise MarketplaceNotFoundError(f"Marketplace player '{player_id}' was not found.")
        return self._build_marketplace_player_view(*row)

    def list_agent_players(self, agent_user_id: str) -> list[dict[str, object]]:
        result = self.list_players(
            limit=100,
            include_unavailable=True,
            agent_user_id=agent_user_id,
            sort="recent",
        )
        return list(result["items"])

    def upsert_listing(
        self,
        *,
        actor: User,
        player_id: str,
        is_available: bool,
        asking_type: AgentAskingType,
        note: str | None,
    ) -> dict[str, object]:
        player = self.session.get(Player, player_id)
        if player is None or not player.is_real_player:
            raise MarketplaceNotFoundError(f"Real player '{player_id}' was not found.")

        listing = self.session.execute(
            select(AgentMarketplaceListing).where(AgentMarketplaceListing.player_id == player_id)
        ).scalar_one_or_none()
        cleaned_note = self._clean(note)
        if listing is None:
            listing = AgentMarketplaceListing(
                player_id=player_id,
                agent_user_id=actor.id,
                is_available=is_available,
                asking_type=asking_type,
                note=cleaned_note,
            )
            self.session.add(listing)
        else:
            if listing.agent_user_id != actor.id:
                raise MarketplaceConflictError("This player is already claimed by another agent.")
            listing.is_available = is_available
            listing.asking_type = asking_type
            listing.note = cleaned_note
        self.session.commit()
        self.session.refresh(listing)
        return {
            "player_id": listing.player_id,
            "agent_user_id": listing.agent_user_id,
            "agent_name": self._display_name(actor),
            "is_available": listing.is_available,
            "asking_type": listing.asking_type,
            "note": listing.note,
            "updated_at": listing.updated_at,
        }

    def start_conversation(
        self,
        *,
        actor: User,
        player_id: str,
        message: str,
        actor_role: str | None = None,
    ) -> dict[str, object]:
        listing = self.session.execute(
            select(AgentMarketplaceListing).where(
                AgentMarketplaceListing.player_id == player_id,
                AgentMarketplaceListing.is_available.is_(True),
            )
        ).scalar_one_or_none()
        if listing is None:
            raise MarketplaceNotFoundError(f"Marketplace listing for player '{player_id}' was not found.")
        if listing.agent_user_id == actor.id:
            raise MarketplacePermissionError("Agents cannot initiate unrelated scout conversations from the marketplace.")

        normalized_role = self._resolve_initiator_role(actor=actor, requested_role=actor_role)
        message_text = self._validated_message(message)
        conversation = self.session.execute(
            select(PlayerConversation).where(
                PlayerConversation.player_id == player_id,
                PlayerConversation.agent_user_id == listing.agent_user_id,
                PlayerConversation.initiator_user_id == actor.id,
                PlayerConversation.initiator_role == normalized_role,
            )
        ).scalar_one_or_none()

        if conversation is None:
            conversation = PlayerConversation(
                player_id=player_id,
                agent_user_id=listing.agent_user_id,
                initiator_user_id=actor.id,
                initiator_role=normalized_role,
                status=PlayerConversationStatus.ACTIVE,
            )
            self.session.add(conversation)
            self.session.flush()
            self.session.add_all(
                [
                    PlayerConversationParticipant(
                        conversation_id=conversation.id,
                        user_id=actor.id,
                        role=normalized_role,
                        last_read_at=utcnow(),
                    ),
                    PlayerConversationParticipant(
                        conversation_id=conversation.id,
                        user_id=listing.agent_user_id,
                        role=ConversationParticipantRole.AGENT,
                    ),
                ]
            )

        created_at = utcnow()
        self.session.add(
            PlayerConversationMessage(
                conversation_id=conversation.id,
                sender_id=actor.id,
                message=message_text,
                created_at=created_at,
            )
        )
        conversation.last_message_at = created_at
        if conversation.status == PlayerConversationStatus.CLOSED:
            conversation.status = PlayerConversationStatus.ACTIVE
        self._mark_participant_read(conversation_id=conversation.id, user_id=actor.id, read_at=created_at)
        self.session.commit()
        return self.get_conversation_detail(conversation_id=conversation.id, actor=actor)

    def list_conversations(self, *, actor: User) -> list[dict[str, object]]:
        conversations = self.session.execute(
            select(PlayerConversation)
            .join(
                PlayerConversationParticipant,
                PlayerConversationParticipant.conversation_id == PlayerConversation.id,
            )
            .where(PlayerConversationParticipant.user_id == actor.id)
            .order_by(
                PlayerConversation.last_message_at.is_(None),
                PlayerConversation.last_message_at.desc(),
                PlayerConversation.updated_at.desc(),
            )
        ).scalars().all()
        if not conversations:
            return []
        return self._build_conversation_summaries(conversations=conversations, current_user_id=actor.id)

    def get_conversation_detail(self, *, conversation_id: str, actor: User) -> dict[str, object]:
        conversation = self._get_conversation_for_actor(conversation_id=conversation_id, actor=actor)
        read_at = utcnow()
        self._mark_participant_read(conversation_id=conversation.id, user_id=actor.id, read_at=read_at)
        self.session.commit()

        summary = self._build_conversation_summaries(
            conversations=[conversation],
            current_user_id=actor.id,
        )[0]
        messages = self.session.execute(
            select(PlayerConversationMessage)
            .where(PlayerConversationMessage.conversation_id == conversation.id)
            .order_by(PlayerConversationMessage.created_at.asc(), PlayerConversationMessage.id.asc())
        ).scalars().all()
        participants = {
            participant["user_id"]: participant
            for participant in summary["participants"]
        }
        return {
            "conversation": summary,
            "messages": [
                {
                    "id": message.id,
                    "conversation_id": message.conversation_id,
                    "sender_id": message.sender_id,
                    "sender_name": participants.get(message.sender_id, {}).get("display_name", message.sender_id),
                    "sender_role": participants.get(message.sender_id, {}).get("role", ConversationParticipantRole.SCOUT),
                    "message": message.message,
                    "created_at": message.created_at,
                }
                for message in messages
            ],
        }

    def send_message(
        self,
        *,
        conversation_id: str,
        actor: User,
        message: str,
    ) -> dict[str, object]:
        conversation = self._get_conversation_for_actor(conversation_id=conversation_id, actor=actor)
        message_text = self._validated_message(message)
        created_at = utcnow()
        self.session.add(
            PlayerConversationMessage(
                conversation_id=conversation.id,
                sender_id=actor.id,
                message=message_text,
                created_at=created_at,
            )
        )
        conversation.last_message_at = created_at
        if conversation.status == PlayerConversationStatus.CLOSED:
            conversation.status = PlayerConversationStatus.ACTIVE
        self._mark_participant_read(conversation_id=conversation.id, user_id=actor.id, read_at=created_at)
        self.session.commit()
        return self.get_conversation_detail(conversation_id=conversation.id, actor=actor)

    def update_conversation_status(
        self,
        *,
        conversation_id: str,
        actor: User,
        status: PlayerConversationStatus,
    ) -> dict[str, object]:
        conversation = self._get_conversation_for_actor(conversation_id=conversation_id, actor=actor)
        conversation.status = status
        self.session.commit()
        return self.get_conversation_detail(conversation_id=conversation.id, actor=actor)

    def _get_conversation_for_actor(self, *, conversation_id: str, actor: User) -> PlayerConversation:
        conversation = self.session.get(PlayerConversation, conversation_id)
        if conversation is None:
            raise MarketplaceNotFoundError(f"Conversation '{conversation_id}' was not found.")
        participant = self.session.execute(
            select(PlayerConversationParticipant).where(
                PlayerConversationParticipant.conversation_id == conversation.id,
                PlayerConversationParticipant.user_id == actor.id,
            )
        ).scalar_one_or_none()
        if participant is None:
            raise MarketplacePermissionError("You are not a participant in this conversation.")
        return conversation

    def _build_conversation_summaries(
        self,
        *,
        conversations: list[PlayerConversation],
        current_user_id: str,
    ) -> list[dict[str, object]]:
        conversation_ids = [conversation.id for conversation in conversations]
        player_ids = [conversation.player_id for conversation in conversations]

        participants = self.session.execute(
            select(PlayerConversationParticipant, User)
            .join(User, User.id == PlayerConversationParticipant.user_id)
            .where(PlayerConversationParticipant.conversation_id.in_(conversation_ids))
            .order_by(PlayerConversationParticipant.joined_at.asc())
        ).all()
        participants_by_conversation: dict[str, list[dict[str, object]]] = defaultdict(list)
        participant_reads: dict[tuple[str, str], object] = {}
        for participant, user in participants:
            payload = {
                "user_id": participant.user_id,
                "display_name": self._display_name(user),
                "role": participant.role,
                "last_read_at": participant.last_read_at,
            }
            participants_by_conversation[participant.conversation_id].append(payload)
            participant_reads[(participant.conversation_id, participant.user_id)] = participant.last_read_at

        messages = self.session.execute(
            select(PlayerConversationMessage)
            .where(PlayerConversationMessage.conversation_id.in_(conversation_ids))
            .order_by(PlayerConversationMessage.created_at.asc(), PlayerConversationMessage.id.asc())
        ).scalars().all()
        latest_message_by_conversation: dict[str, PlayerConversationMessage] = {}
        unread_count_by_conversation: dict[str, int] = defaultdict(int)
        for message in messages:
            latest_message_by_conversation[message.conversation_id] = message
            last_read_at = participant_reads.get((message.conversation_id, current_user_id))
            if message.sender_id != current_user_id and (last_read_at is None or message.created_at > last_read_at):
                unread_count_by_conversation[message.conversation_id] += 1

        player_context_by_player_id = self._load_player_contexts(player_ids)
        summaries: list[dict[str, object]] = []
        for conversation in conversations:
            latest_message = latest_message_by_conversation.get(conversation.id)
            summaries.append(
                {
                    "id": conversation.id,
                    "player": player_context_by_player_id[conversation.player_id],
                    "status": conversation.status,
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at,
                    "last_message_at": conversation.last_message_at,
                    "latest_message_preview": latest_message.message if latest_message is not None else None,
                    "unread_count": unread_count_by_conversation.get(conversation.id, 0),
                    "participants": participants_by_conversation.get(conversation.id, []),
                }
            )
        return summaries

    def _load_player_contexts(self, player_ids: list[str]) -> dict[str, dict[str, object]]:
        rows = self.session.execute(
            self._player_context_statement().where(Player.id.in_(player_ids))
        ).all()
        contexts = {
            player.id: {
                "player_id": player.id,
                "player_name": player.full_name,
                "position": profile.primary_position if profile is not None else player.position,
                "current_club_name": (
                    profile.current_club_name if profile is not None and profile.current_club_name else player.real_world_club_name
                ),
                "asking_type": listing.asking_type,
                "marketplace_note": listing.note,
                "agent_name": self._display_name(agent),
            }
            for player, profile, listing, agent in rows
        }
        missing = [player_id for player_id in player_ids if player_id not in contexts]
        if missing:
            raise MarketplaceNotFoundError(f"Marketplace context for players {missing} was not found.")
        return contexts

    def _player_context_statement(self):
        selected_profiles = self._selected_profiles_subquery()
        return (
            select(Player, RealPlayerProfile, AgentMarketplaceListing, User)
            .join(AgentMarketplaceListing, AgentMarketplaceListing.player_id == Player.id)
            .join(User, User.id == AgentMarketplaceListing.agent_user_id)
            .outerjoin(selected_profiles, selected_profiles.c.gtex_player_id == Player.id)
            .outerjoin(RealPlayerProfile, RealPlayerProfile.id == selected_profiles.c.profile_id)
            .where(Player.is_real_player.is_(True))
        )

    def _marketplace_player_statement(
        self,
        *,
        include_unavailable: bool,
        agent_user_id: str | None = None,
    ):
        selected_profiles = self._selected_profiles_subquery()
        statement = (
            select(
                Player,
                RealPlayerProfile,
                Country,
                PlayerSummaryReadModel,
                AgentMarketplaceListing,
                User,
            )
            .join(AgentMarketplaceListing, AgentMarketplaceListing.player_id == Player.id)
            .join(User, User.id == AgentMarketplaceListing.agent_user_id)
            .outerjoin(selected_profiles, selected_profiles.c.gtex_player_id == Player.id)
            .outerjoin(RealPlayerProfile, RealPlayerProfile.id == selected_profiles.c.profile_id)
            .outerjoin(Country, Country.id == Player.country_id)
            .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
            .where(Player.is_real_player.is_(True))
        )
        if not include_unavailable:
            statement = statement.where(AgentMarketplaceListing.is_available.is_(True))
        if agent_user_id is not None:
            statement = statement.where(AgentMarketplaceListing.agent_user_id == agent_user_id)
        return statement

    def _apply_player_filters(
        self,
        statement,
        *,
        search: str | None,
        position: str | None,
        country: str | None,
        min_age: int | None,
        max_age: int | None,
        availability: str | None,
    ):
        if position:
            statement = statement.where(
                or_(
                    Player.position.ilike(f"%{position.strip()}%"),
                    Player.normalized_position.ilike(f"%{position.strip()}%"),
                    RealPlayerProfile.primary_position.ilike(f"%{position.strip()}%"),
                )
            )
        if country:
            term = f"%{country.strip()}%"
            statement = statement.where(
                or_(
                    Country.name.ilike(term),
                    RealPlayerProfile.nationality.ilike(term),
                )
            )
        if min_age is not None:
            statement = statement.where(self._age_expr() >= min_age)
        if max_age is not None:
            statement = statement.where(self._age_expr() <= max_age)
        if availability and availability.strip().lower() == "free_agent":
            statement = statement.where(
                or_(
                    func.lower(func.coalesce(RealPlayerProfile.current_club_name, Player.real_world_club_name, "")) == "free agent",
                    func.lower(func.coalesce(RealPlayerProfile.current_club_name, Player.real_world_club_name, "")) == "free-agent",
                )
            )
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Player.full_name.ilike(term),
                    Player.canonical_display_name.ilike(term),
                    RealPlayerProfile.canonical_name.ilike(term),
                    Country.name.ilike(term),
                    RealPlayerProfile.current_club_name.ilike(term),
                    Player.real_world_club_name.ilike(term),
                    User.display_name.ilike(term),
                    User.full_name.ilike(term),
                    User.username.ilike(term),
                    AgentMarketplaceListing.note.ilike(term),
                    cast(RealPlayerProfile.known_aliases_json, String).ilike(term),
                )
            )
        return statement

    def _build_marketplace_player_view(
        self,
        player: Player,
        profile: RealPlayerProfile | None,
        country: Country | None,
        summary: PlayerSummaryReadModel | None,
        listing: AgentMarketplaceListing,
        agent: User,
    ) -> dict[str, object]:
        trend_score = None
        if summary is not None and summary.market_interest_score is not None:
            trend_score = float(summary.market_interest_score)
        return {
            "player_id": player.id,
            "player_name": player.full_name,
            "position": profile.primary_position if profile is not None and profile.primary_position else player.position,
            "nationality": country.name if country is not None else (profile.nationality if profile is not None else None),
            "current_club_name": (
                profile.current_club_name if profile is not None and profile.current_club_name else player.real_world_club_name
            ),
            "age": self._player_age(player.date_of_birth or (profile.date_of_birth if profile is not None else None)),
            "current_value_credits": summary.current_value_credits if summary is not None else None,
            "movement_pct": summary.movement_pct if summary is not None else None,
            "trend_score": trend_score,
            "market_interest_score": summary.market_interest_score if summary is not None else None,
            "average_rating": summary.average_rating if summary is not None else None,
            "is_available": listing.is_available,
            "availability_label": "Available now" if listing.is_available else "Unavailable",
            "asking_type": listing.asking_type,
            "marketplace_note": listing.note,
            "agent_user_id": listing.agent_user_id,
            "agent_name": self._display_name(agent),
            "updated_at": listing.updated_at,
        }

    def _selected_profiles_subquery(self):
        ranked_profiles = (
            select(
                RealPlayerProfile.id.label("profile_id"),
                RealPlayerProfile.gtex_player_id.label("gtex_player_id"),
                func.row_number()
                .over(
                    partition_by=RealPlayerProfile.gtex_player_id,
                    order_by=(
                        RealPlayerProfile.source_last_refreshed_at.is_(None),
                        RealPlayerProfile.source_last_refreshed_at.desc(),
                        RealPlayerProfile.updated_at.desc(),
                        RealPlayerProfile.id.desc(),
                    ),
                )
                .label("profile_rank"),
            )
            .subquery()
        )
        return (
            select(ranked_profiles.c.profile_id, ranked_profiles.c.gtex_player_id)
            .where(ranked_profiles.c.profile_rank == 1)
            .subquery()
        )

    def _order_by(self, *, sort: str):
        name_expr = func.lower(Player.full_name)
        if sort == "market_interest":
            return (
                PlayerSummaryReadModel.market_interest_score.is_(None),
                PlayerSummaryReadModel.market_interest_score.desc(),
                AgentMarketplaceListing.updated_at.desc(),
                name_expr.asc(),
            )
        if sort == "name":
            return (name_expr.asc(), AgentMarketplaceListing.updated_at.desc())
        return (
            AgentMarketplaceListing.updated_at.desc(),
            PlayerSummaryReadModel.market_interest_score.is_(None),
            PlayerSummaryReadModel.market_interest_score.desc(),
            name_expr.asc(),
        )

    def _age_expr(self):
        reference_year = self.today.year if self.today is not None else date.today().year
        return reference_year - cast(
            func.strftime("%Y", func.coalesce(RealPlayerProfile.date_of_birth, Player.date_of_birth)),
            Integer,
        )

    def _player_age(self, value: date | None) -> int | None:
        if value is None:
            return None
        reference_date = self.today or date.today()
        return (
            reference_date.year
            - value.year
            - ((reference_date.month, reference_date.day) < (value.month, value.day))
        )

    def _resolve_offset(self, *, cursor: str | None, offset: int) -> int:
        raw_cursor = self._clean(cursor)
        if raw_cursor is None:
            return offset
        try:
            return int(raw_cursor)
        except ValueError as exc:
            raise MarketplaceValidationError("cursor is invalid") from exc

    def _resolve_initiator_role(
        self,
        *,
        actor: User,
        requested_role: str | None,
    ) -> ConversationParticipantRole:
        role = self._clean(requested_role)
        if role is None:
            return ConversationParticipantRole.CLUB if self._user_has_club(actor.id) else ConversationParticipantRole.SCOUT
        if role == ConversationParticipantRole.SCOUT.value:
            return ConversationParticipantRole.SCOUT
        if role == ConversationParticipantRole.CLUB.value:
            if not self._user_has_club(actor.id):
                raise MarketplacePermissionError("Only club-linked users can start conversations as a club.")
            return ConversationParticipantRole.CLUB
        raise MarketplacePermissionError("Marketplace conversations can only be started by scouts or clubs.")

    def _user_has_club(self, user_id: str) -> bool:
        return self.session.execute(
            select(ClubProfile.id).where(ClubProfile.owner_user_id == user_id).limit(1)
        ).scalar_one_or_none() is not None

    def _validated_message(self, message: str) -> str:
        cleaned = self._clean(message)
        if cleaned is None:
            raise MarketplaceValidationError("message cannot be blank")
        if len(cleaned) > 4000:
            raise MarketplaceValidationError("message cannot exceed 4000 characters")
        return cleaned

    def _mark_participant_read(self, *, conversation_id: str, user_id: str, read_at) -> None:
        participant = self.session.execute(
            select(PlayerConversationParticipant).where(
                PlayerConversationParticipant.conversation_id == conversation_id,
                PlayerConversationParticipant.user_id == user_id,
            )
        ).scalar_one_or_none()
        if participant is not None:
            participant.last_read_at = read_at

    def _display_name(self, user: User) -> str:
        for candidate in (user.display_name, user.full_name, user.username, user.email):
            cleaned = self._clean(candidate)
            if cleaned is not None:
                return cleaned
        return user.id

    def _clean(self, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
