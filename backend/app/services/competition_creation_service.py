from __future__ import annotations

from dataclasses import dataclass

from app.common.enums.competition_format import CompetitionFormat
from app.models.competition import Competition
from app.models.competition_prize_rule import CompetitionPrizeRule
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.competition_wallet_ledger import CompetitionWalletLedger
from app.models.base import generate_uuid
from app.schemas.competition_core import CompetitionCreateRequest
from app.services.competition_rules_engine import CompetitionRulesEngine
from app.services.competition_validation_service import CompetitionValidationService


@dataclass(frozen=True, slots=True)
class CompetitionCreationResult:
    competition: Competition
    rule_set: CompetitionRuleSet
    prize_rule: CompetitionPrizeRule
    ledger_entries: tuple[CompetitionWalletLedger, ...]


class CompetitionCreationService:
    def __init__(
        self,
        *,
        rules_engine: CompetitionRulesEngine | None = None,
        validation_service: CompetitionValidationService | None = None,
    ) -> None:
        self._rules_engine = rules_engine or CompetitionRulesEngine()
        self._validation_service = validation_service or CompetitionValidationService(self._rules_engine)

    def build_competition(self, payload: CompetitionCreateRequest) -> CompetitionCreationResult:
        validation = self._validation_service.validate_creation(payload)
        competition_id = generate_uuid()

        competition = Competition(
            id=competition_id,
            host_user_id=payload.core.host_user_id,
            name=payload.core.name,
            description=payload.core.description,
            competition_type=payload.core.format.value,
            format=payload.core.format.value,
            visibility=payload.core.visibility.value,
            status=payload.core.status.value,
            start_mode=payload.core.start_mode.value,
            scheduled_start_at=payload.core.scheduled_start_at,
            currency=payload.financials.currency,
            entry_fee_minor=payload.financials.entry_fee_minor,
            platform_fee_bps=payload.financials.platform_fee_bps,
            host_fee_bps=0,
            host_creation_fee_minor=payload.financials.host_creation_fee_minor,
            gross_pool_minor=validation.fee_summary.gross_pool_minor,
            net_prize_pool_minor=validation.fee_summary.net_prize_pool_minor,
        )

        rule_set = self._build_rule_set(
            payload.rules,
            competition_id,
            validation.min_participants,
            validation.max_participants,
        )
        prize_rule = CompetitionPrizeRule(
            competition_id=competition_id,
            payout_mode=payload.financials.payout_mode.value,
            top_n=payload.financials.top_n,
            payout_percentages=validation.payout_percentages,
        )

        ledger_entries = self._build_creation_ledger_entries(competition)

        return CompetitionCreationResult(
            competition=competition,
            rule_set=rule_set,
            prize_rule=prize_rule,
            ledger_entries=ledger_entries,
        )

    def _build_rule_set(
        self,
        rules_payload,
        competition_id: str,
        min_participants: int,
        max_participants: int,
    ) -> CompetitionRuleSet:
        if rules_payload.format == CompetitionFormat.LEAGUE:
            league = rules_payload.league_rules
            assert league is not None
            return CompetitionRuleSet(
                competition_id=competition_id,
                format=rules_payload.format.value,
                min_participants=min_participants,
                max_participants=max_participants,
                league_win_points=league.win_points,
                league_draw_points=league.draw_points,
                league_loss_points=league.loss_points,
                league_tie_break_order=list(league.tie_break_order),
                league_home_away=league.home_away,
                cup_single_elimination=None,
                cup_two_leg_tie=None,
                cup_extra_time=None,
                cup_penalties=None,
                cup_allowed_participant_sizes=[],
            )
        cup = rules_payload.cup_rules
        assert cup is not None
        return CompetitionRuleSet(
            competition_id=competition_id,
            format=rules_payload.format.value,
            min_participants=min_participants,
            max_participants=max_participants,
            league_win_points=None,
            league_draw_points=None,
            league_loss_points=None,
            league_tie_break_order=[],
            league_home_away=None,
            cup_single_elimination=cup.single_elimination,
            cup_two_leg_tie=cup.two_leg_tie,
            cup_extra_time=cup.extra_time,
            cup_penalties=cup.penalties,
            cup_allowed_participant_sizes=list(cup.allowed_participant_sizes),
        )

    def _build_creation_ledger_entries(self, competition: Competition) -> tuple[CompetitionWalletLedger, ...]:
        entries: list[CompetitionWalletLedger] = []
        if competition.host_creation_fee_minor > 0:
            entries.append(
                CompetitionWalletLedger(
                    competition_id=competition.id,
                    entry_type="host_creation_fee",
                    amount_minor=competition.host_creation_fee_minor,
                    currency=competition.currency,
                    reference_id=competition.host_user_id,
                    payload_json={"reason": "contest_creation"},
                )
            )
        if competition.platform_fee_bps > 0 and competition.gross_pool_minor > 0:
            entries.append(
                CompetitionWalletLedger(
                    competition_id=competition.id,
                    entry_type="platform_fee_projection",
                    amount_minor=competition.gross_pool_minor * competition.platform_fee_bps // 10_000,
                    currency=competition.currency,
                    reference_id=competition.host_user_id,
                    payload_json={
                        "gross_pool_minor": competition.gross_pool_minor,
                        "platform_fee_bps": competition.platform_fee_bps,
                    },
                )
            )
        return tuple(entries)
