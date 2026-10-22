from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.club_legacy.models import (
    ClubLegacyAsset,
    ClubLegacyCatalogueItem,
    ClubLegacyExecutive,
)
from app.models.club_growth import AcademyProfile, AcademyProspect
from app.models.club_infra import ClubFacility, ClubStadium
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.club_trophy import ClubTrophy
from app.models.user import PublicAccountType, User
from app.owner_console.models import OwnerClubState, OwnerSquadPlayer


def _seed_public_club(session):
    unique = uuid4().hex[:8]
    owner = User(
        email=f"public-profile-{unique}@example.test",
        username=f"public_profile_owner_{unique}",
        password_hash="test-hash",
        display_name="Amara Okafor",
        account_type=PublicAccountType.USER,
    )
    session.add(owner)
    session.flush()

    club = ClubProfile(
        owner_user_id=owner.id,
        club_name="Lagos Eclipse FC",
        short_name="LEFC",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug=f"lagos-eclipse-public-profile-{unique}",
        primary_color="#101B32",
        secondary_color="#D5B46A",
        accent_color="#24D18F",
        country_code="NG",
        city_name="Lagos",
        founded_at=date(2004, 8, 15),
        home_venue_name="Eclipse Arena",
        visibility="public",
    )
    session.add(club)
    session.flush()

    session.add_all(
        [
            ClubStadium(
                club_id=club.id,
                name="Eclipse Arena",
                level=4,
                capacity=42000,
                theme_key="night-eclipse",
            ),
            ClubFacility(
                club_id=club.id,
                training_level=4,
                academy_level=5,
                medical_level=3,
                branding_level=4,
                youth_recruitment_level=5,
            ),
            OwnerClubState(
                club_id=club.id,
                owner_user_id=owner.id,
                club_name=club.club_name,
                stage="active",
                manager_json={"name": "Ayo Balogun"},
                facilities_json={"academy": 5},
            ),
            ClubLegacyExecutive(club_id=club.id, role="gm", name="Nneka Manager"),
            ClubLegacyExecutive(
                club_id=club.id,
                role="hoyd",
                name="Chidi Youth Director",
            ),
            OwnerSquadPlayer(
                club_id=club.id,
                name="Samuel Okoro",
                position="ST",
                age=24,
                rating=91,
                potential=93,
                is_regen=False,
            ),
            OwnerSquadPlayer(
                club_id=club.id,
                name="Kaito Mensah",
                position="RW",
                age=17,
                rating=78,
                potential=97,
                is_regen=True,
            ),
            ClubTrophy(
                club_id=club.id,
                trophy_type="league",
                trophy_name="GTEX Champions Cup",
                competition_source="GTEX Champions Cup",
                season_label="2026",
            ),
        ]
    )

    academy = AcademyProfile(club_id=club.id, level=5, capacity_limit=24)
    session.add(academy)
    session.flush()
    session.add(
        AcademyProspect(
            club_id=club.id,
            academy_profile_id=academy.id,
            display_name="Tunde Bello",
            nationality="NG",
            position="CM",
            age=16,
            current_ability=49,
            potential=91,
            portrait_asset_ref=None,
        )
    )

    bus = ClubLegacyCatalogueItem(
        sku=f"public-profile-coach-bus-{unique}",
        name="Vanguard First-Team Coach",
        category="coach",
        price=Decimal("320"),
        supply_cap=10,
        fallback_label="Team coach",
    )
    jet = ClubLegacyCatalogueItem(
        sku=f"public-profile-owner-jet-{unique}",
        name="Sovereign 900X Jet",
        category="jet",
        price=Decimal("50000"),
        supply_cap=5,
        fallback_label="Private jet",
    )
    session.add_all([bus, jet])
    session.flush()
    session.add_all(
        [
            ClubLegacyAsset(
                catalogue_id=bus.id,
                edition_number=1,
                owner_class="club",
                owner_ref=club.id,
                club_id=club.id,
                status="owned",
            ),
            ClubLegacyAsset(
                catalogue_id=jet.id,
                edition_number=1,
                owner_class="owner",
                owner_ref=owner.id,
                club_id=None,
                status="owned",
            ),
        ]
    )
    session.commit()
    return owner.id, club.id


def test_public_club_dossier_has_rich_club_details_and_redacts_private_economics(client, app):
    with app.state.session_factory() as session:
        owner_id, club_id = _seed_public_club(session)

    response = client.get(f"/api/clubs/{club_id}/public-profile")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["club"]["name"] == "Lagos Eclipse FC"
    assert data["owner"]["id"] == owner_id
    assert data["stadium"]["name"] == "Eclipse Arena"
    assert data["stadium"]["capacity"] == 42000
    assert data["facilities"]["training_level"] == 4
    assert data["academy"]["level"] == 5
    assert data["academy"]["prospects"][0]["name"] == "Tunde Bello"
    assert data["squad"]["best_player"]["name"] == "Samuel Okoro"
    assert data["squad"]["most_promising_player"]["name"] == "Kaito Mensah"
    assert data["staff"] is not None
    assert {person["role"]: person["name"] for person in data["staff"]}["manager"] == "Ayo Balogun"
    assert {person["role"]: person["name"] for person in data["staff"]}["general_manager"] == "Nneka Manager"
    assert {person["role"]: person["name"] for person in data["staff"]}["head_of_youth_development"] == "Chidi Youth Director"
    assert any(asset["name"] == "Vanguard First-Team Coach" for asset in data["coach_buses"])
    assert data["trophies"][0]["name"] == "GTEX Champions Cup"

    # Public pages carry the aggregate chosen by the product, not the private
    # wallet breakdown, wages, inbox, or internal economic/sponsor records.
    public_payload = response.text
    for forbidden in ("personal_cash", "personal_assets", "wallet_credits", "salary_minor", "password_hash"):
        assert forbidden not in public_payload


def test_public_owner_profile_lists_public_clubs_and_personal_assets_without_wallet_breakdown(client, app):
    with app.state.session_factory() as session:
        owner_id, club_id = _seed_public_club(session)

    response = client.get(f"/api/owner/public/profile/{owner_id}")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["id"] == owner_id
    assert data["display_name"] == "Amara Okafor"
    assert data["club_count"] == 1
    assert data["public_clubs"][0]["id"] == club_id
    assert data["luxury_asset_count"] == 1
    assert data["assets"][0]["name"] == "Sovereign 900X Jet"
    assert data["assets"][0]["category"] == "jet"
    assert "net_worth" in data
    assert "personal_cash" not in data
    assert "personal_assets" not in data
    assert "wallet" not in data
    assert "password_hash" not in response.text


def test_public_dossiers_return_404_for_private_clubs_and_nonexistent_owners(client, app):
    with app.state.session_factory() as session:
        owner = User(
            email=f"private-profile-{uuid4().hex[:8]}@example.test",
            username=f"private_profile_{uuid4().hex[:8]}",
            password_hash="test-hash",
            display_name="Private Owner",
            account_type=PublicAccountType.USER,
        )
        session.add(owner)
        session.flush()
        private_club = ClubProfile(
            owner_user_id=owner.id,
            club_name="Private Club",
            short_name="PC",
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            slug="private-club-profile",
            primary_color="#101B32",
            secondary_color="#D5B46A",
            accent_color="#24D18F",
            visibility="private",
        )
        session.add(private_club)
        session.commit()
        private_club_id = private_club.id

    assert client.get(f"/api/clubs/{private_club_id}/public-profile").status_code == 404
    assert client.get("/api/owner/public/profile/nonexistent-owner").status_code == 404
