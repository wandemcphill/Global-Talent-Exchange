from __future__ import annotations

from dataclasses import dataclass

from app.common.enums.competition_status import CompetitionStatus
from app.config.competition_constants import (
    USER_COMPETITION_MAX_ENTRY_FEE_MINOR,
    USER_COMPETITION_MAX_HOST_CREATION_FEE_MINOR,
    USER_COMPETITION_MAX_PLATFORM_FEE_BPS,
)
from app.models.competition import Competition
from app.schemas.competition_core import CompetitionCreateRequest, CompetitionUpdateRequest
from app.schemas.competition_financials import CompetitionFeeSummary
from app.services.competition_rules_engine import CompetitionRulesEngine, CompetitionRulesError
from app.schemas.competition_rules import CompetitionRuleSetPayload as CompetitionRuleSetPayload


class CompetitionValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass(frozen=True, slots=True)
class CompetitionValidationResult:
    payout_percentages: list[int]
    fee_summary: CompetitionFeeSummary
    min_participants: int
    max_participants: int


class CompetitionValidationService:
    def __init__(self, rules_engine: CompetitionRulesEngine | None = None) -> None:
        self._rules_engine = rules_engine or CompetitionRulesEngine()

    def validate_creation(self, payload: CompetitionCreateRequest) -> CompetitionValidationResult:
        payload = payload.model_copy(
            update={
                "financials": payload.financials.model_copy(
                    update={
                        "entry_fee_minor": 0,
                        "platform_fee_bps": 0,
                        "host_creation_fee_minor": 0,
                    }
                )
            }
        )
        errors: list[str] = []
        try:
            rule_summary = self._rules_engine.validate_rules(payload.rules)
        except CompetitionRulesError as exc:
            errors.extend(exc.errors)
            rule_summary = None

        errors.extend(self._validate_financial_bounds(payload.financials))
        if rule_summary is not None:
            errors.extend(
                self._validate_paid_competition_minimum(
                    entry_fee_minor=payload.financials.entry_fee_minor,
                    min_participants=rule_summary.min_participants,
                )
            )

        payout_percentages: list[int] = []
        fee_summary: CompetitionFeeSummary | None = None
        if not errors and rule_summary is not None:
            try:
                payout_percentages = self._rules_engine.resolve_payout_percentages(payload.financials)
                errors.extend(
                    self._validate_payout_shape(
                        payout_percentages=payout_percentages,
                        max_participants=rule_summary.max_participants,
                    )
                )
                fee_summary = self._rules_engine.compute_fee_summary(
                    payload.financials,
                    max_participants=rule_summary.max_participants,
                )
                errors.extend(
                    self._validate_prize_pool(
                        entry_fee_minor=payload.financials.entry_fee_minor,
                        fee_summary=fee_summary,
                    )
                )
            except CompetitionRulesError as exc:
                errors.extend(exc.errors)

        if errors:
            raise CompetitionValidationError(errors)

        assert fee_summary is not None
        return CompetitionValidationResult(
            payout_percentages=payout_percentages,
            fee_summary=fee_summary,
            min_participants=rule_summary.min_participants,
            max_participants=rule_summary.max_participants,
        )

    def validate_update(
        self,
        *,
        competition: Competition,
        update: CompetitionUpdateRequest,
        has_paid_participants: bool,
    ) -> None:
        if not update.touches_critical_fields():
            return

        errors: list[str] = []
        if has_paid_participants:
            errors.append("paid competitions cannot change core rules or fee settings after the first paid join")
        if CompetitionStatus(competition.status) in self._locked_statuses():
            errors.append("locked competitions cannot change core rules or fee settings")

        if errors:
            raise CompetitionValidationError(errors)

    def _validate_financial_bounds(self, financials) -> list[str]:
        errors: list[str] = []
        if financials.entry_fee_minor > USER_COMPETITION_MAX_ENTRY_FEE_MINOR:
            errors.append("competition entry is free")
        if financials.platform_fee_bps > USER_COMPETITION_MAX_PLATFORM_FEE_BPS:
            errors.append("competition entry cannot include a platform cut")
        if financials.host_creation_fee_minor > USER_COMPETITION_MAX_HOST_CREATION_FEE_MINOR:
            errors.append("competition entry cannot include a host creation fee")
        return errors

    def _validate_paid_competition_minimum(self, *, entry_fee_minor: int, min_participants: int) -> list[str]:
        del entry_fee_minor, min_participants
        return []

    def _validate_payout_shape(self, *, payout_percentages: list[int], max_participants: int) -> list[str]:
        if len(payout_percentages) > max_participants:
            return ["payout configuration cannot exceed the competition capacity"]
        return []

    def _validate_prize_pool(
        self,
        *,
        entry_fee_minor: int,
        fee_summary: CompetitionFeeSummary,
    ) -> list[str]:
        del entry_fee_minor, fee_summary
        return []

    def _locked_statuses(self) -> set[CompetitionStatus]:
        return {
            CompetitionStatus.LOCKED,
            CompetitionStatus.IN_PROGRESS,
            CompetitionStatus.SEEDED,
            CompetitionStatus.LIVE,
            CompetitionStatus.COMPLETED,
            CompetitionStatus.CANCELLED,
            CompetitionStatus.REFUNDED,
            CompetitionStatus.DISPUTED,
        }
