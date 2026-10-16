from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_finance.models import ClubFinanceProfile, ClubFinanceTransaction
from app.club_finance.service import ClubFinanceService
from app.live_ops.models import SeasonPassClaim, SeasonPassXpGrant
from app.live_ops.service import LiveOpsService
from app.match_engine.simulation.models import InternalPlayer, PlayerRole
from app.models.notification_record import NotificationRecord
from app.predictions.models import PredictionOutcome
from app.predictions.service import PredictionService
from app.services.match_engagement_service import MatchEngagementService


def test_match_engagement_resolves_predictions_finance_and_xp(
    session: Session,
    seeded_context: dict[str, object],
) -> None:
    fan_user = seeded_context["fan_user"]
    assert fan_user is not None

    prediction = PredictionService(session).submit_prediction(
        actor=fan_user,
        match_id="match-1",
        predicted_outcome=PredictionOutcome.HOME_WIN,
        confidence_level=0.8,
    )
    session.commit()

    MatchEngagementService(session).apply_match_result(
        match_id="match-1",
        home_club_id="club-home",
        away_club_id="club-away",
        home_score=2,
        away_score=0,
        home_user_id="owner-home",
        away_user_id="owner-away",
    )
    session.commit()

    session.refresh(prediction)
    assert prediction.actual_outcome == PredictionOutcome.HOME_WIN
    assert prediction.reward_earned > 0

    leaderboard = PredictionService(session).leaderboard(limit=10)
    assert leaderboard[0]["user_id"] == "fan-user"
    assert leaderboard[0]["total_correct_predictions"] == 1

    finance_profiles = {
        item.user_id: item
        for item in session.scalars(select(ClubFinanceProfile)).all()
    }
    assert finance_profiles["owner-home"].match_income == Decimal("13.0000")
    assert finance_profiles["owner-away"].match_income == Decimal("8.0000")

    xp_grants = list(session.scalars(select(SeasonPassXpGrant).order_by(SeasonPassXpGrant.reference_key)).all())
    assert {item.source_type for item in xp_grants} >= {"prediction", "match_played", "match_win"}

    notifications = list(session.scalars(select(NotificationRecord)).all())
    assert {item.template_key for item in notifications} >= {"PREDICTION_RESULT"}


def test_finance_weekly_cycle_applies_sponsors_once_and_enforces_negative_balance(
    session: Session,
    seeded_context: dict[str, object],
) -> None:
    MatchEngagementService(session).apply_match_result(
        match_id="match-1",
        home_club_id="club-home",
        away_club_id="club-away",
        home_score=3,
        away_score=1,
        home_user_id="owner-home",
        away_user_id="owner-away",
    )
    finance_service = ClubFinanceService(session)
    profile = finance_service.get_or_create_profile(user_id="owner-home")
    profile.weekly_wages = Decimal("700.0000")
    profile.expenses = Decimal("40.0000")
    session.commit()

    first_run = finance_service.run_weekly_cycle(as_of=datetime(2026, 3, 27, tzinfo=UTC).date())
    second_run = finance_service.run_weekly_cycle(as_of=datetime(2026, 3, 27, tzinfo=UTC).date())
    session.commit()

    assert first_run["profiles_processed"] >= 1
    assert second_run["profiles_processed"] == 0

    session.refresh(profile)
    assert profile.balance < 0
    assert profile.transfers_blocked is True
    assert profile.forced_sale_required is True

    sponsor_refs = list(
        session.scalars(
            select(ClubFinanceTransaction.reference_key).where(
                ClubFinanceTransaction.transaction_type == "sponsor_payout"
            )
        ).all()
    )
    assert len(sponsor_refs) == len(set(sponsor_refs))


def test_live_ops_claim_reward_updates_finance_balance(
    session: Session,
    seeded_context: dict[str, object],
) -> None:
    live_ops_service = LiveOpsService(session)
    season_pass = live_ops_service.get_or_create_season_pass(user_id="fan-user")
    live_ops_service.award_xp(
        user_id="fan-user",
        source_type="manual_test",
        amount=220,
        reference_key="manual-xp-grant",
    )
    claim = live_ops_service.claim_reward(actor=seeded_context["fan_user"], level=1, season_id=season_pass.season_id)
    session.commit()

    assert isinstance(claim, SeasonPassClaim)
    finance_profile = ClubFinanceService(session).get_or_create_profile(user_id="fan-user")
    assert finance_profile.balance == Decimal("25.0000")
    notifications = list(
        session.scalars(
            select(NotificationRecord).where(NotificationRecord.template_key == "SEASON_PASS_LEVEL_UP")
        ).all()
    )
    assert notifications


def test_internal_player_morale_modifier_changes_performance() -> None:
    low_morale_player = InternalPlayer(
        player_id="p-low",
        player_name="Low Morale",
        role=PlayerRole.FORWARD,
        overall=75,
        finishing=75,
        creativity=70,
        defending=40,
        goalkeeping=5,
        discipline=70,
        fitness=75,
        morale=20,
    )
    high_morale_player = InternalPlayer(
        player_id="p-high",
        player_name="High Morale",
        role=PlayerRole.FORWARD,
        overall=75,
        finishing=75,
        creativity=70,
        defending=40,
        goalkeeping=5,
        discipline=70,
        fitness=75,
        morale=90,
    )

    assert high_morale_player.attacking_value() > low_morale_player.attacking_value()
    assert high_morale_player.control_value() > low_morale_player.control_value()
    assert high_morale_player.defensive_value() > low_morale_player.defensive_value()
