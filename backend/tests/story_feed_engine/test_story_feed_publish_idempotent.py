from __future__ import annotations

import app.models  # noqa: F401
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.story_feed import StoryFeedItem
from app.story_feed_engine.bridges import (
    publish_app_update_story,
    publish_exit_petition_story,
    publish_news_engine_payload,
)
from app.story_feed_engine.service import StoryFeedService


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


def test_publish_idempotent_returns_same_row(session) -> None:
    service = StoryFeedService(session)
    first, created_first = service.publish_idempotent(
        idempotency_key="gtex_news_engine:news_abc",
        source="gtex_news_engine",
        story_type="transfer_leak",
        title="Here we go",
        body="A club is circling.",
        subject_type="gtex_news_engine",
        subject_id="news_abc",
    )
    second, created_second = service.publish_idempotent(
        idempotency_key="gtex_news_engine:news_abc",
        source="gtex_news_engine",
        story_type="transfer_leak",
        title="Here we go again",
        body="Should not create a second row.",
        subject_type="gtex_news_engine",
        subject_id="news_abc",
    )
    session.commit()
    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    count = len(session.scalars(select(StoryFeedItem)).all())
    assert count == 1


def test_news_engine_bridge_is_idempotent(session) -> None:
    payload = {
        "breaking": [
            {
                "id": "news_bridge_1",
                "headline": "World-record buy lands",
                "body": "A platform-record acquisition just cleared escrow.",
                "type": "transfer",
                "priority": 9,
                "player_id": "player-1",
                "journalist": "GTEX Wire",
            }
        ],
        "top_stories": [],
        "rumors": [],
    }
    first = publish_news_engine_payload(session, payload)
    second = publish_news_engine_payload(session, payload)
    session.commit()
    assert first["created"] == 1
    assert second["created"] == 0
    assert second["skipped"] == 1
    items = session.scalars(select(StoryFeedItem)).all()
    assert len(items) == 1
    assert items[0].featured is True
    assert items[0].subject_type == "player"
    assert items[0].metadata_json["idempotency_key"] == "gtex_news_engine:news_bridge_1"


def test_exit_petition_bridge_only_public_stages(session) -> None:
    quiet = publish_exit_petition_story(
        session,
        player_id="p1",
        stage="quiet_discontent",
        message="Quiet for now.",
    )
    formal = publish_exit_petition_story(
        session,
        player_id="p1",
        stage="formal_request",
        message="Formal request lodged.",
        player_name="Tayo Mensah",
    )
    formal_again = publish_exit_petition_story(
        session,
        player_id="p1",
        stage="formal_request",
        message="Formal request lodged.",
        player_name="Tayo Mensah",
    )
    session.commit()
    assert quiet is False
    assert formal is True
    assert formal_again is False
    items = session.scalars(select(StoryFeedItem)).all()
    assert len(items) == 1
    assert items[0].story_type == "regen_exit_petition"


def test_app_update_bridge_requires_tag(session) -> None:
    ignored = publish_app_update_story(
        session,
        announcement_key="maintenance_window",
        title="Brief downtime",
        body="Ledger maintenance.",
        metadata_json={"severity": "info"},
    )
    published = publish_app_update_story(
        session,
        announcement_key="app_update_1.4.0",
        title="GTEX 1.4 is live",
        body="Capital desk and newsroom upgrades.",
        metadata_json={"app_update": True},
    )
    session.commit()
    assert ignored is False
    assert published is True
    items = session.scalars(select(StoryFeedItem)).all()
    assert len(items) == 1
    assert items[0].story_type == "app_update"
