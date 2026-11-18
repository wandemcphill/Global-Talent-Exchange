from datetime import UTC, datetime, timedelta

from app.ingestion.models import Player
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound
from app.models.transfer_market import (
    MarketWatchlistEntry,
    TransferListing,
    TransferListingBid,
    TransferNegotiation,
)
from app.models.user import User
from app.services.competition_orchestrator import CompetitionOrchestrator
from app.transfer_market.service import TransferMarketService


def test_fixture_search_hides_private_competitions_from_outsiders(session) -> None:
    competition = UserCompetition(
        host_user_id="user-alpha",
        name="Secret Friends Cup",
        format="knockout",
        visibility="private",
        currency="credit",
        metadata_json={},
        fixed_prizes_json={},
        eligibility_rules_json={},
        ranking_policy_json={},
    )
    session.add(competition)
    session.flush()
    round_row = CompetitionRound(
        competition_id=competition.id,
        round_number=1,
        name="Final",
        metadata_json={},
    )
    session.add(round_row)
    session.flush()
    session.add(
        CompetitionMatch(
            competition_id=competition.id,
            round_id=round_row.id,
            round_number=1,
            home_club_id="club-alpha",
            away_club_id="club-bravo",
            status="scheduled",
            metadata_json={},
        )
    )
    session.commit()

    orchestrator = CompetitionOrchestrator(session=session)
    hidden = orchestrator.search_fixtures(q="Secret Friends", viewer_user_id=None)
    visible = orchestrator.search_fixtures(q="Alpha", viewer_user_id="user-alpha")

    assert hidden == []
    assert len(visible) == 1
    assert visible[0]["home_name"] == "Alpha FC"
    assert visible[0]["status"] == "scheduled"
    assert visible[0]["route"].startswith("/app/match/")


def test_listing_search_filters_name_gsi_and_keeps_private_listings_off_the_board(session) -> None:
    bind = session.get_bind()
    for model in (TransferListing, TransferListingBid, TransferNegotiation, MarketWatchlistEntry):
        model.__table__.create(bind, checkfirst=True)
    session.add_all(
        [
            Player(
                id="player-kane",
                source_provider="test",
                provider_external_id="kane",
                full_name="Harry Kane",
                canonical_display_name="Harry Kane",
                governed_gsi=91,
                current_club_profile_id="club-alpha",
            ),
            Player(
                id="player-youth",
                source_provider="test",
                provider_external_id="youth",
                full_name="Youth Prospect",
                canonical_display_name="Youth Prospect",
                governed_gsi=74,
                current_club_profile_id="club-bravo",
            ),
        ]
    )
    session.flush()
    expires = datetime.now(UTC) + timedelta(days=7)
    session.add_all(
        [
            TransferListing(
                id="listing-kane",
                player_id="player-kane",
                selling_club_id="club-alpha",
                base_price=1000,
                expires_at=expires,
                visibility="public",
                status="open",
            ),
            TransferListing(
                id="listing-private",
                player_id="player-youth",
                selling_club_id="club-bravo",
                base_price=100,
                expires_at=expires,
                visibility="private",
                status="open",
            ),
        ]
    )
    session.commit()

    service = TransferMarketService(session)
    by_name = service.list_listings(q="Kane", public_board=True)
    by_gsi = service.list_listings(min_gsi=90, public_board=True)
    board = service.list_listings(status="open", public_board=True)

    assert [item.player_id for item in by_name] == ["player-kane"]
    assert [item.player_id for item in by_gsi] == ["player-kane"]
    assert "listing-private" not in {item.id for item in board}
    assert session.get(User, "user-alpha") is not None
