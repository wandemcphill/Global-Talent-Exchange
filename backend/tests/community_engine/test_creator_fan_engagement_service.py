from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_round import CompetitionRound
from backend.app.models.creator_fan_engagement import CreatorMatchChatMessage, CreatorRivalrySignalSurface
from backend.app.models.creator_monetization import CreatorMatchGiftEvent
from backend.app.models.media_engine import MatchView
from backend.app.models.user import User
from backend.app.services.creator_fan_engagement_service import CreatorFanEngagementError, CreatorFanEngagementService


def _user(session: Session, user_id: str) -> User:
    user = session.get(User, user_id)
    assert user is not None
    return user


def test_chat_room_open_closed_window_rules(service: CreatorFanEngagementService, session: Session) -> None:
    match = session.get(CompetitionMatch, "match-1")
    assert match is not None
    scheduled_at = match.scheduled_at
    assert scheduled_at is not None

    before_open = service.get_chat_room(
        actor=_user(session, "fan-season-share"),
        match_id="match-1",
        now=scheduled_at - timedelta(hours=1, minutes=1),
    )
    assert before_open["is_open"] is False
    assert before_open["phase"] == "closed"

    pre_match = service.get_chat_room(
        actor=_user(session, "fan-season-share"),
        match_id="match-1",
        now=scheduled_at - timedelta(minutes=30),
    )
    assert pre_match["is_open"] is True
    assert pre_match["phase"] == "pre_match"

    match.status = "in_progress"
    live = service.get_chat_room(
        actor=_user(session, "fan-season-share"),
        match_id="match-1",
        now=scheduled_at + timedelta(minutes=10),
    )
    assert live["is_open"] is True
    assert live["phase"] == "live"

    match.status = "completed"
    match.completed_at = scheduled_at + timedelta(hours=2)
    post_match = service.get_chat_room(
        actor=_user(session, "fan-season-share"),
        match_id="match-1",
        now=match.completed_at + timedelta(minutes=10),
    )
    assert post_match["is_open"] is True
    assert post_match["phase"] == "post_match"

    closed = service.get_chat_room(
        actor=_user(session, "fan-season-share"),
        match_id="match-1",
        now=match.completed_at + timedelta(minutes=16),
    )
    assert closed["is_open"] is False
    assert closed["phase"] == "closed"


def test_comment_eligibility_rules(service: CreatorFanEngagementService, session: Session) -> None:
    match = session.get(CompetitionMatch, "match-1")
    assert match is not None
    scheduled_at = match.scheduled_at
    assert scheduled_at is not None
    now = scheduled_at - timedelta(minutes=30)

    share_season = service.get_chat_room(actor=_user(session, "fan-season-share"), match_id="match-1", now=now)
    season_only = service.get_chat_room(actor=_user(session, "fan-season"), match_id="match-1", now=now)
    paying = service.get_chat_room(actor=_user(session, "fan-paying"), match_id="match-1", now=now)
    share_paying = service.get_chat_room(actor=_user(session, "fan-share-paying"), match_id="match-1", now=now)
    basic = service.get_chat_room(actor=_user(session, "fan-basic"), match_id="match-1", now=now)

    assert share_season["access"]["can_comment"] is True
    assert share_season["access"]["visibility_priority"] == 300
    assert season_only["access"]["can_comment"] is True
    assert season_only["access"]["visibility_priority"] == 200
    assert paying["access"]["can_comment"] is True
    assert paying["access"]["visibility_priority"] == 100
    assert share_paying["access"]["can_comment"] is True
    assert share_paying["access"]["visibility_priority"] == 100
    assert basic["access"]["can_comment"] is False
    assert basic["access"]["reason"] == "fan_chat_access_denied"


def test_comment_ranking_orders_by_visibility_priority(service: CreatorFanEngagementService, session: Session) -> None:
    match = session.get(CompetitionMatch, "match-1")
    assert match is not None
    scheduled_at = match.scheduled_at
    assert scheduled_at is not None
    now = scheduled_at - timedelta(minutes=20)

    high = service.post_chat_message(
        actor=_user(session, "fan-season-share"),
        match_id="match-1",
        body="Top tier fan here",
        supported_club_id="club-home",
        metadata_json={},
        now=now,
    )
    mid = service.post_chat_message(
        actor=_user(session, "fan-season"),
        match_id="match-1",
        body="Season pass holder only",
        supported_club_id="club-away",
        metadata_json={},
        now=now,
    )
    low = service.post_chat_message(
        actor=_user(session, "fan-paying"),
        match_id="match-1",
        body="Paid viewer checking in",
        supported_club_id="club-home",
        metadata_json={},
        now=now,
    )
    session.commit()

    messages = service.list_chat_messages(match_id="match-1")

    assert [message.id for message in messages[:3]] == [high.id, mid.id, low.id]
    assert [message.visibility_priority for message in messages[:3]] == [300, 200, 100]


def test_tactical_advice_creation_retrieval_and_no_match_control_mutation(service: CreatorFanEngagementService, session: Session) -> None:
    match = session.get(CompetitionMatch, "match-1")
    assert match is not None
    scheduled_at = match.scheduled_at
    assert scheduled_at is not None
    before_status = match.status
    before_score = (match.home_score, match.away_score)

    advice = service.create_tactical_advice(
        actor=_user(session, "fan-season"),
        match_id="match-1",
        advice_type="tactical_adjustment",
        suggestion_text="Protect the lead",
        supported_club_id="club-away",
        metadata_json={},
        now=scheduled_at - timedelta(minutes=10),
    )
    session.commit()

    advice_items = service.list_tactical_advice(match_id="match-1")

    assert advice_items[0].id == advice.id
    assert advice_items[0].metadata_json["authority"] == "advisory_only"
    session.refresh(match)
    assert match.status == before_status
    assert (match.home_score, match.away_score) == before_score


def test_tactical_advice_rate_limit_blocks_rapid_repeat_submissions(
    service: CreatorFanEngagementService,
    session: Session,
) -> None:
    match = session.get(CompetitionMatch, "match-1")
    assert match is not None
    scheduled_at = match.scheduled_at
    assert scheduled_at is not None

    service.create_tactical_advice(
        actor=_user(session, "fan-season"),
        match_id="match-1",
        advice_type="tactical_adjustment",
        suggestion_text="Protect the midfield",
        supported_club_id="club-away",
        metadata_json={},
        now=scheduled_at - timedelta(minutes=10),
    )

    with pytest.raises(CreatorFanEngagementError) as exc_info:
        service.create_tactical_advice(
            actor=_user(session, "fan-season"),
            match_id="match-1",
            advice_type="formation_change",
            suggestion_text="Go more direct",
            supported_club_id="club-away",
            metadata_json={},
            now=scheduled_at - timedelta(minutes=9),
        )

    assert exc_info.value.reason == "tactical_advice_rate_limited"


def test_fan_wall_retrieval_includes_gifts_and_fan_events(service: CreatorFanEngagementService, session: Session) -> None:
    scheduled_at = session.get(CompetitionMatch, "match-1").scheduled_at
    assert scheduled_at is not None

    service.follow_creator_club(actor=_user(session, "fan-season-share"), club_id="club-home", metadata_json={})
    group = service.create_fan_group(
        actor=_user(session, "fan-season-share"),
        club_id="club-home",
        name="Speed Army",
        description="Fastest fan group",
        identity_label="Speed Army",
        is_official=False,
        metadata_json={},
    )
    service.join_fan_competition(
        actor=_user(session, "fan-season-share"),
        fan_competition_id=service.create_fan_competition(
            actor=_user(session, "fan-season-share"),
            club_id="club-home",
            title="Speed Army Predictions",
            description="Predict the result",
            match_id="match-1",
            starts_at=scheduled_at - timedelta(hours=1),
            ends_at=scheduled_at + timedelta(hours=2),
            metadata_json={},
        )["id"],
        fan_group_id=group["id"],
        metadata_json={},
    )
    service.create_tactical_advice(
        actor=_user(session, "fan-season-share"),
        match_id="match-1",
        advice_type="substitution",
        suggestion_text="Sub striker now",
        supported_club_id="club-home",
        metadata_json={},
        now=scheduled_at - timedelta(minutes=5),
    )
    session.add(
        CreatorMatchGiftEvent(
            id="gift-1",
            season_id="season-1",
            competition_id="competition-1",
            match_id="match-1",
            sender_user_id="fan-season-share",
            recipient_creator_user_id="creator-home-user",
            club_id="club-home",
            gift_label="Mega Horn",
            gross_amount_coin=Decimal("8.0000"),
            creator_share_coin=Decimal("5.6000"),
            platform_share_coin=Decimal("2.4000"),
            note="For the comeback",
            metadata_json={},
        )
    )
    session.commit()

    wall = service.get_fan_wall(match_id="match-1")
    item_types = {item["item_type"] for item in wall["items"]}

    assert wall["layout_hints_json"]["avoid_video_overlay"] is True
    assert "gift" in item_types
    assert "tactical_advice" in item_types
    assert "follow" in item_types or "fan_group_launch" in item_types


def test_rivalry_outputs_generate_homepage_and_notification_signals(service: CreatorFanEngagementService, session: Session) -> None:
    match = session.get(CompetitionMatch, "match-1")
    assert match is not None
    scheduled_at = match.scheduled_at
    assert scheduled_at is not None

    for index in range(2, 5):
        session.add(
            CompetitionRound(
                id=f"round-{index}",
                competition_id="competition-1",
                round_number=index,
                stage="league",
                status="completed",
                metadata_json={},
            )
        )
        session.add(
            CompetitionMatch(
                id=f"match-history-{index}",
                competition_id="competition-1",
                round_id=f"round-{index}",
                round_number=index,
                stage="league",
                home_club_id="club-home" if index % 2 == 0 else "club-away",
                away_club_id="club-away" if index % 2 == 0 else "club-home",
                scheduled_at=scheduled_at - timedelta(days=index),
                match_date=(scheduled_at - timedelta(days=index)).date(),
                status="completed",
                home_score=2,
                away_score=1,
                completed_at=scheduled_at - timedelta(days=index) + timedelta(hours=2),
                metadata_json={},
            )
        )
    for user_id in ("fan-season-share", "fan-season", "fan-paying", "fan-share-paying", "creator-home-user"):
        session.add(
            MatchView(
                id=f"view-{user_id}",
                user_id=user_id,
                match_key="match-1",
                competition_key="competition-1",
                view_date_key="20260317",
                watch_seconds=900,
                premium_unlocked=True,
                metadata_json={},
            )
        )
    session.add(
        MatchView(
            id="view-history",
            user_id="fan-basic",
            match_key="match-history-2",
            competition_key="competition-1",
            view_date_key="20260315",
            watch_seconds=120,
            premium_unlocked=False,
            metadata_json={},
        )
    )
    service.post_chat_message(
        actor=_user(session, "fan-season-share"),
        match_id="match-1",
        body="This rivalry is real",
        supported_club_id="club-home",
        metadata_json={},
        now=scheduled_at - timedelta(minutes=10),
    )
    service.create_tactical_advice(
        actor=_user(session, "fan-paying"),
        match_id="match-1",
        advice_type="formation_change",
        suggestion_text="Switch to attacking",
        supported_club_id="club-away",
        metadata_json={},
        now=scheduled_at - timedelta(minutes=5),
    )
    session.add(
        CreatorMatchGiftEvent(
            id="gift-rivalry",
            season_id="season-1",
            competition_id="competition-1",
            match_id="match-1",
            sender_user_id="fan-paying",
            recipient_creator_user_id="creator-away-user",
            club_id="club-away",
            gift_label="Fire Banner",
            gross_amount_coin=Decimal("12.0000"),
            creator_share_coin=Decimal("8.4000"),
            platform_share_coin=Decimal("3.6000"),
            note="Big match energy",
            metadata_json={},
        )
    )
    session.commit()

    outputs = service.list_rivalry_signals(match_id="match-1")

    assert {item.surface for item in outputs} == {
        CreatorRivalrySignalSurface.HOMEPAGE_PROMOTION,
        CreatorRivalrySignalSurface.NOTIFICATION,
    }
    assert all(item.signal_status.value == "active" for item in outputs)
    assert all(item.score >= 60 for item in outputs)
    assert outputs[0].rationale_json["frequent_matches"] >= 3
