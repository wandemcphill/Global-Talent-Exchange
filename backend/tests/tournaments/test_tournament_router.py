from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import get_session
from app.models import Base
from app.models.base import utcnow
from app.models.event_backbone import EventOutbox
from app.models.tournament import Tournament, TournamentMatch, TournamentPlayer, TournamentRound
from app.models.user import User
from app.models.wallet import LedgerAccount, LedgerBalanceProjection, LedgerEntry, LedgerEntryReason, LedgerSourceTag, LedgerTransaction, LedgerUnit
from app.tournaments.router import router
from app.wallets.service import LedgerPosting, WalletService


def _build_app(database_url: str) -> tuple[TestClient, sessionmaker]:
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            LedgerAccount.__table__,
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            EventOutbox.__table__,
            Tournament.__table__,
            TournamentRound.__table__,
            TournamentMatch.__table__,
            TournamentPlayer.__table__,
        ],
    )
    app = FastAPI()
    app.include_router(router)

    def override_get_session():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app), SessionLocal


@pytest.fixture()
def tournament_client(tmp_path: Path):
    client, session_factory = _build_app(f"sqlite:///{tmp_path / 'tournament-router.db'}")
    try:
        yield client, session_factory
    finally:
        client.close()


def _create_user(session, *, suffix: int) -> User:
    user = User(
        email=f"player{suffix}@example.com",
        username=f"player_{suffix}",
        display_name=f"Player {suffix}",
        password_hash="not-used",
    )
    session.add(user)
    session.flush()
    return user


def _fund_user(session, *, user: User, amount: int) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal(str(amount))),
            LedgerPosting(account=platform_account, amount=Decimal(str(-amount))),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=f"seed-balance:{user.id}:{amount}",
        description="Seed tournament wallet balance for tests",
    )


def _get_credit_balance(session, user: User) -> Decimal:
    wallet_service = WalletService()
    return wallet_service.get_wallet_summary(session, user, currency=LedgerUnit.CREDIT).available_balance


def _seed_users(session_factory: sessionmaker, *, count: int, balance: int = 1_000) -> list[User]:
    with session_factory() as session:
        users = [_create_user(session, suffix=index + 1) for index in range(count)]
        for user in users:
            _fund_user(session, user=user, amount=balance)
        session.commit()
        return users


def _create_tournament(client: TestClient, *, name: str = "Weekend Clash", max_players: int = 4, entry_fee: int = 500) -> dict:
    response = client.post(
        "/api/tournaments",
        json={
            "name": name,
            "game_type": "prediction",
            "entry_fee": entry_fee,
            "max_players": max_players,
            "round_timeout_minutes": 60,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _join_all(client: TestClient, tournament_id: str, users: list[User]) -> dict:
    latest_payload: dict | None = None
    for user in users:
        response = client.post(f"/api/tournaments/{tournament_id}/join", json={"user_id": user.id})
        assert response.status_code == 200, response.text
        latest_payload = response.json()
    assert latest_payload is not None
    return latest_payload


def test_join_flow_deducts_entry_fee_and_starts_when_full(tournament_client) -> None:
    client, session_factory = tournament_client
    users = _seed_users(session_factory, count=4)
    tournament = _create_tournament(client)

    payload = _join_all(client, tournament["tournament_id"], users)

    assert payload["status"] == "active"
    assert payload["prize_pool"] == 2_000
    assert payload["player_count"] == 4
    assert payload["current_round"] == 1
    assert [player["bracket_slot"] for player in payload["players"]] == [1, 2, 3, 4]

    round_one_matches = [match for match in payload["matches"] if match["round_number"] == 1]
    assert len(round_one_matches) == 2
    assert (round_one_matches[0]["player_one_user_id"], round_one_matches[0]["player_two_user_id"]) == (users[0].id, users[3].id)
    assert (round_one_matches[1]["player_one_user_id"], round_one_matches[1]["player_two_user_id"]) == (users[1].id, users[2].id)

    with session_factory() as session:
        balances = [_get_credit_balance(session, session.get(User, user.id)) for user in users]
    assert balances == [Decimal("500.0000")] * 4


def test_completed_matches_advance_and_finish_tournament(tournament_client) -> None:
    client, session_factory = tournament_client
    users = _seed_users(session_factory, count=4)
    tournament = _create_tournament(client)
    payload = _join_all(client, tournament["tournament_id"], users)
    tournament_id = payload["tournament_id"]

    round_one_matches = [match for match in payload["matches"] if match["round_number"] == 1]
    first_result = client.post(
        f"/api/tournaments/{tournament_id}/matches/{round_one_matches[0]['match_id']}/result",
        json={"winner_user_id": users[0].id, "player_one_score": 3, "player_two_score": 1},
    )
    assert first_result.status_code == 200, first_result.text
    assert first_result.json()["current_round"] == 1

    second_result = client.post(
        f"/api/tournaments/{tournament_id}/matches/{round_one_matches[1]['match_id']}/result",
        json={"winner_user_id": users[1].id, "player_one_score": 2, "player_two_score": 0},
    )
    assert second_result.status_code == 200, second_result.text
    advanced = second_result.json()
    assert advanced["current_round"] == 2
    assert advanced["status"] == "active"

    final_match = next(match for match in advanced["matches"] if match["round_number"] == 2)
    final_result = client.post(
        f"/api/tournaments/{tournament_id}/matches/{final_match['match_id']}/result",
        json={"winner_user_id": users[0].id, "player_one_score": 1, "player_two_score": 0},
    )
    assert final_result.status_code == 200, final_result.text
    completed = final_result.json()

    assert completed["status"] == "completed"
    assert completed["current_round"] == 2
    assert completed["winner_user_id"] == users[0].id
    winner = next(player for player in completed["players"] if player["user_id"] == users[0].id)
    assert winner["status"] == "winner"


def test_timeout_advances_unfinished_round_using_bracket_priority(tournament_client) -> None:
    client, session_factory = tournament_client
    users = _seed_users(session_factory, count=4)
    tournament = _create_tournament(client)
    payload = _join_all(client, tournament["tournament_id"], users)
    tournament_id = payload["tournament_id"]

    round_one_matches = [match for match in payload["matches"] if match["round_number"] == 1]
    first_result = client.post(
        f"/api/tournaments/{tournament_id}/matches/{round_one_matches[0]['match_id']}/result",
        json={"winner_user_id": users[0].id},
    )
    assert first_result.status_code == 200, first_result.text

    with session_factory() as session:
        active_round = session.scalar(
            select(TournamentRound).where(
                TournamentRound.tournament_id == tournament_id,
                TournamentRound.round_number == 1,
            )
        )
        assert active_round is not None
        active_round.timeout_at = utcnow() - timedelta(minutes=1)
        session.commit()

    advance_response = client.post(f"/api/tournaments/{tournament_id}/advance")
    assert advance_response.status_code == 200, advance_response.text
    advanced = advance_response.json()

    assert advanced["current_round"] == 2
    timed_out_match = next(
        match for match in advanced["matches"] if match["round_number"] == 1 and match["slot_index"] == 2
    )
    assert timed_out_match["resolution"] == "timeout"
    assert timed_out_match["winner_user_id"] == users[1].id

    final_match = next(match for match in advanced["matches"] if match["round_number"] == 2)
    assert final_match["player_one_user_id"] == users[0].id
    assert final_match["player_two_user_id"] == users[1].id
