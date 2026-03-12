from __future__ import annotations

import pytest

from backend.app.schemas.competition_financials import CompetitionFinancialsPayload
from backend.app.schemas.competition_rules import CompetitionRuleSetPayload
from backend.app.services.competition_rules_engine import CompetitionRulesEngine, CompetitionRulesError


def test_rules_engine_builds_deterministic_top_n_payouts_and_fee_summary() -> None:
    rules_engine = CompetitionRulesEngine()
    rules = CompetitionRuleSetPayload.model_validate(
        {
            "format": "league",
            "league_rules": {
                "win_points": 3,
                "draw_points": 1,
                "loss_points": 0,
                "tie_break_order": ["points", "goal_diff", "goals_for"],
                "home_away": False,
                "min_participants": 4,
                "max_participants": 12,
            },
        }
    )
    financials = CompetitionFinancialsPayload.model_validate(
        {
            "entry_fee_minor": 2500,
            "currency": "USD",
            "platform_fee_bps": 500,
            "host_creation_fee_minor": 1000,
            "payout_mode": "top_n",
            "top_n": 3,
        }
    )

    summary = rules_engine.validate_rules(rules)
    payout_percentages = rules_engine.resolve_payout_percentages(financials)
    fee_summary = rules_engine.compute_fee_summary(financials, max_participants=summary.max_participants)

    assert summary.min_participants == 4
    assert summary.max_participants == 12
    assert payout_percentages == [34, 33, 33]
    assert fee_summary.gross_pool_minor == 30_000
    assert fee_summary.platform_fee_minor == 1_500
    assert fee_summary.net_prize_pool_minor == 27_500


def test_rules_engine_rejects_duplicate_league_tie_breaks() -> None:
    rules_engine = CompetitionRulesEngine()
    payload = CompetitionRuleSetPayload.model_validate(
        {
            "format": "league",
            "league_rules": {
                "win_points": 3,
                "draw_points": 1,
                "loss_points": 0,
                "tie_break_order": ["points", "points"],
                "home_away": True,
                "min_participants": 4,
                "max_participants": 8,
            },
        }
    )

    with pytest.raises(CompetitionRulesError, match="cannot contain duplicates"):
        rules_engine.validate_rules(payload)


def test_rules_engine_rejects_unsupported_cup_bracket_sizes() -> None:
    rules_engine = CompetitionRulesEngine()
    payload = CompetitionRuleSetPayload.model_validate(
        {
            "format": "cup",
            "cup_rules": {
                "single_elimination": True,
                "two_leg_tie": True,
                "extra_time": True,
                "penalties": True,
                "min_participants": 4,
                "max_participants": 8,
                "allowed_participant_sizes": [4, 8, 10],
            },
        }
    )

    with pytest.raises(CompetitionRulesError, match="supported bracket sizes"):
        rules_engine.validate_rules(payload)


def test_rules_engine_requires_custom_percentages_to_total_hundred() -> None:
    rules_engine = CompetitionRulesEngine()
    financials = CompetitionFinancialsPayload.model_validate(
        {
            "entry_fee_minor": 500,
            "currency": "USD",
            "platform_fee_bps": 250,
            "host_creation_fee_minor": 0,
            "payout_mode": "custom_percent",
            "payout_percentages": [60, 20],
        }
    )

    with pytest.raises(CompetitionRulesError, match="must total 100"):
        rules_engine.resolve_payout_percentages(financials)
