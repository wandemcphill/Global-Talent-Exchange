from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_current_social_user, get_session
from app.community_engine.social_router import router as social_router
from app.models.base import Base
from app.models.community_engine import (
    CommunityReaction,
    CommunityUserBlock,
    LiveThread,
    LiveThreadMessage,
    PrivateMessage,
    PrivateMessageParticipant,
    PrivateMessageThread,
)
from app.models.moderation_report import ModerationReport
from app.models.user import KycStatus, User, UserRole


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            LiveThread.__table__,
            LiveThreadMessage.__table__,
            PrivateMessageThread.__table__,
            PrivateMessageParticipant.__table__,
            PrivateMessage.__table__,
            CommunityUserBlock.__table__,
            CommunityReaction.__table__,
            ModerationReport.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        db_session.add_all(
            [
                User(
                    id="user-ayo",
                    email="ayo@example.com",
                    username="ayo",
                    display_name="Ayo",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                    last_login_at=datetime.now(UTC),
                ),
                User(
                    id="user-tunde",
                    email="tunde@example.com",
                    username="tunde",
                    display_name="Tunde",
                    password_hash="x",
                    role=UserRole.USER,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                    last_login_at=datetime.now(UTC),
                ),
                User(
                    id="admin-user",
                    email="admin@example.com",
                    username="admin",
                    display_name="Admin",
                    password_hash="x",
                    role=UserRole.ADMIN,
                    kyc_status=KycStatus.FULLY_VERIFIED,
                    last_login_at=datetime.now(UTC),
                ),
            ]
        )
        db_session.commit()
        yield db_session
    engine.dispose()


@pytest.fixture()
def user_state(session: Session) -> dict[str, User]:
    return {"user": session.get(User, "user-ayo")}


@pytest.fixture()
def app(session: Session, user_state: dict[str, User]) -> FastAPI:
    application = FastAPI()
    application.include_router(social_router)

    def override_session() -> Iterator[Session]:
        yield session

    def override_user() -> User:
        return user_state["user"]

    def override_admin() -> User:
        user = user_state["user"]
        if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise AssertionError("test requested admin route with non-admin user")
        return user

    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_current_social_user] = override_user
    application.dependency_overrides[get_current_admin] = override_admin
    return application


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_dm_persists_read_mute_report_hide_and_block(
    client: TestClient,
    session: Session,
    user_state: dict[str, User],
) -> None:
    create_response = client.post(
        "/chats/threads",
        json={
            "participant_user_ids": ["user-tunde"],
            "subject": "Transfer talk",
            "initial_message": "Can we discuss the friendly cup?",
        },
    )
    assert create_response.status_code == 201, create_response.text
    thread_payload = create_response.json()
    thread_id = thread_payload["id"]
    assert {item["user_id"] for item in thread_payload["participants"]} == {"user-ayo", "user-tunde"}

    message_response = client.post(
        f"/chats/threads/{thread_id}/messages",
        json={"body": "Kickoff after the derby."},
    )
    assert message_response.status_code == 201, message_response.text
    message_id = message_response.json()["id"]

    user_state["user"] = session.get(User, "user-tunde")
    list_response = client.get(f"/chats/threads/{thread_id}/messages")
    assert list_response.status_code == 200, list_response.text
    assert [item["body"] for item in list_response.json()] == [
        "Can we discuss the friendly cup?",
        "Kickoff after the derby.",
    ]

    read_response = client.post(f"/chats/threads/{thread_id}/read")
    assert read_response.status_code == 200, read_response.text
    mute_response = client.post(f"/chats/threads/{thread_id}/mute", json={"muted": True})
    assert mute_response.status_code == 200, mute_response.text
    assert mute_response.json()["is_muted"] is True

    report_response = client.post(
        f"/chats/messages/{message_id}/report",
        json={"reason_code": "abuse", "description": "Needs moderation review."},
    )
    assert report_response.status_code == 201, report_response.text
    assert report_response.json()["target_type"] == "chat_message"

    user_state["user"] = session.get(User, "admin-user")
    reports_response = client.get("/admin/chat/reports")
    assert reports_response.status_code == 200, reports_response.text
    assert len(reports_response.json()) == 1

    hide_response = client.post(f"/admin/chat/messages/{message_id}/hide")
    assert hide_response.status_code == 200, hide_response.text
    assert hide_response.json()["visibility"] in {"hidden", "HIDDEN"}

    user_state["user"] = session.get(User, "user-tunde")
    visible_messages = client.get(f"/chats/threads/{thread_id}/messages").json()
    assert all(item["id"] != message_id for item in visible_messages)

    block_response = client.post("/chats/users/user-ayo/block", json={"reason": "spam"})
    assert block_response.status_code == 201, block_response.text
    blocked_post_response = client.post(
        f"/chats/threads/{thread_id}/messages",
        json={"body": "This should not send."},
    )
    assert blocked_post_response.status_code == 403


def test_discussion_threads_replies_reactions_and_admin_lock(
    client: TestClient,
    session: Session,
    user_state: dict[str, User],
) -> None:
    categories_response = client.get("/discussions/categories")
    assert categories_response.status_code == 200, categories_response.text
    assert any(item["code"] == "tactics_room" for item in categories_response.json())

    create_response = client.post(
        "/discussions/threads",
        json={
            "category": "tactics_room",
            "title": "How do you break a low block?",
            "body": "Share football tactics only, no copied articles.",
        },
    )
    assert create_response.status_code == 201, create_response.text
    thread_id = create_response.json()["id"]
    assert create_response.json()["thread_type"] == "discussion"

    user_state["user"] = session.get(User, "user-tunde")
    reply_response = client.post(
        f"/discussions/threads/{thread_id}/replies",
        json={"body": "Overload the half-space and pull the fullback narrow."},
    )
    assert reply_response.status_code == 201, reply_response.text
    reply_id = reply_response.json()["id"]

    react_response = client.post(f"/discussions/replies/{reply_id}/react", json={"reaction_type": "agree"})
    assert react_response.status_code == 201, react_response.text
    assert react_response.json()["reaction_type"] == "agree"

    report_response = client.post(
        f"/discussions/replies/{reply_id}/report",
        json={"reason_code": "off_topic", "description": "Moderator should inspect this reply."},
    )
    assert report_response.status_code == 201, report_response.text
    assert report_response.json()["target_type"] == "discussion_reply"

    listed = client.get("/discussions/threads", params={"category": "tactics_room"})
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["id"] == thread_id

    user_state["user"] = session.get(User, "admin-user")
    admin_reports = client.get("/admin/discussions/reports")
    assert admin_reports.status_code == 200, admin_reports.text
    assert len(admin_reports.json()) == 1

    lock_response = client.post(f"/admin/discussions/threads/{thread_id}/lock")
    assert lock_response.status_code == 200, lock_response.text
    assert lock_response.json()["status"] in {"locked", "LOCKED"}

    user_state["user"] = session.get(User, "user-ayo")
    locked_reply = client.post(
        f"/discussions/threads/{thread_id}/replies",
        json={"body": "Trying to post after lock."},
    )
    assert locked_reply.status_code == 403

    reactions = session.scalars(select(CommunityReaction)).all()
    assert len(reactions) == 1
