from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_wallet_user, get_session as auth_get_session
from app.betting.router import router as betting_router
from app.models.base import Base
from app.models.betting import BetAuditLog, BetIntegrityAlert, BetTicket, BettingProfile
from app.models.calendar_engine import GlobalEvent
from app.models.competition_match import CompetitionMatch
from app.models.event_backbone import EventOutbox
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerAccount, LedgerBalanceProjection, LedgerEntry, LedgerTransaction, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService
from app.match_engine.services.match_simulation_service import MatchSimulationService
from backend.tests.match_engine.helpers import build_request


def _build_app() -> tuple[FastAPI, sessionmaker[Session], User]:
    app = FastAPI()
    app.include_router(betting_router)
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            CompetitionMatch.__table__,
            GlobalEvent.__table__,
            BettingProfile.__table__,
            BetTicket.__table__,
            BetAuditLog.__table__,
            BetIntegrityAlert.__table__,
            LedgerAccount.__table__,
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            EventOutbox.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    actor = User(
        id="user-1",
        email="bettor@example.com",
        username="bettor",
        full_name="Bet Tester",
        display_name="Bet Tester",
        password_hash="hash",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
        is_active=True,
    )
    with session_factory() as session:
        session.add(actor)
        session.commit()
        session.refresh(actor)
        _seed_main_wallet(session, actor)
        request = build_request(seed=91, match_id="bet-match")
        session.add(
            CompetitionMatch(
                id="bet-match",
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                stage="final",
                home_club_id=request.home_team.team_id,
                away_club_id=request.away_team.team_id,
                scheduled_at=datetime.now(timezone.utc),
                status="scheduled",
                metadata_json={"preview_request": request.model_dump(mode="json")},
            )
        )
        session.commit()

    def override_session():
        with session_factory() as session:
            yield session

    def override_user() -> User:
        return actor

    app.dependency_overrides[auth_get_session] = override_session
    app.dependency_overrides[get_current_wallet_user] = override_user
    return app, session_factory, actor


def _seed_main_wallet(session: Session, actor: User) -> None:
    wallet_service = WalletService()
    accounts = wallet_service.ensure_default_accounts(session, actor)
    operations = wallet_service.ensure_operations_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=accounts[LedgerUnit.CREDIT], amount=Decimal("200.0000")),
            LedgerPosting(account=operations, amount=Decimal("-200.0000")),
        ],
        reason=wallet_service.trade_settlement_reason,
        reference="seed-wallet",
        description="Seed wallet for betting tests",
        actor=actor,
    )
    session.flush()


def test_betting_router_places_and_settles_bet() -> None:
    app, session_factory, _actor = _build_app()
    replay = MatchSimulationService().build_replay_payload(build_request(seed=91, match_id="bet-match"))
    if replay.summary.home_score > replay.summary.away_score:
        winner_key = "home"
    elif replay.summary.away_score > replay.summary.home_score:
        winner_key = "away"
    else:
        winner_key = "draw"

    with TestClient(app) as client:
        preference_response = client.post(
            "/bets/preferences",
            json={"region_code": "GLOBAL", "opt_in": True, "is_enabled": True, "age_gate_confirmed": True},
        )
        assert preference_response.status_code == 200, preference_response.text

        odds_response = client.get("/bets/odds/bet-match")
        assert odds_response.status_code == 200, odds_response.text
        assert odds_response.json()["markets"]

        place_response = client.post(
            "/bets/place",
            json={
                "match_id": "bet-match",
                "bet_type": "match_winner",
                "selection_key": winner_key,
                "stake_amount": "10.0000",
                "region_code": "GLOBAL",
                "auto_fund_from_main": True,
                "opt_in_acknowledged": True,
                "age_gate_confirmed": True,
            },
        )
        assert place_response.status_code == 201, place_response.text
        assert place_response.json()["ticket"]["status"] == "placed"

    with session_factory() as session:
        match = session.get(CompetitionMatch, "bet-match")
        assert match is not None
        match.status = "completed"
        match.metadata_json = {
            **dict(match.metadata_json or {}),
            "replay_payload": replay.model_dump(mode="json"),
        }
        session.commit()

    with TestClient(app) as client:
        history_response = client.get("/bets/history")

    assert history_response.status_code == 200, history_response.text
    body = history_response.json()
    assert body["items"][0]["status"] == "won"
    assert Decimal(body["profile"]["bet_balance"]) > Decimal("0.0000")
