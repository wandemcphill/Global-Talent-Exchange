from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.models.player_cards  # noqa: F401
import app.models.real_world_football  # noqa: F401
import app.models.user  # noqa: F401
from app.models.calendar_engine import CalendarEvent
from app.football_events_engine.service import (
    EventCategoryToggle,
    RealWorldFootballEventCreate,
    RealWorldFootballEventService,
)
from app.ingestion.models import MarketSignal, Player
from app.models.base import Base
from app.models.player_cards import PlayerCard, PlayerCardFormBuff, PlayerCardTier
from app.models.real_world_football import PlayerDemandSignal, PlayerFormModifier, RealWorldFootballEvent, TrendingPlayerFlag
from app.models.story_feed import StoryFeedItem
from app.models.user import User, UserRole
from app.player_cards.service import PlayerCardMarketService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        yield db_session
    engine.dispose()


def _seed_admin(session) -> User:
    admin = User(
        id="admin-user",
        email="admin@example.com",
        username="admin",
        password_hash="x",
        role=UserRole.ADMIN,
    )
    session.add(admin)
    session.flush()
    return admin


def _seed_player_with_card(session) -> Player:
    player = Player(
        id="player-1",
        source_provider="test",
        provider_external_id="player-1",
        full_name="Ayo Striker",
        short_name="A. Striker",
        is_tradable=True,
    )
    tier = PlayerCardTier(
        id="tier-elite",
        code="elite",
        name="Elite",
        rarity_rank=1,
        max_supply=1000,
        supply_multiplier=1.0,
        base_mint_price_credits=Decimal("10.0"),
        color_hex="#FFD700",
        is_active=True,
        metadata_json={},
    )
    card = PlayerCard(
        id="card-1",
        player_id=player.id,
        tier_id=tier.id,
        edition_code="base",
        display_name="Ayo Striker Elite",
        season_label="2026",
        card_variant="base",
        supply_total=10,
        supply_available=10,
        is_active=True,
        metadata_json={},
    )
    session.add_all([player, tier, card])
    session.flush()
    return player


def _service(session) -> RealWorldFootballEventService:
    service = RealWorldFootballEventService(session)
    service.seed_defaults()
    return service


def test_event_normalization_canonicalizes_type_and_defaults_title(session) -> None:
    _seed_player_with_card(session)
    service = _service(session)

    normalized = service.normalize_event(
        RealWorldFootballEventCreate(
            event_type="Hat Trick",
            player_id="player-1",
            occurred_at=datetime(2026, 3, 16, 14, 0, tzinfo=UTC),
        )
    )

    assert normalized.event_type == "hat_trick"
    assert normalized.title == "Ayo Striker hit a hat trick"
    assert normalized.requires_admin_review is False
    assert normalized.normalized_payload_json["rule_effect_codes"]


def test_hat_trick_creates_modifier_flag_demand_signal_and_card_buff(session) -> None:
    admin = _seed_admin(session)
    _seed_player_with_card(session)
    service = _service(session)

    event = service.create_event(
        RealWorldFootballEventCreate(
            event_type="hat trick",
            player_id="player-1",
            occurred_at=datetime(2026, 3, 16, 15, 0, tzinfo=UTC),
        ),
        actor=admin,
    )

    modifiers = session.scalars(select(PlayerFormModifier).where(PlayerFormModifier.event_id == event.id)).all()
    flags = session.scalars(select(TrendingPlayerFlag).where(TrendingPlayerFlag.event_id == event.id)).all()
    signals = session.scalars(select(PlayerDemandSignal).where(PlayerDemandSignal.event_id == event.id)).all()
    card_buffs = session.scalars(select(PlayerCardFormBuff)).all()

    assert event.approval_status == "approved"
    assert len(modifiers) == 1
    assert len(flags) == 1
    assert len(signals) == 1
    assert len(card_buffs) == 1
    assert modifiers[0].modifier_type == "hot_player_of_the_week"
    assert signals[0].market_buzz_score > 0


def test_modifier_expiry_marks_records_expired_and_removes_card_buff(session) -> None:
    admin = _seed_admin(session)
    _seed_player_with_card(session)
    service = _service(session)
    occurred_at = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    event = service.create_event(
        RealWorldFootballEventCreate(
            event_type="big debut",
            player_id="player-1",
            occurred_at=occurred_at,
        ),
        actor=admin,
    )

    result = service.expire_effects(as_of=occurred_at + timedelta(days=10))
    modifier = session.scalar(select(PlayerFormModifier).where(PlayerFormModifier.event_id == event.id))

    assert result["expired_form_modifiers"] >= 1
    assert modifier is not None
    assert modifier.status == "expired"
    assert session.scalars(select(PlayerCardFormBuff)).all() == []


def test_player_impact_exposes_trending_assignment(session) -> None:
    admin = _seed_admin(session)
    _seed_player_with_card(session)
    service = _service(session)
    service.create_event(
        RealWorldFootballEventCreate(
            event_type="form surge",
            player_id="player-1",
            occurred_at=datetime(2026, 3, 16, 11, 0, tzinfo=UTC),
        ),
        actor=admin,
    )

    impact = service.get_player_impact("player-1")

    assert "trending" in impact.active_flag_codes
    assert impact.gameplay_effect_total > 0


def test_sensitive_event_requires_review_and_admin_override_reapplies_effects(session) -> None:
    admin = _seed_admin(session)
    _seed_player_with_card(session)
    service = _service(session)
    event = service.create_event(
        RealWorldFootballEventCreate(
            event_type="transfer rumor",
            player_id="player-1",
            occurred_at=datetime(2026, 3, 16, 10, 0, tzinfo=UTC),
        ),
        actor=admin,
    )

    assert event.approval_status == "pending_review"
    service.review_event(event.id, actor=admin, approve=True, notes="confirmed by admin")
    signal = session.scalar(select(PlayerDemandSignal).where(PlayerDemandSignal.event_id == event.id))
    story = session.scalar(
        select(StoryFeedItem).where(
            StoryFeedItem.subject_type == "real_world_football_event",
            StoryFeedItem.subject_id == event.id,
        )
    )
    calendar_event = session.scalar(
        select(CalendarEvent).where(
            CalendarEvent.source_type == "real_world_football_event",
            CalendarEvent.source_id == event.id,
        )
    )
    assert signal is not None
    assert story is not None
    assert calendar_event is None
    assert story.story_type == "transfer_rumor"
    assert event.metadata_json["story_feed_item_id"] == story.id
    assert signal.demand_score == pytest.approx(7.0)

    service.override_event_severity(event.id, actor=admin, severity=0.5)
    updated_signal = session.scalar(select(PlayerDemandSignal).where(PlayerDemandSignal.event_id == event.id, PlayerDemandSignal.status == "active"))
    assert updated_signal is not None
    assert updated_signal.demand_score == pytest.approx(3.5)


def test_confirmed_transfer_review_publishes_story_and_calendar_event(session) -> None:
    admin = _seed_admin(session)
    _seed_player_with_card(session)
    service = _service(session)
    event = service.create_event(
        RealWorldFootballEventCreate(
            event_type="confirmed transfer",
            player_id="player-1",
            occurred_at=datetime(2026, 3, 16, 13, 0, tzinfo=UTC),
        ),
        actor=admin,
    )

    assert event.approval_status == "pending_review"
    service.review_event(event.id, actor=admin, approve=True, notes="transfer confirmed")

    story = session.scalar(
        select(StoryFeedItem).where(
            StoryFeedItem.subject_type == "real_world_football_event",
            StoryFeedItem.subject_id == event.id,
        )
    )
    calendar_event = session.scalar(
        select(CalendarEvent).where(
            CalendarEvent.source_type == "real_world_football_event",
            CalendarEvent.source_id == event.id,
        )
    )

    assert story is not None
    assert calendar_event is not None
    assert story.story_type == "transfer_news"
    assert event.metadata_json["story_feed_item_id"] == story.id
    assert event.metadata_json["calendar_event_id"] == calendar_event.id


def test_demand_signal_generation_mirrors_positive_market_signal_and_category_disable_revokes(session) -> None:
    admin = _seed_admin(session)
    _seed_player_with_card(session)
    service = _service(session)
    event = service.create_event(
        RealWorldFootballEventCreate(
            event_type="breakout performance",
            player_id="player-1",
            occurred_at=datetime(2026, 3, 16, 9, 0, tzinfo=UTC),
        ),
        actor=admin,
    )

    signal = session.scalar(select(PlayerDemandSignal).where(PlayerDemandSignal.event_id == event.id))
    mirrored = session.scalar(select(MarketSignal).where(MarketSignal.provider_external_id == signal.id))

    assert signal is not None
    assert signal.scouting_interest_delta > 0
    assert signal.recommendation_priority_delta > 0
    assert mirrored is not None
    assert mirrored.score > 0

    service.set_event_category_enabled(EventCategoryToggle(event_type="breakout performance", is_enabled=False), actor=admin)
    refreshed_event = session.get(RealWorldFootballEvent, event.id)
    assert refreshed_event is not None
    impact = service.get_player_impact("player-1")
    assert impact.active_demand_signals == ()


def test_player_card_detail_surfaces_real_world_visibility(session) -> None:
    admin = _seed_admin(session)
    _seed_player_with_card(session)
    service = _service(session)
    service.create_event(
        RealWorldFootballEventCreate(
            event_type="hat trick",
            player_id="player-1",
            occurred_at=datetime(2026, 3, 16, 16, 0, tzinfo=UTC),
        ),
        actor=admin,
    )

    detail = PlayerCardMarketService(session=session).get_player_detail(player_id="player-1")

    assert detail["real_world_flags"]
    assert detail["real_world_form_modifiers"]
    assert detail["demand_signals"]
    assert detail["market_buzz_score"] > 0
