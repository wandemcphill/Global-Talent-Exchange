from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.legend_layer.service import LegendLayerService
from app.ingestion.models import Player
from app.models.club_profile import ClubProfile
from app.models.commentary_event import CommentaryEvent
from app.models.news_article import NewsArticle
from app.models.player_fan_reaction import PlayerFanReaction
from app.models.player_interview import PlayerInterview
from app.models.player_personality import PlayerPersonality
from app.models.player_token_market import PlayerShareMarket
from app.models.prestige_rating import PrestigeRating
from app.models.user import User


def test_legend_layer_full_story_simulation(
    client,
    app_session_factory,
) -> None:
    with app_session_factory() as session:
        home_owner = User(email="legend-home@test.local", username="legend-home", password_hash="hash")
        away_owner = User(email="legend-away@test.local", username="legend-away", password_hash="hash")
        session.add_all([home_owner, away_owner])
        session.flush()

        home_club = ClubProfile(
            owner_user_id=home_owner.id,
            club_name="North City Legends",
            slug="north-city-legends",
            primary_color="#AA2200",
            secondary_color="#FFF4D6",
            accent_color="#1A1A1A",
        )
        away_club = ClubProfile(
            owner_user_id=away_owner.id,
            club_name="South Town Originals",
            slug="south-town-originals",
            primary_color="#002E6D",
            secondary_color="#D5E6FF",
            accent_color="#F2B632",
        )
        session.add_all([home_club, away_club])
        session.flush()

        home_player = Player(
            source_provider="legend-test",
            provider_external_id="legend-home-player",
            full_name="Kelechi Star",
            canonical_display_name="Kelechi Star",
            current_club_profile_id=home_club.id,
            market_value_eur=1_500_000.0,
            current_market_reference_value=1_500_000.0,
            normalized_position="forward",
        )
        away_player = Player(
            source_provider="legend-test",
            provider_external_id="legend-away-player",
            full_name="Musa Drift",
            canonical_display_name="Musa Drift",
            current_club_profile_id=away_club.id,
            market_value_eur=900_000.0,
            current_market_reference_value=900_000.0,
            normalized_position="midfielder",
        )
        session.add_all([home_player, away_player])
        session.flush()

        home_player.market_value_eur = home_player.market_value_eur or 1_500_000.0
        home_player.current_market_reference_value = home_player.current_market_reference_value or home_player.market_value_eur

        market = session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == home_player.id))
        if market is None:
            market = PlayerShareMarket(
                player_id=home_player.id,
                total_shares=1000,
                circulating_shares=250,
                share_price_coin=Decimal("1.0000"),
                status="active",
                metadata_json={},
            )
            session.add(market)
            session.flush()
        old_price = Decimal(market.share_price_coin or Decimal("0.0000"))

        session.add_all(
            [
                CommentaryEvent(
                    match_id="fixture-legend",
                    minute=43,
                    event_type="goal",
                    context={"player_id": home_player.id},
                    generated_line=f"{home_player.full_name} puts {home_club.club_name} ahead before the break.",
                ),
                CommentaryEvent(
                    match_id="fixture-legend",
                    minute=89,
                    event_type="goal",
                    context={"player_id": home_player.id},
                    generated_line=f"{home_player.full_name} strikes late again to finish the job for {home_club.club_name}.",
                ),
            ]
        )

        service = LegendLayerService(session=session)
        articles = service.process_match_completed(
            {
                "competition_id": "legend-cup",
                "season_id": "legend-season",
                "competition_type": "cup",
                "fixture_id": "fixture-legend",
                "home_club_id": home_club.id,
                "home_club_name": home_club.club_name,
                "away_club_id": away_club.id,
                "away_club_name": away_club.club_name,
                "home_user_id": home_club.owner_user_id,
                "away_user_id": away_club.owner_user_id,
                "home_goals": 2,
                "away_goals": 0,
                "winner_team_id": home_club.id,
                "is_final": True,
                "user_ids": [home_club.owner_user_id, away_club.owner_user_id],
                "player_stats": [
                    {
                        "player_id": home_player.id,
                        "player_name": home_player.full_name,
                        "team_id": home_club.id,
                        "team_name": home_club.club_name,
                        "goals": 2,
                        "assists": 0,
                        "saves": 0,
                        "yellow_cards": 0,
                        "red_card": False,
                        "rating": 8.9,
                    },
                    {
                        "player_id": away_player.id,
                        "player_name": away_player.full_name,
                        "team_id": away_club.id,
                        "team_name": away_club.club_name,
                        "goals": 0,
                        "assists": 0,
                        "saves": 0,
                        "yellow_cards": 1,
                        "red_card": False,
                        "rating": 5.4,
                    },
                ],
            },
            event_id="legend-event-1",
        )
        session.commit()

        assert any(article.article_type == "match_report" for article in articles)
        assert any(article.related_player_id == home_player.id for article in articles)

        personality = session.scalar(select(PlayerPersonality).where(PlayerPersonality.player_id == home_player.id))
        assert personality is not None
        assert personality.confidence > 50
        assert personality.ego > 50
        assert personality.clutch_factor > 50

        interviews = list(
            session.scalars(select(PlayerInterview).where(PlayerInterview.player_id == home_player.id)).all()
        )
        assert interviews

        fan_reactions = list(
            session.scalars(select(PlayerFanReaction).where(PlayerFanReaction.player_id == home_player.id)).all()
        )
        assert fan_reactions

        lifetime_player_rank = session.scalar(
            select(PrestigeRating).where(
                PrestigeRating.entity_type == "player",
                PrestigeRating.entity_id == home_player.id,
                PrestigeRating.scope == "lifetime",
                PrestigeRating.season_key == "lifetime",
            )
        )
        seasonal_club_rank = session.scalar(
            select(PrestigeRating).where(
                PrestigeRating.entity_type == "club",
                PrestigeRating.entity_id == home_club.id,
                PrestigeRating.scope == "seasonal",
                PrestigeRating.season_key == "legend-season",
            )
        )
        lifetime_user_rank = session.scalar(
            select(PrestigeRating).where(
                PrestigeRating.entity_type == "user",
                PrestigeRating.entity_id == home_club.owner_user_id,
                PrestigeRating.scope == "lifetime",
                PrestigeRating.season_key == "lifetime",
            )
        )
        assert lifetime_player_rank is not None
        assert seasonal_club_rank is not None
        assert lifetime_user_rank is not None
        assert lifetime_player_rank.prestige_score > 0
        assert seasonal_club_rank.rank_position == 1

        # A match narrates the market; it does not price it. This asserted
        # `> old_price` until the economic-integrity remediation, which returned
        # tradable price to the trading/issuance/governed-admin writers and left
        # the bounded matchday overlay in app.value_engine.matchday_signal as the
        # single path from form to value. The story linkage is still recorded.
        refreshed_market = session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == home_player.id))
        assert refreshed_market is not None
        assert Decimal(refreshed_market.share_price_coin) == old_price
        assert refreshed_market.metadata_json["last_narrative_rating"] is not None

        primary_article_id = articles[0].id
        home_player_id = home_player.id
        home_club_id = home_club.id

    feed_response = client.get("/news/feed")
    assert feed_response.status_code == 200, feed_response.text
    feed_payload = feed_response.json()
    assert any(item["related_match_id"] == "fixture-legend" for item in feed_payload)

    article_response = client.get(f"/news/{primary_article_id}")
    assert article_response.status_code == 200, article_response.text
    assert article_response.json()["id"] == primary_article_id

    global_rankings = client.get(
        "/rankings/global",
        params={"scope": "seasonal", "season_key": "legend-season"},
    )
    assert global_rankings.status_code == 200, global_rankings.text
    assert any(item["entity_id"] == home_club_id for item in global_rankings.json()["clubs"])

    player_rankings = client.get(
        "/rankings/players",
        params={"scope": "lifetime"},
    )
    assert player_rankings.status_code == 200, player_rankings.text
    assert any(item["entity_id"] == home_player_id for item in player_rankings.json()["entries"])

    club_rankings = client.get(
        "/rankings/clubs",
        params={"scope": "seasonal", "season_key": "legend-season"},
    )
    assert club_rankings.status_code == 200, club_rankings.text
    assert club_rankings.json()["entries"][0]["entity_id"] == home_club_id

    personality_response = client.get(f"/players/{home_player_id}/personality")
    assert personality_response.status_code == 200, personality_response.text
    assert personality_response.json()["player_id"] == home_player_id

    interviews_response = client.get(f"/players/{home_player_id}/interviews")
    assert interviews_response.status_code == 200, interviews_response.text
    assert len(interviews_response.json()) >= 1

    with app_session_factory() as session:
        stored_articles = list(
            session.scalars(select(NewsArticle).where(NewsArticle.related_match_id == "fixture-legend")).all()
        )
        assert len(stored_articles) >= 2
