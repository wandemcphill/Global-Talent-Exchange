"""National-pool seeds carry a full profile and a working dossier.

Before this, `GET /regen-universe/players/{id}` resolved only through
`RegenProfile`, so every national seed 404ed and the regen dossier was dark for
the bulk of the regen population. These pin the fix, and pin the two things it
must not do: invent values that contradict the seed's own card, and create
economy rows.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models.regen import RegenProfile
from app.models.regen_ecosystem import NationalRegenSeed
from app.regen_universe.seed_profile_service import (
    RegenSeedProfileService,
    build_seed_profile_view,
)
from app.regen_universe.service import RegenUniverseService
from tests.regen_universe_support import build_regen_universe_session


def _make_seed(session, *, suffix: str = "1", age: int = 18) -> NationalRegenSeed:
    seed = NationalRegenSeed(
        seed_key=f"test_batch:NGA:u20:AM:{suffix}",
        display_name=f"Test Seed {suffix}",
        age=age,
        age_band="u20",
        country_code="NGA",
        country_name="Nigeria",
        confederation_code="CAF",
        seed_type="preseeded_national_pool",
        generation_index=1,
        primary_position="AM",
        secondary_positions_json=["CM"],
        current_rating=71,
        potential_rating=88,
        growth_curve=0.62,
        personality_seed_json={
            "temperament": 55,
            "ambition": 81,
            "resilience": 63,
            "work_rate": 74,
            "media_appetite": 40,
            "story_seed": {
                "background": "academy product",
                "temperament": "calm",
                "ambition": "top_flight",
                "pressure_response": "steady",
                "snippet": "A calm academy product with top-flight ambition.",
            },
        },
        rarity_tier="rare",
        status="active",
        preseed_batch="test_batch",
        metadata_json={},
    )
    session.add(seed)
    session.commit()
    return seed


def test_seed_profile_matches_the_card_the_dossier_was_opened_from() -> None:
    session = build_regen_universe_session()
    try:
        seed = _make_seed(session)
        view = build_seed_profile_view(seed)

        # Anything the seed already publishes must survive verbatim: a dossier
        # that disagreed with its own card would be worse than no dossier.
        assert view.display_name == seed.display_name
        assert view.age == seed.age
        assert view.primary_position == seed.primary_position
        assert view.current_rating == seed.current_rating
        assert view.potential == seed.potential_rating
        assert view.growth_curve == seed.growth_curve
        assert view.birth_country_code == seed.country_code

        # The bands must bracket the published values, never contradict them.
        assert view.current_ability_range.minimum <= seed.current_rating
        assert view.current_ability_range.maximum >= seed.current_rating
        assert view.potential_range.maximum >= seed.potential_rating

        # A seed is not a player, and the profile says so.
        assert view.player_id is None
    finally:
        session.close()


def test_seed_profile_preserves_the_personality_the_seeder_stored() -> None:
    session = build_regen_universe_session()
    try:
        seed = _make_seed(session)
        view = build_seed_profile_view(seed)

        # These five were persisted by the original seeding run, so a later
        # backfill must not overwrite values a user may already have seen.
        assert view.personality.temperament == 55
        assert view.personality.ambition == 81
        assert view.personality.resilience == 63
        assert view.personality.work_rate == 74
        assert view.personality.media_appetite == 40
        assert view.story_seed is not None
        assert view.story_seed.background == "academy product"
    finally:
        session.close()


def test_seed_profile_is_deterministic() -> None:
    session = build_regen_universe_session()
    try:
        seed = _make_seed(session)
        first = build_seed_profile_view(seed)
        second = build_seed_profile_view(seed)
        assert first.model_dump(mode="json") == second.model_dump(mode="json")
    finally:
        session.close()


def test_showcase_serves_a_seed_that_has_no_regen_profile() -> None:
    session = build_regen_universe_session()
    try:
        seed = _make_seed(session)
        payload = RegenUniverseService(session).get_player_showcase(seed.id)

        assert payload is not None
        assert payload["player_id"] == seed.id
        assert payload["profile"].display_name == seed.display_name

        # A depth seed has no career, no ranking and no valuation. Those are
        # absent so the client can say "not rated" rather than render zeroes.
        assert payload["legacy"] is None
        assert payload["prestige"] is None
        assert payload["latest_value"] is None
        assert payload["timeline"] == []
    finally:
        session.close()


def test_serving_a_seed_dossier_creates_no_economy_rows() -> None:
    session = build_regen_universe_session()
    try:
        seed = _make_seed(session)
        before = session.scalar(select(RegenProfile).where(RegenProfile.regen_id == seed.id))
        assert before is None

        RegenUniverseService(session).get_player_showcase(seed.id)

        # The whole point of storing the profile on the seed: no regen_profiles
        # row, and therefore no ingestion_players and no player_cards row, so
        # the national depth pool never becomes tradable.
        after = session.scalar(select(RegenProfile).where(RegenProfile.regen_id == seed.id))
        assert after is None
    finally:
        session.close()


def test_unknown_id_still_returns_none() -> None:
    session = build_regen_universe_session()
    try:
        assert RegenUniverseService(session).get_player_showcase("not-a-real-id") is None
    finally:
        session.close()


def test_backfill_is_idempotent() -> None:
    session = build_regen_universe_session()
    try:
        _make_seed(session, suffix="1")
        _make_seed(session, suffix="2")
        service = RegenSeedProfileService(session)

        first = service.backfill()
        assert first["scanned"] == 2
        assert first["written"] == 2
        assert first["skipped_existing"] == 0
        session.commit()

        # Re-running must not rewrite what is already there, so the job is safe
        # to repeat and safe to interrupt.
        second = service.backfill()
        assert second["scanned"] == 2
        assert second["written"] == 0
        assert second["skipped_existing"] == 2
    finally:
        session.close()


def test_snapshot_survives_a_session_round_trip() -> None:
    session = build_regen_universe_session()
    try:
        seed = _make_seed(session)
        RegenSeedProfileService(session).ensure_profile(seed)
        session.commit()
        session.expire_all()

        reloaded = session.get(NationalRegenSeed, seed.id)
        assert reloaded is not None
        # metadata_json is a plain JSON column: an in-place mutation would not
        # be seen as dirty and would silently fail to persist.
        assert RegenSeedProfileService.snapshot_for(reloaded) is not None
    finally:
        session.close()
