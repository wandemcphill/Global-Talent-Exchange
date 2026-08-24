from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.models.calendar_engine import CalendarEvent
from app.models.competition import Competition
from app.models.competition_entry import CompetitionEntry
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_wallet_ledger import CompetitionWalletLedger


def _create_competition(
    client,
    *,
    host: dict[str, str],
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
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "scheduled_start_at": datetime(2035, 3, 20, tzinfo=timezone.utc).isoformat(),
        },
        headers=host["headers"],
    )
    assert response.status_code == 201, response.text
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
            json={"club_id": entrant["club_id"]},
        )
        assert join.status_code == 200, join.text


def test_league_round_and_fixture_generation(
    client,
    competition_admin_headers,
    auth_user_factory,
    competition_club_factory,
) -> None:
    host = auth_user_factory(suffix="league-fixtures-host")
    competition_id = _create_competition(
        client, host=host, name="League Fixtures", format="league", capacity=4
    )
    entrants = []
    for index in range(1, 5):
        entrant = auth_user_factory(suffix=f"league-fixture-{index}")
        entrant["club_id"] = competition_club_factory(owner_user_id=entrant["user_id"])
        entrants.append(entrant)
    _publish_and_join(client, competition_id, competition_admin_headers, entrants)

    seed = client.post(
        f"/api/competitions/{competition_id}/seed",
        headers=competition_admin_headers,
        json={"seed_method": "random"},
    )
    assert seed.status_code == 200
    launch = client.post(
        f"/api/competitions/{competition_id}/launch",
        headers=competition_admin_headers,
    )
    assert launch.status_code == 200

    rounds = client.get(f"/api/competitions/{competition_id}/rounds").json()
    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures").json()

    assert len(rounds) == 3
    assert len(fixtures) == 6
    assert {match["stage"] for match in fixtures} == {"league"}


def test_standings_update_after_match_completion(
    client,
    competition_admin_headers,
    auth_user_factory,
    competition_club_factory,
) -> None:
    host = auth_user_factory(suffix="league-standings-host")
    competition_id = _create_competition(
        client, host=host, name="League Standings", format="league", capacity=2
    )
    entrants = []
    for index in range(1, 3):
        entrant = auth_user_factory(suffix=f"league-standings-{index}")
        entrant["club_id"] = competition_club_factory(owner_user_id=entrant["user_id"])
        entrants.append(entrant)
    _publish_and_join(client, competition_id, competition_admin_headers, entrants)

    seed = client.post(
        f"/api/competitions/{competition_id}/seed",
        headers=competition_admin_headers,
        json={"seed_method": "random"},
    )
    assert seed.status_code == 200
    launch = client.post(
        f"/api/competitions/{competition_id}/launch",
        headers=competition_admin_headers,
    )
    assert launch.status_code == 200

    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures").json()
    assert len(fixtures) == 1
    match = fixtures[0]

    event = client.post(
        f"/api/competitions/{competition_id}/matches/{match['id']}/events",
        headers=competition_admin_headers,
        json={"event_type": "goal", "minute": 12, "club_id": match["home_club_id"], "highlight": True},
    )
    assert event.status_code == 201

    result = client.post(
        f"/api/competitions/{competition_id}/matches/{match['id']}/result",
        headers=competition_admin_headers,
        json={"home_score": 2, "away_score": 1},
    )
    assert result.status_code == 200

    standings = client.get(f"/api/competitions/{competition_id}/standings").json()
    assert len(standings) == 2
    leader = standings[0]
    assert leader["points"] == 3
    assert leader["wins"] == 1


def test_re_settling_a_completed_match_with_a_different_score_returns_409(
    client,
    competition_admin_headers,
    auth_user_factory,
    competition_club_factory,
) -> None:
    """A duplicate/late ``.../result`` call with a conflicting scoreline is a client-fixable

    conflict (the match is already settled), not a server fault. Before this fix,
    ``CompetitionMatchService.complete_match``'s plain ``ValueError`` fell through the
    router's ``_handle_competition_errors`` (which only recognizes
    ``CompetitionActionError``) and surfaced as an unhandled 500.
    """
    host = auth_user_factory(suffix="league-resettle-host")
    competition_id = _create_competition(
        client, host=host, name="League Resettle", format="league", capacity=2
    )
    entrants = []
    for index in range(1, 3):
        entrant = auth_user_factory(suffix=f"league-resettle-{index}")
        entrant["club_id"] = competition_club_factory(owner_user_id=entrant["user_id"])
        entrants.append(entrant)
    _publish_and_join(client, competition_id, competition_admin_headers, entrants)

    seed = client.post(
        f"/api/competitions/{competition_id}/seed",
        headers=competition_admin_headers,
        json={"seed_method": "random"},
    )
    assert seed.status_code == 200
    launch = client.post(
        f"/api/competitions/{competition_id}/launch",
        headers=competition_admin_headers,
    )
    assert launch.status_code == 200

    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures").json()
    match = fixtures[0]

    first = client.post(
        f"/api/competitions/{competition_id}/matches/{match['id']}/result",
        headers=competition_admin_headers,
        json={"home_score": 2, "away_score": 1},
    )
    assert first.status_code == 200

    conflicting = client.post(
        f"/api/competitions/{competition_id}/matches/{match['id']}/result",
        headers=competition_admin_headers,
        json={"home_score": 0, "away_score": 4},
    )
    assert conflicting.status_code == 409, conflicting.text
    assert "already settled" in conflicting.json()["detail"]

    # The original settled result must be untouched by the rejected replay.
    standings = client.get(f"/api/competitions/{competition_id}/standings").json()
    leader = next(row for row in standings if row["club_id"] == match["home_club_id"])
    assert leader["points"] == 3


def test_cup_playoff_progression_and_settlement(
    client,
    competition_admin_headers,
    auth_user_factory,
    competition_club_factory,
) -> None:
    host = auth_user_factory(suffix="cup-progression-host")
    competition_id = _create_competition(client, host=host, name="Cup Progression", format="cup", capacity=4)
    entrants = []
    for index in range(1, 5):
        entrant = auth_user_factory(suffix=f"cup-progression-{index}")
        entrant["club_id"] = competition_club_factory(owner_user_id=entrant["user_id"])
        entrants.append(entrant)
    _publish_and_join(client, competition_id, competition_admin_headers, entrants)

    seeded = client.post(
        f"/api/competitions/{competition_id}/seed",
        headers=competition_admin_headers,
        json={"seed_method": "random"},
    ).json()
    assert seeded["status"] == "seeded"

    launched = client.post(
        f"/api/competitions/{competition_id}/launch",
        headers=competition_admin_headers,
    ).json()
    assert launched["status"] == "live"

    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures").json()
    assert len(fixtures) == 2
    for match in fixtures:
        result = client.post(
            f"/api/competitions/{competition_id}/matches/{match['id']}/result",
            headers=competition_admin_headers,
            json={"home_score": 1, "away_score": 0, "winner_club_id": match["home_club_id"]},
        )
        assert result.status_code == 200

    advanced = client.post(
        f"/api/competitions/{competition_id}/advance",
        headers=competition_admin_headers,
        json={"force": False},
    ).json()
    assert advanced["status"] in {"live", "completed"}

    fixtures = client.get(f"/api/competitions/{competition_id}/fixtures").json()
    final_matches = [match for match in fixtures if match["round_number"] == 2]
    assert len(final_matches) == 1

    final_match = final_matches[0]
    client.post(
        f"/api/competitions/{competition_id}/matches/{final_match['id']}/result",
        headers=competition_admin_headers,
        json={"home_score": 2, "away_score": 0, "winner_club_id": final_match["home_club_id"]},
    )

    completed = client.post(
        f"/api/competitions/{competition_id}/advance",
        headers=competition_admin_headers,
        json={"force": False},
    ).json()
    assert completed["status"] == "completed"

    settled = client.post(
        f"/api/competitions/{competition_id}/finalize",
        headers=competition_admin_headers,
        json={"settle": True},
    ).json()
    assert settled["status"] == "settled"


def test_schedule_blackout_avoids_exclusive_window(client, app_session_factory, auth_user_factory) -> None:
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

    host = auth_user_factory(suffix="blackout-host")
    competition_id = _create_competition(client, host=host, name="Blackout League", format="league", capacity=4)
    preview = client.post(
        f"/api/competitions/{competition_id}/schedule/preview",
        headers=host["headers"],
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
    competition_club_factory,
) -> None:
    host = auth_user_factory(suffix="locked-league-host")
    competition_id = _create_competition(client, host=host, name="Locked League", format="league", capacity=4)
    entrants = []
    for index in range(1, 5):
        entrant = auth_user_factory(suffix=f"locked-league-{index}")
        entrant["club_id"] = competition_club_factory(owner_user_id=entrant["user_id"])
        entrants.append(entrant)
    _publish_and_join(client, competition_id, competition_admin_headers, entrants)

    seed = client.post(
        f"/api/competitions/{competition_id}/seed",
        headers=competition_admin_headers,
        json={"seed_method": "random"},
    )
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
    competition_club_factory,
) -> None:
    host = auth_user_factory(suffix="paid-join-host")
    competition_id = _create_competition(
        client,
        host=host,
        name="Paid Join Guard",
        format="league",
        capacity=2,
        entry_fee="25.00",
        currency="credit",
    )
    entrant = auth_user_factory(suffix="paid-join-guard", funded_credit=Decimal("100.0000"))
    entrant["club_id"] = competition_club_factory(owner_user_id=entrant["user_id"])

    publish = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=competition_admin_headers,
        json={"open_for_join": True},
    )
    assert publish.status_code == 200

    first_join = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"club_id": entrant["club_id"]},
    )
    assert first_join.status_code == 200, first_join.text

    second_join = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrant["headers"],
        json={"club_id": entrant["club_id"]},
    )
    assert second_join.status_code == 200, second_join.text

    with app_session_factory() as session:
        participant_count = session.scalar(
            select(func.count())
            .select_from(CompetitionParticipant)
            .where(
                CompetitionParticipant.competition_id == competition_id,
                CompetitionParticipant.club_id == entrant["club_id"],
            )
        )
        entry_count = session.scalar(
            select(func.count())
            .select_from(CompetitionEntry)
            .where(
                CompetitionEntry.competition_id == competition_id,
                CompetitionEntry.club_id == entrant["club_id"],
            )
        )
        fee_collection_count = session.scalar(
            select(func.count())
            .select_from(CompetitionWalletLedger)
            .where(
                CompetitionWalletLedger.competition_id == competition_id,
                CompetitionWalletLedger.entry_type == "entry_fee_collection",
                CompetitionWalletLedger.reference_id == entrant["user_id"],
            )
        )
        participant = session.scalar(
            select(CompetitionParticipant).where(
                CompetitionParticipant.competition_id == competition_id,
                CompetitionParticipant.club_id == entrant["club_id"],
            )
        )

    assert participant_count == 1
    assert entry_count == 1
    assert fee_collection_count == 1
    assert participant is not None
    assert participant.paid_at is not None
    assert participant.paid_entry_fee_minor == 250000
