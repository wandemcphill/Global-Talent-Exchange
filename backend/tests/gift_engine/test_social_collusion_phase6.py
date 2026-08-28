from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_visibility import CompetitionVisibility
from app.admin_engine.service import AdminEngineService
from app.common.enums.match_status import MatchStatus
from app.gift_engine.service import GiftEngineService
from app.models import (
    Base,
    ClubProfile,
    ClubRankingAbuseFlag,
    ClubRankingEvent,
    Competition,
    CompetitionMatch,
    CompetitionParticipant,
    CompetitionRound,
    GiftAbuseFlag,
    LedgerEntryReason,
    LedgerUnit,
)
from app.models.user import User
from app.services.club_ranking_integrity_service import ClubRankingIntegrityService
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session
    engine.dispose()


def _create_user(session: Session, *, email: str, username: str) -> User:
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
    )
    session.commit()
    return user


def _fund_fan_coin(session: Session, user: User, amount: Decimal) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference=f"seed-phase6-social-collusion:{user.id}",
        actor=user,
    )
    session.commit()


def _create_club(session: Session, *, owner: User, name: str) -> ClubProfile:
    now = datetime.now(timezone.utc)
    club = ClubProfile(
        owner_user_id=owner.id,
        club_name=name,
        short_name=name[:20],
        slug=f"{name.lower().replace(' ', '-')}-{uuid4().hex[:8]}",
        primary_color="#A6FF1A",
        secondary_color="#0B1210",
        accent_color="#58D5FF",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        created_at=now - timedelta(days=30),
        updated_at=now - timedelta(days=30),
    )
    session.add(club)
    session.flush()
    return club


def _seed_established_history(session: Session, *, club: ClubProfile, competition: Competition) -> None:
    created_at = datetime.now(timezone.utc) - timedelta(days=30)
    for index in range(5):
        session.add(
            ClubRankingEvent(
                event_key=f"phase6-seed:{club.id}:{index}:{uuid4().hex}",
                event_kind="seed_history",
                club_id=club.id,
                competition_id=competition.id,
                result="win",
                base_points=Decimal("3.0000"),
                raw_points_delta=Decimal("1.0000"),
                final_points_delta=Decimal("1.0000"),
                integrity_status="clean",
                reason="seeded_established_history",
                created_at=created_at,
                updated_at=created_at,
            )
        )
    session.flush()


def _seed_completed_match(
    session: Session,
    *,
    host: User,
    home: ClubProfile,
    away: ClubProfile,
) -> tuple[Competition, CompetitionMatch]:
    competition = Competition(
        host_user_id=host.id,
        name=f"Phase 6 Ranked Ladder {uuid4().hex[:6]}",
        competition_type=CompetitionFormat.LEAGUE.value,
        competition_mode="competition",
        format=CompetitionFormat.LEAGUE.value,
        visibility=CompetitionVisibility.PUBLIC.value,
        status=CompetitionStatus.LIVE.value,
        stage="league",
        currency="credit",
        entry_fee_minor=0,
        platform_fee_bps=2000,
        is_ranked=True,
    )
    session.add(competition)
    session.flush()
    session.add_all(
        [
            CompetitionParticipant(competition_id=competition.id, user_id=home.owner_user_id, club_id=home.id),
            CompetitionParticipant(competition_id=competition.id, user_id=away.owner_user_id, club_id=away.id),
        ]
    )
    round_row = CompetitionRound(
        competition_id=competition.id,
        round_number=1,
        stage="league",
        status="completed",
    )
    session.add(round_row)
    session.flush()
    match = CompetitionMatch(
        competition_id=competition.id,
        round_id=round_row.id,
        round_number=1,
        stage="league",
        home_club_id=home.id,
        away_club_id=away.id,
        status=MatchStatus.COMPLETED.value,
        home_score=2,
        away_score=0,
        winner_club_id=home.id,
        completed_at=datetime.now(timezone.utc),
        metadata_json={"result_type": "played"},
    )
    session.add(match)
    session.commit()
    return competition, match


def _record_ranked_win(session: Session, *, host: User, home: ClubProfile, away: ClubProfile) -> ClubRankingEvent:
    competition, match = _seed_completed_match(session, host=host, home=home, away=away)
    if not session.scalar(
        select(ClubRankingEvent).where(
            ClubRankingEvent.club_id == home.id,
            ClubRankingEvent.event_kind == "seed_history",
        )
    ):
        _seed_established_history(session, club=home, competition=competition)
        _seed_established_history(session, club=away, competition=competition)
    ClubRankingIntegrityService(session).record_match_result(competition=competition, match=match)
    session.commit()
    event = session.scalar(select(ClubRankingEvent).where(ClubRankingEvent.event_key == f"match:{match.id}:{home.id}"))
    assert event is not None
    return event


def test_repeated_ranked_matches_plus_reciprocal_gifts_create_combined_collusion_flags(session: Session) -> None:
    AdminEngineService(session).seed_defaults()
    host = _create_user(session, email="phase6-host@example.com", username="phase6-host")
    opponent_owner = _create_user(session, email="phase6-opponent@example.com", username="phase6-opponent")
    home = _create_club(session, owner=host, name="Phase Six Home FC")
    away = _create_club(session, owner=opponent_owner, name="Phase Six Away FC")

    first_event = _record_ranked_win(session, host=host, home=home, away=away)
    second_event = _record_ranked_win(session, host=host, home=home, away=away)
    assert "combined_play_gift_collusion" not in first_event.reason
    assert "combined_play_gift_collusion" not in second_event.reason

    _fund_fan_coin(session, host, Decimal("100.0000"))
    _fund_fan_coin(session, opponent_owner, Decimal("100.0000"))
    GiftEngineService(session).send_gift(
        sender=host,
        recipient_user_id=opponent_owner.id,
        gift_key="whistle_blow",
        quantity=Decimal("30.0000"),
        idempotency_key="phase6-first-gift",
    )
    reciprocal = GiftEngineService(session).send_gift(
        sender=opponent_owner,
        recipient_user_id=host.id,
        gift_key="whistle_blow",
        quantity=Decimal("30.0000"),
        idempotency_key="phase6-reciprocal-gift",
    )
    session.commit()

    assert reciprocal.abuse_status == "review"
    assert session.scalar(select(GiftAbuseFlag).where(GiftAbuseFlag.flag_type == "competition_gift_collusion"))
    assert session.scalar(
        select(ClubRankingAbuseFlag).where(ClubRankingAbuseFlag.flag_type == "combined_play_gift_collusion")
    )

    reviewed_events = session.scalars(
        select(ClubRankingEvent).where(
            ClubRankingEvent.event_kind == "match_result",
            ClubRankingEvent.club_id == home.id,
        )
    ).all()
    assert any("combined_play_gift_collusion" in event.reason for event in reviewed_events)
    assert all(event.integrity_status in {"review", "blocked"} for event in reviewed_events)

    third_event = _record_ranked_win(session, host=host, home=home, away=away)
    assert third_event.integrity_status in {"review", "blocked"}
    assert "combined_play_gift_collusion" in third_event.reason
    assert third_event.anti_farm_multiplier <= Decimal("0.2500")
    assert third_event.final_points_delta <= Decimal("1.0000")


def test_single_normal_gift_after_one_ranked_match_does_not_create_combined_collusion(session: Session) -> None:
    AdminEngineService(session).seed_defaults()
    host = _create_user(session, email="phase6-clean-host@example.com", username="phase6-clean-host")
    opponent_owner = _create_user(session, email="phase6-clean-opponent@example.com", username="phase6-clean-opponent")
    home = _create_club(session, owner=host, name="Clean Gift Home FC")
    away = _create_club(session, owner=opponent_owner, name="Clean Gift Away FC")
    event = _record_ranked_win(session, host=host, home=home, away=away)

    _fund_fan_coin(session, host, Decimal("20.0000"))
    gift = GiftEngineService(session).send_gift(
        sender=host,
        recipient_user_id=opponent_owner.id,
        gift_key="whistle_blow",
        quantity=Decimal("1.0000"),
        idempotency_key="phase6-clean-gift",
    )
    session.commit()

    assert gift.abuse_status == "clean"
    assert session.scalar(select(GiftAbuseFlag).where(GiftAbuseFlag.flag_type == "competition_gift_collusion")) is None
    refreshed_event = session.get(ClubRankingEvent, event.id)
    assert refreshed_event is not None
    assert "combined_play_gift_collusion" not in refreshed_event.reason
