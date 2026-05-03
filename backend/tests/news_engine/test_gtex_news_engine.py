from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from time import perf_counter

import app.models  # noqa: F401
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ingestion.models import Player
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.player_cards import PlayerCard, PlayerCardListing, PlayerCardTier, PlayerStatsSnapshot
from app.models.regen import RegenProfile
from app.models.user import User
from app.services.gtex_news_engine import (
    GTEXNewsEngineService,
    GTEXNewsRateLimitError,
    generate_listing,
    here_we_go_story,
)
from app.services.personalized_feed import rank_for_user


class MemoryCache:
    enabled = True

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.counts: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        del ttl_seconds
        self.values[key] = value

    def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self.values.pop(key, None)

    def increment(self, key: str, amount: int = 1, ttl_seconds: int | None = None) -> int:
        del ttl_seconds
        self.counts[key] = self.counts.get(key, 0) + amount
        return self.counts[key]

    def ping(self) -> bool:
        return True


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


def test_generate_listing_is_deterministic_and_schema_stable() -> None:
    data = {
        "player": {
            "id": "regen-news-1",
            "name": "Tayo Mensah",
            "club": "Lagos Stars",
            "potential": 91,
            "form": "hot",
            "morale": 77,
            "is_regen": True,
            "is_unhappy": False,
            "loyalty": 64,
        }
    }

    started = perf_counter()
    first = generate_listing(data)
    elapsed = perf_counter() - started
    second = generate_listing(data)

    assert first == second
    assert elapsed < 0.2
    assert set(first) == {
        "id",
        "headline",
        "body",
        "type",
        "priority",
        "club",
        "player_id",
        "player_name",
        "is_regen",
        "journalist",
        "created_at",
        "metadata",
    }
    assert first["type"] == "regen"
    assert first["is_regen"] is True


def test_here_we_go_only_triggers_when_deal_is_genuinely_ready() -> None:
    player = {"id": "p1", "name": "Rare Gem", "is_regen": True}

    assert (
        here_we_go_story(
            player,
            "Sangotedo FC",
            deal_score=0.91,
            player_agrees_terms=True,
            club_funds_available=True,
        )
        is not None
    )
    assert (
        here_we_go_story(
            player,
            "Sangotedo FC",
            deal_score=0.91,
            player_agrees_terms=False,
            club_funds_available=True,
        )
        is None
    )


def test_daily_news_prioritizes_regens_and_uses_cache(session) -> None:
    owner = User(id="owner-news", email="owner-news@example.com", username="ownernews", password_hash="hashed")
    club = ClubProfile(
        id="club-news",
        owner_user_id=owner.id,
        club_name="Lagos Stars",
        slug="lagos-stars",
        primary_color="#101010",
        secondary_color="#ffffff",
        accent_color="#0aa",
        country_code="NG",
        region_name="Lagos",
        city_name="Sangotedo",
    )
    player = Player(
        id="regen-player-news",
        source_provider="test",
        provider_external_id="regen-player-news",
        full_name="Quantum Kid",
        position="ST",
        normalized_position="st",
        morale=82,
        is_tradable=True,
        is_real_player=False,
    )
    tier = PlayerCardTier(
        id="tier-news",
        code="regen-news",
        name="Regen News",
        rarity_rank=1,
        max_supply=1,
        supply_multiplier=1.0,
        base_mint_price_credits=Decimal("0.0000"),
        is_active=True,
        metadata_json={},
    )
    card = PlayerCard(
        id="card-news",
        player_id=player.id,
        tier_id=tier.id,
        edition_code="regen",
        display_name="Quantum Kid Regen",
        card_variant="regen_unique",
        supply_total=1,
        supply_available=1,
        is_active=True,
        metadata_json={},
    )
    regen = RegenProfile(
        id="regen-news",
        regen_id="regen-news",
        player_id=player.id,
        linked_unique_card_id=card.id,
        generated_for_club_id=club.id,
        birth_country_code="NG",
        primary_position="ST",
        secondary_positions_json=[],
        current_gsi=86,
        current_ability_range_json={"minimum": 80, "maximum": 87},
        potential_range_json={"minimum": 88, "maximum": 94},
        scout_confidence="high",
        generation_source="academy",
        metadata_json={},
    )
    stats = PlayerStatsSnapshot(
        player_id=player.id,
        as_of=datetime.now(timezone.utc),
        source_type="test",
        stats_json={"goals_last_3": 5},
    )
    listing = PlayerCardListing(
        listing_id="listing-news",
        player_card_id=card.id,
        seller_user_id=owner.id,
        quantity=1,
        price_per_card_credits=Decimal("250.0000"),
        status="open",
        is_negotiable=True,
        integrity_context_json={},
        metadata_json={"target_club": "Ajah United", "leak_stage": 3},
    )
    session.add_all([owner, club, player, tier, card, regen, stats, listing])
    session.flush()
    cache = MemoryCache()
    service = GTEXNewsEngineService(session, cache_backend=cache)

    first = service.daily_news(user_id="viewer", force=True)
    second = service.daily_news(user_id="viewer", force=False)
    all_stories = [*first["breaking"], *first["top_stories"], *first["rumors"]]

    assert first == second
    assert any(story["is_regen"] for story in all_stories)
    assert any("Quantum Kid" in story["headline"] for story in all_stories)
    assert any(story["type"] in {"regen", "form"} for story in all_stories)


def test_listing_generation_rate_limits_per_listing(session) -> None:
    service = GTEXNewsEngineService(session, cache_backend=MemoryCache())

    for index in range(5):
        service.generate_listing_with_cache(
            {
                "listing_type": "transfer",
                "stage": 2,
                "nonce": index,
                "player": {"id": "regen-rate", "name": "Rate Test", "is_regen": True},
            },
            user_id="viewer",
            listing_id="listing-rate",
        )

    with pytest.raises(GTEXNewsRateLimitError):
        service.generate_listing_with_cache(
            {
                "listing_type": "transfer",
                "stage": 2,
                "nonce": "blocked",
                "player": {"id": "regen-rate", "name": "Rate Test", "is_regen": True},
            },
            user_id="viewer",
            listing_id="listing-rate",
        )


def test_story_memory_mutates_duplicate_headlines_within_48h(session) -> None:
    cache = MemoryCache()
    service = GTEXNewsEngineService(session, cache_backend=cache)
    story = {
        "id": "story-1",
        "headline": "Wonderkid explodes onto the scene",
        "body": "A first version.",
        "type": "regen",
        "priority": 8,
        "club": "Lagos Stars",
        "player_id": "regen-memory",
        "player_name": "Memory Kid",
        "is_regen": True,
        "journalist": "Ada Okonkwo",
        "created_at": None,
        "metadata": {},
    }

    first = service._apply_story_memory([story], scope="test-memory")
    second = service._apply_story_memory([story], scope="test-memory")

    assert first[0]["headline"] == "Wonderkid explodes onto the scene"
    assert second[0]["headline"] != first[0]["headline"]
    assert second[0]["metadata"]["story_memory"]["mutation_index"] > 0


def test_personalized_feed_boosts_favorite_club_and_watched_player() -> None:
    stories = [
        {
            "headline": "Neutral story",
            "body": "A quiet update.",
            "type": "market",
            "priority": 4,
            "club": "Elsewhere FC",
            "player_id": "p0",
            "player_name": "Other Player",
            "metadata": {},
        },
        {
            "headline": "Quantum Kid sparks Lagos Stars debate",
            "body": "Lagos Stars fans are alive.",
            "type": "regen",
            "priority": 4,
            "club": "Lagos Stars",
            "player_id": "regen-player-news",
            "player_name": "Quantum Kid",
            "is_regen": True,
            "metadata": {},
        },
    ]

    ranked = rank_for_user(
        stories,
        {
            "user_id": "viewer",
            "favorite_club": "Lagos Stars",
            "watched_players": ["Quantum Kid"],
            "rival_clubs": [],
        },
    )

    assert ranked[0]["player_name"] == "Quantum Kid"
    assert ranked[0]["priority"] == 10
    assert ranked[0]["metadata"]["personalization"]["boost"] == 6


def test_breaking_news_surfaces_wonderkid_explosion(session) -> None:
    owner = User(id="owner-breaking", email="owner-breaking@example.com", username="ownerbreaking", password_hash="hashed")
    club = ClubProfile(
        id="club-breaking",
        owner_user_id=owner.id,
        club_name="Ajah United",
        slug="ajah-united",
        primary_color="#101010",
        secondary_color="#ffffff",
        accent_color="#0aa",
        country_code="NG",
        region_name="Lagos",
        city_name="Ajah",
    )
    player = Player(
        id="regen-breaking-player",
        source_provider="test",
        provider_external_id="regen-breaking-player",
        full_name="Breaking Kid",
        position="ST",
        normalized_position="st",
        morale=90,
        is_tradable=True,
        is_real_player=False,
    )
    tier = PlayerCardTier(
        id="tier-breaking",
        code="regen-breaking",
        name="Regen Breaking",
        rarity_rank=1,
        max_supply=1,
        supply_multiplier=1.0,
        base_mint_price_credits=Decimal("0.0000"),
        is_active=True,
        metadata_json={},
    )
    card = PlayerCard(
        id="card-breaking",
        player_id=player.id,
        tier_id=tier.id,
        edition_code="regen",
        display_name="Breaking Kid Regen",
        card_variant="regen_unique",
        supply_total=1,
        supply_available=1,
        is_active=True,
        metadata_json={},
    )
    regen = RegenProfile(
        id="regen-breaking",
        regen_id="regen-breaking",
        player_id=player.id,
        linked_unique_card_id=card.id,
        generated_for_club_id=club.id,
        birth_country_code="NG",
        primary_position="ST",
        secondary_positions_json=[],
        current_gsi=89,
        current_ability_range_json={"minimum": 84, "maximum": 90},
        potential_range_json={"minimum": 90, "maximum": 96},
        scout_confidence="high",
        generation_source="academy",
        metadata_json={},
    )
    stats = PlayerStatsSnapshot(
        player_id=player.id,
        as_of=datetime.now(timezone.utc),
        source_type="test",
        stats_json={"goals_last_3": 6},
    )
    session.add_all([owner, club, player, tier, card, regen, stats])
    session.flush()

    breaking = GTEXNewsEngineService(session, cache_backend=MemoryCache()).breaking_news(force=True)

    assert any("Breaking Kid" in story["headline"] for story in breaking)
    assert all(int(story["priority"]) >= 8 for story in breaking)
