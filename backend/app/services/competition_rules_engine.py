from __future__ import annotations

from dataclasses import dataclass

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_payout_mode import CompetitionPayoutMode
from app.config.competition_constants import (
    CUP_ALLOWED_PARTICIPANT_SIZES,
    LEAGUE_RULE_ALLOWED_TIE_BREAKS,
    LEAGUE_RULE_DRAW_POINTS_MAX,
    LEAGUE_RULE_DRAW_POINTS_MIN,
    LEAGUE_RULE_LOSS_POINTS_MAX,
    LEAGUE_RULE_LOSS_POINTS_MIN,
    LEAGUE_RULE_WIN_POINTS_MAX,
    LEAGUE_RULE_WIN_POINTS_MIN,
    USER_COMPETITION_MAX_PARTICIPANTS,
    USER_COMPETITION_MIN_PARTICIPANTS,
)
from app.schemas.competition_financials import CompetitionFeeSummary, CompetitionFinancialsPayload
from app.schemas.competition_rules import CompetitionRuleSetPayload, CupRuleSetPayload, LeagueRuleSetPayload


class CompetitionRulesError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass(frozen=True, slots=True)
class CompetitionRuleSummary:
    format: CompetitionFormat
    min_participants: int
    max_participants: int


class CompetitionRulesEngine:
    def validate_rules(self, payload: CompetitionRuleSetPayload) -> CompetitionRuleSummary:
        errors: list[str] = []
        if payload.format == CompetitionFormat.LEAGUE and payload.league_rules is not None:
            errors.extend(self._validate_league_rules(payload.league_rules))
            summary = CompetitionRuleSummary(
                format=payload.format,
                min_participants=payload.league_rules.min_participants,
                max_participants=payload.league_rules.max_participants,
            )
        elif payload.format == CompetitionFormat.CUP and payload.cup_rules is not None:
            errors.extend(self._validate_cup_rules(payload.cup_rules))
            summary = CompetitionRuleSummary(
                format=payload.format,
                min_participants=payload.cup_rules.min_participants,
                max_participants=payload.cup_rules.max_participants,
            )
        else:
            errors.append("Competition rule set does not match the selected format.")
            summary = CompetitionRuleSummary(format=payload.format, min_participants=0, max_participants=0)

        if errors:
            raise CompetitionRulesError(errors)
        return summary

    def resolve_payout_percentages(self, financials: CompetitionFinancialsPayload) -> list[int]:
        payout_mode = financials.payout_mode
        percentages = list(financials.payout_percentages)

        if payout_mode == CompetitionPayoutMode.WINNER_TAKE_ALL:
            if percentages and (len(percentages) != 1 or sum(percentages) != 100):
                raise CompetitionRulesError(["winner_take_all payouts must be a single 100% value"])
            return [100]

        if payout_mode == CompetitionPayoutMode.TOP_N:
            if financials.top_n is None:
                raise CompetitionRulesError(["top_n is required for top_n payout mode"])
            if not percentages:
                return self._even_split(financials.top_n)
            if len(percentages) != financials.top_n:
                raise CompetitionRulesError(["payout_percentages must match top_n entries"])
            return self._validate_percentages(percentages)

        if payout_mode == CompetitionPayoutMode.CUSTOM_PERCENT:
            if not percentages:
                raise CompetitionRulesError(["custom_percent payouts require explicit percentages"])
            return self._validate_percentages(percentages)

        raise CompetitionRulesError(["Unsupported payout mode."])

    def compute_fee_summary(
        self,
        financials: CompetitionFinancialsPayload,
        *,
        max_participants: int,
    ) -> CompetitionFeeSummary:
        gross_pool_minor = financials.entry_fee_minor * max_participants
        platform_fee_minor = (gross_pool_minor * financials.platform_fee_bps) // 10_000
        net_prize_pool_minor = gross_pool_minor - platform_fee_minor - financials.host_creation_fee_minor
        if net_prize_pool_minor < 0:
            net_prize_pool_minor = 0
        return CompetitionFeeSummary(
            entry_fee_minor=financials.entry_fee_minor,
            currency=financials.currency,
            platform_fee_bps=financials.platform_fee_bps,
            host_creation_fee_minor=financials.host_creation_fee_minor,
            gross_pool_minor=gross_pool_minor,
            platform_fee_minor=platform_fee_minor,
            net_prize_pool_minor=net_prize_pool_minor,
        )

    def _validate_league_rules(self, rules: LeagueRuleSetPayload) -> list[str]:
        errors: list[str] = []
        if not (LEAGUE_RULE_WIN_POINTS_MIN <= rules.win_points <= LEAGUE_RULE_WIN_POINTS_MAX):
            errors.append("league win_points are outside the allowed range")
        if not (LEAGUE_RULE_DRAW_POINTS_MIN <= rules.draw_points <= LEAGUE_RULE_DRAW_POINTS_MAX):
            errors.append("league draw_points are outside the allowed range")
        if not (LEAGUE_RULE_LOSS_POINTS_MIN <= rules.loss_points <= LEAGUE_RULE_LOSS_POINTS_MAX):
            errors.append("league loss_points are outside the allowed range")
        if rules.win_points <= rules.draw_points or rules.draw_points < rules.loss_points:
            errors.append("league scoring must reward wins above draws and draws above losses")
        if not rules.tie_break_order:
            errors.append("league tie_break_order must include at least one tie-break")
        if any(item not in LEAGUE_RULE_ALLOWED_TIE_BREAKS for item in rules.tie_break_order):
            errors.append("league tie_break_order includes unsupported criteria")
        if len(set(rules.tie_break_order)) != len(rules.tie_break_order):
            errors.append("league tie_break_order cannot contain duplicates")
        errors.extend(self._validate_participant_bounds(rules.min_participants, rules.max_participants))
        return errors

    def _validate_cup_rules(self, rules: CupRuleSetPayload) -> list[str]:
        errors: list[str] = []
        if rules.single_elimination is not True:
            errors.append("cup competitions must be single elimination")
        errors.extend(self._validate_participant_bounds(rules.min_participants, rules.max_participants))
        allowed_sizes = rules.allowed_participant_sizes or list(CUP_ALLOWED_PARTICIPANT_SIZES)
        if any(size <= 1 or not self._is_power_of_two(size) for size in allowed_sizes):
            errors.append("cup allowed participant sizes must be powers of two")
        if any(size not in CUP_ALLOWED_PARTICIPANT_SIZES for size in allowed_sizes):
            errors.append("cup allowed participant sizes must use the supported bracket sizes")
        if rules.min_participants not in allowed_sizes:
            errors.append("cup min_participants must be an allowed bracket size")
        if rules.max_participants not in allowed_sizes:
            errors.append("cup max_participants must be an allowed bracket size")
        if rules.min_participants > rules.max_participants:
            errors.append("cup min_participants cannot exceed max_participants")
        return errors

    def _validate_participant_bounds(self, minimum: int, maximum: int) -> list[str]:
        errors: list[str] = []
        if minimum < USER_COMPETITION_MIN_PARTICIPANTS:
            errors.append("min_participants is below the allowed minimum")
        if maximum > USER_COMPETITION_MAX_PARTICIPANTS:
            errors.append("max_participants exceeds the allowed maximum")
        if minimum > maximum:
            errors.append("min_participants cannot exceed max_participants")
        return errors

    def _even_split(self, count: int) -> list[int]:
        if count <= 0:
            raise CompetitionRulesError(["top_n must be at least 1"])
        base = 100 // count
        remainder = 100 % count
        return [base + (1 if index < remainder else 0) for index in range(count)]

    def _validate_percentages(self, percentages: list[int]) -> list[int]:
        if any(value <= 0 for value in percentages):
            raise CompetitionRulesError(["payout percentages must be positive"])
        if sum(percentages) != 100:
            raise CompetitionRulesError(["payout percentages must total 100"])
        return percentages

    def _is_power_of_two(self, value: int) -> bool:
        return value > 0 and (value & (value - 1) == 0)
