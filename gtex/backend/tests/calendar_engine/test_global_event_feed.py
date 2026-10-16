from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy.orm import Session

from app.calendar_engine.schemas import GlobalEventView
from app.calendar_engine.service import CalendarEngineService
from app.models.calendar_engine import GlobalEvent


def test_global_event_feed_omits_deprecated_betting_route() -> None:
    start_time = datetime(2026, 4, 15, 18, 0, tzinfo=UTC)
    end_time = start_time + timedelta(hours=2)
    event = GlobalEvent(
        event_key="gtex-final",
        event_name="GTEX Final",
        start_time=start_time,
        end_time=end_time,
        event_type="match",
        priority=95,
        match_id="match-1",
        status="scheduled",
        metadata_json={"family": "cup"},
    )
    event.id = "event-1"
    event.created_at = start_time - timedelta(days=1)
    event.updated_at = start_time - timedelta(hours=2)

    payload = CalendarEngineService(session=cast(Session, object()))._serialize_global_event(
        event,
        now=start_time - timedelta(hours=1),
    )
    view = GlobalEventView.model_validate(payload)

    assert view.engagement is not None
    assert view.engagement.match_route == "/matches/match-1"
    assert view.engagement.pre_match_show_route == "/shows/pre-match/match-1"
    assert view.engagement.post_match_show_route == "/shows/post-match/match-1"
    assert "betting_route" not in payload["engagement"]
