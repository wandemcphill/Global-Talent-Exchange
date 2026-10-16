from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.models.club_profile import ClubProfile
from app.models.competition_escrow import CompetitionEscrow


def _error_message(response) -> str:
    payload = response.json()
    return payload.get("detail") or payload.get("message")


def _create_club(app_session_factory, *, owner_user_id: str, slug: str, name: str) -> str:
    with app_session_factory() as session:
        club = ClubProfile(
            owner_user_id=owner_user_id,
            club_name=name,
            short_name=name[:20],
            slug=slug,
            primary_color="#A6FF1A",
            secondary_color="#0B1210",
            accent_color="#58D5FF",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
        )
        session.add(club)
        session.commit()
        return club.id


def test_paid_user_hosted_join_creates_fan_coin_escrow_and_visible_pot(
    client,
    app_session_factory,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="competition-os-host")
    entrant = auth_user_factory(suffix="competition-os-entrant", funded_credit="50.0000")
    club_id = _create_club(
        app_session_factory,
        owner_user_id=entrant["user_id"],
        slug="competition-os-entrant-fc",
        name="Competition OS Entrant FC",
    )

    create_response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Competition OS Paid Ladder",
            "format": "league",
            "visibility": "public",
            "entry_fee": "10.00",
            "capacity": 4,
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "rules_summary": "Paid user-hosted ladder competition.",
        },
    )
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert created["platform_fee_pct"] == "0.20"
    assert created["currency"] == "credit"
    assert created["is_ranked"] is True

    competition_id = created["id"]
    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=host["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200, publish_response.text

    join_response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"club_id": club_id},
    )
    assert join_response.status_code == 200, join_response.text
    joined = join_response.json()
    assert joined["participant_count"] == 1
    assert joined["gross_pot"] == "10.0000"
    assert joined["net_payout_pot"] == "8.0000"

    pot_response = client.get(f"/api/competitions/{competition_id}/pot")
    assert pot_response.status_code == 200, pot_response.text
    pot = pot_response.json()
    assert pot["gross_pot"] == "10.0000"
    assert pot["platform_fee_amount"] == "2.0000"
    assert pot["net_payout_pot"] == "8.0000"
    assert pot["remaining_slots"] == 3

    participants_response = client.get(f"/api/competitions/{competition_id}/participants")
    assert participants_response.status_code == 200, participants_response.text
    participants = participants_response.json()["participants"]
    assert participants[0]["club_id"] == club_id
    assert participants[0]["escrow_status"] == "escrowed"

    with app_session_factory() as session:
        escrow = session.scalar(
            select(CompetitionEscrow).where(
                CompetitionEscrow.competition_id == competition_id,
                CompetitionEscrow.user_id == entrant["user_id"],
                CompetitionEscrow.club_id == club_id,
            )
        )
        assert escrow is not None
        assert escrow.amount_minor == 100_000
        assert escrow.currency == "credit"
        assert escrow.escrow_status == "escrowed"


def test_host_funded_fixed_prize_requires_escrow_before_publish(
    client,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="competition-os-unfunded-host")
    create_response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Competition OS Unfunded Prize",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "capacity": 4,
            "prize_mode": "host_funded_fixed",
            "host_funded_prize_total": "100.00",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "rules_summary": "Host-funded prize must be guaranteed.",
        },
    )
    assert create_response.status_code == 201, create_response.text
    competition_id = create_response.json()["id"]

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=host["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 400
    assert _error_message(publish_response) == "host_prize_insufficient_balance"


def test_host_funded_fixed_prize_escrows_and_refunds_on_cancel(
    client,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="competition-os-funded-host", funded_credit=Decimal("200.0000"))
    create_response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Competition OS Fixed Prize",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "capacity": 4,
            "prize_mode": "host_funded_fixed",
            "fixed_prizes": {"1": "60.00", "2": "25.00", "3": "15.00"},
            "payout_structure": [
                {"place": 1, "percent": "0.60"},
                {"place": 2, "percent": "0.25"},
                {"place": 3, "percent": "0.15"},
            ],
            "rules_summary": "Advertised prizes are net winner payouts.",
        },
    )
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert created["host_funded_prize_total"] == "100.00"
    assert created["host_funding_required"] == "125.00"
    assert created["host_platform_fee"] == "25.00"

    competition_id = created["id"]
    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=host["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200, publish_response.text
    assert publish_response.json()["host_funding_escrowed"] == "125.00"

    cancel_response = client.post(f"/api/competitions/{competition_id}/cancel", headers=host["headers"])
    assert cancel_response.status_code == 200, cancel_response.text
    assert cancel_response.json()["status"] == "cancelled"
    assert cancel_response.json()["host_funding_escrowed"] == "0.00"


def test_join_blocks_explicit_club_owned_by_another_user(
    client,
    app_session_factory,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="competition-os-owner-host")
    entrant = auth_user_factory(suffix="competition-os-owner-entrant")
    intruder = auth_user_factory(suffix="competition-os-owner-intruder")
    club_id = _create_club(
        app_session_factory,
        owner_user_id=entrant["user_id"],
        slug="competition-os-owned-club",
        name="Competition OS Owned Club",
    )
    create_response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Competition OS Ownership Gate",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "capacity": 4,
            "payout_structure": [{"place": 1, "percent": "1.00"}],
        },
    )
    assert create_response.status_code == 201, create_response.text
    competition_id = create_response.json()["id"]
    assert (
        client.post(
            f"/api/competitions/{competition_id}/publish",
            headers=host["headers"],
            json={"open_for_join": True},
        ).status_code
        == 200
    )

    join_response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=intruder["headers"],
        json={"club_id": club_id},
    )
    assert join_response.status_code == 400
    assert _error_message(join_response) == "club_owner_required"


def test_random_quote_and_discovery_filters_surface_ranked_ladder_metadata(
    client,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="competition-os-random-host")
    create_response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Competition OS Random Duel",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "capacity": 2,
            "competition_mode": "one_v_one",
            "online_now": True,
            "is_ranked": False,
            "payout_structure": [{"place": 1, "percent": "1.00"}],
        },
    )
    assert create_response.status_code == 201, create_response.text
    competition_id = create_response.json()["id"]
    assert (
        client.post(
            f"/api/competitions/{competition_id}/publish",
            headers=host["headers"],
            json={"open_for_join": True},
        ).status_code
        == 200
    )

    discovery_response = client.get("/api/competitions", params={"ranked": "false", "starts": "online_now"})
    assert discovery_response.status_code == 200, discovery_response.text
    assert any(item["id"] == competition_id for item in discovery_response.json()["items"])

    quote_response = client.post(
        "/api/competitions/random/quote",
        headers=host["headers"],
        json={"mode": "one_v_one"},
    )
    assert quote_response.status_code == 200, quote_response.text
    quote = quote_response.json()
    assert quote["competition_id"] == competition_id
    assert quote["ranked"] is False


def test_national_competition_join_ignores_club_ranking_gate(
    client,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="competition-os-national-host")
    entrant = auth_user_factory(suffix="competition-os-national-entrant")
    create_response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "National Team Trial Cup",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "capacity": 2,
            "competition_type": "national_team",
            "competition_mode": "national_team",
            "min_club_ranking": 9999,
            "payout_structure": [{"place": 1, "percent": "1.00"}],
        },
    )
    assert create_response.status_code == 201, create_response.text
    competition_id = create_response.json()["id"]
    assert (
        client.post(
            f"/api/competitions/{competition_id}/publish",
            headers=host["headers"],
            json={"open_for_join": True},
        ).status_code
        == 200
    )

    join_response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={},
    )
    assert join_response.status_code == 200, join_response.text
    assert join_response.json()["participant_count"] == 1
