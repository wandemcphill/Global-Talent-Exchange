from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.admin_engine.service import AdminEngineService
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.hosted_competition_engine.router import admin_router as hosted_admin_router
from app.hosted_competition_engine.router import router as hosted_router
from app.hosted_competition_engine.schemas import AdminHostedCompetitionCreateRequest
from app.hosted_competition_engine.service import HostedCompetitionError, HostedCompetitionService
from app.models.base import Base
from app.models.hosted_competition import (
    CompetitionTemplate,
    HostedCompetitionStatus,
    UserHostedCompetition,
)
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService

import app.models.hosted_competition  # noqa: F401
import app.models.user  # noqa: F401
import app.models.user_wallet  # noqa: F401
import app.models.wallet  # noqa: F401


def _create_user(session, *, user_id: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="test-hash",  # pragma: allowlist secret
        role=role,
    )
    session.add(user)
    return user


def test_private_hosted_competition_requires_invite_and_accepts_invited_user() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    AdminEngineService(session).seed_defaults()
    try:
        host = _create_user(session, user_id="host-user")
        guest = _create_user(session, user_id="guest-user")
        outsider = _create_user(session, user_id="outsider-user")
        template = CompetitionTemplate(
            template_key="invite-cup",
            title="Invite Cup",
            description="Private hosted invite cup",
            competition_type="user_hosted_cup",
            team_type="club",
            age_grade="senior",
            cup_or_league="cup",
            participants=4,
            viewing_mode="broadcast",
            gift_rules={},
            seeding_method="random",
            is_user_hostable=True,
            funding_mode="fancoin_entry_pool",
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            platform_fee_bps=0,
            metadata_json={},
            active=True,
        )
        session.add(template)
        session.flush()
        competition = UserHostedCompetition(
            template_id=template.id,
            host_user_id=host.id,
            title="Private Fast Cup",
            slug="private-fast-cup",
            description="Invite-only fast cup",
            status=HostedCompetitionStatus.OPEN,
            visibility="private",
            max_participants=4,
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            platform_fee_amount=Decimal("0.0000"),
            metadata_json={},
        )
        session.add(competition)
        session.commit()

        app = FastAPI()
        app.include_router(hosted_router)
        app.state.current_user_id = outsider.id

        def override_session():
            yield session

        def override_current_user() -> User:
            user = session.get(User, app.state.current_user_id)
            assert user is not None
            return user

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_current_user] = override_current_user

        with TestClient(app) as client:
            blocked_join = client.post(f"/hosted-competitions/{competition.id}/join")
            assert blocked_join.status_code == 400, blocked_join.text
            assert "invite is required" in blocked_join.json()["detail"].lower()

            app.state.current_user_id = host.id
            invite_response = client.post(
                f"/hosted-competitions/{competition.id}/invites",
                json={
                    "recipient_user_ids": [guest.id],
                    "message": "Join the private fast cup.",
                },
            )
            assert invite_response.status_code == 200, invite_response.text
            invite_payload = invite_response.json()["invites"][0]
            assert invite_payload["recipient_user_id"] == guest.id
            assert invite_payload["status"] == "pending"

            app.state.current_user_id = guest.id
            my_invites = client.get("/hosted-competitions/mine/invites")
            assert my_invites.status_code == 200, my_invites.text
            assert [item["invite_id"] for item in my_invites.json()] == [invite_payload["invite_id"]]

            accept_response = client.post(
                f"/hosted-competitions/{competition.id}/invites/accept",
                json={"invite_id": invite_payload["invite_id"]},
            )
            assert accept_response.status_code == 200, accept_response.text
            accepted = accept_response.json()
            assert accepted["participant"]["user_id"] == guest.id
            assert accepted["invite"]["status"] == "accepted"
            assert accepted["current_participants"] == 1
    finally:
        session.close()
        engine.dispose()


def test_passcode_competition_requires_valid_passcode_to_join() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    AdminEngineService(session).seed_defaults()
    try:
        host = _create_user(session, user_id="host-passcode")
        guest = _create_user(session, user_id="guest-passcode")
        template = CompetitionTemplate(
            template_key="passcode-cup",
            title="Passcode Cup",
            description="Passcode hosted cup",
            competition_type="user_hosted_cup",
            team_type="club",
            age_grade="senior",
            cup_or_league="cup",
            participants=4,
            viewing_mode="broadcast",
            gift_rules={},
            seeding_method="random",
            is_user_hostable=True,
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            platform_fee_bps=0,
            metadata_json={},
            active=True,
        )
        session.add(template)
        session.flush()
        competition = UserHostedCompetition(
            template_id=template.id,
            host_user_id=host.id,
            title="Passcode Fast Cup",
            slug="passcode-fast-cup",
            description="Passcode fast cup",
            status=HostedCompetitionStatus.OPEN,
            visibility="passcode",
            max_participants=4,
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            platform_fee_amount=Decimal("0.0000"),
            metadata_json={"join_passcode": "CUP123", "join_passcode_required": True},
        )
        session.add(competition)
        session.commit()

        app = FastAPI()
        app.include_router(hosted_router)

        def override_session():
            yield session

        def override_current_user() -> User:
            return guest

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_current_user] = override_current_user

        with TestClient(app) as client:
            blocked_join = client.post(f"/hosted-competitions/{competition.id}/join")
            assert blocked_join.status_code == 400, blocked_join.text
            assert "passcode" in blocked_join.json()["detail"].lower()

            wrong_join = client.post(
                f"/hosted-competitions/{competition.id}/join",
                json={"passcode": "wrong"},
            )
            assert wrong_join.status_code == 400, wrong_join.text
            assert "passcode" in wrong_join.json()["detail"].lower()

            accepted_join = client.post(
                f"/hosted-competitions/{competition.id}/join",
                json={"passcode": "CUP123"},
            )
            assert accepted_join.status_code == 200, accepted_join.text
            assert accepted_join.json()["participant"]["user_id"] == guest.id
    finally:
        session.close()
        engine.dispose()


def test_admin_can_create_free_gtex_hosted_competition() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    AdminEngineService(session).seed_defaults()
    try:
        admin = _create_user(session, user_id="admin-host", role=UserRole.ADMIN)
        wallet_service = WalletService()
        admin_coin_account = wallet_service.get_user_account(session, admin, LedgerUnit.COIN)
        platform_coin_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=admin_coin_account, amount=Decimal("100.0000")),
                LedgerPosting(account=platform_coin_account, amount=Decimal("-100.0000")),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference="seed-admin-gtex-prize",
            actor=admin,
        )
        session.commit()
        template = CompetitionTemplate(
            template_key="admin-cup",
            title="Admin Cup",
            description="Official admin-hosted cup",
            competition_type="gtex_hosted_cup",
            team_type="club",
            age_grade="senior",
            cup_or_league="cup",
            participants=4,
            viewing_mode="broadcast",
            gift_rules={},
            seeding_method="random",
            is_user_hostable=True,
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            platform_fee_bps=0,
            metadata_json={},
            active=True,
        )
        session.add(template)
        session.commit()

        app = FastAPI()
        app.include_router(hosted_admin_router)

        def override_session():
            yield session

        def override_admin() -> User:
            return admin

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_current_admin] = override_admin

        with TestClient(app) as client:
            response = client.post(
                "/admin/hosted-competitions",
                json={
                    "template_key": "admin-cup",
                    "title": "Official GTEX Cup",
                    "gtex_hosted": True,
                    "funding_mode": "host_funded_gtex_coin_prize",
                    "reward_pool_coin": "100.0000",
                    "join_passcode": "VIP",
                },
            )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["host_participation_created"] is True
        assert payload["competition"]["entry_fee_fancoin"] == "0.0000"
        assert payload["competition"]["reward_pool_coin"] == "100.0000"
        assert payload["competition"]["visibility"] == "passcode"
        assert payload["competition"]["metadata_json"]["gtex_hosted"] is True
        assert payload["competition"]["metadata_json"]["join_passcode_required"] is True
    finally:
        session.close()
        engine.dispose()


def test_hosted_competition_finance_requires_host_or_admin() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        host = _create_user(session, user_id="finance-host")
        outsider = _create_user(session, user_id="finance-outsider")
        admin = _create_user(session, user_id="finance-admin", role=UserRole.ADMIN)
        template = CompetitionTemplate(
            template_key="finance-cup",
            title="Finance Cup",
            description="Hosted finance cup",
            competition_type="user_hosted_cup",
            team_type="club",
            age_grade="senior",
            cup_or_league="cup",
            participants=4,
            viewing_mode="broadcast",
            gift_rules={},
            seeding_method="random",
            is_user_hostable=True,
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            platform_fee_bps=0,
            metadata_json={},
            active=True,
        )
        session.add(template)
        session.flush()
        competition = UserHostedCompetition(
            template_id=template.id,
            host_user_id=host.id,
            title="Finance Fast Cup",
            slug="finance-fast-cup",
            description="Finance-only cup",
            status=HostedCompetitionStatus.OPEN,
            visibility="public",
            max_participants=4,
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            platform_fee_amount=Decimal("0.0000"),
            metadata_json={},
        )
        session.add(competition)
        session.commit()

        app = FastAPI()
        app.include_router(hosted_router)
        app.state.current_user_id = host.id

        def override_session():
            yield session

        app.dependency_overrides[get_session] = override_session

        with TestClient(app) as client:
            unauthenticated = client.get(f"/hosted-competitions/{competition.id}/finance")
            assert unauthenticated.status_code == 401

            def override_current_user() -> User:
                user = session.get(User, app.state.current_user_id)
                assert user is not None
                return user

            app.dependency_overrides[get_current_user] = override_current_user

            host_response = client.get(f"/hosted-competitions/{competition.id}/finance")
            assert host_response.status_code == 200, host_response.text

            app.state.current_user_id = outsider.id
            outsider_response = client.get(f"/hosted-competitions/{competition.id}/finance")
            assert outsider_response.status_code == 403

            app.state.current_user_id = admin.id
            admin_response = client.get(f"/hosted-competitions/{competition.id}/finance")
            assert admin_response.status_code == 200, admin_response.text
    finally:
        session.close()
        engine.dispose()


def test_gtex_hosted_reward_pool_is_funded_and_finalize_requires_exact_unique_placements() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        admin = _create_user(session, user_id="gtex-reward-admin", role=UserRole.ADMIN)
        winner = _create_user(session, user_id="gtex-reward-winner")
        runner_up = _create_user(session, user_id="gtex-reward-runner")
        template = CompetitionTemplate(
            template_key="gtex-reward-cup",
            title="GTEX Reward Cup",
            description="Official reward cup",
            competition_type="gtex_hosted_cup",
            team_type="club",
            age_grade="senior",
            cup_or_league="cup",
            participants=2,
            viewing_mode="broadcast",
            gift_rules={},
            seeding_method="random",
            is_user_hostable=True,
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            platform_fee_bps=0,
            metadata_json={},
            active=True,
        )
        session.add(template)
        session.commit()

        service = HostedCompetitionService(session)
        competition, _template, _host_created = service.create_admin_competition(
            admin=admin,
            payload=AdminHostedCompetitionCreateRequest(
                template_key="gtex-reward-cup",
                title="Official Reward Cup",
                gtex_hosted=True,
                reward_pool_fancoin=Decimal("100.0000"),
                max_participants=2,
            ),
        )
        service.join_competition(user=winner, competition_id=competition.id)
        service.join_competition(user=runner_up, competition_id=competition.id)
        session.commit()

        finance = service.finance_snapshot(competition.id)
        assert finance["escrow_balance"] == Decimal("100.0000")

        with pytest.raises(HostedCompetitionError, match="must equal 100"):
            service.finalize_competition(
                actor=admin,
                competition_id=competition.id,
                placements=[
                    {"user_id": winner.id, "rank": 1, "payout_percent": Decimal("90.0000")},
                ],
            )

        with pytest.raises(HostedCompetitionError, match="distinct participant"):
            service.finalize_competition(
                actor=admin,
                competition_id=competition.id,
                placements=[
                    {"user_id": winner.id, "rank": 1, "payout_percent": Decimal("50.0000")},
                    {"user_id": winner.id, "rank": 2, "payout_percent": Decimal("50.0000")},
                ],
            )

        with pytest.raises(HostedCompetitionError, match="rank must be unique"):
            service.finalize_competition(
                actor=admin,
                competition_id=competition.id,
                placements=[
                    {"user_id": winner.id, "rank": 1, "payout_percent": Decimal("50.0000")},
                    {"user_id": runner_up.id, "rank": 1, "payout_percent": Decimal("50.0000")},
                ],
            )
    finally:
        session.close()
        engine.dispose()
