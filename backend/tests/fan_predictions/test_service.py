from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin_engine.schemas import AdminRewardRuleStabilityControls
from app.fan_predictions.service import FanPredictionService
from app.models.admin_rules import AdminRewardRule
from app.models.competition_match import CompetitionMatch
from app.models.reward_settlement import RewardSettlement
from app.services.competition_match_service import CompetitionMatchService


def test_prediction_tokens_settlement_rewards_and_leaderboards(
    session: Session,
    seeded_context: dict[str, object],
) -> None:
    admin = seeded_context["admin"]
    fan_one = seeded_context["fan_one"]
    fan_two = seeded_context["fan_two"]
    rule_set = seeded_context["rule_set"]
    match = seeded_context["match"]
    assert admin is not None
    assert fan_one is not None
    assert fan_two is not None
    assert rule_set is not None
    assert match is not None

    service = FanPredictionService(session)
    fan_one_tokens = service.token_summary(actor=fan_one, today=datetime(2026, 3, 17, tzinfo=UTC).date())
    fan_two_tokens = service.token_summary(actor=fan_two, today=datetime(2026, 3, 17, tzinfo=UTC).date())
    assert fan_one_tokens["available_tokens"] == 6
    assert fan_two_tokens["available_tokens"] == 5

    fixture = service.ensure_fixture(
        match_id=match.id,
        actor=admin,
        promo_pool_fancoin=Decimal("120.0000"),
        badge_code="prediction-ace",
    )
    service.submit_prediction(
        actor=fan_one,
        match_id=match.id,
        winner_club_id="club-alpha",
        first_goal_scorer_player_id="player-hero",
        total_goals=3,
        mvp_player_id="player-hero",
        fan_segment_club_id="club-alpha",
    )
    service.submit_prediction(
        actor=fan_two,
        match_id=match.id,
        winner_club_id="club-bravo",
        first_goal_scorer_player_id="player-hero",
        total_goals=2,
        mvp_player_id="player-bravo",
        fan_segment_club_id="club-bravo",
    )
    session.commit()

    match_service = CompetitionMatchService(session)
    match_service.record_event(
        competition_id="competition-1",
        match_id="match-1",
        event_type="goal",
        minute=5,
        added_time=None,
        club_id="club-alpha",
        player_id="player-hero",
        secondary_player_id=None,
        card_type=None,
        highlight=True,
        metadata_json={},
    )
    match_service.record_event(
        competition_id="competition-1",
        match_id="match-1",
        event_type="mvp",
        minute=90,
        added_time=None,
        club_id="club-alpha",
        player_id="player-hero",
        secondary_player_id=None,
        card_type=None,
        highlight=True,
        metadata_json={},
    )
    completed_match = session.get(CompetitionMatch, "match-1")
    assert completed_match is not None
    match_service.complete_match(
        match=completed_match,
        rule_set=rule_set,
        home_score=2,
        away_score=1,
        winner_club_id="club-alpha",
    )
    session.commit()

    refreshed_fixture = service.get_fixture(match_id="match-1")
    submission = service.get_submission_for_user(fixture_id=fixture.id, user_id="fan-one")
    assert submission is not None
    assert refreshed_fixture.status.value == "settled"
    assert submission.points_awarded == 20
    assert submission.perfect_card is True

    grants = service.list_reward_grants(fixture_id=fixture.id)
    assert len(grants) == 2
    fancoin_grant = next(item for item in grants if item.reward_type.value == "fancoin")
    badge_grants = [item for item in grants if item.reward_type.value == "badge"]
    assert fancoin_grant.user_id == "fan-one"
    assert fancoin_grant.fancoin_amount == Decimal("120.0000")
    assert badge_grants[0].badge_code == "prediction-ace"

    reward_settlement = session.get(RewardSettlement, fancoin_grant.reward_settlement_id)
    assert reward_settlement is not None
    assert reward_settlement.reward_source == "gtex_promotional_pool"
    assert reward_settlement.gross_amount == Decimal("120.0000")

    leaderboard = service.weekly_leaderboard(week_start=submission.leaderboard_week_start)
    assert leaderboard["entries"][0]["user_id"] == "fan-one"
    assert leaderboard["entries"][0]["total_points"] == 20

    club_leaderboard = service.creator_club_weekly_leaderboard(
        club_id="club-alpha",
        week_start=submission.leaderboard_week_start,
    )
    assert club_leaderboard["entries"][0]["user_id"] == "fan-one"


def test_prediction_rewards_require_multiple_distinct_participants(
    session: Session,
    seeded_context: dict[str, object],
) -> None:
    admin = seeded_context["admin"]
    fan_one = seeded_context["fan_one"]
    rule_set = seeded_context["rule_set"]
    match = seeded_context["match"]
    assert admin is not None
    assert fan_one is not None
    assert rule_set is not None
    assert match is not None

    service = FanPredictionService(session)
    fixture = service.ensure_fixture(
        match_id=match.id,
        actor=admin,
        promo_pool_fancoin=Decimal("50.0000"),
        badge_code="solo-ace",
    )
    service.submit_prediction(
        actor=fan_one,
        match_id=match.id,
        winner_club_id="club-alpha",
        first_goal_scorer_player_id="player-hero",
        total_goals=1,
        mvp_player_id="player-hero",
        fan_segment_club_id="club-alpha",
    )
    session.commit()

    match_service = CompetitionMatchService(session)
    match_service.record_event(
        competition_id="competition-1",
        match_id="match-1",
        event_type="goal",
        minute=4,
        added_time=None,
        club_id="club-alpha",
        player_id="player-hero",
        secondary_player_id=None,
        card_type=None,
        highlight=True,
        metadata_json={},
    )
    match_service.record_event(
        competition_id="competition-1",
        match_id="match-1",
        event_type="mvp",
        minute=90,
        added_time=None,
        club_id="club-alpha",
        player_id="player-hero",
        secondary_player_id=None,
        card_type=None,
        highlight=True,
        metadata_json={},
    )
    completed_match = session.get(CompetitionMatch, "match-1")
    assert completed_match is not None
    match_service.complete_match(
        match=completed_match,
        rule_set=rule_set,
        home_score=1,
        away_score=0,
        winner_club_id="club-alpha",
    )
    session.commit()

    refreshed_fixture = service.get_fixture(match_id="match-1")
    grants = service.list_reward_grants(fixture_id=fixture.id)

    assert all(item.reward_type.value != "fancoin" for item in grants)
    assert any(item.reward_type.value == "badge" for item in grants)
    assert refreshed_fixture.metadata_json["fan_prediction_fairness"]["reward_payout_status"] == "fancoin_withheld_low_participation"
    assert refreshed_fixture.metadata_json["fan_prediction_fairness"]["distinct_participants"] == 1
    assert (
        session.scalar(
            select(RewardSettlement).where(RewardSettlement.competition_key == "fan_prediction:match-1")
        )
        is None
    )


def test_prediction_rewards_cap_fancoin_pool_by_fairness_controls(
    session: Session,
    seeded_context: dict[str, object],
) -> None:
    admin = seeded_context["admin"]
    fan_one = seeded_context["fan_one"]
    fan_two = seeded_context["fan_two"]
    rule_set = seeded_context["rule_set"]
    match = seeded_context["match"]
    assert admin is not None
    assert fan_one is not None
    assert fan_two is not None
    assert rule_set is not None
    assert match is not None

    session.add(
        AdminRewardRule(
            rule_key="fan-prediction-fairness",
            title="Fan Prediction Fairness",
            description="Cap low-liquidity fan prediction payouts.",
            trading_fee_bps=2000,
            gift_platform_rake_bps=3000,
            withdrawal_fee_bps=1000,
            minimum_withdrawal_fee_credits=Decimal("5.0000"),
            competition_platform_fee_bps=1000,
            stability_controls_json=AdminRewardRuleStabilityControls(
                fan_prediction={
                    "min_distinct_participants_for_fancoin": 2,
                    "max_fixture_promo_pool_fancoin": "90.0000",
                    "max_fancoin_pool_per_participant": "40.0000",
                    "max_reward_winners": 3,
                }
            ).model_dump(mode="json"),
            active=True,
        )
    )
    session.commit()

    service = FanPredictionService(session)
    fixture = service.ensure_fixture(
        match_id=match.id,
        actor=admin,
        promo_pool_fancoin=Decimal("120.0000"),
    )
    service.submit_prediction(
        actor=fan_one,
        match_id=match.id,
        winner_club_id="club-alpha",
        first_goal_scorer_player_id="player-hero",
        total_goals=2,
        mvp_player_id="player-hero",
        fan_segment_club_id="club-alpha",
    )
    service.submit_prediction(
        actor=fan_two,
        match_id=match.id,
        winner_club_id="club-bravo",
        first_goal_scorer_player_id="player-hero",
        total_goals=1,
        mvp_player_id="player-bravo",
        fan_segment_club_id="club-bravo",
    )
    session.commit()

    match_service = CompetitionMatchService(session)
    match_service.record_event(
        competition_id="competition-1",
        match_id="match-1",
        event_type="goal",
        minute=5,
        added_time=None,
        club_id="club-alpha",
        player_id="player-hero",
        secondary_player_id=None,
        card_type=None,
        highlight=True,
        metadata_json={},
    )
    match_service.record_event(
        competition_id="competition-1",
        match_id="match-1",
        event_type="mvp",
        minute=90,
        added_time=None,
        club_id="club-alpha",
        player_id="player-hero",
        secondary_player_id=None,
        card_type=None,
        highlight=True,
        metadata_json={},
    )
    completed_match = session.get(CompetitionMatch, "match-1")
    assert completed_match is not None
    match_service.complete_match(
        match=completed_match,
        rule_set=rule_set,
        home_score=2,
        away_score=0,
        winner_club_id="club-alpha",
    )
    session.commit()

    refreshed_fixture = service.get_fixture(match_id="match-1")
    grants = service.list_reward_grants(fixture_id=fixture.id)
    fancoin_grant = next(item for item in grants if item.reward_type.value == "fancoin")

    assert fancoin_grant.fancoin_amount == Decimal("80.0000")
    assert refreshed_fixture.metadata_json["fan_prediction_fairness"]["reward_payout_status"] == "fancoin_capped"
    assert refreshed_fixture.metadata_json["fan_prediction_fairness"]["effective_promo_pool_fancoin"] == "80.0000"
