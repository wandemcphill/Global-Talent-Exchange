from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from secrets import token_hex
from typing import Iterable

from fastapi import Depends
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_session
from backend.app.common.enums.competition_format import CompetitionFormat
from backend.app.common.enums.competition_payout_mode import CompetitionPayoutMode
from backend.app.common.enums.competition_start_mode import CompetitionStartMode
from backend.app.common.enums.competition_status import CompetitionStatus
from backend.app.common.enums.competition_visibility import CompetitionVisibility
from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.common.enums.match_status import MatchStatus
from backend.app.config.competition_constants import USER_COMPETITION_MIN_PARTICIPANTS
from backend.app.models.competition import Competition
from backend.app.models.competition_entry import CompetitionEntry
from backend.app.models.competition_invite import CompetitionInvite
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_match_event import CompetitionMatchEvent
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.competition_prize_rule import CompetitionPrizeRule
from backend.app.models.competition_reward_pool import CompetitionRewardPool
from backend.app.models.competition_round import CompetitionRound
from backend.app.models.competition_rule_set import CompetitionRuleSet
from backend.app.models.competition_schedule_job import CompetitionScheduleJob
from backend.app.models.competition_seed_rule import CompetitionSeedRule
from backend.app.models.competition_visibility_rule import CompetitionVisibilityRule
from backend.app.schemas.competition_core import CompetitionCorePayload
from backend.app.schemas.competition_financials import CompetitionFinancialsPayload
from backend.app.schemas.competition_lifecycle import (
    CompetitionAdvanceRequest,
    CompetitionFinalizeRequest,
    CompetitionInviteAcceptRequest,
    CompetitionMatchEventRequest,
    CompetitionMatchResultRequest,
    CompetitionMatchEventView,
    CompetitionRoundView,
    CompetitionScheduleJobRequest,
    CompetitionScheduleJobView,
    CompetitionSchedulePreviewRequest,
    CompetitionSchedulePreviewResponse,
    CompetitionSeedRequest,
    CompetitionStandingView,
    CompetitionMatchView,
    CompetitionStructureRequest,
    CompetitionVisibilityRuleRequest,
)
from backend.app.schemas.competition_requests import (
    CompetitionCreateRequest,
    CompetitionInviteCreateRequest,
    CompetitionJoinRequest,
    CompetitionLeaveRequest,
    CompetitionPublishRequest,
    CompetitionUpdateRequest,
    PayoutRuleRequest,
    validate_format_capacity_for_update,
)
from backend.app.schemas.competition_responses import (
    CompetitionFinancialSummaryView,
    CompetitionFeesView,
    CompetitionInviteView,
    CompetitionInvitesResponse,
    CompetitionListResponse,
    CompetitionSummaryView,
    JoinEligibilityView,
)
from backend.app.schemas.competition_rules import CompetitionRuleSetPayload, CupRuleSetPayload, LeagueRuleSetPayload
from backend.app.services.competition_creation_service import CompetitionCreationService
from backend.app.services.competition_discovery_service import CompetitionDiscoveryFilter, CompetitionDiscoveryService
from backend.app.services.competition_fee_service import CompetitionFeeService
from backend.app.services.competition_invite_service import CompetitionInviteService
from backend.app.services.competition_join_service import CompetitionJoinService, JoinDecision
from backend.app.services.competition_lifecycle_service import CompetitionLifecycleService
from backend.app.services.competition_rules_engine import CompetitionRulesEngine
from backend.app.services.competition_validation_service import CompetitionValidationService
from backend.app.services.competition_visibility_service import CompetitionVisibilityService

_DEFAULT_RULES = (
    "Skill-based, player-versus-player contest with transparent entry fees, disclosed platform service fees, "
    "and a rules-based prize pool. No odds, house-banked outcomes, or prediction markets."
)
_FOUR_PLACES = Decimal("0.0001")


class CompetitionActionError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(slots=True)
class CompetitionOrchestrator:
    session: Session
    invite_service: CompetitionInviteService = field(default_factory=CompetitionInviteService)
    join_service: CompetitionJoinService = field(default_factory=CompetitionJoinService)
    fee_service: CompetitionFeeService = field(default_factory=CompetitionFeeService)
    creation_service: CompetitionCreationService = field(default_factory=CompetitionCreationService)
    rules_engine: CompetitionRulesEngine = field(default_factory=CompetitionRulesEngine)
    validation_service: CompetitionValidationService = field(default_factory=CompetitionValidationService)
    visibility_service: CompetitionVisibilityService = field(default_factory=CompetitionVisibilityService)
    lifecycle_service: CompetitionLifecycleService = field(init=False)

    def __post_init__(self) -> None:
        self.lifecycle_service = CompetitionLifecycleService(self.session)

    def create(self, payload: CompetitionCreateRequest) -> CompetitionSummaryView:
        self._validate_against_thread_a_domain(payload)
        domain_payload = backend_competition_create_request(
            payload,
            default_platform_fee_pct=self.fee_service.default_platform_fee_pct,
        )
        creation = self.creation_service.build_competition(domain_payload)
        competition = creation.competition
        competition.competition_type = payload.competition_type or competition.format
        competition.source_type = payload.source_type
        competition.source_id = payload.source_id
        competition.host_fee_bps = self._pct_to_bps(payload.host_fee_pct)
        if payload.scheduled_start_at:
            competition.scheduled_start_at = payload.scheduled_start_at
        if payload.rules_summary:
            competition.description = payload.rules_summary
        if payload.beginner_friendly is not None:
            competition.metadata_json = {**(competition.metadata_json or {}), "beginner_friendly": payload.beginner_friendly}
        if payload.creator_name:
            competition.metadata_json = {**(competition.metadata_json or {}), "creator_name": payload.creator_name}
        rule_set = creation.rule_set
        if payload.structure:
            self._apply_structure(rule_set, payload.structure)
        prize_rule = creation.prize_rule
        if payload.payout_structure:
            prize_rule.payout_percentages = [int(rule.percent * Decimal("100")) for rule in payload.payout_structure]
            prize_rule.top_n = len(prize_rule.payout_percentages)
            prize_rule.payout_mode = CompetitionPayoutMode.CUSTOM_PERCENT.value
        seed_rule = CompetitionSeedRule(
            competition_id=competition.id,
            seed_method=payload.seed_method or "random",
        )
        visibility_rules = self._build_visibility_rules(competition.id, payload.visibility_rules)

        self.session.add(competition)
        self.session.add(rule_set)
        self.session.add(prize_rule)
        self.session.add(seed_rule)
        if visibility_rules:
            self.session.add_all(visibility_rules)
        if creation.ledger_entries:
            self.session.add_all(creation.ledger_entries)

        pool_amount_minor = self._projected_reward_pool_minor(
            competition=competition,
            rule_set=rule_set,
        )
        reward_pool = CompetitionRewardPool(
            competition_id=competition.id,
            pool_type="entry_fee",
            currency=competition.currency,
            amount_minor=pool_amount_minor,
            status="planned",
            metadata_json={},
        )
        self.session.add(reward_pool)
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition)

    def update(self, competition_id: str, payload: CompetitionUpdateRequest) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        if CompetitionStatus(competition.status) in {
            CompetitionStatus.LOCKED,
            CompetitionStatus.IN_PROGRESS,
            CompetitionStatus.COMPLETED,
            CompetitionStatus.SETTLED,
            CompetitionStatus.CANCELLED,
        }:
            return self._to_summary(competition)

        participant_count = self._participant_count(competition.id)
        if payload.capacity is not None:
            if participant_count > payload.capacity:
                raise CompetitionActionError(
                    "Capacity cannot be reduced below current participant count.",
                    reason="capacity_too_low",
                )
            validate_format_capacity_for_update(CompetitionFormat(competition.format), payload.capacity)

        if payload.name is not None:
            competition.name = payload.name
        if payload.visibility is not None:
            competition.visibility = payload.visibility.value
        if payload.rules_summary is not None:
            competition.description = payload.rules_summary
        if payload.beginner_friendly is not None:
            competition.metadata_json = {**(competition.metadata_json or {}), "beginner_friendly": payload.beginner_friendly}
        if payload.scheduled_start_at is not None:
            competition.scheduled_start_at = payload.scheduled_start_at
        if payload.competition_type is not None:
            competition.competition_type = payload.competition_type

        rule_set = self._rule_set(competition.id)
        if payload.capacity is not None:
            rule_set.max_participants = payload.capacity
        if payload.structure is not None:
            self._apply_structure(rule_set, payload.structure)

        if payload.entry_fee is not None:
            competition.entry_fee_minor = self._to_minor_units(payload.entry_fee)
        if payload.platform_fee_pct is not None:
            competition.platform_fee_bps = self._pct_to_bps(payload.platform_fee_pct)
        if payload.host_fee_pct is not None:
            competition.host_fee_bps = self._pct_to_bps(payload.host_fee_pct)

        self._refresh_financials(competition, rule_set)

        prize_rule = self._prize_rule(competition.id)
        if payload.payout_structure is not None:
            prize_rule.payout_percentages = [int(rule.percent * Decimal("100")) for rule in payload.payout_structure]
            prize_rule.top_n = len(prize_rule.payout_percentages)
            prize_rule.payout_mode = CompetitionPayoutMode.CUSTOM_PERCENT.value

        if payload.seed_method is not None:
            seed_rule = self._seed_rule(competition.id)
            seed_rule.seed_method = payload.seed_method

        if payload.visibility_rules is not None:
            self.session.query(CompetitionVisibilityRule).filter(
                CompetitionVisibilityRule.competition_id == competition.id
            ).delete()
            rules = self._build_visibility_rules(competition.id, payload.visibility_rules)
            if rules:
                self.session.add_all(rules)

        competition.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition)

    def publish(self, competition_id: str, *, open_for_join: bool = True) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        if CompetitionStatus(competition.status) in {CompetitionStatus.LIVE, CompetitionStatus.COMPLETED, CompetitionStatus.SETTLED}:
            return self._to_summary(competition)
        competition.status = CompetitionStatus.OPEN.value
        competition.opened_at = datetime.now(timezone.utc)
        competition.stage = "registration"
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition)

    def get(self, competition_id: str, *, user_id: str | None = None, invite_code: str | None = None) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        return self._to_summary(competition, user_id=user_id, invite_code=invite_code)

    def summary(self, competition_id: str, *, user_id: str | None = None, invite_code: str | None = None) -> CompetitionSummaryView | None:
        return self.get(competition_id, user_id=user_id, invite_code=invite_code)

    def list(
        self,
        *,
        public_only: bool = False,
        format: CompetitionFormat | None = None,
        fee_filter: str | None = None,
        sort: str = "trending",
        creator_id: str | None = None,
        beginner_friendly: bool | None = None,
        filters: CompetitionDiscoveryFilter | None = None,
    ) -> CompetitionListResponse:
        if filters is not None:
            public_only = filters.public_only
            format = filters.format
            fee_filter = filters.fee_filter
            sort = filters.sort
            creator_id = filters.creator_id
            beginner_friendly = filters.beginner_friendly
        stmt = select(Competition)
        if public_only:
            stmt = stmt.where(Competition.visibility == CompetitionVisibility.PUBLIC.value)
        if format is not None:
            stmt = stmt.where(Competition.format == format.value)
        if creator_id is not None:
            stmt = stmt.where(Competition.host_user_id == creator_id)
        competitions = list(self.session.scalars(stmt).all())

        items = [self._to_summary(item) for item in competitions]
        if fee_filter == "free":
            items = [item for item in items if item.entry_fee <= 0]
        elif fee_filter == "paid":
            items = [item for item in items if item.entry_fee > 0]
        if beginner_friendly is not None:
            items = [item for item in items if item.beginner_friendly == beginner_friendly]

        if sort == "new":
            items.sort(key=lambda item: item.created_at, reverse=True)
        elif sort == "prize_pool":
            items.sort(key=lambda item: item.prize_pool, reverse=True)
        elif sort == "fill_rate":
            items.sort(
                key=lambda item: (item.participant_count / max(item.capacity, 1), item.prize_pool, item.updated_at),
                reverse=True,
            )
        else:
            items.sort(
                key=lambda item: (item.participant_count / max(item.capacity, 1), item.prize_pool, item.updated_at),
                reverse=True,
            )

        return CompetitionListResponse(total=len(items), items=tuple(items))
