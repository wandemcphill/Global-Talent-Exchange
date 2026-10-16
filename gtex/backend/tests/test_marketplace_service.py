from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ingestion.models import Country, Player
from app.marketplace.service import (
    AgentMarketplaceService,
    MarketplacePermissionError,
)
from app.models import Base
from app.models.agent_marketplace import (
    AgentAskingType,
    AgentMarketplaceListing,
    PlayerConversation,
    PlayerConversationMessage,
    PlayerConversationParticipant,
)
from app.models.club_profile import ClubProfile
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.models.user import User, UserRole
from app.players.read_models import PlayerSummaryReadModel


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Country.__table__,
            Player.__table__,
            RealPlayerSourceLink.__table__,
            RealPlayerProfile.__table__,
            PlayerSummaryReadModel.__table__,
            ClubProfile.__table__,
            AgentMarketplaceListing.__table__,
            PlayerConversation.__table__,
            PlayerConversationParticipant.__table__,
            PlayerConversationMessage.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as active_session:
        yield active_session


def _make_user(*, user_id: str, username: str, display_name: str) -> User:
    return User(
        id=user_id,
        email=f"{username}@example.com",
        username=username,
        display_name=display_name,
        password_hash="not-used",
        role=UserRole.USER,
        is_active=True,
    )


def _seed_marketplace_player(
    session: Session,
    *,
    player_id: str,
    player_name: str,
    country_name: str = "Nigeria",
    club_name: str = "Free Agent",
) -> Player:
    country = Country(
        id=f"country-{player_id}",
        source_provider="test",
        provider_external_id=f"country-{player_id}",
        name=country_name,
        alpha2_code="NG",
        alpha3_code="NGA",
        fifa_code="NGA",
    )
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=f"player-{player_id}",
        country_id=country.id,
        full_name=player_name,
        position="ST",
        normalized_position="st",
        date_of_birth=date(2001, 5, 17),
        is_real_player=True,
        real_world_club_name=club_name,
        canonical_display_name=player_name,
    )
    source_link = RealPlayerSourceLink(
        id=f"link-{player_id}",
        gtex_player_id=player.id,
        source_name="test",
        source_player_key=f"source-{player_id}",
        canonical_name=player_name,
        nationality=country_name,
        primary_position="ST",
        current_real_world_club=club_name,
    )
    profile = RealPlayerProfile(
        id=f"profile-{player_id}",
        gtex_player_id=player.id,
        source_link_id=source_link.id,
        source_name="test",
        source_player_key=f"source-{player_id}",
        canonical_name=player_name,
        nationality=country_name,
        primary_position="ST",
        current_club_name=club_name,
        current_league_name="Test League",
    )
    summary = PlayerSummaryReadModel(
        player_id=player.id,
        player_name=player_name,
        current_club_name=club_name,
        last_snapshot_at=datetime(2026, 3, 26, tzinfo=timezone.utc),
        current_value_credits=125000.0,
        previous_value_credits=120000.0,
        movement_pct=4.2,
        average_rating=7.1,
        market_interest_score=84,
    )
    session.add_all([country, player, source_link, profile, summary])
    session.flush()
    return player


def test_list_players_returns_agent_metadata_and_filters_available(session: Session) -> None:
    agent = _make_user(user_id="agent-1", username="agent1", display_name="Prime Sports")
    other_agent = _make_user(user_id="agent-2", username="agent2", display_name="Hidden Agency")
    session.add_all([agent, other_agent])
    active_player = _seed_marketplace_player(session, player_id="player-1", player_name="John Doe")
    inactive_player = _seed_marketplace_player(
        session,
        player_id="player-2",
        player_name="Mark Hill",
        club_name="Port Town",
    )
    session.add_all(
        [
            AgentMarketplaceListing(
                player_id=active_player.id,
                agent_user_id=agent.id,
                is_available=True,
                asking_type=AgentAskingType.TRIAL,
                note="Open to trials",
            ),
            AgentMarketplaceListing(
                player_id=inactive_player.id,
                agent_user_id=other_agent.id,
                is_available=False,
                asking_type=AgentAskingType.TRANSFER,
                note="Already in negotiations",
            ),
        ]
    )
    session.commit()

    service = AgentMarketplaceService(session=session, today=date(2026, 3, 26))
    result = service.list_players(limit=20, availability="free_agent")

    assert result["total"] == 1
    item = result["items"][0]
    assert item["player_name"] == "John Doe"
    assert item["asking_type"] == AgentAskingType.TRIAL
    assert item["availability_label"] == "Available now"
    assert item["marketplace_note"] == "Open to trials"
    assert item["agent_name"] == "Prime Sports"


def test_start_conversation_infers_club_role_for_club_owner(session: Session) -> None:
    agent = _make_user(user_id="agent-1", username="agent1", display_name="Prime Sports")
    club_owner = _make_user(user_id="club-1", username="club1", display_name="Atlas FC")
    session.add_all([agent, club_owner])
    player = _seed_marketplace_player(session, player_id="player-1", player_name="John Doe")
    session.add(
        ClubProfile(
            id="club-profile-1",
            owner_user_id=club_owner.id,
            club_name="Atlas FC",
            short_name="Atlas",
            slug="atlas-fc",
            primary_color="#000000",
            secondary_color="#ffffff",
            accent_color="#ff8800",
        )
    )
    session.add(
        AgentMarketplaceListing(
            player_id=player.id,
            agent_user_id=agent.id,
            is_available=True,
            asking_type=AgentAskingType.TRIAL,
            note="Can arrange a trial window",
        )
    )
    session.commit()

    service = AgentMarketplaceService(session=session, today=date(2026, 3, 26))
    detail = service.start_conversation(
        actor=club_owner,
        player_id=player.id,
        message="Can we arrange a trial next month?",
    )

    conversation = detail["conversation"]
    assert conversation["status"].value == "active"
    assert conversation["player"]["asking_type"] == AgentAskingType.TRIAL
    assert {participant["role"].value for participant in conversation["participants"]} == {"club", "agent"}
    assert detail["messages"][0]["sender_role"].value == "club"
    assert detail["messages"][0]["message"] == "Can we arrange a trial next month?"

    agent_conversations = service.list_conversations(actor=agent)
    assert len(agent_conversations) == 1
    assert agent_conversations[0]["unread_count"] == 1


def test_agent_cannot_start_conversation_but_can_reply_when_participant(session: Session) -> None:
    agent = _make_user(user_id="agent-1", username="agent1", display_name="Prime Sports")
    scout = _make_user(user_id="scout-1", username="scout1", display_name="North Scout")
    session.add_all([agent, scout])
    player = _seed_marketplace_player(session, player_id="player-1", player_name="John Doe")
    session.add(
        AgentMarketplaceListing(
            player_id=player.id,
            agent_user_id=agent.id,
            is_available=True,
            asking_type=AgentAskingType.TRANSFER,
            note="Looking for European move",
        )
    )
    session.commit()

    service = AgentMarketplaceService(session=session, today=date(2026, 3, 26))

    with pytest.raises(MarketplacePermissionError):
        service.start_conversation(
            actor=agent,
            player_id=player.id,
            message="I want to pitch this player.",
        )

    started = service.start_conversation(
        actor=scout,
        player_id=player.id,
        message="Interested in this player",
        actor_role="scout",
    )
    conversation_id = started["conversation"]["id"]

    agent_view = service.get_conversation_detail(conversation_id=conversation_id, actor=agent)
    assert agent_view["conversation"]["unread_count"] == 0

    replied = service.send_message(
        conversation_id=conversation_id,
        actor=agent,
        message="Yes, the player is available for a transfer.",
    )

    assert replied["messages"][-1]["sender_role"].value == "agent"
    scout_conversations = service.list_conversations(actor=scout)
    assert scout_conversations[0]["unread_count"] == 1
