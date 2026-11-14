from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import (
    get_current_admin,
    get_current_social_user,
    get_optional_current_user,
    get_session,
)
from app.community_engine.social_feed_router import social_feed_router
from app.models.base import Base
from app.models.community_engine import CommunityReaction, CommunityUserBlock
from app.models.community_social import (
    CommunityBookmark,
    CommunityChannel,
    CommunityChannelMessage,
    CommunityPollVote,
    CommunityPost,
    CommunityPostComment,
    CommunityUserMute,
)
from app.models.moderation_report import ModerationReport
from app.models.user import KycStatus, User, UserRole


def _user(user_id: str, username: str, role: UserRole = UserRole.USER) -> User:
    return User(
        id=user_id,
        email=f"{username}@example.com",
        username=username,
        display_name=username.title(),
        password_hash="x",
        role=role,
        kyc_status=KycStatus.FULLY_VERIFIED,
        last_login_at=datetime.now(UTC),
    )


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
            CommunityChannel.__table__,
            CommunityChannelMessage.__table__,
            CommunityPost.__table__,
            CommunityPostComment.__table__,
            CommunityBookmark.__table__,
            CommunityPollVote.__table__,
            CommunityUserMute.__table__,
            CommunityReaction.__table__,
            CommunityUserBlock.__table__,
            ModerationReport.__table__,
        ],
    )
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with maker() as db:
        db.add_all(
            [
                _user("u-fan", "newfan"),
                _user("u-other", "otherfan"),
                _user("u-admin", "adminuser", UserRole.ADMIN),
            ]
        )
        db.commit()
        yield db
    engine.dispose()


@pytest.fixture()
def actor_state() -> dict[str, str]:
    return {"id": "u-fan"}


@pytest.fixture()
def client(session: Session, actor_state: dict[str, str]) -> TestClient:
    app = FastAPI()
    app.include_router(social_feed_router, prefix="/community")

    def override_session() -> Iterator[Session]:
        yield session

    def current() -> User:
        return session.get(User, actor_state["id"])

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_social_user] = current
    app.dependency_overrides[get_optional_current_user] = current
    app.dependency_overrides[get_current_admin] = lambda: session.get(User, "u-admin")
    return TestClient(app)


def test_clubless_new_user_can_chat_post_and_react(client: TestClient) -> None:
    channels = client.get("/community/channels").json()["channels"]
    slugs = {c["slug"] for c in channels}
    assert {"global-lounge", "football-talk", "gtex-regens", "competitions-recruitment"} <= slugs

    posted = client.post("/community/channels/global-lounge/messages", json={"body": "Hello GTEX, first day here"})
    assert posted.status_code == 201
    assert posted.json()["seq"] == 1
    assert posted.json()["sender"]["username"] == "newfan"

    post = client.post(
        "/community/posts",
        json={"post_type": "football_discussion", "title": "Best press?", "body": "Gegenpress or low block?"},
    )
    assert post.status_code == 201
    post_id = post.json()["id"]

    react = client.post(f"/community/posts/{post_id}/reactions", json={"reaction_type": "like"})
    assert react.json() == {"post_id": post_id, "reaction_type": "like", "active": True, "reaction_count": 1}
    save = client.post(f"/community/posts/{post_id}/bookmark")
    assert save.json()["bookmarked"] is True
    saved = client.get("/community/posts", params={"saved_only": True}).json()["posts"]
    assert [p["id"] for p in saved] == [post_id]


def test_channel_messages_are_sequenced_and_catch_up_without_duplicates(client: TestClient) -> None:
    for idx in range(1, 6):
        assert (
            client.post(
                "/community/channels/football-talk/messages", json={"body": f"message number {idx} here"}
            ).status_code
            == 201
        )
    page = client.get("/community/channels/football-talk/messages", params={"limit": 3}).json()
    assert [m["seq"] for m in page["messages"]] == [3, 4, 5]
    assert page["has_more"] is True and page["next_before_seq"] == 3
    older = client.get("/community/channels/football-talk/messages", params={"before_seq": 3}).json()
    assert [m["seq"] for m in older["messages"]] == [1, 2]
    catch_up = client.get("/community/channels/football-talk/messages", params={"after_seq": 4}).json()
    assert [m["seq"] for m in catch_up["messages"]] == [5]


def test_poll_requires_valid_options_and_one_vote_per_user(client: TestClient) -> None:
    bad = client.post("/community/posts", json={"post_type": "poll", "body": "Who wins?", "poll_options": ["A"]})
    assert bad.status_code == 400
    poll = client.post(
        "/community/posts",
        json={"post_type": "poll", "body": "Who wins?", "poll_options": ["Lions", "Eagles"]},
    ).json()
    option_id = poll["poll"]["options"][0]["id"]
    voted = client.post(f"/community/posts/{poll['id']}/vote", json={"option_id": option_id}).json()
    assert voted["poll"]["total_votes"] == 1
    revote = client.post(
        f"/community/posts/{poll['id']}/vote", json={"option_id": poll["poll"]["options"][1]["id"]}
    ).json()
    assert revote["poll"]["total_votes"] == 1
    assert client.post(f"/community/posts/{poll['id']}/vote", json={"option_id": "nope"}).status_code == 400


def test_muted_user_content_hidden_and_reports_deduplicated(client: TestClient, actor_state: dict[str, str]) -> None:
    actor_state["id"] = "u-other"
    client.post("/community/channels/global-lounge/messages", json={"body": "spammy chatter from other"})
    actor_state["id"] = "u-fan"
    before = client.get("/community/channels/global-lounge/messages").json()["messages"]
    assert len(before) == 1
    assert client.post("/community/users/u-other/mute", json={"muted": True}).status_code == 200
    assert client.get("/community/channels/global-lounge/messages").json()["messages"] == []

    first = client.post(
        "/community/reports",
        json={"target_type": "channel_message", "target_id": before[0]["id"], "description": "abuse"},
    )
    assert first.status_code == 201
    dup = client.post(
        "/community/reports",
        json={"target_type": "channel_message", "target_id": before[0]["id"], "description": "abuse"},
    )
    assert dup.status_code == 400


def test_only_admin_can_hide_and_non_admin_cannot_pin(client: TestClient, actor_state: dict[str, str]) -> None:
    msg = client.post("/community/channels/matchday/messages", json={"body": "what a goal that was"}).json()
    assert client.post(f"/community/channels/messages/{msg['id']}/pin").status_code == 403
    resolved = client.post(
        "/community/admin/moderation/resolve",
        json={"target_type": "channel_message", "target_id": msg["id"], "action": "hide"},
    )
    assert resolved.status_code == 200
    assert client.get("/community/channels/matchday/messages").json()["messages"] == []
