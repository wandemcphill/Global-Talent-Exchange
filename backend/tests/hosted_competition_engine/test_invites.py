from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.hosted_competition_engine.router import admin_router as hosted_admin_router
from app.hosted_competition_engine.router import router as hosted_router
from app.models.base import Base
from app.models.hosted_competition import (
    CompetitionTemplate,
    HostedCompetitionStatus,
    UserHostedCompetition,
)
from app.models.user import User, UserRole

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
    try:
        admin = _create_user(session, user_id="admin-host", role=UserRole.ADMIN)
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
            entry_fee_fancoin=Decimal("200.0000"),
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
                    "join_passcode": "VIP",
                },
            )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["host_participation_created"] is False
        assert payload["competition"]["entry_fee_fancoin"] == "0.0000"
        assert payload["competition"]["visibility"] == "passcode"
        assert payload["competition"]["metadata_json"]["gtex_hosted"] is True
        assert payload["competition"]["metadata_json"]["join_passcode_required"] is True
    finally:
        session.close()
        engine.dispose()
