from __future__ import annotations

from decimal import Decimal

import app.models  # noqa: F401
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai_reporter.service import AIReporterService
from app.ingestion.models import Player
from app.models.base import Base
from app.models.player_cards import PlayerCard, PlayerCardListing, PlayerCardTier
from app.models.user import User


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def test_ai_reporter_publishes_transfer_listing_once(session) -> None:
    seller = User(id="seller", email="seller@example.com", username="seller", password_hash="hashed")
    player = Player(
        id="player-news",
        source_provider="test",
        provider_external_id="player-news",
        full_name="Future Star",
        position="ST",
        normalized_position="st",
        is_tradable=True,
        is_real_player=False,
    )
    tier = PlayerCardTier(
        id="tier-news",
        code="elite-news",
        name="Elite News",
        rarity_rank=1,
        max_supply=100,
        supply_multiplier=1.0,
        base_mint_price_credits=Decimal("10.0000"),
        is_active=True,
        metadata_json={},
    )
    card = PlayerCard(
        id="card-news",
        player_id=player.id,
        tier_id=tier.id,
        edition_code="regen",
        display_name="Future Star Elite News",
        card_variant="regen_unique",
        supply_total=1,
        supply_available=1,
        is_active=True,
        metadata_json={},
    )
    listing = PlayerCardListing(
        listing_id="listing-news",
        player_card_id=card.id,
        seller_user_id=seller.id,
        quantity=1,
        price_per_card_credits=Decimal("42.0000"),
        status="open",
        is_negotiable=True,
        integrity_context_json={},
        metadata_json={},
    )
    session.add_all([seller, player, tier, card, listing])
    session.flush()

    service = AIReporterService(session)
    first = service.run_daily_digest(beats=["transfer_listings"], limit_per_beat=1)
    second = service.run_daily_digest(beats=["transfer_listings"], limit_per_beat=1)

    assert first.generated_count == 1
    assert first.items[0].story_type == "ai_reporter_transfer_listing"
    assert "Future Star" in first.items[0].title
    assert first.items[0].metadata_json["cost_tier"] == "zero-cost"
    assert second.generated_count == 0
    assert second.skipped_duplicate_count == 1
    assert service.list_reporter_feed(beat="transfer_listings")[0].subject_id == "listing-news"

