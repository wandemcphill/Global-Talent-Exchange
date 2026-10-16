from __future__ import annotations

from app.club_identity.models.reputation import ClubReputationProfile
from app.club_identity.reputation.prestige_tier_service import PrestigeTierService
from app.club_identity.reputation.reputation_calculator import ReputationCalculator
from app.club_identity.reputation.schemas import ContinentalStage, SeasonReputationOutcome, WorldSuperCupStage


def test_reputation_calculator_applies_weighted_score_inputs() -> None:
    calculator = ReputationCalculator()
    profile = ClubReputationProfile(
        club_id="club-1",
        total_league_titles=1,
        total_continental_qualifications=1,
        prestige_tier="Established",
    )
    outcome = SeasonReputationOutcome(
        club_id="club-1",
        season=4,
        league_finish=1,
        qualified_for_continental=True,
        continental_stage=ContinentalStage.WINNER,
        qualified_for_world_super_cup=True,
        world_super_cup_stage=WorldSuperCupStage.SEMI_FINAL,
        other_trophy_wins=1,
        consecutive_top_competition_seasons=4,
        top_scorer_awards=1,
        top_assist_awards=1,
        undefeated_league_season=True,
        league_title_streak=2,
        continental_title_streak=2,
        club_age_years=75,
        activity_consistency_ratio=0.9,
        fair_play_bonus=True,
        giant_killer=True,
    )

    result = calculator.calculate(outcome=outcome, profile=profile)

    assert result.total_delta == 685
    assert "continental_champion" in result.badges
    assert "back_to_back_champion" in result.badges
    assert "invincibles" in result.badges
    assert "golden_attack" in result.badges
    assert "giant_killer" in result.badges


def test_prestige_tier_thresholds_are_stable() -> None:
    service = PrestigeTierService()

    assert service.determine_tier(0).value == "Local"
    assert service.determine_tier(150).value == "Rising"
    assert service.determine_tier(350).value == "Established"
    assert service.determine_tier(650).value == "Elite"
    assert service.determine_tier(1050).value == "Legendary"
    assert service.determine_tier(1600).value == "Dynasty"
