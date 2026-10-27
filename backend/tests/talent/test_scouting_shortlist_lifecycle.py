"""Comprehensive end-to-end tests for GTEX Scouting and Shortlist Lifecycle.

Covers Issue #169 and authoritative requirements from Issue #176:
- Authenticated scouting writes for both regens and real universe players
- Real-identity report persistence and retrieval
- Multi-tenant club isolation (preventing leakage of private scouting reports)
- Server-side derived identity and club ownership validation on shortlists
- Rejection of unauthorized and cross-club mutations
- Idempotency and duplicate prevention on shortlists
- Transfer Room handoff connecting scouting discoveries to the canonical transfer market
"""

from __future__ import annotations

from datetime import date
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_optional_current_user, get_session
from app.ingestion.models import Player
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.regen_ecosystem import Scout
from app.models.scouting_intelligence import ScoutReport
from app.models.transfer_market import MarketWatchlistEntry, TransferListing
from app.models.user import KycStatus, User, UserRole
from app.routes.player_lifecycle import router as player_lifecycle_router
from app.talent.models import TalentProfile
from app.talent.router import admin_router, router as talent_router
from app.transfer_market.router import router as transfer_market_router

EXTRA_TRUNCATE_TABLES = (
    "market_watchlist_entries",
    "transfer_listings",
    "scout_reports",
    "regen_scout_reports",
    "scouts",
    "regen_profiles",
    "club_profiles",
)


@pytest.fixture()
def lifecycle_client(session: Session):
    for tbl in EXTRA_TRUNCATE_TABLES:
        try:
            session.execute(select(1))
            from sqlalchemy import text

            session.execute(text(f"DELETE FROM {tbl}"))
            session.commit()
        except Exception:
            session.rollback()

    class Identity:
        user: User | None = None

    identity = Identity()

    app = FastAPI()
    app.include_router(player_lifecycle_router)
    app.include_router(player_lifecycle_router, prefix="/api/v2")
    app.include_router(talent_router)
    app.include_router(talent_router, prefix="/api/v2")
    app.include_router(admin_router)
    app.include_router(transfer_market_router)

    def _session_override():
        yield session

    def _current_user() -> User:
        if identity.user is None:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        return identity.user

    def _optional_user() -> User | None:
        return identity.user

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_optional_current_user] = _optional_user

    with TestClient(app) as client:
        yield client, identity, session


def _seed_club_and_user(
    session: Session,
    *,
    user_id: str,
    username: str,
    club_id: str,
    club_name: str,
) -> tuple[User, ClubProfile]:
    user = User(
        id=user_id,
        email=f"{username}@example.com",
        username=username,
        password_hash="unused",  # pragma: allowlist secret
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    club = ClubProfile(
        id=club_id,
        owner_user_id=user_id,
        club_name=club_name,
        short_name=club_name[:8],
        slug=f"slug-{username}",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        primary_color="#10B981",
        secondary_color="#064E3B",
        accent_color="#F59E0B",
    )
    session.add(user)
    session.add(club)
    session.flush()
    return user, club


def _seed_real_player(session: Session, *, player_id: str, name: str) -> Player:
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=f"ext-{player_id}",
        full_name=name,
        canonical_display_name=name,
        position="ST",
        normalized_position="ST",
        secondary_positions_json=[],
        date_of_birth=date(1999, 12, 29),
        preferred_foot="right",
        dna_profile={
            "overall_rating": 84,
            "potential_rating": 89,
            "pace": 88,
            "shooting": 85,
            "passing": 72,
            "dribbling": 81,
            "defending": 42,
            "physicality": 84,
        },
    )
    session.add(player)
    profile = TalentProfile(
        player_id=player.id,
        display_name=name,
        position_code="ST",
        visibility_state="published",
        moderation_state="clear",
        verification_tier="unverified",
        composite_score=84.0,
    )
    session.add(profile)
    session.flush()
    return player


def _seed_regen_player(
    session: Session,
    *,
    regen_id: str,
    name: str,
    created_by_club_id: str,
) -> Player:
    from tests.regen_universe_support import _create_regen_player
    from app.models.player_cards import PlayerCardTier

    tier = session.get(PlayerCardTier, "tier-standard")
    if tier is None:
        tier = PlayerCardTier(
            id="tier-standard",
            code="standard",
            name="Standard",
            rarity_rank=1,
        )
        session.add(tier)
        session.flush()

    player = _create_regen_player(
        session,
        player_id=f"p-{regen_id}",
        regen_id=regen_id,
        name=name,
        birth_date=date(2008, 5, 10),
        position="CM",
        normalized_position="midfielder",
        club_profile_id=created_by_club_id,
        tier_id=tier.id,
    )
    session.flush()
    return player


def test_scout_real_player_success_and_persistence(lifecycle_client):
    client, identity, session = lifecycle_client
    user, club = _seed_club_and_user(
        session, user_id="user-scout-1", username="scout1", club_id="club-1", club_name="Lagos FC"
    )
    player = _seed_real_player(session, player_id="real-osimhen-9", name="Victor Osimhen")

    # Seed active scout assigned to this user and club
    scout = Scout(
        id="scout-1",
        club_user_id=user.id,
        club_id=club.id,
        region="West Africa",
        skill_rating=85,
        specialty="Youth Striker",
        active=True,
    )
    session.add(scout)
    session.commit()

    identity.user = user

    # Act: Scout the real player via POST /scout/report/{player_id}
    response = client.post(f"/scout/report/{player.id}")
    assert response.status_code == 200, response.text
    payload = response.json()

    # Assert honest report fields derived from real player identity
    assert payload["player_id"] == player.id
    assert payload["scout_id"] == scout.id
    assert payload["club_id"] == club.id
    assert payload["accuracy"] == 85
    assert payload["visible_stats"]["pace"] == 88
    assert payload["visible_stats"]["shooting"] == 85
    # The seeded TalentProfile has no persisted ranking snapshot, so the
    # service must not expose its database-default neutral consistency score.
    assert payload["hidden_stats"]["consistency"] is None
    assert "form" not in payload["visible_stats"]

    # Assert persisted ScoutReport in canonical intelligence table
    db_report = session.scalar(
        select(ScoutReport).where(ScoutReport.player_id == player.id, ScoutReport.club_id == club.id)
    )
    assert db_report is not None
    assert db_report.current_ability_estimate == 84
    assert db_report.future_potential_estimate == 89


@pytest.mark.parametrize(
    ("dna_profile", "expected_detail"),
    [
        ({"pace": 88, "potential_rating": 89}, "overall_rating is unavailable"),
        ({"overall_rating": 84, "pace": 88}, "potential rating is unavailable"),
    ],
)
def test_real_player_scouting_does_not_invent_missing_ratings(
    lifecycle_client, dna_profile: dict[str, int], expected_detail: str
):
    client, identity, session = lifecycle_client
    user, club = _seed_club_and_user(
        session,
        user_id="user-scout-missing-rating",
        username="scout_missing_rating",
        club_id="club-missing-rating",
        club_name="Data Integrity FC",
    )
    player = _seed_real_player(
        session,
        player_id=f"real-missing-{expected_detail.split()[0]}",
        name="Unrated Player",
    )
    player.dna_profile = dna_profile
    scout = Scout(
        id=f"scout-missing-{expected_detail.split()[0]}",
        club_user_id=user.id,
        club_id=club.id,
        region="Global",
        skill_rating=85,
        specialty="General",
        active=True,
    )
    session.add(scout)
    session.commit()
    identity.user = user

    response = client.post(f"/scout/report/{player.id}")

    assert response.status_code == 409, response.text
    assert expected_detail in response.json()["detail"]
    assert (
        session.scalar(
            select(ScoutReport).where(
                ScoutReport.player_id == player.id,
                ScoutReport.club_id == club.id,
            )
        )
        is None
    )


def test_mislinked_scout_cannot_write_reports_to_another_club(lifecycle_client):
    client, identity, session = lifecycle_client
    user_a, _ = _seed_club_and_user(
        session,
        user_id="user-scout-mismatch-a",
        username="scout_mismatch_a",
        club_id="club-scout-mismatch-a",
        club_name="Owner A FC",
    )
    _, club_b = _seed_club_and_user(
        session,
        user_id="user-scout-mismatch-b",
        username="scout_mismatch_b",
        club_id="club-scout-mismatch-b",
        club_name="Owner B FC",
    )
    player = _seed_real_player(session, player_id="real-mismatch-target", name="Target Player")
    session.add(
        Scout(
            id="scout-mislinked",
            club_user_id=user_a.id,
            club_id=club_b.id,
            region="Global",
            skill_rating=90,
            active=True,
        )
    )
    session.commit()
    identity.user = user_a

    response = client.post(f"/scout/report/{player.id}")

    assert response.status_code == 404, response.text
    assert (
        session.scalar(
            select(ScoutReport).where(
                ScoutReport.player_id == player.id,
                ScoutReport.club_id == club_b.id,
            )
        )
        is None
    )


def test_scout_regen_player_success_and_persistence(lifecycle_client):
    client, identity, session = lifecycle_client
    user, club = _seed_club_and_user(
        session, user_id="user-scout-2", username="scout2", club_id="club-2", club_name="Abuja Stars"
    )
    regen = _seed_regen_player(session, regen_id="regen-wonderkid-1", name="Emeka Obi", created_by_club_id=club.id)

    scout = Scout(
        id="scout-2",
        club_user_id=user.id,
        club_id=club.id,
        region="Nigeria",
        skill_rating=90,
        specialty="Regen Midfielders",
        active=True,
    )
    session.add(scout)
    session.commit()

    identity.user = user

    response = client.post(f"/scout/report/{regen.id}")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["player_id"] == regen.id or payload["regen_profile_id"] is not None
    assert payload["scout_id"] == scout.id
    assert payload["club_id"] == club.id
    assert payload["accuracy"] == 90
    assert "technical" in payload["visible_stats"]
    assert "physical" in payload["visible_stats"]
    assert "mental" in payload["visible_stats"]
    assert "tactical" in payload["visible_stats"]


def test_scout_report_retrieval_and_strict_club_isolation(lifecycle_client):
    """Verifies report retrieval and ensures Club B CANNOT see Club A's private scout reports."""
    client, identity, session = lifecycle_client
    user_a, club_a = _seed_club_and_user(
        session, user_id="user-club-a", username="club_a_owner", club_id="club-a", club_name="Club Alpha"
    )
    user_b, club_b = _seed_club_and_user(
        session, user_id="user-club-b", username="club_b_owner", club_id="club-b", club_name="Club Beta"
    )
    player = _seed_real_player(session, player_id="real-target-1", name="Target Player")

    scout_a = Scout(
        id="scout-a", club_user_id=user_a.id, club_id=club_a.id, region="North", skill_rating=88, active=True
    )
    scout_b = Scout(
        id="scout-b", club_user_id=user_b.id, club_id=club_b.id, region="South", skill_rating=82, active=True
    )
    session.add_all([scout_a, scout_b])
    session.commit()

    # Club A scouts the player
    identity.user = user_a
    res = client.post(f"/scout/report/{player.id}")
    assert res.status_code == 200

    # Club A can retrieve their own report
    get_res_a = client.get(f"/scout/reports/{player.id}")
    assert get_res_a.status_code == 200
    assert get_res_a.json()["player_id"] == player.id
    assert get_res_a.json()["club_id"] == club_a.id

    # Club A can list all reports for their club
    list_res_a = client.get("/scout/reports")
    assert list_res_a.status_code == 200
    assert len(list_res_a.json()) == 1

    # Switch identity to Club B
    identity.user = user_b

    # Club B attempts to retrieve Club A's scouting report for this player
    get_res_b = client.get(f"/scout/reports/{player.id}")
    # Must return 404 to ensure complete isolation (no leakage of existence or data)
    assert get_res_b.status_code == 404

    # Club B's report list must be completely empty
    list_res_b = client.get("/scout/reports")
    assert list_res_b.status_code == 200
    assert len(list_res_b.json()) == 0


def test_scout_without_active_scout_returns_404(lifecycle_client):
    client, identity, session = lifecycle_client
    user, club = _seed_club_and_user(
        session, user_id="user-no-scout", username="noscout", club_id="club-no-scout", club_name="No Scout FC"
    )
    player = _seed_real_player(session, player_id="real-p-1", name="Some Player")
    session.commit()

    identity.user = user
    # Has a club but no active Scout record
    response = client.post(f"/scout/report/{player.id}")
    assert response.status_code == 404
    assert "No active scout" in response.json()["detail"]


def test_scout_nonexistent_player_returns_404(lifecycle_client):
    client, identity, session = lifecycle_client
    user, club = _seed_club_and_user(
        session, user_id="user-valid-scout", username="validscout", club_id="club-v", club_name="Valid FC"
    )
    scout = Scout(id="scout-v", club_user_id=user.id, club_id=club.id, region="HQ", skill_rating=80, active=True)
    session.add(scout)
    session.commit()

    identity.user = user
    response = client.post("/scout/report/nonexistent-id-999")
    assert response.status_code == 404


def test_shortlist_ownership_enforcement_on_creation(lifecycle_client):
    """Ensures shortlists cannot be created claiming clubs not owned by the caller."""
    client, identity, session = lifecycle_client
    user_a, club_a = _seed_club_and_user(
        session, user_id="user-a", username="usera", club_id="club-a", club_name="Club A"
    )
    user_b, club_b = _seed_club_and_user(
        session, user_id="user-b", username="userb", club_id="club-b", club_name="Club B"
    )
    session.commit()

    identity.user = user_a

    # User A tries to create a shortlist claiming Club B
    cross_club_res = client.post("/talent/shortlists", json={"name": "Sneaky List", "club_id": club_b.id})
    assert cross_club_res.status_code == 403
    assert "permission" in cross_club_res.json()["detail"].lower()

    # User A creates a shortlist with their own club
    valid_res = client.post("/talent/shortlists", json={"name": "Alpha Targets", "club_id": club_a.id})
    assert valid_res.status_code == 201
    assert valid_res.json()["club_id"] == club_a.id

    # User A creates a shortlist omitting club_id -> auto-derives club_a
    derived_res = client.post("/talent/shortlists", json={"name": "Auto Derived Club List"})
    assert derived_res.status_code == 201
    assert derived_res.json()["club_id"] == club_a.id


def test_shortlist_entry_lifecycle_and_duplicate_prevention(lifecycle_client):
    client, identity, session = lifecycle_client
    user, club = _seed_club_and_user(
        session, user_id="user-sl-owner", username="slowner", club_id="club-sl", club_name="Shortlist FC"
    )
    player = _seed_real_player(session, player_id="real-shortlist-target", name="Star Talent")
    session.commit()

    identity.user = user

    # Create shortlist
    create_sl = client.post("/talent/shortlists", json={"name": "Primary Targets"})
    assert create_sl.status_code == 201
    sl_id = create_sl.json()["id"]

    # Add real player to shortlist
    add_res = client.post(
        f"/talent/shortlists/{sl_id}/entries",
        json={"player_id": player.id, "priority": 1, "note": "High priority summer target."},
    )
    assert add_res.status_code == 201
    entries = add_res.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["player_id"] == player.id
    assert entries[0]["note"] == "High priority summer target."
    entry_id = entries[0]["id"]

    # Repeated addition of same player to same shortlist must fail with 400
    dup_res = client.post(
        f"/talent/shortlists/{sl_id}/entries",
        json={"player_id": player.id, "priority": 2},
    )
    assert dup_res.status_code == 400
    assert "already on this shortlist" in dup_res.json()["detail"].lower()

    # List shortlists with include_entries
    list_res = client.get("/talent/shortlists?include_entries=true")
    assert list_res.status_code == 200
    assert list_res.json()["shortlists"][0]["entry_count"] == 1

    # Remove entry
    del_res = client.delete(f"/talent/shortlists/{sl_id}/entries/{entry_id}")
    assert del_res.status_code == 204

    # Verify entry is removed
    check_res = client.get(f"/talent/shortlists/{sl_id}")
    assert check_res.status_code == 200
    assert check_res.json()["entry_count"] == 0


def test_transfer_room_handoff_from_scouting_discovery(lifecycle_client):
    """Certifies the bridge from discovery -> canonical transfer market watchlist -> open listing check."""
    client, identity, session = lifecycle_client
    user, club = _seed_club_and_user(
        session, user_id="user-transfer-lead", username="transferscout", club_id="club-tf", club_name="Transfer FC"
    )
    player = _seed_real_player(session, player_id="real-tf-star", name="Target Phenom")

    scout = Scout(
        id="scout-tf",
        club_user_id=user.id,
        club_id=club.id,
        region="Europe",
        skill_rating=92,
        active=True,
    )
    # Seed an open transfer listing in canonical transfer market
    from datetime import datetime, timezone, timedelta

    listing = TransferListing(
        id="listing-tf-star",
        player_id=player.id,
        selling_club_id=club.id,
        base_price=45000000.0,
        status="open",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session.add_all([scout, listing])
    session.commit()

    identity.user = user

    # 1. Scout player
    scout_res = client.post(f"/scout/report/{player.id}")
    assert scout_res.status_code == 200

    # 2. Hand off discovery from scout report to transfer room
    handoff_res = client.post(f"/scout/reports/{player.id}/transfer-room")
    assert handoff_res.status_code == 200
    payload = handoff_res.json()

    assert payload["status"] == "handed_off"
    assert payload["player_id"] == player.id
    assert payload["club_id"] == club.id
    assert payload["has_active_listing"] is True
    assert payload["listing_id"] == "listing-tf-star"
    assert payload["market_status"] == "open_opportunity"

    # Verify canonical MarketWatchlistEntry was persisted in the database
    watchlist_entry = session.scalar(
        select(MarketWatchlistEntry).where(
            MarketWatchlistEntry.club_id == club.id, MarketWatchlistEntry.player_id == player.id
        )
    )
    assert watchlist_entry is not None
    assert watchlist_entry.source == "scouting_discovery"

    # The authenticated club can read its persisted shortlist with canonical
    # player data and the current listing, but cannot query another club's data.
    watchlist_res = client.get(f"/api/transfer-market/watchlist?club_id={club.id}")
    assert watchlist_res.status_code == 200, watchlist_res.text
    watchlist_payload = watchlist_res.json()
    assert len(watchlist_payload) == 1
    assert watchlist_payload[0]["player_id"] == player.id
    assert watchlist_payload[0]["player"]["full_name"] == player.full_name
    assert watchlist_payload[0]["active_listing"]["id"] == "listing-tf-star"

    forbidden_watchlist_res = client.get("/api/transfer-market/watchlist?club_id=other-club")
    assert forbidden_watchlist_res.status_code in {403, 404}

    # 3. Also verify handoff from shortlist entry
    sl_res = client.post("/talent/shortlists", json={"name": "Window Radar"})
    sl_id = sl_res.json()["id"]
    add_sl_res = client.post(f"/talent/shortlists/{sl_id}/entries", json={"player_id": player.id})
    entry_id = add_sl_res.json()["entries"][0]["id"]

    sl_handoff_res = client.post(f"/talent/shortlists/{sl_id}/entries/{entry_id}/transfer-room")
    assert sl_handoff_res.status_code == 200
    sl_payload = sl_handoff_res.json()
    assert sl_payload["status"] == "handed_off"
    assert sl_payload["has_active_listing"] is True
