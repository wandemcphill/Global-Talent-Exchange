from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from backend.tests.support.secrets import TEST_PASSWORD
from app.auth.service import AuthService
from app.models.user import User
from app.models.wallet import LedgerUnit
from app.wallets.service import WalletService


def _register_user(session, *, suffix: str, funded: bool) -> User:
    user = AuthService().register_user(
        session,
        email=f"treasure-{suffix}@example.com",
        username=f"treasure_{suffix}",
        password=TEST_PASSWORD,
    )
    if funded:
        WalletService().credit_trade_proceeds(
            session,
            user=user,
            amount=Decimal("100.0000"),
            reference=f"seed:{user.id}",
            description="Competition API treasure chest funding",
            external_reference=f"seed:{user.id}",
            unit=LedgerUnit.CREDIT,
        )
    return user


def _login(client, *, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_paid_league_finalize_exposes_rewards_progression_and_wallet_payouts(
    client,
    app_session_factory,
    competition_admin_headers,
) -> None:
    suffix = uuid4().hex[:8]
    with app_session_factory() as session:
        host = _register_user(session, suffix=f"{suffix}-host", funded=False)
        entrants = [
            _register_user(session, suffix=f"{suffix}-a", funded=True),
            _register_user(session, suffix=f"{suffix}-b", funded=True),
            _register_user(session, suffix=f"{suffix}-c", funded=True),
            _register_user(session, suffix=f"{suffix}-d", funded=True),
        ]
        session.commit()
        host_id = host.id
        host_username = host.username
        entrant_ids = [user.id for user in entrants]
        entrant_emails = [user.email for user in entrants]
        winner_id = entrants[0].id
        winner_username = entrants[0].username

    create_response = client.post(
        "/api/competitions",
        json={
            "name": f"Treasure Chest League {suffix}",
            "format": "league",
            "visibility": "public",
            "entry_fee": "20.00",
            "currency": "credit",
            "capacity": 4,
            "creator_id": host_id,
            "creator_name": host_username,
            "platform_fee_pct": "0.10",
            "host_fee_pct": "0.05",
            "payout_structure": [
                {"place": 1, "percent": "0.60"},
                {"place": 2, "percent": "0.25"},
                {"place": 3, "percent": "0.15"},
            ],
            "rules_summary": "Treasure chest payout validation flow.",
        },
    )
    assert create_response.status_code == 201
    competition_id = create_response.json()["id"]

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=competition_admin_headers,
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200

    entrant_headers = [_login(client, email=email) for email in entrant_emails]
    for index, (entrant_id, headers) in enumerate(zip(entrant_ids, entrant_headers, strict=True), start=1):
        join_response = client.post(
            f"/api/competitions/{competition_id}/join",
            headers=headers,
            json={"user_id": entrant_id, "user_name": f"Entrant {index}"},
        )
        assert join_response.status_code == 200

    seed_response = client.post(
        f"/api/competitions/{competition_id}/seed",
        json={"seed_method": "random"},
    )
    assert seed_response.status_code == 200

    launch_response = client.post(
        f"/api/competitions/{competition_id}/launch",
        headers=competition_admin_headers,
    )
    assert launch_response.status_code == 200

    fixtures_response = client.get(f"/api/competitions/{competition_id}/fixtures")
    assert fixtures_response.status_code == 200
    fixtures = fixtures_response.json()
    assert len(fixtures) == 6

    entrant_rank = {entrant_id: rank for rank, entrant_id in enumerate(entrant_ids)}
    for fixture in fixtures:
        home_rank = entrant_rank[fixture["home_club_id"]]
        away_rank = entrant_rank[fixture["away_club_id"]]
        home_wins = home_rank < away_rank
        result_response = client.post(
            f"/api/competitions/{competition_id}/matches/{fixture['id']}/result",
            json={
                "home_score": 2 if home_wins else 0,
                "away_score": 0 if home_wins else 2,
                "winner_club_id": fixture["home_club_id"] if home_wins else fixture["away_club_id"],
            },
        )
        assert result_response.status_code == 200

    finalize_response = client.post(
        f"/api/competitions/{competition_id}/finalize",
        json={"settle": True},
    )
    assert finalize_response.status_code == 200
    assert finalize_response.json()["status"] == "settled"

    rewards_response = client.get(f"/api/competitions/{competition_id}/rewards")
    assert rewards_response.status_code == 200
    rewards = rewards_response.json()
    assert rewards["competition_id"] == competition_id
    assert [item["amount"] for item in rewards["rewards"]] == ["40.80", "17.00", "10.20"]
    assert [item["status"] for item in rewards["rewards"]] == ["settled", "settled", "settled"]
    assert rewards["rewards"][0]["subject_id"] == entrant_ids[0]
    assert rewards["rewards"][0]["resolved_user_id"] == entrant_ids[0]
    assert rewards["rewards"][0]["display_name"] == winner_username
    assert rewards["rewards"][0]["badge_code"] == "treasure_chest_gold"
    assert rewards["rewards"][0]["title_awarded"] == "Champion"
    assert rewards["rewards"][0]["ranking_points_delta"] == 100

    standings_response = client.get(f"/api/competitions/{competition_id}/standings")
    assert standings_response.status_code == 200
    standings = standings_response.json()
    assert [item["club_id"] for item in standings] == entrant_ids
    assert standings[0]["reward_amount"] == "40.8000"
    assert standings[0]["reward_currency"] == "credit"
    assert standings[0]["reward_status"] == "settled"
    assert standings[0]["badge_code"] == "treasure_chest_gold"
    assert standings[0]["title_awarded"] == "Champion"
    assert standings[0]["career_title"] == "Champion"
    assert standings[0]["career_ranking_points"] == 100
    assert standings[0]["career_total_wins"] == 3
    assert standings[0]["career_total_earnings"] == "40.8000"

    progression_response = client.get(f"/api/competitions/players/{winner_id}/progression")
    assert progression_response.status_code == 200
    progression = progression_response.json()
    assert progression["subject_id"] == winner_id
    assert progression["resolved_user_id"] == winner_id
    assert progression["display_name"] == winner_username
    assert progression["current_title"] == "Champion"
    assert progression["ranking_points"] == 100
    assert progression["total_wins"] == 3
    assert progression["total_championships"] == 1
    assert progression["total_podiums"] == 1
    assert progression["total_competitions"] == 1
    assert progression["total_earnings"] == "40.8000"
    assert progression["best_placement"] == 1
    assert "treasure_chest_gold" in progression["badges"]
    assert "treasure_chest_breakthrough" in progression["badges"]
    assert progression["titles"] == ["Champion"]
    assert len(progression["history"]) == 1
    assert progression["history"][0]["placement"] == 1
    assert progression["history"][0]["earnings"] == "40.8000"
    assert progression["history"][0]["reward_status"] == "settled"

    with app_session_factory() as session:
        wallet_service = WalletService()
        winner = session.get(User, entrant_ids[0])
        runner_up = session.get(User, entrant_ids[1])
        third_place = session.get(User, entrant_ids[2])
        fourth_place = session.get(User, entrant_ids[3])
        host = session.get(User, host_id)
        assert winner is not None
        assert runner_up is not None
        assert third_place is not None
        assert fourth_place is not None
        assert host is not None
        assert wallet_service.get_balance(
            session, wallet_service.get_user_account(session, winner, LedgerUnit.CREDIT)
        ) == Decimal("120.8000")
        assert wallet_service.get_balance(
            session, wallet_service.get_user_account(session, runner_up, LedgerUnit.CREDIT)
        ) == Decimal("97.0000")
        assert wallet_service.get_balance(
            session, wallet_service.get_user_account(session, third_place, LedgerUnit.CREDIT)
        ) == Decimal("90.2000")
        assert wallet_service.get_balance(
            session, wallet_service.get_user_account(session, fourth_place, LedgerUnit.CREDIT)
        ) == Decimal("80.0000")
        assert wallet_service.get_balance(
            session, wallet_service.get_user_account(session, host, LedgerUnit.CREDIT)
        ) == Decimal("4.0000")
        assert wallet_service.get_balance(
            session, wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
        ) == Decimal("8.0000")
