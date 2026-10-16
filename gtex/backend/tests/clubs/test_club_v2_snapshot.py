from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from app.models.base import utcnow
from app.models.club_ranking_integrity import ClubRankingEvent
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.player_cards import PlayerMarketValueSnapshot
from app.models.transfer_market import MarketWatchlistEntry, TransferHubOffer, TransferListing, TransferListingBid
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerBalanceProjection,
    LedgerUnit,
)
from app.ingestion.models import Country, Player


def test_club_v2_snapshot_returns_live_aggregate(client, create_club, session) -> None:
    profile = create_club()
    club_id = str(profile["id"])
    now = utcnow()

    country = Country(
        id="country-ng",
        source_provider="test",
        provider_external_id="ng",
        name="Nigeria",
        alpha2_code="NG",
        alpha3_code="NGA",
        fifa_code="NGA",
    )
    player = Player(
        id="player-live-1",
        source_provider="test",
        provider_external_id="player-live-1",
        country_id=country.id,
        current_club_profile_id=club_id,
        full_name="Adaeze Okoro",
        short_name="A. Okoro",
        position="ST",
        normalized_position="ST",
        market_value_eur=125000.0,
        is_real_player=True,
        canonical_display_name="Adaeze Okoro",
    )
    session.add_all(
        [
            country,
            player,
            PlayerMarketValueSnapshot(
                player_id=player.id,
                as_of=now,
                avg_trade_price_credits=Decimal("75000"),
                last_trade_price_credits=Decimal("72000"),
            ),
            LedgerAccount(
                id="wallet-credit",
                owner_user_id="user-owner",
                code="user:user-owner:credit",
                label="Fan Coin",
                unit=LedgerUnit.CREDIT,
                kind=LedgerAccountKind.USER,
            ),
            LedgerBalanceProjection(
                account_id="wallet-credit",
                owner_user_id="user-owner",
                unit=LedgerUnit.CREDIT,
                balance=Decimal("123456.0000"),
            ),
            Competition(
                id="competition-live",
                host_user_id="user-owner",
                name="Founders Cup",
                format="league",
                visibility="private",
                status="active",
                start_mode="manual",
                currency="credit",
                scheduled_start_at=now + timedelta(days=1),
            ),
            CompetitionParticipant(
                competition_id="competition-live",
                club_id=club_id,
                user_id="user-owner",
                status="joined",
                seed=2,
                played=3,
                wins=2,
                draws=1,
                losses=0,
                goals_for=7,
                goals_against=3,
                goal_diff=4,
                points=7,
            ),
            CompetitionRound(
                id="round-live",
                competition_id="competition-live",
                round_number=1,
                stage="league",
                group_key="A",
                name="Round 1",
            ),
            CompetitionMatch(
                competition_id="competition-live",
                round_id="round-live",
                round_number=1,
                stage="league",
                home_club_id=club_id,
                away_club_id="opponent-club",
                status="scheduled",
            ),
            ClubRankingEvent(
                event_key="rank-live-1",
                event_kind="match_result",
                club_id=club_id,
                competition_id="competition-live",
                match_id=None,
                result="win",
                base_points=Decimal("3.0000"),
                raw_points_delta=Decimal("3.0000"),
                final_points_delta=Decimal("3.0000"),
            ),
            TransferListing(
                id="listing-live",
                player_id=player.id,
                selling_club_id=club_id,
                base_price=Decimal("85000"),
                current_highest_bid=Decimal("90000"),
                status="open",
                expires_at=now + timedelta(days=3),
            ),
            TransferListingBid(
                listing_id="listing-live",
                bidder_club_id=club_id,
                amount=Decimal("90000"),
            ),
            TransferHubOffer(
                listing_id="listing-live",
                seller_club_id=club_id,
                bidder_club_id=club_id,
                cash_amount=Decimal("91000"),
                status="open",
            ),
            MarketWatchlistEntry(club_id=club_id, player_id=player.id),
        ]
    )
    session.flush()

    response = client.get(f"/api/clubs/{club_id}/v2-snapshot")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["live"] is True
    assert payload["fixture"] is False
    assert payload["demo"] is False
    assert payload["metadata"]["fake_context"] is False
    assert payload["club_id"] == club_id
    assert payload["club"]["club_name"] == "Legacy FC"
    assert payload["squad"]["player_count"] >= 1
    assert payload["squad"]["squad_value_credits"] >= 75000
    live_player = next(player for player in payload["squad"]["players"] if player["player_id"] == "player-live-1")
    assert live_player["name"] == "Adaeze Okoro"
    assert payload["competitions"]["active_count"] == 1
    assert payload["competitions"]["upcoming_match_count"] == 1
    assert payload["wallet"]["wallet_credits"] == 123456
    assert payload["ranking"]["reputation_score"] == 0
    assert payload["ranking"]["ranking_points"] == "3.0000"
    assert payload["facilities"]["stadium"]["club_id"] == club_id
    assert payload["transfers"]["outgoing_listing_count"] == 1
    assert payload["transfers"]["watchlist_count"] == 1
    assert payload["growth"]["club_id"] == club_id
    assert payload["lifecycle"]["club_id"] == club_id
    assert "projection_not_loaded" not in response.text


def test_club_v2_snapshot_fails_closed_for_non_owner(client, create_club) -> None:
    profile = create_club()
    club_id = str(profile["id"])
    client.app.state.current_user_id = "user-other"

    response = client.get(f"/api/clubs/{club_id}/v2-snapshot")

    assert response.status_code == 403
    assert response.json()["detail"] == "club_owner_required"


def test_club_v2_snapshot_missing_club_does_not_fabricate_context(client) -> None:
    response = client.get("/api/clubs/not-a-club/v2-snapshot")

    assert response.status_code == 404
    assert response.json()["detail"] == "club_not_found"
