from __future__ import annotations

from sqlalchemy import select

from app.ingestion.models import Country, Player
from app.legend_layer.adapter import LegendaryPlayerAdapter
from app.legend_layer.schemas import LegendaryPlayerRegistryRecord
from app.models.player_token_market import PlayerShareMarket
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink


def test_legendary_player_adapter_creation_and_idempotency(app_session_factory) -> None:
    kanu_record = LegendaryPlayerRegistryRecord(
        registry_id="legend-kanu-nwankwo",
        full_name="Kanu Nwankwo",
        first_name="Kanu",
        last_name="Nwankwo",
        short_name="K. Nwankwo",
        nationality="Nigeria",
        nationality_code="NGA",
        preferred_foot="right",
        primary_position="ST",
        secondary_positions=["CAM", "CF"],
        historical_height_cm=197,
        historical_weight_kg=80,
        birth_year=1976,
        signature_traits={
            "tall_lanky_physique": True,
            "technical_finesse": 92,
            "creativity": 88,
            "finishing": 86,
            "stamina": 64,
        },
        base_attributes={
            "pace": 70,
            "shooting": 85,
            "passing": 82,
            "dribbling": 89,
            "defending": 35,
            "physical": 68,
        },
        overall_rating=84,
        potential=87,
        market_reference_value=25000000.0,
        historical_club_name="Arsenal",
        historical_league_name="Premier League",
    )

    with app_session_factory() as session:
        adapter = LegendaryPlayerAdapter(session=session)
        player1 = adapter.convert_record(kanu_record)
        session.commit()

        player1_id = player1.id

        # 1. Identity fields
        assert player1.full_name == "Kanu Nwankwo"
        assert player1.first_name == "Kanu"
        assert player1.last_name == "Nwankwo"
        assert player1.short_name == "K. Nwankwo"
        assert player1.position == "ST"
        assert player1.normalized_position == "ST"
        assert player1.secondary_positions_json == ["CAM", "CF"]
        assert player1.preferred_foot == "right"
        assert player1.is_tradable is True
        assert player1.is_real_player is True
        assert player1.real_player_tier == "legendary_registry"

        # 2. Height within strictly ±1 cm
        assert abs(player1.height_cm - 197) <= 1

        # 3. Signature traits and attributes stored
        assert player1.dna_profile["is_legendary_registry"] is True
        assert player1.dna_profile["overall_rating"] == 84
        assert player1.dna_profile["potential"] == 87
        assert player1.dna_profile["signature_traits"]["stamina"] == 64
        assert player1.dna_profile["signature_traits"]["technical_finesse"] == 92

        # 4. Associated records created
        country = session.scalar(select(Country).where(Country.id == player1.country_id))
        assert country is not None
        assert country.name == "Nigeria"
        assert country.alpha3_code == "NGA"

        source_link = session.scalar(
            select(RealPlayerSourceLink).where(
                RealPlayerSourceLink.source_name == "legendary_registry",
                RealPlayerSourceLink.source_player_key == "legend-kanu-nwankwo",
            )
        )
        assert source_link is not None

        profile = session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.gtex_player_id == player1_id))
        assert profile is not None
        assert profile.canonical_name == "Kanu Nwankwo"
        assert profile.primary_position == "ST"
        assert profile.secondary_positions_json == ["CAM", "CF"]
        assert profile.height_cm == player1.height_cm

        share_market = session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player1_id))
        assert share_market is not None
        assert share_market.status == "active"
        assert share_market.share_price_coin > 0

    # 5. Idempotency test - repeated conversion returns same player without duplicate records
    with app_session_factory() as session:
        adapter = LegendaryPlayerAdapter(session=session)
        player2 = adapter.convert_record(kanu_record)
        session.commit()

        assert player2.id == player1_id

        all_players = list(
            session.scalars(
                select(Player).where(
                    Player.source_provider == "legendary_registry",
                    Player.provider_external_id == "legend-kanu-nwankwo",
                )
            ).all()
        )
        assert len(all_players) == 1


def test_legendary_player_downstream_compatibility(app_session_factory) -> None:
    kanu_record = LegendaryPlayerRegistryRecord(
        registry_id="legend-kanu-downstream",
        full_name="Kanu Nwankwo",
        nationality="Nigeria",
        nationality_code="NGA",
        preferred_foot="right",
        primary_position="ST",
        historical_height_cm=197,
        overall_rating=84,
        potential=87,
    )

    with app_session_factory() as session:
        adapter = LegendaryPlayerAdapter(session=session)
        player = adapter.convert_record(kanu_record)
        session.commit()

        # Searchability
        searched_player = session.scalar(
            select(Player).where(
                Player.full_name == "Kanu Nwankwo",
                Player.provider_external_id == "legend-kanu-downstream",
                Player.is_tradable == True,  # noqa: E712
            )
        )
        assert searched_player is not None
        assert searched_player.id == player.id

        # Tradability
        market = session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id))
        assert market is not None
        assert market.status == "active"
