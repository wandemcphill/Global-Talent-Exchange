from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.betting.schemas import BetPlaceRequest, BetPreferenceRequest
from app.betting.service import BettingService
from app.calendar_engine.service import CalendarEngineService
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.base import Base
from app.models.betting import BetAuditLog, BetIntegrityAlert, BetTicket, BettingProfile
from app.models.calendar_engine import GlobalEvent
from app.models.competition_match import CompetitionMatch
from app.models.event_backbone import EventOutbox
from app.models.pundit_profile import PunditProfile
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerAccount, LedgerBalanceProjection, LedgerEntry, LedgerTransaction, LedgerUnit
from app.pundits.service import PunditService
from app.wallets.service import LedgerPosting, WalletService
from backend.tests.match_engine.helpers import build_request


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            CompetitionMatch.__table__,
            GlobalEvent.__table__,
            PunditProfile.__table__,
            BettingProfile.__table__,
            BetTicket.__table__,
            BetAuditLog.__table__,
            BetIntegrityAlert.__table__,
            LedgerAccount.__table__,
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            EventOutbox.__table__,
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_wallet(session: Session, actor: User) -> None:
    wallet_service = WalletService()
    accounts = wallet_service.ensure_default_accounts(session, actor)
    operations = wallet_service.ensure_operations_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[LedgerPosting(account=accounts[LedgerUnit.CREDIT], amount=Decimal("300.0000")), LedgerPosting(account=operations, amount=Decimal("-300.0000"))],
        reason=wallet_service.trade_settlement_reason,
        reference="seed-main-wallet",
        description="Seed main wallet for integration flow",
        actor=actor,
    )


def test_media_betting_flow_runs_end_to_end() -> None:
    session_factory = _session_factory()
    request = build_request(seed=123, match_id="media-flow", is_final=True)
    replay = MatchSimulationService().build_replay_payload(request)
    with session_factory() as session:
        actor = User(
            id="media-user",
            email="media@example.com",
            username="media-user",
            full_name="Media User",
            display_name="Media User",
            password_hash="hash",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        )
        session.add(actor)
        session.flush()
        _seed_wallet(session, actor)
        session.add(
            CompetitionMatch(
                id="media-flow",
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                stage="final",
                home_club_id=request.home_team.team_id,
                away_club_id=request.away_team.team_id,
                scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
                status="scheduled",
                metadata_json={"preview_request": request.model_dump(mode="json")},
            )
        )
        session.commit()

        calendar = CalendarEngineService(session)
        upcoming_before = calendar.upcoming_events_feed(days=2)
        pre_show = PunditService(session).build_pre_match_show("media-flow")

        betting = BettingService(session)
        betting.update_preferences(actor=actor, payload=BetPreferenceRequest(region_code="GLOBAL", opt_in=True, is_enabled=True, age_gate_confirmed=True))
        if replay.summary.home_score > replay.summary.away_score:
            winner_key = "home"
        elif replay.summary.away_score > replay.summary.home_score:
            winner_key = "away"
        else:
            winner_key = "draw"
        place = betting.place_bet(
            actor=actor,
            payload=BetPlaceRequest(
                match_id="media-flow",
                bet_type="match_winner",
                selection_key=winner_key,
                stake_amount=Decimal("15.0000"),
                region_code="GLOBAL",
                auto_fund_from_main=True,
                opt_in_acknowledged=True,
                age_gate_confirmed=True,
            ),
        )
        session.flush()

        match = session.get(CompetitionMatch, "media-flow")
        assert match is not None
        match.status = "completed"
        match.metadata_json = {**dict(match.metadata_json or {}), "replay_payload": replay.model_dump(mode="json")}
        session.flush()

        post_show = PunditService(session).build_post_match_show("media-flow")
        settled = betting.settle_match_bets(match_id="media-flow")
        upcoming_after = calendar.upcoming_events_feed(days=2)
        profile = session.scalar(select(BettingProfile).where(BettingProfile.user_id == actor.id))
        session.commit()

    assert upcoming_before["events"]
    assert pre_show.show_type == "pre_match"
    assert pre_show.prediction is not None
    assert any(item["engagement"]["betting_route"] == "/bets/odds/media-flow" for item in upcoming_before["events"] if item["match_id"] == "media-flow")
    assert place.ticket.status == "placed"
    assert post_show.show_type == "post_match"
    assert post_show.player_ratings
    assert settled[0].status == "won"
    assert profile is not None
    assert profile.locked_bet_balance == Decimal("0.0000")
    assert profile.available_bet_balance > Decimal("0.0000")
    assert upcoming_after["events"]
