from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.competitive_integrity.schemas import (
    CompetitiveMatchExecutionView,
    CompetitiveMatchView,
    ControllerSummaryView,
    FastGamePlayRequest,
    FastGameRunStartRequest,
    MatchControlLogView,
    NotificationEventRequest,
)
from app.competitive_integrity.service import (
    CompetitiveIntegrityService,
    ManagerLockedError,
    MatchSideResolution,
    applyManagerInstructions,
    resolveController,
)
from app.match_engine.schemas import MatchFinalSummaryView, MatchReplayPayloadView
from app.models import Base
from app.models.competitive_integrity import CompetitiveNotificationStatus, FastGameRun, Manager, ManagerType, MatchControllerType
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService
from backend.tests.match_engine.helpers import build_team


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _create_user(session, email: str, username: str) -> User:
    service = AuthService()
    user = service.register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
        display_name=username,
    )
    session.flush()
    return user


def _fund_user(session, user: User, amount: Decimal) -> None:
    wallet = WalletService()
    user_account = wallet.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=f"seed:{user.id}",
        external_reference=f"seed:{user.id}",
        description="Seed wallet balance",
        actor=user,
    )
    session.flush()


def _coin_balance(session, user: User) -> Decimal:
    wallet = WalletService()
    summary = wallet.get_wallet_summary(session, user, currency=LedgerUnit.COIN)
    return Decimal(summary.available_balance)


def _stub_execution(match_id: str, winner_team_id: str) -> CompetitiveMatchExecutionView:
    summary = MatchFinalSummaryView.model_construct(
        winner_team_id=winner_team_id,
        upset=False,
        home_score=3,
        away_score=1,
    )
    replay = MatchReplayPayloadView.model_construct(summary=summary)
    return CompetitiveMatchExecutionView.model_construct(
        match=CompetitiveMatchView.model_construct(id=match_id),
        controllers=ControllerSummaryView.model_construct(
            home=MatchControllerType.USER,
            away=MatchControllerType.USER,
        ),
        control_logs=[
            MatchControlLogView.model_construct(
                side="home",
                controller_type=MatchControllerType.USER,
                timestamp=datetime.now(timezone.utc),
            )
        ],
        replay=replay,
    )


def test_resolve_controller_and_manager_instruction_dsl() -> None:
    assert resolveController(MatchSideResolution(is_user_online=True, manager=None)) is MatchControllerType.USER
    assert resolveController(MatchSideResolution(is_user_online=False, manager=None)) is MatchControllerType.FROZEN
    manager = Manager(user_id="owner-1", type=ManagerType.REAL_MANAGER, appointed_user_id="coach-1")
    assert resolveController(MatchSideResolution(is_user_online=False, manager=manager)) is MatchControllerType.MANAGER

    instructions = {
        "formation": "4-3-3",
        "rules": [
            {"minute": 60, "condition": "losing", "action": "add_striker"},
            {"minute": 75, "condition": "winning", "action": "protect_lead"},
        ],
    }
    applied = applyManagerInstructions(
        {"minute": 61, "score_for": 0, "score_against": 1, "formation": "4-3-3"},
        instructions,
    )
    assert applied[0]["formation"] == "4-2-4"


def test_fast_game_run_locks_manager_and_pays_reward(session, monkeypatch) -> None:
    actor = _create_user(session, "owner@example.com", "owner")
    opponent = _create_user(session, "opponent@example.com", "opponent")
    _fund_user(session, actor, Decimal("100.0000"))
    manager = Manager(user_id=actor.id, type=ManagerType.USER, instructions={}, tactical_profile={})
    session.add(manager)
    session.flush()

    service = CompetitiveIntegrityService(session=session)
    run = service.start_run(
        actor=actor,
        payload=FastGameRunStartRequest(
            manager_id=manager.id,
            entry_fee_amount=Decimal("10.0000"),
            base_reward_amount=Decimal("20.0000"),
            base_rating=1200,
            scaling_factor=25,
        ),
    )
    assert run.manager_locked_id == manager.id
    assert _coin_balance(session, actor) == Decimal("90.0000")
    stored_run = session.get(FastGameRun, run.id)
    assert stored_run is not None
    stored_run.wins = 9
    session.flush()

    execution_stub = _stub_execution("match-123", "home-fast")
    monkeypatch.setattr(
        CompetitiveIntegrityService,
        "execute_match",
        lambda self, actor, match_id, payload: execution_stub,
    )

    result = service.play_fast_game(
        actor=actor,
        run_id=run.id,
        payload=FastGamePlayRequest(
            home_manager_id=manager.id,
            away_user_id=opponent.id,
            locked_lineup_home=build_team("home-fast", "Home Fast", 88),
            locked_lineup_away=build_team("away-fast", "Away Fast", 62),
        ),
    )

    assert result.result == "win"
    assert result.max_reward_triggered is True
    assert result.run.is_active is False
    assert result.reward_amount > Decimal("0.0000")
    assert _coin_balance(session, actor) > Decimal("90.0000")


def test_fast_game_rejects_manager_switch(session) -> None:
    actor = _create_user(session, "owner2@example.com", "owner2")
    opponent = _create_user(session, "opponent2@example.com", "opponent2")
    _fund_user(session, actor, Decimal("40.0000"))
    manager_a = Manager(user_id=actor.id, type=ManagerType.USER, instructions={}, tactical_profile={})
    manager_b = Manager(user_id=actor.id, type=ManagerType.USER, instructions={}, tactical_profile={})
    session.add_all([manager_a, manager_b])
    session.flush()

    service = CompetitiveIntegrityService(session=session)
    run = service.start_run(
        actor=actor,
        payload=FastGameRunStartRequest(manager_id=manager_a.id, entry_fee_amount=Decimal("5.0000")),
    )

    with pytest.raises(ManagerLockedError):
        service.play_fast_game(
            actor=actor,
            run_id=run.id,
            payload=FastGamePlayRequest(
                home_manager_id=manager_b.id,
                away_user_id=opponent.id,
                locked_lineup_home=build_team("home-lock", "Home Lock", 80),
                locked_lineup_away=build_team("away-lock", "Away Lock", 79),
            ),
        )


def test_notification_delivery_falls_back_to_sms(session) -> None:
    actor = _create_user(session, "notify@example.com", "notify")
    actor.phone_number = "+2340000000000"
    session.flush()
    service = CompetitiveIntegrityService(session=session)

    queued = service.create_notification_event(
        actor=actor,
        payload=NotificationEventRequest(
            user_id=actor.id,
            type="CHALLENGE_RECEIVED",
            payload={"challenge_id": "challenge-1"},
        ),
    )
    assert queued.status is CompetitiveNotificationStatus.PENDING

    first_pass = service.deliver_due_notifications()
    second_pass = service.deliver_due_notifications()
    rows = service.list_notifications(actor=actor)

    assert first_pass == 0
    assert second_pass == 1
    assert rows[0].channel.value == "sms"
    assert rows[0].status is CompetitiveNotificationStatus.SENT
