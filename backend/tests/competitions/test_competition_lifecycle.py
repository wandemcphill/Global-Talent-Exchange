from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.calendar_engine import CalendarEvent
from app.models.competition import Competition
from app.models.competition_entry import CompetitionEntry
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_wallet_ledger import CompetitionWalletLedger
from app.models.club_profile import ClubProfile


class _UnwrappingResponse:
    """Wraps a TestClient response so `.json()` returns the v2 envelope's `data`."""

    def __init__(self, response):
        self._response = response

    def __getattr__(self, name):
        return getattr(self._response, name)

    def json(self):
        payload = self._response.json()
        if isinstance(payload, dict) and isinstance(payload.get("success"), bool) and "data" in payload:
            return payload["data"]
        return payload


@pytest.fixture(autouse=True)
def _canonicalize_v2(client):
    # The API contract guard 410s deprecated `/api/...` aliases and the envelope
    # middleware wraps v2 success bodies. Route this file's legacy-style calls to
    # canonical `/api/v2/...` with the version header and unwrap the envelope.
    original = client.request

    def patched(method, url, *args, **kwargs):
        if isinstance(url, str) and url.startswith("/api/") and not url.startswith("/api/v2/"):
            url = "/api/v2" + url[len("/api"):]
        headers = dict(kwargs.get("headers") or {})
        headers.setdefault("X-API-Version", "2")
        kwargs["headers"] = headers
        return _UnwrappingResponse(original(method, url, *args, **kwargs))

    client.request = patched
    yield
    client.request = original


def _create_competition(
    client,
    *,
    name: str,
    format: str,
    capacity: int,
    entry_fee: str = "0.00",
    currency: str = "credit",
) -> str:
    response = client.post(
        "/api/competitions",
        json={
            "name": name,
            "format": format,
            "visibility": "public",
            "entry_fee": entry_fee,
            "currency": currency,
            "capacity": capacity,
            "creator_id": f"host-{name}",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "scheduled_start_at": datetime(2035, 3, 20, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _publish_and_join(
    client, competition_id: str, admin_headers: dict[str, str], entrants: list[dict[str, str]]
) -> None:
    publish = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=admin_headers,
        json={"open_for_join": True},
    )
    assert publish.status_code == 200
    for entrant in entrants:
        join = client.post(
            f"/api/competitions/{competition_id}/join",
            headers=entrant["headers"],
            json={"user_id": entrant["user_id"]},
        )
        assert join.status_code == 200


def test_league_round_and_fixture_generation(client, competition_admin_headers, auth_user_factory) -> None:
    competition_id = _create_competition(client, name="League Fixtures", format="league", capacity=4)
    entrants = [auth_user_factory(suffix=f"league-fixture-{index}") for index in range(1, 5)]
    _publish_and_join(client, competition_id, competition_admin_headers, entrants)

    seed = client.post(f"/api/competitions/{competition_id}/seed", json={"seed_method": "random"})
    assert seed.status_code == 200
    launch = client.post(
        f"/api/competitions/{competition_id}/launch",
        headers=competition_admin_headers,
    )
    assert launch.status_code == 200

    bracket = client.get(f"/api/competitions/{competition_id}/rounds").json()
    fixtures_payload = client.get(f"/api/competitions/{competition_id}/fixtures").json()
    fixtures = fixtures_payload["items"]

    assert bracket["status"] == "empty"
    assert bracket["state"]["reason"] == "competition_has_no_bracket"
    assert fixtures_payload["status"] == "synced"
    assert len(fixtures) == 6
    assert {match["stage"] for match in fixtures} == {"league"}


def test_standings_update_after_match_completion(client, competition_admin_headers, auth_user_factory) -> None:
    competition_id = _create_competition(client, name="League Standings", format="league", capacity=2)
    entrants = [auth_user_factory(suffix=f"league-standings-{index}") for index in range(1, 3)]
    _publish_and_join(client, competition_id, competition_admin_headers, entrants)

    seed = client.post(f"/api/competitions/{competition_id}/seed", json={"seed_method": "random"})
    assert seed.status_code == 200
    launch = client.post(
        f"/api/competitions/{competition_id}/launch",
        headers=competition_admin_headers,
    )
    assert launch.status_code == 200

    fixtures_payload = client.get(f"/api/competitions/{competition_id}/fixtures").json()
    fixtures = fixtures_payload["items"]
    assert fixtures_payload["score_status"] == "pending_results"
    assert fixtures_payload["authoritative_scores"] is False
    assert len(fixtures) == 1
    match = fixtures[0]

    event = client.post(
        f"/api/competitions/{competition_id}/matches/{match['id']}/events",
        json={"event_type": "goal", "minute": 12, "club_id": match["home_club_id"], "highlight": True},
    )
    assert event.status_code == 201

    result = client.post(
        f"/api/competitions/{competition_id}/matches/{match['id']}/result",
        json={"home_score": 2, "away_score": 1},
    )
    assert result.status_code == 200

    standings_payload = client.get(f"/api/competitions/{competition_id}/standings").json()
    standings = standings_payload["items"]
    assert standings_payload["status"] == "synced"
    assert len(standings) == 2
    leader = standings[0]
    assert leader["points"] == 3
    assert leader["wins"] == 1


def test_cup_playoff_progression_and_settlement(client, competition_admin_headers, auth_user_factory) -> None:
    competition_id = _create_competition(client, name="Cup Progression", format="cup", capacity=4)
    entrants = [auth_user_factory(suffix=f"cup-progression-{index}") for index in range(1, 5)]
    _publish_and_join(client, competition_id, competition_admin_headers, entrants)

    seeded = client.post(f"/api/competitions/{competition_id}/seed", json={"seed_method": "random"}).json()
    assert seeded["status"] == "seeded"

    launched = client.post(
        f"/api/competitions/{competition_id}/launch",
        headers=competition_admin_headers,
    ).json()
    assert launched["status"] == "live"

    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures").json()["items"]
    assert len(fixtures) == 2
    for match in fixtures:
        result = client.post(
            f"/api/competitions/{competition_id}/matches/{match['id']}/result",
            json={"home_score": 1, "away_score": 0, "winner_club_id": match["home_club_id"]},
        )
        assert result.status_code == 200

    advanced = client.post(f"/api/competitions/{competition_id}/advance", json={"force": False}).json()
    assert advanced["status"] in {"live", "completed"}

    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures").json()["items"]
    final_matches = [match for match in fixtures if match["round_number"] == 2]
    assert len(final_matches) == 1

    final_match = final_matches[0]
    client.post(
        f"/api/competitions/{competition_id}/matches/{final_match['id']}/result",
        json={"home_score": 2, "away_score": 0, "winner_club_id": final_match["home_club_id"]},
    )

    completed = client.post(f"/api/competitions/{competition_id}/advance", json={"force": False}).json()
    assert completed["status"] == "completed"

    settled = client.post(f"/api/competitions/{competition_id}/finalize", json={"settle": True}).json()
    assert settled["status"] == "settled"


def test_schedule_blackout_avoids_exclusive_window(client, app_session_factory) -> None:
    blocked_date = date(2026, 3, 20)
    with app_session_factory() as session:
        session.add(
            CalendarEvent(
                event_key="world-cup-block",
                title="World Cup",
                source_type="gtx",
                starts_on=blocked_date,
                ends_on=blocked_date,
                exclusive_windows=True,
                pause_other_gtx_competitions=True,
                status="scheduled",
            )
        )
        session.commit()

    competition_id = _create_competition(client, name="Blackout League", format="league", capacity=4)
    preview = client.post(
        f"/api/competitions/{competition_id}/schedule/preview",
        json={"start_date": blocked_date.isoformat()},
    )
    assert preview.status_code == 200
    payload = preview.json()
    assert "Schedule avoided calendar blackout windows." in payload["warnings"]
    assert blocked_date.isoformat() not in payload["assigned_dates"]


def test_launch_applies_tournament_lock_metadata(
    client,
    app_session_factory,
    competition_admin_headers,
    auth_user_factory,
) -> None:
    competition_id = _create_competition(client, name="Locked League", format="league", capacity=4)
    entrants = [auth_user_factory(suffix=f"locked-league-{index}") for index in range(1, 5)]
    _publish_and_join(client, competition_id, competition_admin_headers, entrants)

    seed = client.post(f"/api/competitions/{competition_id}/seed", json={"seed_method": "random"})
    assert seed.status_code == 200
    launch = client.post(
        f"/api/competitions/{competition_id}/launch",
        headers=competition_admin_headers,
    )
    assert launch.status_code == 200

    with app_session_factory() as session:
        competition = session.get(Competition, competition_id)
        assert competition is not None
        lock = dict((competition.metadata_json or {}).get("tournament_lock") or {})

    assert lock["active"] is True
    assert lock["reason"] == "competition_live"
    assert lock["transfers_disabled"] is True
    assert lock["rentals_disabled"] is True


def test_paid_competition_join_is_idempotent_and_collects_single_fee(
    client,
    app_session_factory,
    competition_admin_headers,
    auth_user_factory,
) -> None:
    competition_id = _create_competition(
        client,
        name="Paid Join Guard",
        format="league",
        capacity=2,
        entry_fee="25.00",
        currency="credit",
    )
    entrant = auth_user_factory(suffix="paid-join-guard", funded_credit=Decimal("100.0000"))

    publish = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=competition_admin_headers,
        json={"open_for_join": True},
    )
    assert publish.status_code == 200

    first_join = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"user_id": entrant["user_id"]},
    )
    assert first_join.status_code == 200, first_join.text

    second_join = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"user_id": entrant["user_id"]},
    )
    assert second_join.status_code == 200, second_join.text

    with app_session_factory() as session:
        # Participants are keyed by the entrant's club id (orchestrator resolves the
        # joining user's ClubProfile), not the raw user id.
        club = session.scalar(
            select(ClubProfile).where(ClubProfile.owner_user_id == entrant["user_id"])
        )
        assert club is not None
        participant_count = session.scalar(
            select(func.count())
            .select_from(CompetitionParticipant)
            .where(
                CompetitionParticipant.competition_id == competition_id,
                CompetitionParticipant.club_id == club.id,
            )
        )
        entry_count = session.scalar(
            select(func.count())
            .select_from(CompetitionEntry)
            .where(
                CompetitionEntry.competition_id == competition_id,
                CompetitionEntry.club_id == club.id,
            )
        )
        # Single entrant joined twice; the fee-collection ledger must hold exactly one row.
        fee_collection_count = session.scalar(
            select(func.count())
            .select_from(CompetitionWalletLedger)
            .where(
                CompetitionWalletLedger.competition_id == competition_id,
                CompetitionWalletLedger.entry_type == "entry_fee_collection",
            )
        )
        participant = session.scalar(
            select(CompetitionParticipant).where(
                CompetitionParticipant.competition_id == competition_id,
                CompetitionParticipant.club_id == club.id,
            )
        )

    assert participant_count == 1
    assert entry_count == 1
    assert fee_collection_count == 1
    assert participant is not None
    assert participant.paid_at is not None
    assert participant.paid_entry_fee_minor == 250000
