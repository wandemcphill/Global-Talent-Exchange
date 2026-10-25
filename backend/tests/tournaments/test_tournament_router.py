from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_user
from app.db import get_session
from app.models import Base
from app.models.event_backbone import EventOutbox
from app.models.risk_ops import AuditLog
from app.models.tournament import Tournament, TournamentPlayer
from app.models.user import User, UserRole
from app.modules import DOMAIN_MODULES
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransaction,
    LedgerTransactionStatus,
    LedgerTransactionType,
    LedgerUnit,
)
from app.tournaments.router import router
from app.wallets.service import LedgerPosting, WalletService

REFUND_CONFIRMATION = "REFUND_LEGACY_TOURNAMENT_FEES"
REFUND_REASON = "Audited retirement refund for verified historic tournament entry"


class _StubActor:
    """Test-only actor resolved from headers; role checks remain inside the actual handlers."""

    def __init__(self, user_id: str, role: str) -> None:
        self.id = user_id
        try:
            self.role = UserRole(role)
        except ValueError:
            self.role = UserRole.USER


def _override_get_current_user(request: Request) -> _StubActor:
    return _StubActor(
        request.headers.get("X-Test-Actor-Id", ""),
        request.headers.get("X-Test-Actor-Role", UserRole.SUPER_ADMIN.value),
    )


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
            AuditLog.__table__,
            Tournament.__table__,
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
    app.dependency_overrides[get_current_user] = _override_get_current_user
    return TestClient(app), SessionLocal


@pytest.fixture()
def tournament_client(tmp_path: Path):
    client, session_factory = _build_app(f"sqlite:///{tmp_path / 'tournament-retirement.db'}")
    try:
        yield client, session_factory
    finally:
        client.close()


def _create_user(session, *, suffix: int, role: UserRole = UserRole.USER) -> User:
    user = User(
        email=f"retirement{suffix}@example.com",
        username=f"retirement_{suffix}",
        display_name=f"Retirement User {suffix}",
        # This value is a synthetic database fixture, not a real credential.
        # Keep the pre-existing detector sentinel stable for the secret scan baseline.
        password_hash="not-used",
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def _fund_user(session, *, user: User, amount: int = 1_000) -> None:
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
        reference=f"seed-retirement-balance:{user.id}:{amount}",
        description="Seed a test-only wallet balance",
        idempotency_key=f"seed-retirement-balance:{user.id}:{amount}",
    )


def _seed_entry(
    session_factory: sessionmaker,
    *,
    suffix: int = 1,
    fee: int = 250,
    verified_payment: bool = True,
) -> dict[str, str]:
    with session_factory() as session:
        admin = _create_user(session, suffix=suffix * 10 + 1, role=UserRole.SUPER_ADMIN)
        user = _create_user(session, suffix=suffix * 10 + 2)
        _fund_user(session, user=user)

        tournament = Tournament(
            name=f"Retired Cup {suffix}",
            game_type="prediction",
            entry_fee=fee,
            max_players=4,
            status="registration",
            rounds=2,
            current_round=1,
            prize_pool=fee,
            round_timeout_minutes=60,
        )
        session.add(tournament)
        session.flush()

        pool_account = LedgerAccount(
            owner_user_id=None,
            code=f"tournament:{tournament.id}:pool:credit",
            label=f"{tournament.name} Prize Pool",
            unit=LedgerUnit.CREDIT,
            kind=LedgerAccountKind.SYSTEM,
            allow_negative=False,
        )
        session.add(pool_account)
        session.flush()

        transaction_id = None
        if verified_payment:
            wallet_service = WalletService()
            user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
            key = f"tournament:{tournament.id}:entry:{user.id}"
            entries = wallet_service.append_transaction(
                session,
                postings=[
                    LedgerPosting(
                        account=user_account,
                        amount=Decimal(str(-fee)),
                        source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                        transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                    ),
                    LedgerPosting(
                        account=pool_account,
                        amount=Decimal(str(fee)),
                        source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                        transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                    ),
                ],
                reason=LedgerEntryReason.COMPETITION_ENTRY,
                source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                reference=key,
                description="Test-only original legacy tournament entry fee",
                idempotency_key=key,
                metadata={"tournament_id": tournament.id, "user_id": user.id},
            )
            transaction_id = entries[0].transaction_id

        player = TournamentPlayer(
            tournament_id=tournament.id,
            user_id=user.id,
            bracket_slot=1,
            status="registered",
            entry_transaction_id=transaction_id,
        )
        session.add(player)
        session.commit()
        return {
            "admin_id": admin.id,
            "user_id": user.id,
            "tournament_id": tournament.id,
            "entry_id": player.id,
            "original_transaction_id": transaction_id or "",
        }


def _headers(user_id: str, role: str = "super_admin") -> dict[str, str]:
    return {"X-Test-Actor-Id": user_id, "X-Test-Actor-Role": role}


def _credit_balance(session, user_id: str) -> Decimal:
    account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == f"user:{user_id}:credit"))
    if account is None:
        return Decimal("0.0000")
    balance = session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.account_id == account.id,
            LedgerEntry.unit == LedgerUnit.CREDIT,
        )
    )
    return Decimal(str(balance or 0)).quantize(Decimal("0.0001"))


def _execute_refunds(client: TestClient, *, ids: dict[str, str], role: str = "super_admin"):
    return client.post(
        "/api/tournaments/admin/retirement/refunds/execute",
        json={
            "tournament_id": ids["tournament_id"],
            "reason": REFUND_REASON,
            "confirmation": REFUND_CONFIRMATION,
        },
        headers=_headers(ids["admin_id"], role),
    )


def test_legacy_tournament_mutations_return_gone_and_do_not_create_or_charge(tournament_client) -> None:
    client, session_factory = tournament_client
    ids = _seed_entry(session_factory)
    before = None
    with session_factory() as session:
        before = _credit_balance(session, ids["user_id"])

    create = client.post(
        "/api/tournaments",
        json={
            "name": "Another Retired Cup",
            "game_type": "prediction",
            "entry_fee": 999,
            "max_players": 4,
            "round_timeout_minutes": 60,
        },
        headers=_headers(ids["admin_id"]),
    )
    assert create.status_code == 410
    assert create.headers.get("Deprecation") == "true"

    join = client.post(
        f"/api/tournaments/{ids['tournament_id']}/join",
        json={"user_id": ids["user_id"]},
        headers=_headers(ids["user_id"], "user"),
    )
    assert join.status_code == 410

    cancel = client.post(
        f"/api/tournaments/{ids['tournament_id']}/cancel",
        headers=_headers(ids["admin_id"]),
    )
    assert cancel.status_code == 410

    result = client.post(
        f"/api/tournaments/{ids['tournament_id']}/matches/nonexistent/result",
        json={"winner_user_id": ids["user_id"]},
        headers=_headers(ids["user_id"], "user"),
    )
    assert result.status_code == 410

    advance = client.post(
        f"/api/tournaments/{ids['tournament_id']}/advance",
        headers=_headers(ids["user_id"], "user"),
    )
    assert advance.status_code == 410

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Tournament)) == 1
        assert _credit_balance(session, ids["user_id"]) == before


def test_join_as_another_user_still_fails_before_retirement_response(tournament_client) -> None:
    client, session_factory = tournament_client
    ids = _seed_entry(session_factory)
    response = client.post(
        f"/api/tournaments/{ids['tournament_id']}/join",
        json={"user_id": ids["user_id"]},
        headers=_headers(ids["admin_id"], "user"),
    )
    assert response.status_code == 403


def test_refund_dry_run_is_read_only_and_reports_verified_source(tournament_client) -> None:
    client, session_factory = tournament_client
    ids = _seed_entry(session_factory)

    with session_factory() as session:
        entries_before = session.scalar(select(func.count()).select_from(LedgerEntry))
        transactions_before = session.scalar(select(func.count()).select_from(LedgerTransaction))

    response = client.get(
        "/api/tournaments/admin/retirement/refunds/dry-run",
        params={"tournament_id": ids["tournament_id"]},
        headers=_headers(ids["admin_id"]),
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["status"] == "ready"
    assert report["mutation_performed"] is False
    assert report["execution_allowed"] is True
    assert report["summary"]["entry_count"] == 1
    assert report["summary"]["eligible"] == 1
    assert report["summary"]["eligible_refund_amount"] == "250.0000"
    assert report["items"][0]["entry_id"] == ids["entry_id"]
    assert report["items"][0]["status"] == "eligible"
    assert report["items"][0]["entry_transaction_id"] == ids["original_transaction_id"]

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(LedgerEntry)) == entries_before
        assert session.scalar(select(func.count()).select_from(LedgerTransaction)) == transactions_before


def test_refund_dry_run_and_execute_are_admin_only(tournament_client) -> None:
    client, _session_factory = tournament_client
    ids = _seed_entry(_session_factory)

    dry_run = client.get(
        "/api/tournaments/admin/retirement/refunds/dry-run",
        headers=_headers(ids["user_id"], "user"),
    )
    assert dry_run.status_code == 403

    execute = _execute_refunds(client, ids=ids, role="user")
    assert execute.status_code == 403


def test_refund_execution_is_audited_and_retries_do_not_double_refund(tournament_client) -> None:
    client, session_factory = tournament_client
    ids = _seed_entry(session_factory)

    first = _execute_refunds(client, ids=ids)
    assert first.status_code == 200, first.text
    payload = first.json()
    assert payload["status"] == "refunded"
    assert payload["mutation_performed"] is True
    assert payload["refunded_count"] == 1
    assert payload["refunded_amount"] == "250.0000"

    with session_factory() as session:
        assert _credit_balance(session, ids["user_id"]) == Decimal("1000.0000")
        refund_logs = session.scalars(
            select(AuditLog).where(AuditLog.action_key == "legacy_tournament.entry_fee_refund")
        ).all()
        assert len(refund_logs) == 1
        assert refund_logs[0].actor_user_id == ids["admin_id"]
        assert refund_logs[0].resource_id == ids["entry_id"]
        assert refund_logs[0].metadata_json["original_entry_transaction_id"] == ids["original_transaction_id"]

    second = _execute_refunds(client, ids=ids)
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "already_refunded"
    assert second.json()["refunded_count"] == 0

    with session_factory() as session:
        assert _credit_balance(session, ids["user_id"]) == Decimal("1000.0000")
        refund_transactions = session.scalars(
            select(LedgerTransaction).where(
                LedgerTransaction.idempotency_key == f"tournament:{ids['tournament_id']}:refund:{ids['user_id']}"
            )
        ).all()
        assert len(refund_transactions) == 1


def test_unverified_entry_is_reported_and_never_refunded(tournament_client) -> None:
    client, session_factory = tournament_client
    ids = _seed_entry(session_factory, suffix=2, verified_payment=False)

    dry_run = client.get(
        "/api/tournaments/admin/retirement/refunds/dry-run",
        params={"tournament_id": ids["tournament_id"]},
        headers=_headers(ids["admin_id"]),
    )
    assert dry_run.status_code == 200
    report = dry_run.json()
    assert report["status"] == "blocked"
    assert report["summary"]["unverified"] == 1
    assert report["items"][0]["reason"] == "entry_transaction_reference_missing"

    execute = _execute_refunds(client, ids=ids)
    assert execute.status_code == 409
    assert execute.json()["detail"]["status"] == "blocked"

    with session_factory() as session:
        assert _credit_balance(session, ids["user_id"]) == Decimal("1000.0000")
        assert (
            session.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(
                    LedgerTransaction.idempotency_key == f"tournament:{ids['tournament_id']}:refund:{ids['user_id']}"
                )
            )
            == 0
        )


def test_pool_shortfall_blocks_entire_refund_batch(tournament_client) -> None:
    client, session_factory = tournament_client
    ids = _seed_entry(session_factory, suffix=3)

    with session_factory() as session:
        pool = session.scalar(
            select(LedgerAccount).where(LedgerAccount.code == f"tournament:{ids['tournament_id']}:pool:credit")
        )
        platform = WalletService().ensure_platform_account(session, LedgerUnit.CREDIT)
        assert pool is not None
        WalletService().append_transaction(
            session,
            postings=[
                LedgerPosting(
                    account=pool,
                    amount=Decimal("-250"),
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    transaction_type=LedgerTransactionType.ADJUSTMENT,
                ),
                LedgerPosting(
                    account=platform,
                    amount=Decimal("250"),
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    transaction_type=LedgerTransactionType.ADJUSTMENT,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            transaction_type=LedgerTransactionType.ADJUSTMENT,
            reference=f"test-drain:{ids['tournament_id']}",
            description="Test-only drain to simulate insufficient refund pool",
            idempotency_key=f"test-drain:{ids['tournament_id']}",
        )
        session.commit()

    dry_run = client.get(
        "/api/tournaments/admin/retirement/refunds/dry-run",
        params={"tournament_id": ids["tournament_id"]},
        headers=_headers(ids["admin_id"]),
    )
    assert dry_run.status_code == 200
    report = dry_run.json()
    assert report["status"] == "blocked"
    assert report["items"][0]["status"] == "blocked"
    assert report["items"][0]["reason"] == "insufficient_pool_balance_for_refund_batch"
    assert report["tournaments"][0]["pool_shortfall"] == "250.0000"

    execute = _execute_refunds(client, ids=ids)
    assert execute.status_code == 409
    with session_factory() as session:
        assert _credit_balance(session, ids["user_id"]) == Decimal("750.0000")
        assert (
            session.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(
                    LedgerTransaction.idempotency_key == f"tournament:{ids['tournament_id']}:refund:{ids['user_id']}"
                )
            )
            == 0
        )


def test_unknown_tournament_refund_target_returns_404(tournament_client) -> None:
    client, session_factory = tournament_client
    with session_factory() as session:
        admin = _create_user(session, suffix=991, role=UserRole.SUPER_ADMIN)
        session.commit()
        admin_id = admin.id

    response = client.post(
        "/api/tournaments/admin/retirement/refunds/execute",
        json={
            "tournament_id": "not-a-real-tournament",
            "reason": REFUND_REASON,
            "confirmation": REFUND_CONFIRMATION,
        },
        headers=_headers(admin_id),
    )
    assert response.status_code == 404


def test_concurrent_refund_requests_never_double_credit(tournament_client) -> None:
    client, session_factory = tournament_client
    ids = _seed_entry(session_factory, suffix=4)
    barrier = Barrier(2)

    def execute() -> object:
        barrier.wait(timeout=5)
        return _execute_refunds(client, ids=ids)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _index: execute(), range(2)))

    assert all(response.status_code in {200, 409} for response in responses)

    with session_factory() as session:
        assert _credit_balance(session, ids["user_id"]) == Decimal("1000.0000")
        refund_transactions = session.scalars(
            select(LedgerTransaction).where(
                LedgerTransaction.idempotency_key == f"tournament:{ids['tournament_id']}:refund:{ids['user_id']}"
            )
        ).all()
        assert len(refund_transactions) == 1
        assert refund_transactions[0].status == LedgerTransactionStatus.COMMITTED


def test_retired_tournament_router_precedes_api_v1_aliases() -> None:
    # Both modules historically registered /api/tournaments/{id} and /join.
    # The database-backed retirement router must win before the demo alias.
    names = [module.name for module in DOMAIN_MODULES]
    assert names.index("tournaments") < names.index("api_v1")
