from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from hashlib import sha256
from secrets import token_hex
from typing import Any, Iterable

from fastapi import Depends, Request
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_payout_mode import CompetitionPayoutMode
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_visibility import CompetitionVisibility
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.match_status import MatchStatus
from app.config.competition_constants import USER_COMPETITION_MIN_PARTICIPANTS
from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.models.competition import Competition
from app.models.competition_entry import CompetitionEntry
from app.models.competition_invite import CompetitionInvite
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_prize_rule import CompetitionPrizeRule
from app.models.competition_reward import CompetitionReward
from app.models.competition_reward_pool import CompetitionRewardPool
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.competition_schedule_job import CompetitionScheduleJob
from app.models.competition_seed_rule import CompetitionSeedRule
from app.models.competition_visibility_rule import CompetitionVisibilityRule
from app.models.club_profile import ClubProfile
from app.schemas.competition_core import (
    CompetitionCorePayload,
    CompetitionCreateRequest as CompetitionCoreCreateRequest,
)
from app.schemas.competition_financials import CompetitionFinancialsPayload
from app.schemas.competition_lifecycle import (
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
from app.schemas.competition_requests import (
    CompetitionCreateRequest,
    CompetitionHostType,
    CompetitionUpdateRequest,
    validate_format_capacity_for_update,
)
from app.schemas.competition_responses import (
    CompetitionFinancialSummaryView,
    CompetitionHistoryEntryView,
    CompetitionFeesView,
    CompetitionProgressionView,
    DynamicPrizePoolView,
    CompetitionInviteView,
    CompetitionInvitesResponse,
    CompetitionListResponse,
    CompetitionRewardView,
    CompetitionRewardsResponse,
    CompetitionSummaryView,
    JoinEligibilityView,
)
from app.schemas.competition_rules import CompetitionRuleSetPayload, CupRuleSetPayload, LeagueRuleSetPayload
from app.services.competition_creation_service import CompetitionCreationService
from app.services.competition_discovery_service import CompetitionDiscoveryFilter
from app.services.competition_fee_service import CompetitionFeeService
from app.services.competition_join_service import CompetitionJoinService, JoinDecision
from app.services.competition_lifecycle_service import CompetitionLifecycleService
from app.services.competition_progression_service import CompetitionProgressionService
from app.services.competition_reminder_service import CompetitionReminderService
from app.services.competition_rules_engine import CompetitionRulesEngine
from app.services.competition_auto_runner import CompetitionAutoRunner
from app.services.competition_validation_service import CompetitionValidationService
from app.services.competition_visibility_service import CompetitionVisibilityService
from app.services.competition_wallet_service import CompetitionWalletService
from app.services.dynamic_prize_pool_service import DynamicPrizePoolListContext, DynamicPrizePoolService
from app.risk_ops_engine.service import RiskOpsService
from app.wallets.service import InsufficientBalanceError

_DEFAULT_RULES = (
    "Skill-based, player-versus-player contest with transparent entry fees, disclosed platform service fees, "
    "and a rules-based prize pool. No odds, house-banked outcomes, or prediction markets."
)
_DISCOVERY_SKIP_REASONS = frozenset({"invalid_summary_state", "rules_missing"})
_TWO_PLACES = Decimal("0.01")
_FOUR_PLACES = Decimal("0.0001")
_DYNAMIC_PRIZE_POOL_UNSET = object()
_PASSCODE_METADATA_KEY = "join_passcode_hash"
_REQUIRES_PASSCODE_METADATA_KEY = "requires_passcode"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class CompetitionActionError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(frozen=True, slots=True)
class _CompetitionSummaryContext:
    creator_id: str
    viewer_user_id: str | None = None
    invite_code: str | None = None
    league_id: str | None = None
    season_id: str | None = None


@dataclass(frozen=True, slots=True)
class _CompetitionListQueryContext:
    participant_counts: dict[str, int]
    rule_sets: dict[str, CompetitionRuleSet]
    prize_rules: dict[str, CompetitionPrizeRule]
    visibility_rules: dict[str, tuple[CompetitionVisibilityRule, ...]]
    dynamic_prize_pool_context: DynamicPrizePoolListContext | None = None


@dataclass(slots=True)
class CompetitionOrchestrator:
    session: Session
    join_service: CompetitionJoinService = field(default_factory=CompetitionJoinService)
    fee_service: CompetitionFeeService = field(default_factory=CompetitionFeeService)
    creation_service: CompetitionCreationService = field(default_factory=CompetitionCreationService)
    rules_engine: CompetitionRulesEngine = field(default_factory=CompetitionRulesEngine)
    validation_service: CompetitionValidationService = field(default_factory=CompetitionValidationService)
    visibility_service: CompetitionVisibilityService = field(default_factory=CompetitionVisibilityService)
    lifecycle_service: CompetitionLifecycleService = field(init=False)
    competition_wallet_service: CompetitionWalletService = field(init=False)
    progression_service: CompetitionProgressionService = field(init=False)
    auto_runner: CompetitionAutoRunner = field(init=False)
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)

    def __post_init__(self) -> None:
        self.lifecycle_service = CompetitionLifecycleService(self.session, event_publisher=self.event_publisher)
        self.competition_wallet_service = CompetitionWalletService(self.session)
        self.progression_service = CompetitionProgressionService(self.session)
        self.auto_runner = CompetitionAutoRunner(self.session)

    def _publish_competition_update(
        self,
        *,
        event_name: str,
        competition: Competition,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.event_publisher.publish(
            DomainEvent(
                name=event_name,
                payload={
                    "competition_id": competition.id,
                    "status": competition.status,
                    "stage": competition.stage,
                    "participant_count": self._participant_count(competition.id),
                    **dict(extra or {}),
                },
                aggregate_id=competition.id,
                aggregate_type="competition",
                partition_key=competition.id,
                producer="competition_orchestrator",
            )
        )

    def _audit_competition_action(
        self,
        *,
        actor_user_id: str | None,
        action_key: str,
        competition: Competition,
        detail: str,
        metadata_json: dict | None = None,
    ) -> None:
        RiskOpsService(self.session).log_audit(
            actor_user_id=actor_user_id,
            action_key=action_key,
            resource_type="competition",
            resource_id=competition.id,
            detail=detail,
            metadata_json={
                "competition_id": competition.id,
                "status": competition.status,
                "format": competition.format,
                "entry_fee_minor": competition.entry_fee_minor,
                "currency": competition.currency,
                **dict(metadata_json or {}),
            },
        )

    @staticmethod
    def _consume_invite(invite: CompetitionInvite) -> None:
        invite.uses += 1
        invite.responded_at = datetime.now(timezone.utc)
        invite.status = "fulfilled" if invite.uses >= invite.max_uses else "accepted"

    def create(self, payload: CompetitionCreateRequest) -> CompetitionSummaryView:
        self._validate_against_thread_a_domain(payload)
        host_type = self._host_type_for_payload(payload)
        if payload.creator_id is None:
            raise CompetitionActionError("Authenticated creator is required.", reason="creator_required")
        if host_type is CompetitionHostType.USER_HOSTED and "gtex" in payload.name.lower():
            raise CompetitionActionError(
                "User-hosted competitions cannot use GTEX in the competition name.",
                reason="reserved_gtex_name",
            )
        payload.source_type = host_type.value
        payload.type = host_type.value
        if host_type is CompetitionHostType.USER_HOSTED:
            payload.currency = "credit"
        is_platform_competition = host_type is CompetitionHostType.GTEX_HOSTED
        domain_payload = backend_competition_create_request(
            payload,
            default_platform_fee_pct=self.fee_service.default_platform_fee_pct,
        )
        if is_platform_competition:
            domain_payload.financials.entry_fee_minor = 0
            domain_payload.financials.platform_fee_bps = 0
            domain_payload.financials.host_creation_fee_minor = 0
            domain_payload.financials.currency = "coin"
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
            competition.metadata_json = {
                **(competition.metadata_json or {}),
                "beginner_friendly": payload.beginner_friendly,
            }
        competition.metadata_json = {
            **(competition.metadata_json or {}),
            "host_type": host_type.value,
            "special_rules": payload.special_rules,
            _REQUIRES_PASSCODE_METADATA_KEY: bool(payload.passcode),
            **({_PASSCODE_METADATA_KEY: self._hash_passcode(payload.passcode)} if payload.passcode else {}),
        }
        if payload.creator_name:
            competition.metadata_json = {**(competition.metadata_json or {}), "creator_name": payload.creator_name}
        if payload.created_at:
            competition.created_at = payload.created_at
            competition.updated_at = payload.created_at
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

        dynamic_prize_pool = self._dynamic_prize_pool(competition, rule_set=rule_set)
        pool_amount_minor = (
            dynamic_prize_pool.total_pool_minor
            if dynamic_prize_pool is not None
            else self._projected_reward_pool_minor(
                competition=competition,
                rule_set=rule_set,
            )
        )
        reward_pool = CompetitionRewardPool(
            competition_id=competition.id,
            pool_type="promo_pool" if is_platform_competition else "entry_fee",
            currency=competition.currency,
            amount_minor=pool_amount_minor,
            status="planned",
            metadata_json=(
                DynamicPrizePoolService(self.session).apply_to_reward_pool(
                    metadata_json={},
                    snapshot=dynamic_prize_pool,
                )
                if dynamic_prize_pool is not None
                else {}
            ),
        )
        self.session.add(reward_pool)
        self._audit_competition_action(
            actor_user_id=competition.host_user_id,
            action_key="competition.created",
            competition=competition,
            detail="Competition created.",
            metadata_json={
                "source_type": competition.source_type,
                "source_id": competition.source_id,
                "reward_pool_type": reward_pool.pool_type,
                "reward_pool_amount_minor": reward_pool.amount_minor,
            },
        )
        self.session.commit()
        self.session.refresh(competition)
        self._publish_competition_update(
            event_name="competition.created",
            competition=competition,
            extra={
                "source_type": competition.source_type,
                "entry_fee_minor": competition.entry_fee_minor,
                "currency": competition.currency,
                "reward_pool_type": reward_pool.pool_type,
            },
        )
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
            competition.metadata_json = {
                **(competition.metadata_json or {}),
                "beginner_friendly": payload.beginner_friendly,
            }
        if payload.scheduled_start_at is not None:
            competition.scheduled_start_at = payload.scheduled_start_at
        if payload.competition_type is not None:
            competition.competition_type = payload.competition_type

        rule_set = self._rule_set(competition.id)
        if payload.capacity is not None:
            rule_set.max_participants = payload.capacity
        if payload.structure is not None:
            self._apply_structure(rule_set, payload.structure)

        is_platform_competition = self._is_platform_competition(competition.source_type)
        if payload.entry_fee is not None and not is_platform_competition:
            competition.entry_fee_minor = self._to_minor_units(payload.entry_fee)
        if payload.platform_fee_pct is not None and not is_platform_competition:
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
        self._audit_competition_action(
            actor_user_id=competition.host_user_id,
            action_key="competition.updated",
            competition=competition,
            detail="Competition updated.",
            metadata_json={
                "capacity": rule_set.max_participants,
                "visibility": competition.visibility,
                "competition_type": competition.competition_type,
            },
        )
        self.session.commit()
        self.session.refresh(competition)
        self._publish_competition_update(
            event_name="competition.updated",
            competition=competition,
        )
        return self._to_summary(competition)

    def publish(self, competition_id: str, *, open_for_join: bool = True) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        if CompetitionStatus(competition.status) in {
            CompetitionStatus.LIVE,
            CompetitionStatus.COMPLETED,
            CompetitionStatus.SETTLED,
        }:
            return self._to_summary(competition)
        competition.status = CompetitionStatus.OPEN.value
        competition.opened_at = datetime.now(timezone.utc)
        competition.stage = "registration"
        self._audit_competition_action(
            actor_user_id=competition.host_user_id,
            action_key="competition.published",
            competition=competition,
            detail="Competition published for registration.",
            metadata_json={"open_for_join": open_for_join},
        )
        self.session.commit()
        self.session.refresh(competition)
        self._publish_competition_update(
            event_name="competition.published",
            competition=competition,
            extra={"open_for_join": open_for_join},
        )
        return self._to_summary(competition)

    def get(
        self, competition_id: str, *, user_id: str | None = None, invite_code: str | None = None
    ) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        return self._to_summary(competition, user_id=user_id, invite_code=invite_code)

    def summary(
        self, competition_id: str, *, user_id: str | None = None, invite_code: str | None = None
    ) -> CompetitionSummaryView | None:
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
        if fee_filter == "free":
            stmt = stmt.where(Competition.entry_fee_minor == 0)
        elif fee_filter == "paid":
            stmt = stmt.where(Competition.entry_fee_minor > 0)
        if sort == "new":
            stmt = stmt.order_by(Competition.created_at.desc())
        competitions = list(self.session.scalars(stmt).all())
        list_context = self._list_query_context(competitions)
        dynamic_prize_pool_service = (
            DynamicPrizePoolService(self.session) if list_context.dynamic_prize_pool_context is not None else None
        )

        items: list[CompetitionSummaryView] = []
        for item in competitions:
            preloaded_rule_set = list_context.rule_sets.get(item.id)
            dynamic_prize_pool = None
            if dynamic_prize_pool_service is not None and preloaded_rule_set is not None:
                snapshot = dynamic_prize_pool_service.snapshot_from_list_context(
                    competition=item,
                    rule_set=preloaded_rule_set,
                    context=list_context.dynamic_prize_pool_context,
                )
                dynamic_prize_pool = snapshot if snapshot.enabled else None
            summary = self._safe_list_summary(
                item,
                participant_count=list_context.participant_counts.get(item.id, 0),
                rule_set=preloaded_rule_set,
                prize_rule=list_context.prize_rules.get(item.id),
                visibility_rules=list_context.visibility_rules.get(item.id, ()),
                dynamic_prize_pool=dynamic_prize_pool,
            )
            if summary is not None:
                items.append(summary)
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

    def join(
        self,
        competition_id: str,
        *,
        user_id: str,
        user_name: str | None,
        invite_code: str | None,
        club_name: str | None = None,
        passcode: str | None = None,
    ) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None

        rule_set = self._rule_set(competition.id)
        club = self._resolve_join_club(competition, user_id=user_id, club_name=club_name)
        participant_key = club.id if club is not None else user_id
        club_identity = self._club_identity_payload(club) if club is not None else {}
        participant = self._participant(competition.id, participant_key)
        participant_count = self._participant_count(competition.id)
        join_decision = self._join_decision_for(
            competition,
            user_id=user_id,
            club_id=participant_key,
            invite_code=invite_code,
            passcode=passcode,
            participant_count=participant_count,
            already_joined=participant is not None,
            visibility_context=club_identity,
        )
        if not join_decision.eligible:
            return self._to_summary(competition, user_id=user_id, invite_code=invite_code)
        if participant is not None:
            return self._to_summary(competition, user_id=user_id, invite_code=invite_code)

        invite_used = None
        if invite_code:
            invite_used = self._resolve_invite(
                competition.id,
                invite_code=invite_code,
                club_id=participant_key,
                consume=False,
            )
            if invite_used is None and join_decision.requires_invite:
                return self._to_summary(competition, user_id=user_id, invite_code=invite_code)

        entry = CompetitionEntry(
            competition_id=competition.id,
            club_id=participant_key,
            user_id=user_id,
            entry_type="invite" if invite_used else "direct",
            status="accepted",
            invite_id=invite_used.id if invite_used else None,
            responded_at=datetime.now(timezone.utc),
            metadata_json={
                **({"user_name": user_name} if user_name else {}),
                **club_identity,
                **({"invite_code": invite_code} if invite_code else {}),
                **({"passcode_verified": True} if passcode and self._passcode_matches(competition, passcode) else {}),
            },
        )
        entry_savepoint = self.session.begin_nested()
        try:
            self.session.add(entry)
            self.session.flush()
        except IntegrityError as exc:
            entry_savepoint.rollback()
            raise CompetitionActionError("User has already joined this competition.", reason="duplicate_entry") from exc
        else:
            entry_savepoint.commit()
        participant = CompetitionParticipant(
            competition_id=competition.id,
            club_id=participant_key,
            entry_id=entry.id,
            status="joined",
            paid_entry_fee_minor=competition.entry_fee_minor,
        )
        participant_savepoint = self.session.begin_nested()
        try:
            self.session.add(participant)
            self.session.flush()
        except IntegrityError as exc:
            participant_savepoint.rollback()
            raise CompetitionActionError("User has already joined this competition.", reason="duplicate_entry") from exc
        else:
            participant_savepoint.commit()
        try:
            fee_result = self.competition_wallet_service.collect_entry_fee(
                competition=competition,
                participant_user_id=user_id,
            )
        except InsufficientBalanceError as exc:
            raise CompetitionActionError(
                "Available balance is lower than the competition entry fee.",
                reason="entry_fee_insufficient_balance",
            ) from exc
        if competition.entry_fee_minor > 0 and fee_result.status != "settled":
            raise CompetitionActionError(
                "Competition entry payment could not be validated.",
                reason="entry_fee_unverified",
            )
        if invite_used is not None:
            self._consume_invite(invite_used)
        entry.metadata_json = {
            **dict(entry.metadata_json or {}),
            "entry_fee_status": fee_result.status,
            "entry_fee_transaction_id": fee_result.transaction_id,
            "entry_fee_reason": fee_result.reason,
        }
        participant.paid_at = datetime.now(timezone.utc) if fee_result.status == "settled" else None
        self._audit_competition_action(
            actor_user_id=user_id,
            action_key="competition.joined",
            competition=competition,
            detail="Competition join completed.",
            metadata_json={
                "participant_user_id": user_id,
                **club_identity,
                "entry_id": entry.id,
                "participant_id": participant.id,
                "entry_type": entry.entry_type,
                "invite_id": invite_used.id if invite_used is not None else None,
                "entry_fee_status": fee_result.status,
                "entry_fee_transaction_id": fee_result.transaction_id,
            },
        )
        self._refresh_financials(competition, rule_set, participant_count=participant_count + 1)
        CompetitionReminderService(self.session).dispatch_due_reminders()
        self.session.commit()
        self.session.refresh(competition)
        self.auto_runner.run_until_idle(competition)
        self.session.commit()
        self.session.refresh(competition)
        self._publish_competition_update(
            event_name="competition.joined",
            competition=competition,
            extra={"user_id": user_id, **club_identity},
        )
        return self._to_summary(competition, user_id=user_id, invite_code=invite_code)

    def leave(self, competition_id: str, *, user_id: str) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        rule_set = self._rule_set(competition.id)
        participant = self._participant_for_user(competition, user_id=user_id)
        if participant is None:
            return self._to_summary(competition, user_id=user_id)
        if CompetitionStatus(competition.status) in {
            CompetitionStatus.SEEDED,
            CompetitionStatus.LIVE,
            CompetitionStatus.COMPLETED,
            CompetitionStatus.SETTLED,
        }:
            raise CompetitionActionError(
                "Competition entries can no longer be withdrawn after the bracket locks.",
                reason="competition_locked",
            )
        entry = self.session.get(CompetitionEntry, participant.entry_id) if participant.entry_id else None
        if entry is not None:
            if (entry.metadata_json or {}).get("entry_fee_status") == "settled":
                try:
                    refund_result = self.competition_wallet_service.refund_entry_fee(
                        competition=competition,
                        participant_user_id=user_id,
                        amount_minor=participant.paid_entry_fee_minor,
                    )
                except InsufficientBalanceError as exc:
                    raise CompetitionActionError(
                        "Competition escrow balance is lower than the refundable entry fee.",
                        reason="entry_fee_refund_unavailable",
                    ) from exc
                entry.metadata_json = {
                    **dict(entry.metadata_json or {}),
                    "entry_fee_refund_status": refund_result.status,
                    "entry_fee_refund_transaction_id": refund_result.transaction_id,
                    "entry_fee_refund_reason": refund_result.reason,
                }
            entry.status = "withdrawn"
            entry.responded_at = datetime.now(timezone.utc)
        self.session.delete(participant)
        participant_count = max(0, self._participant_count(competition.id) - 1)
        self._refresh_financials(competition, rule_set, participant_count=participant_count)
        self._audit_competition_action(
            actor_user_id=user_id,
            action_key="competition.left",
            competition=competition,
            detail="Competition entry withdrawn.",
            metadata_json={
                "participant_user_id": user_id,
                "entry_id": entry.id if entry is not None else None,
                "participant_id": participant.id,
                "refund_status": (
                    (entry.metadata_json or {}).get("entry_fee_refund_status") if entry is not None else None
                ),
                "refund_transaction_id": (
                    (entry.metadata_json or {}).get("entry_fee_refund_transaction_id") if entry is not None else None
                ),
            },
        )
        self.session.commit()
        self.session.refresh(competition)
        self._publish_competition_update(
            event_name="competition.left",
            competition=competition,
            extra={"user_id": user_id},
        )
        return self._to_summary(competition, user_id=user_id)

    def create_invite(
        self,
        competition_id: str,
        *,
        issued_by: str,
        max_uses: int,
        expires_at: datetime | None,
        note: str | None,
    ) -> CompetitionInviteView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        if competition.host_user_id != issued_by:
            raise CompetitionActionError("Only the competition creator can issue invites.", reason="invite_forbidden")
        invite_code = self._generate_invite_code()
        invite = CompetitionInvite(
            competition_id=competition_id,
            invited_by_user_id=issued_by,
            invite_code=invite_code,
            max_uses=max_uses,
            expires_at=expires_at,
            status="pending",
            metadata_json={"note": note} if note else {},
        )
        self.session.add(invite)
        self._audit_competition_action(
            actor_user_id=issued_by,
            action_key="competition.invite.created",
            competition=competition,
            detail="Competition invite created.",
            metadata_json={
                "invite_code": invite.invite_code,
                "invite_id": invite.id,
                "max_uses": invite.max_uses,
                "expires_at": invite.expires_at.isoformat() if invite.expires_at is not None else None,
            },
        )
        self.session.commit()
        self.session.refresh(invite)
        return self._invite_view(invite)

    def list_invites(self, competition_id: str) -> CompetitionInvitesResponse | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        invites = list(
            self.session.scalars(
                select(CompetitionInvite)
                .where(CompetitionInvite.competition_id == competition_id)
                .order_by(CompetitionInvite.created_at.desc())
            ).all()
        )
        return CompetitionInvitesResponse(
            competition_id=competition_id, invites=tuple(self._invite_view(item) for item in invites)
        )

    def accept_invite(
        self,
        competition_id: str,
        payload: CompetitionInviteAcceptRequest,
        *,
        actor_user_id: str | None = None,
    ) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        rule_set = self._rule_set(competition.id)
        resolved_user_id = actor_user_id or payload.user_id
        if resolved_user_id is None:
            raise CompetitionActionError("Authenticated user is required.", reason="user_required")
        club = self._resolve_join_club(competition, user_id=resolved_user_id, club_name=payload.club_name)
        club_id = club.id if club is not None else self._normalized_string(payload.club_id)
        if not club_id:
            raise CompetitionActionError("A club is required to accept this competition invite.", reason="club_required")
        if payload.club_id and club is not None and payload.club_id != club.id:
            raise CompetitionActionError("Invite club does not belong to the authenticated user.", reason="club_owner_required")
        club_identity = self._club_identity_payload(club) if club is not None else {}
        participant_count = self._participant_count(competition.id)
        participant = self._participant(competition.id, club_id)
        if participant is not None:
            return self._to_summary(competition, user_id=resolved_user_id, invite_code=payload.invite_code)
        invite = self._resolve_invite(
            competition.id,
            invite_code=payload.invite_code,
            invite_id=payload.invite_id,
            club_id=club_id,
            consume=False,
        )
        if invite is None:
            raise CompetitionActionError("Invite is invalid or expired.", reason="invite_invalid")
        entry = CompetitionEntry(
            competition_id=competition.id,
            club_id=club_id,
            user_id=resolved_user_id,
            entry_type="invite",
            status="accepted",
            invite_id=invite.id,
            responded_at=datetime.now(timezone.utc),
            metadata_json={"invite_code": invite.invite_code, **club_identity},
        )
        entry_savepoint = self.session.begin_nested()
        try:
            self.session.add(entry)
            self.session.flush()
        except IntegrityError as exc:
            entry_savepoint.rollback()
            raise CompetitionActionError("User has already joined this competition.", reason="duplicate_entry") from exc
        else:
            entry_savepoint.commit()
        participant = CompetitionParticipant(
            competition_id=competition.id,
            club_id=club_id,
            entry_id=entry.id,
            status="joined",
            paid_entry_fee_minor=competition.entry_fee_minor,
        )
        participant_savepoint = self.session.begin_nested()
        try:
            self.session.add(participant)
            self.session.flush()
        except IntegrityError as exc:
            participant_savepoint.rollback()
            raise CompetitionActionError("User has already joined this competition.", reason="duplicate_entry") from exc
        else:
            participant_savepoint.commit()
        try:
            fee_result = self.competition_wallet_service.collect_entry_fee(
                competition=competition,
                participant_user_id=resolved_user_id,
            )
        except InsufficientBalanceError as exc:
            raise CompetitionActionError(
                "Available balance is lower than the competition entry fee.",
                reason="entry_fee_insufficient_balance",
            ) from exc
        if competition.entry_fee_minor > 0 and fee_result.status != "settled":
            raise CompetitionActionError(
                "Competition entry payment could not be validated.",
                reason="entry_fee_unverified",
            )
        self._consume_invite(invite)
        entry.metadata_json = {
            **dict(entry.metadata_json or {}),
            "entry_fee_status": fee_result.status,
            "entry_fee_transaction_id": fee_result.transaction_id,
            "entry_fee_reason": fee_result.reason,
        }
        participant.paid_at = datetime.now(timezone.utc) if fee_result.status == "settled" else None
        self._audit_competition_action(
            actor_user_id=resolved_user_id,
            action_key="competition.invite.accepted",
            competition=competition,
            detail="Competition invite accepted.",
            metadata_json={
                "participant_user_id": resolved_user_id,
                "club_id": club_id,
                **club_identity,
                "entry_id": entry.id,
                "participant_id": participant.id,
                "invite_id": invite.id,
                "invite_code": invite.invite_code,
                "entry_fee_status": fee_result.status,
                "entry_fee_transaction_id": fee_result.transaction_id,
            },
        )
        self._refresh_financials(competition, rule_set, participant_count=participant_count + 1)
        self.session.commit()
        self.session.refresh(competition)
        self.auto_runner.run_until_idle(competition)
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition, user_id=resolved_user_id, invite_code=invite.invite_code)

    def financials(self, competition_id: str) -> CompetitionFinancialSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        participant_count = self._participant_count(competition.id)
        rule_set = self._rule_set(competition.id)
        fees = self._fees_for(competition, participant_count=participant_count)
        dynamic_prize_pool = self._dynamic_prize_pool(competition, rule_set=rule_set)
        prize_pool = dynamic_prize_pool.total_pool if dynamic_prize_pool is not None else fees.prize_pool
        payout_structure = self._payout_breakdown(
            competition=competition,
            prize_pool=prize_pool,
        )
        return CompetitionFinancialSummaryView(
            competition_id=competition.id,
            participant_count=participant_count,
            entry_fee=fees.entry_fee,
            gross_pool=(fees.entry_fee * Decimal(participant_count)).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP),
            platform_fee_pct=fees.platform_fee_pct,
            platform_fee_amount=fees.platform_fee_amount,
            host_fee_pct=fees.host_fee_pct,
            host_fee_amount=fees.host_fee_amount,
            prize_pool=prize_pool,
            payout_structure=payout_structure,
            dynamic_prize_pool=self._dynamic_prize_pool_view(dynamic_prize_pool),
            currency=competition.currency,
        )

    def rewards(self, competition_id: str) -> CompetitionRewardsResponse | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        rewards = list(
            self.session.scalars(
                select(CompetitionReward)
                .where(CompetitionReward.competition_id == competition_id)
                .order_by(CompetitionReward.placement.asc(), CompetitionReward.created_at.asc())
            ).all()
        )
        return CompetitionRewardsResponse(
            competition_id=competition_id,
            rewards=tuple(self._reward_view(item) for item in rewards),
        )

    def progression(self, subject_id: str) -> CompetitionProgressionView | None:
        profile = self.progression_service.profile_for_subject(subject_id)
        if profile is None:
            return None
        history = self.progression_service.history_for_subject(subject_id)
        return CompetitionProgressionView(
            subject_id=profile.subject_id,
            resolved_user_id=profile.resolved_user_id,
            display_name=profile.display_name,
            current_title=profile.current_title or "Rising Challenger",
            ranking_points=profile.ranking_points,
            total_wins=profile.total_wins,
            total_championships=profile.total_championships,
            total_podiums=profile.total_podiums,
            total_competitions=profile.total_competitions,
            total_earnings=self.progression_service.minor_to_decimal(profile.total_earnings_minor),
            best_placement=profile.best_placement,
            badges=tuple(profile.badges_json or []),
            titles=tuple(profile.titles_json or []),
            history=tuple(self._history_view(item) for item in history),
        )

    def rounds(self, competition_id: str) -> tuple[CompetitionRoundView, ...] | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        rounds = list(
            self.session.scalars(
                select(CompetitionRound)
                .where(CompetitionRound.competition_id == competition_id)
                .order_by(CompetitionRound.stage, CompetitionRound.group_key, CompetitionRound.round_number)
            ).all()
        )
        return tuple(self._round_view(item) for item in rounds)

    def fixtures(self, competition_id: str) -> tuple[CompetitionMatchView, ...] | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        matches = list(
            self.session.scalars(
                select(CompetitionMatch)
                .where(CompetitionMatch.competition_id == competition_id)
                .order_by(CompetitionMatch.match_date, CompetitionMatch.round_number, CompetitionMatch.slot_sequence)
            ).all()
        )
        return tuple(self._match_view(match) for match in matches)

    def standings(
        self, competition_id: str, *, group_key: str | None = None
    ) -> tuple[CompetitionStandingView, ...] | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        rule_set = self._rule_set(competition.id)
        standings = self.lifecycle_service.match_service.standings(
            competition_id=competition.id,
            rule_set=rule_set,
            group_key=group_key,
        )
        history_map = self.progression_service.history_map_for_competition(competition.id)
        profile_map = self.progression_service.profile_map(participant.club_id for participant in standings)
        views: list[CompetitionStandingView] = []
        for index, participant in enumerate(standings, start=1):
            history = history_map.get(participant.club_id)
            profile = profile_map.get(participant.club_id)
            views.append(
                CompetitionStandingView(
                    club_id=participant.club_id,
                    seed=participant.seed,
                    group_key=participant.group_key,
                    played=participant.played,
                    wins=participant.wins,
                    draws=participant.draws,
                    losses=participant.losses,
                    goals_for=participant.goals_for,
                    goals_against=participant.goals_against,
                    goal_diff=participant.goal_diff,
                    points=participant.points,
                    rank=index,
                    reward_amount=(
                        self.progression_service.minor_to_decimal(history.earnings_minor)
                        if history is not None
                        else Decimal("0.0000")
                    ),
                    reward_currency=history.currency if history is not None else None,
                    reward_status=history.reward_status if history is not None else None,
                    badge_code=history.badge_code if history is not None else None,
                    title_awarded=history.title_awarded if history is not None else None,
                    ranking_points_delta=history.ranking_points_delta if history is not None else 0,
                    career_title=profile.current_title if profile is not None else None,
                    career_ranking_points=profile.ranking_points if profile is not None else 0,
                    career_total_wins=profile.total_wins if profile is not None else 0,
                    career_total_earnings=(
                        self.progression_service.minor_to_decimal(profile.total_earnings_minor)
                        if profile is not None
                        else Decimal("0.0000")
                    ),
                )
            )
        return tuple(views)

    def seed_competition(self, competition_id: str, payload: CompetitionSeedRequest) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        if CompetitionStatus(competition.status) in {
            CompetitionStatus.LIVE,
            CompetitionStatus.COMPLETED,
            CompetitionStatus.SETTLED,
        }:
            return self._to_summary(competition)
        seed_rule = self._seed_rule(competition.id)
        if payload.seed_method is not None:
            seed_rule.seed_method = payload.seed_method
        self.lifecycle_service.seed_competition(competition, manual_seed_order=payload.manual_seed_order)
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition)

    def launch_competition(self, competition_id: str) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        if CompetitionStatus(competition.status) in {
            CompetitionStatus.LIVE,
            CompetitionStatus.COMPLETED,
            CompetitionStatus.SETTLED,
        }:
            return self._to_summary(competition)
        try:
            self.lifecycle_service.launch_competition(competition)
            self.auto_runner.run_until_idle(competition)
        except ValueError as exc:
            raise CompetitionActionError(str(exc), reason="competition_launch_blocked") from exc
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition)

    def advance_competition(
        self, competition_id: str, payload: CompetitionAdvanceRequest
    ) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        if CompetitionStatus(competition.status) not in {CompetitionStatus.LIVE, CompetitionStatus.SEEDED}:
            return self._to_summary(competition)
        self.lifecycle_service.advance_competition(competition, force=payload.force)
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition)

    def finalize_competition(
        self, competition_id: str, payload: CompetitionFinalizeRequest
    ) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        try:
            self.lifecycle_service.finalize_competition(competition, settle=payload.settle)
        except ValueError as exc:
            raise CompetitionActionError(str(exc), reason="competition_finalize_blocked") from exc
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition)

    def schedule_preview(
        self,
        competition_id: str,
        payload: CompetitionSchedulePreviewRequest,
    ) -> CompetitionSchedulePreviewResponse | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        rule_set = self._rule_set(competition.id)
        participant_count = max(self._participant_count(competition.id), rule_set.min_participants)
        start_date = payload.start_date or (competition.scheduled_start_at or datetime.now(timezone.utc)).date()
        preview = self.lifecycle_service.schedule_service.preview(
            competition=competition,
            rule_set=rule_set,
            participant_count=participant_count,
            start_date=start_date,
            requested_dates=payload.requested_dates,
            priority=payload.priority,
            requires_exclusive_windows=payload.requires_exclusive_windows,
            alignment_group=payload.alignment_group,
        )
        round_count, match_count = self._schedule_counts(competition, rule_set, participant_count)
        return CompetitionSchedulePreviewResponse(
            competition_id=competition.id,
            round_count=round_count,
            match_count=match_count,
            requested_dates=preview.requested_dates,
            assigned_dates=preview.assigned_dates,
            schedule_plan=preview.plan,
            warnings=preview.warnings,
        )

    def create_schedule_job(
        self,
        competition_id: str,
        payload: CompetitionScheduleJobRequest,
    ) -> CompetitionScheduleJobView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        rule_set = self._rule_set(competition.id)
        participant_count = max(self._participant_count(competition.id), rule_set.min_participants)
        start_date = payload.start_date or (competition.scheduled_start_at or datetime.now(timezone.utc)).date()
        job = self.lifecycle_service.schedule_service.create_job(
            competition=competition,
            rule_set=rule_set,
            participant_count=participant_count,
            start_date=start_date,
            requested_dates=payload.requested_dates,
            priority=payload.priority,
            requires_exclusive_windows=payload.requires_exclusive_windows,
            alignment_group=payload.alignment_group,
            preview_only=payload.preview_only,
            created_by_user_id=payload.created_by_user_id,
        )
        self.session.commit()
        self.session.refresh(job)
        return self._schedule_job_view(job)

    def schedule_job_status(
        self, competition_id: str, *, job_id: str | None = None
    ) -> CompetitionScheduleJobView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        stmt = select(CompetitionScheduleJob).where(CompetitionScheduleJob.competition_id == competition_id)
        if job_id:
            stmt = stmt.where(CompetitionScheduleJob.id == job_id)
        job = self.session.scalar(stmt.order_by(CompetitionScheduleJob.created_at.desc()))
        if job is None:
            return None
        return self._schedule_job_view(job)

    def record_match_event(
        self,
        competition_id: str,
        match_id: str,
        payload: CompetitionMatchEventRequest,
    ) -> CompetitionMatchEventView | None:
        match = self._match(competition_id, match_id)
        if match is None:
            return None
        event = self.lifecycle_service.record_match_event(
            match=match,
            event_type=payload.event_type,
            minute=payload.minute,
            added_time=payload.added_time,
            club_id=payload.club_id,
            player_id=payload.player_id,
            secondary_player_id=payload.secondary_player_id,
            card_type=payload.card_type,
            highlight=payload.highlight,
            metadata_json=payload.metadata_json,
        )
        self.session.commit()
        return self._event_view(event)

    def list_match_events(self, competition_id: str, match_id: str) -> tuple[CompetitionMatchEventView, ...] | None:
        match = self._match(competition_id, match_id)
        if match is None:
            return None
        events = list(
            self.session.scalars(
                select(CompetitionMatchEvent)
                .where(
                    CompetitionMatchEvent.competition_id == competition_id,
                    CompetitionMatchEvent.match_id == match_id,
                )
                .order_by(CompetitionMatchEvent.created_at)
            ).all()
        )
        return tuple(self._event_view(item) for item in events)

    def complete_match(
        self,
        competition_id: str,
        match_id: str,
        payload: CompetitionMatchResultRequest,
    ) -> CompetitionMatchView | None:
        match = self._match(competition_id, match_id)
        if match is None:
            return None
        updated = self.lifecycle_service.complete_match(
            match=match,
            home_score=payload.home_score,
            away_score=payload.away_score,
            decided_by_penalties=payload.decided_by_penalties,
            winner_club_id=payload.winner_club_id,
        )
        self.session.commit()
        return self._match_view(updated)

    def _fees_for(self, competition: Competition, *, participant_count: int) -> CompetitionFeesView:
        entry_fee = self._to_decimal(competition.entry_fee_minor)
        platform_fee_pct = self._from_bps(competition.platform_fee_bps)
        host_fee_pct = self._from_bps(competition.host_fee_bps)
        return self.fee_service.resolve_fees(
            entry_fee=entry_fee,
            participant_count=participant_count,
            platform_fee_pct=platform_fee_pct,
            host_fee_pct=host_fee_pct,
        )

    def _to_summary(
        self,
        competition: Competition,
        *,
        user_id: str | None = None,
        invite_code: str | None = None,
        participant_count: int | None = None,
        rule_set: CompetitionRuleSet | None = None,
        prize_rule: CompetitionPrizeRule | None = None,
        visibility_rules: Iterable[CompetitionVisibilityRule] | None = None,
        dynamic_prize_pool: object = _DYNAMIC_PRIZE_POOL_UNSET,
    ) -> CompetitionSummaryView:
        participant_count = (
            participant_count if participant_count is not None else self._participant_count(competition.id)
        )
        rule_set = rule_set or self._rule_set(competition.id)
        fees = self._fees_for(competition, participant_count=participant_count)
        resolved_dynamic_prize_pool = (
            self._dynamic_prize_pool(competition, rule_set=rule_set)
            if dynamic_prize_pool is _DYNAMIC_PRIZE_POOL_UNSET
            else dynamic_prize_pool
        )
        prize_pool = (
            resolved_dynamic_prize_pool.total_pool if resolved_dynamic_prize_pool is not None else fees.prize_pool
        )
        payout_structure = self._payout_breakdown(
            competition=competition,
            prize_pool=prize_pool,
            prize_rule=prize_rule,
        )
        metadata = self._summary_metadata(competition)
        context = self._summary_context(
            competition,
            metadata=metadata,
            user_id=user_id,
            invite_code=invite_code,
        )
        capacity = self._summary_capacity(rule_set)
        join_decision = self._join_decision_for(
            competition,
            user_id=context.viewer_user_id,
            invite_code=context.invite_code,
            participant_count=participant_count,
            rule_set=rule_set,
            visibility_rules=visibility_rules,
        )
        host_type = self._host_type_for_competition(competition)
        return CompetitionSummaryView(
            id=competition.id,
            name=competition.name,
            format=self._coerce_enum(CompetitionFormat, competition.format, field_name="format"),
            visibility=self._coerce_enum(CompetitionVisibility, competition.visibility, field_name="visibility"),
            status=self._coerce_enum(CompetitionStatus, competition.status, field_name="status"),
            match_type=self._match_type_for(competition),
            type=self._match_type_for(competition),
            host_type=host_type.value,
            creator_id=context.creator_id,
            creator_name=metadata.get("creator_name"),
            participant_count=participant_count,
            capacity=capacity,
            currency=self._normalized_string(competition.currency) or "credit",
            entry_fee=fees.entry_fee,
            platform_fee_pct=fees.platform_fee_pct,
            host_fee_pct=fees.host_fee_pct,
            platform_fee_amount=fees.platform_fee_amount,
            host_fee_amount=fees.host_fee_amount,
            prize_pool=prize_pool,
            payout_structure=payout_structure,
            rules_summary=competition.description or _DEFAULT_RULES,
            join_eligibility=JoinEligibilityView(
                eligible=join_decision.eligible,
                reason=join_decision.reason,
                requires_invite=join_decision.requires_invite,
                requires_passcode=join_decision.requires_passcode or self._requires_passcode(competition),
            ),
            dynamic_prize_pool=self._dynamic_prize_pool_view(resolved_dynamic_prize_pool),
            beginner_friendly=metadata.get("beginner_friendly"),
            requires_passcode=self._requires_passcode(competition),
            scheduled_start_at=competition.scheduled_start_at,
            special_rules=self._normalized_string(metadata.get("special_rules")),
            created_at=competition.created_at,
            updated_at=competition.updated_at,
        )

    def _safe_list_summary(
        self,
        competition: Competition,
        *,
        participant_count: int | None = None,
        rule_set: CompetitionRuleSet | None = None,
        prize_rule: CompetitionPrizeRule | None = None,
        visibility_rules: Iterable[CompetitionVisibilityRule] | None = None,
        dynamic_prize_pool: object = _DYNAMIC_PRIZE_POOL_UNSET,
    ) -> CompetitionSummaryView | None:
        try:
            return self._to_summary(
                competition,
                participant_count=participant_count,
                rule_set=rule_set,
                prize_rule=prize_rule,
                visibility_rules=visibility_rules,
                dynamic_prize_pool=dynamic_prize_pool,
            )
        except CompetitionActionError as exc:
            if exc.reason in _DISCOVERY_SKIP_REASONS:
                return None
            raise
        except ValidationError:
            return None

    def _dynamic_prize_pool(
        self,
        competition: Competition,
        *,
        rule_set: CompetitionRuleSet,
    ):
        snapshot = DynamicPrizePoolService(self.session).snapshot(
            competition=competition,
            rule_set=rule_set,
            exclude_competition_id=competition.id,
        )
        return snapshot if snapshot.enabled else None

    def _dynamic_prize_pool_view(self, snapshot) -> DynamicPrizePoolView | None:
        if snapshot is None:
            return None
        return DynamicPrizePoolView(
            enabled=snapshot.enabled,
            base_funding=snapshot.base_funding,
            activity_boost=snapshot.activity_boost,
            jackpot_rollover=snapshot.jackpot_rollover,
            total_pool=snapshot.total_pool,
            active_users_5min=snapshot.active_users_5min,
            trade_volume_5min=snapshot.trade_volume_5min,
        )

    def _payout_breakdown(
        self,
        *,
        competition: Competition,
        prize_pool: Decimal,
        prize_rule: CompetitionPrizeRule | None = None,
    ) -> tuple:
        prize_rule = prize_rule or self._prize_rule(competition.id)
        payouts = [
            (index + 1, (Decimal(percent) / Decimal("100")).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP))
            for index, percent in enumerate(prize_rule.payout_percentages or [])
        ]
        if not payouts:
            return ()
        return self.fee_service.build_payouts(prize_pool=prize_pool, payout_structure=tuple(payouts))

    def _participant_count(self, competition_id: str) -> int:
        return int(
            self.session.scalar(select(func.count()).where(CompetitionParticipant.competition_id == competition_id))
            or 0
        )

    def _participant(self, competition_id: str, club_id: str) -> CompetitionParticipant | None:
        return self.session.scalar(
            select(CompetitionParticipant).where(
                CompetitionParticipant.competition_id == competition_id,
                CompetitionParticipant.club_id == club_id,
            )
        )

    def _match(self, competition_id: str, match_id: str) -> CompetitionMatch | None:
        match = self.session.get(CompetitionMatch, match_id)
        if match is None or match.competition_id != competition_id:
            return None
        return match

    def _round_view(self, round_entry: CompetitionRound) -> CompetitionRoundView:
        return CompetitionRoundView(
            id=round_entry.id,
            competition_id=round_entry.competition_id,
            round_number=round_entry.round_number,
            stage=round_entry.stage,
            group_key=round_entry.group_key,
            name=round_entry.name,
            status=round_entry.status,
            starts_at=round_entry.starts_at,
            ends_at=round_entry.ends_at,
        )

    def _match_view(self, match: CompetitionMatch) -> CompetitionMatchView:
        return CompetitionMatchView(
            id=match.id,
            competition_id=match.competition_id,
            round_id=match.round_id,
            round_number=match.round_number,
            stage=match.stage,
            group_key=match.group_key,
            home_club_id=match.home_club_id,
            away_club_id=match.away_club_id,
            scheduled_at=match.scheduled_at,
            match_date=match.match_date,
            window=FixtureWindow(match.window) if match.window else None,
            slot_sequence=match.slot_sequence,
            status=MatchStatus(match.status),
            home_score=match.home_score,
            away_score=match.away_score,
            winner_club_id=match.winner_club_id,
            decided_by_penalties=match.decided_by_penalties,
            requires_winner=match.requires_winner,
        )

    def _event_view(self, event: CompetitionMatchEvent) -> CompetitionMatchEventView:
        return CompetitionMatchEventView(
            id=event.id,
            match_id=event.match_id,
            event_type=event.event_type,
            minute=event.minute,
            added_time=event.added_time,
            club_id=event.club_id,
            player_id=event.player_id,
            secondary_player_id=event.secondary_player_id,
            card_type=event.card_type,
            highlight=event.highlight,
            created_at=event.created_at,
            metadata_json=event.metadata_json or {},
        )

    def _reward_view(self, reward: CompetitionReward) -> CompetitionRewardView:
        metadata = dict(reward.metadata_json or {})
        display_name = metadata.get("display_name")
        return CompetitionRewardView(
            reward_id=reward.id,
            subject_id=metadata.get("subject_id") or reward.club_id or reward.participant_id or reward.id,
            resolved_user_id=metadata.get("resolved_user_id"),
            display_name=display_name if isinstance(display_name, str) else None,
            placement=reward.placement,
            amount=self._to_decimal(reward.amount_minor),
            currency=reward.currency,
            status=reward.status,
            ledger_transaction_id=reward.ledger_transaction_id,
            badge_code=metadata.get("badge_code") if isinstance(metadata.get("badge_code"), str) else None,
            title_awarded=metadata.get("title_awarded") if isinstance(metadata.get("title_awarded"), str) else None,
            ranking_points_delta=int(metadata.get("ranking_points_delta") or 0),
        )

    def _history_view(self, entry) -> CompetitionHistoryEntryView:
        return CompetitionHistoryEntryView(
            competition_id=entry.competition_id,
            competition_name=entry.competition_name,
            placement=entry.placement,
            played=entry.played,
            wins=entry.wins,
            draws=entry.draws,
            losses=entry.losses,
            points=entry.points,
            earnings=self.progression_service.minor_to_decimal(entry.earnings_minor),
            currency=entry.currency,
            reward_status=entry.reward_status,
            ledger_transaction_id=entry.ledger_transaction_id,
            badge_code=entry.badge_code,
            title_awarded=entry.title_awarded,
            ranking_points_delta=entry.ranking_points_delta,
            completed_at=entry.completed_at,
        )

    def _schedule_job_view(self, job: CompetitionScheduleJob) -> CompetitionScheduleJobView:
        return CompetitionScheduleJobView(
            id=job.id,
            competition_id=job.competition_id,
            status=job.status,
            requested_dates=tuple(date.fromisoformat(item) for item in job.requested_dates_json),
            assigned_dates=tuple(date.fromisoformat(item) for item in job.assigned_dates_json),
            created_at=job.created_at,
            error_message=job.error_message,
        )

    def _rule_set(self, competition_id: str) -> CompetitionRuleSet:
        rule_set = self.session.scalar(
            select(CompetitionRuleSet).where(CompetitionRuleSet.competition_id == competition_id)
        )
        if rule_set is None:
            raise CompetitionActionError("Competition rules are missing.", reason="rules_missing")
        return rule_set

    def _prize_rule(self, competition_id: str) -> CompetitionPrizeRule:
        prize_rule = self.session.scalar(
            select(CompetitionPrizeRule).where(CompetitionPrizeRule.competition_id == competition_id)
        )
        if prize_rule is None:
            raise CompetitionActionError("Competition prize rules are missing.", reason="rules_missing")
        return prize_rule

    def _seed_rule(self, competition_id: str) -> CompetitionSeedRule:
        seed_rule = self.session.scalar(
            select(CompetitionSeedRule).where(CompetitionSeedRule.competition_id == competition_id)
        )
        if seed_rule is None:
            seed_rule = CompetitionSeedRule(competition_id=competition_id)
            self.session.add(seed_rule)
            self.session.flush()
        return seed_rule

    def _apply_structure(self, rule_set: CompetitionRuleSet, payload: CompetitionStructureRequest) -> None:
        if payload.group_stage_enabled is not None:
            rule_set.group_stage_enabled = payload.group_stage_enabled
        if payload.group_count is not None:
            rule_set.group_count = payload.group_count
        if payload.group_size is not None:
            rule_set.group_size = payload.group_size
        if payload.group_advance_count is not None:
            rule_set.group_advance_count = payload.group_advance_count
        if payload.knockout_bracket_size is not None:
            rule_set.knockout_bracket_size = payload.knockout_bracket_size

    def _build_visibility_rules(
        self,
        competition_id: str,
        rules: Iterable[CompetitionVisibilityRuleRequest] | None,
    ) -> list[CompetitionVisibilityRule]:
        if not rules:
            return []
        built: list[CompetitionVisibilityRule] = []
        for rule in rules:
            built.append(
                CompetitionVisibilityRule(
                    competition_id=competition_id,
                    rule_type=rule.rule_type,
                    rule_payload=rule.rule_payload,
                    priority=rule.priority,
                    enabled=rule.enabled,
                )
            )
        return built

    def _join_decision_for(
        self,
        competition: Competition,
        *,
        user_id: str | None = None,
        club_id: str | None = None,
        invite_code: str | None = None,
        passcode: str | None = None,
        participant_count: int | None = None,
        already_joined: bool | None = None,
        rule_set: CompetitionRuleSet | None = None,
        visibility_rules: Iterable[CompetitionVisibilityRule] | None = None,
        visibility_context: dict[str, Any] | None = None,
    ) -> JoinDecision:
        rule_set = rule_set or self._rule_set(competition.id)
        user_id = self._normalized_string(user_id)
        club_id = self._normalized_string(club_id)
        invite_code = self._normalized_string(invite_code)
        if user_id and self._requires_club_entry(competition) and not club_id:
            try:
                resolved_club = self._resolve_join_club(competition, user_id=user_id)
            except CompetitionActionError:
                return JoinDecision(eligible=False, reason="club_required")
            club_id = resolved_club.id if resolved_club is not None else None
            visibility_context = self._club_identity_payload(resolved_club) if resolved_club is not None else visibility_context
        participant_count = (
            participant_count if participant_count is not None else self._participant_count(competition.id)
        )
        already_joined = (
            already_joined
            if already_joined is not None
            else (self._participant(competition.id, club_id or user_id) is not None if (club_id or user_id) else False)
        )
        invite_valid = (
            self._resolve_invite(competition.id, invite_code=invite_code, club_id=club_id or user_id, consume=False)
            is not None
        )
        join_decision = self.join_service.evaluate_join(
            status=self._coerce_enum(CompetitionStatus, competition.status, field_name="status"),
            visibility=self._coerce_enum(CompetitionVisibility, competition.visibility, field_name="visibility"),
            participant_count=participant_count,
            capacity=self._summary_capacity(rule_set),
            already_joined=already_joined,
            invite_valid=invite_valid,
            scheduled_start_at=competition.scheduled_start_at,
        )
        if (
            join_decision.eligible
            and not already_joined
            and self._requires_passcode(competition)
            and not self._passcode_matches(competition, passcode)
        ):
            return JoinDecision(
                eligible=False,
                reason="passcode_required",
                requires_invite=False,
                requires_passcode=True,
            )
        if join_decision.eligible and not already_joined:
            rules = (
                list(visibility_rules)
                if visibility_rules is not None
                else list(
                    self.session.scalars(
                        select(CompetitionVisibilityRule).where(
                            CompetitionVisibilityRule.competition_id == competition.id
                        )
                    ).all()
                )
            )
            visibility_decision = self.visibility_service.evaluate(
                competition,
                club_id=club_id or user_id or "anonymous",
                invite_valid=invite_valid,
                rules=rules,
                context=visibility_context or {},
            )
            if not visibility_decision.allowed:
                return JoinDecision(
                    eligible=False,
                    reason=visibility_decision.reason,
                    requires_invite=visibility_decision.requires_invite,
                )
        return join_decision

    def _list_query_context(self, competitions: list[Competition]) -> _CompetitionListQueryContext:
        if not competitions:
            return _CompetitionListQueryContext(
                participant_counts={},
                rule_sets={},
                prize_rules={},
                visibility_rules={},
            )
        competition_ids = tuple(competition.id for competition in competitions)
        participant_counts = {
            str(competition_id): int(count or 0)
            for competition_id, count in self.session.execute(
                select(
                    CompetitionParticipant.competition_id,
                    func.count(CompetitionParticipant.id),
                )
                .where(CompetitionParticipant.competition_id.in_(competition_ids))
                .group_by(CompetitionParticipant.competition_id)
            ).all()
        }
        rule_sets = {
            item.competition_id: item
            for item in self.session.scalars(
                select(CompetitionRuleSet).where(CompetitionRuleSet.competition_id.in_(competition_ids))
            ).all()
        }
        prize_rules = {
            item.competition_id: item
            for item in self.session.scalars(
                select(CompetitionPrizeRule).where(CompetitionPrizeRule.competition_id.in_(competition_ids))
            ).all()
        }
        grouped_visibility_rules: defaultdict[str, list[CompetitionVisibilityRule]] = defaultdict(list)
        for item in self.session.scalars(
            select(CompetitionVisibilityRule)
            .where(CompetitionVisibilityRule.competition_id.in_(competition_ids))
            .order_by(
                CompetitionVisibilityRule.competition_id.asc(),
                CompetitionVisibilityRule.priority.asc(),
                CompetitionVisibilityRule.created_at.asc(),
            )
        ).all():
            grouped_visibility_rules[item.competition_id].append(item)
        dynamic_service = DynamicPrizePoolService(self.session)
        dynamic_prize_pool_context = (
            dynamic_service.build_list_context()
            if any(dynamic_service.is_enabled_for(competition) for competition in competitions)
            else None
        )
        return _CompetitionListQueryContext(
            participant_counts=participant_counts,
            rule_sets=rule_sets,
            prize_rules=prize_rules,
            visibility_rules={
                competition_id: tuple(items) for competition_id, items in grouped_visibility_rules.items()
            },
            dynamic_prize_pool_context=dynamic_prize_pool_context,
        )

    def _summary_context(
        self,
        competition: Competition,
        *,
        metadata: dict[str, object],
        user_id: str | None = None,
        invite_code: str | None = None,
    ) -> _CompetitionSummaryContext:
        return _CompetitionSummaryContext(
            creator_id=self._required_identifier(competition.host_user_id, field_name="host_user_id"),
            viewer_user_id=self._normalized_string(user_id),
            invite_code=self._normalized_string(invite_code),
            league_id=self._normalized_string(metadata.get("creator_league_config_id"))
            or self._normalized_string(competition.source_id),
            season_id=self._normalized_string(metadata.get("creator_league_season_id")),
        )

    def _summary_metadata(self, competition: Competition) -> dict[str, object]:
        metadata = competition.metadata_json
        if metadata is None:
            return {}
        if isinstance(metadata, dict):
            return metadata
        raise CompetitionActionError("Competition metadata is invalid.", reason="invalid_summary_state")

    def _summary_capacity(self, rule_set: CompetitionRuleSet) -> int:
        if not isinstance(rule_set.max_participants, int) or rule_set.max_participants < 2:
            raise CompetitionActionError("Competition capacity is invalid.", reason="invalid_summary_state")
        return rule_set.max_participants

    def _required_identifier(self, value: object, *, field_name: str) -> str:
        normalized = self._normalized_string(value)
        if normalized is None:
            raise CompetitionActionError(f"Competition {field_name} is missing.", reason="invalid_summary_state")
        return normalized

    def _coerce_enum(self, enum_type: type[Enum], value: object, *, field_name: str):
        try:
            return enum_type(value)
        except ValueError as exc:
            raise CompetitionActionError(
                f"Competition {field_name} is invalid.", reason="invalid_summary_state"
            ) from exc

    def _requires_club_entry(self, competition: Competition) -> bool:
        metadata = competition.metadata_json if isinstance(competition.metadata_json, dict) else {}
        markers = {
            self._normalized_string(competition.competition_type),
            self._normalized_string(competition.source_type),
            self._normalized_string(metadata.get("competition_scope")),
        }
        normalized = " ".join(sorted(item.lower() for item in markers if item))
        if any(token in normalized for token in ("national", "nation", "country_team", "international")):
            return False
        return True

    def _resolve_join_club(
        self,
        competition: Competition,
        *,
        user_id: str,
        club_name: str | None = None,
    ) -> ClubProfile | None:
        if not self._requires_club_entry(competition):
            return None
        normalized_name = self._normalized_string(club_name)
        stmt = select(ClubProfile).where(ClubProfile.owner_user_id == user_id)
        if normalized_name:
            stmt = stmt.where(func.lower(ClubProfile.club_name) == normalized_name.lower())
        clubs = list(self.session.scalars(stmt.order_by(ClubProfile.created_at.asc())).all())
        if not clubs:
            raise CompetitionActionError(
                "You need a club before entering club competitions.",
                reason="club_required",
            )
        if normalized_name is None and len(clubs) > 1:
            raise CompetitionActionError(
                "Choose the club name you want to enter with.",
                reason="club_name_required",
            )
        return clubs[0]

    def _club_identity_payload(self, club: ClubProfile | None) -> dict[str, Any]:
        if club is None:
            return {}
        country_code = self._normalized_string(club.country_code)
        state_name = self._normalized_string(club.region_name)
        city_name = self._normalized_string(club.city_name)
        address_parts = [part for part in (country_code, state_name, city_name) if part]
        flag = self._country_flag(country_code)
        display_name = f"{flag} {club.club_name}" if flag else club.club_name
        return {
            "club_id": club.id,
            "club_name": club.club_name,
            "club_display_name": display_name,
            "club_country_flag": flag,
            "club_country": country_code,
            "club_state": state_name,
            "club_city": city_name,
            "club_address": ", ".join(address_parts),
            "country": country_code,
            "state": state_name,
            "city": city_name,
            "region": state_name or country_code,
        }

    def _participant_for_user(self, competition: Competition, *, user_id: str) -> CompetitionParticipant | None:
        participant = self._participant(competition.id, user_id)
        if participant is not None or not self._requires_club_entry(competition):
            return participant
        club_ids = tuple(
            self.session.scalars(select(ClubProfile.id).where(ClubProfile.owner_user_id == user_id)).all()
        )
        if not club_ids:
            return None
        return self.session.scalar(
            select(CompetitionParticipant).where(
                CompetitionParticipant.competition_id == competition.id,
                CompetitionParticipant.club_id.in_(club_ids),
            )
        )

    @staticmethod
    def _country_flag(country_code: str | None) -> str:
        if not country_code:
            return ""
        code = country_code.strip().upper()
        if len(code) != 2 or not code.isalpha():
            return ""
        return "".join(chr(ord(char) - ord("A") + 0x1F1E6) for char in code)

    def _normalized_string(self, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None

    def _resolve_invite(
        self,
        competition_id: str,
        *,
        invite_code: str | None = None,
        invite_id: str | None = None,
        club_id: str | None = None,
        consume: bool = False,
    ) -> CompetitionInvite | None:
        if not invite_code and not invite_id:
            return None
        if invite_id:
            invite = self.session.get(CompetitionInvite, invite_id)
        else:
            invite = self.session.scalar(select(CompetitionInvite).where(CompetitionInvite.invite_code == invite_code))
        if invite is None or invite.competition_id != competition_id:
            return None
        expires_at = _as_utc(invite.expires_at)
        if expires_at and datetime.now(timezone.utc) >= expires_at:
            return None
        if invite.club_id and club_id and invite.club_id != club_id:
            return None
        if invite.uses >= invite.max_uses:
            return None
        if consume:
            invite.uses += 1
            invite.responded_at = datetime.now(timezone.utc)
            invite.status = "fulfilled" if invite.uses >= invite.max_uses else "accepted"
        return invite

    def _generate_invite_code(self) -> str:
        for _ in range(6):
            invite_code = token_hex(6)
            exists = self.session.scalar(select(CompetitionInvite).where(CompetitionInvite.invite_code == invite_code))
            if exists is None:
                return invite_code
        raise CompetitionActionError("Failed to generate invite code.", reason="invite_code_unavailable")

    def _projected_reward_pool_minor(self, *, competition: Competition, rule_set: CompetitionRuleSet) -> int:
        participant_count = rule_set.max_participants
        gross_pool = competition.entry_fee_minor * participant_count
        platform_fee_minor = gross_pool * competition.platform_fee_bps // 10_000
        host_fee_minor = gross_pool * competition.host_fee_bps // 10_000
        net_pool = gross_pool - platform_fee_minor - host_fee_minor
        return max(net_pool, 0)

    def _refresh_financials(
        self,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        *,
        participant_count: int | None = None,
    ) -> None:
        if self._is_platform_competition(competition.source_type):
            competition.entry_fee_minor = 0
            competition.platform_fee_bps = 0
            competition.host_fee_bps = 0
            competition.gross_pool_minor = 0
            competition.net_prize_pool_minor = 0
            reward_pool = self.session.scalar(
                select(CompetitionRewardPool)
                .where(CompetitionRewardPool.competition_id == competition.id)
                .order_by(CompetitionRewardPool.created_at.desc())
            )
            if reward_pool is not None:
                reward_pool.pool_type = "promo_pool"
                if reward_pool.status in {"planned", "projected", "pending"}:
                    snapshot = self._dynamic_prize_pool(competition, rule_set=rule_set)
                    if snapshot is not None:
                        reward_pool.amount_minor = snapshot.total_pool_minor
                        reward_pool.metadata_json = DynamicPrizePoolService(self.session).apply_to_reward_pool(
                            metadata_json=reward_pool.metadata_json,
                            snapshot=snapshot,
                        )
            return
        participant_count = (
            participant_count if participant_count is not None else self._participant_count(competition.id)
        )
        gross_pool = competition.entry_fee_minor * participant_count
        platform_fee_minor = gross_pool * competition.platform_fee_bps // 10_000
        host_fee_minor = gross_pool * competition.host_fee_bps // 10_000
        net_pool = gross_pool - platform_fee_minor - host_fee_minor
        competition.gross_pool_minor = gross_pool
        competition.net_prize_pool_minor = max(net_pool, 0)
        reward_pool = self.session.scalar(
            select(CompetitionRewardPool)
            .where(
                CompetitionRewardPool.competition_id == competition.id,
                CompetitionRewardPool.pool_type == "entry_fee",
            )
            .order_by(CompetitionRewardPool.created_at.desc())
        )
        if reward_pool is not None and reward_pool.status in {"planned", "projected", "pending"}:
            reward_pool.amount_minor = competition.net_prize_pool_minor

    def _schedule_counts(
        self,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        participant_count: int,
    ) -> tuple[int, int]:
        if participant_count <= 1:
            return 0, 0
        if rule_set.group_stage_enabled:
            group_size = rule_set.group_size or max(2, min(4, participant_count))
            group_count = rule_set.group_count or max(1, int((participant_count + group_size - 1) / group_size))
            group_matches_per_group = group_size * (group_size - 1) // 2
            if rule_set.league_home_away:
                group_matches_per_group *= 2
            group_matches = group_matches_per_group * group_count
            group_rounds = max(1, group_size - 1)
            if rule_set.league_home_away:
                group_rounds *= 2
            advance_count = rule_set.group_advance_count or 2
            bracket_size = rule_set.knockout_bracket_size or self._next_power_of_two(group_count * advance_count)
            knockout_matches = max(0, bracket_size - 1)
            knockout_rounds = int(bracket_size).bit_length() - 1
            return group_rounds + knockout_rounds, group_matches + knockout_matches

        if competition.format == CompetitionFormat.LEAGUE.value:
            rounds = participant_count - 1
            matches = participant_count * (participant_count - 1) // 2
            if rule_set.league_home_away:
                rounds *= 2
                matches *= 2
            return max(rounds, 1), matches

        bracket_size = rule_set.knockout_bracket_size or self._next_power_of_two(participant_count)
        rounds = max(1, int(bracket_size).bit_length() - 1)
        matches = max(0, bracket_size - 1)
        return rounds, matches

    def _next_power_of_two(self, value: int) -> int:
        bracket = 1
        while bracket < value:
            bracket *= 2
        return bracket

    def _pct_to_bps(self, value: Decimal | None) -> int:
        if value is None:
            return 0
        return int((value * Decimal("10000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def _from_bps(self, value: int) -> Decimal:
        return (Decimal(value) / Decimal("10000")).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

    def _to_minor_units(self, value: Decimal) -> int:
        return int((value * Decimal("10000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def _to_decimal(self, value: int) -> Decimal:
        return (Decimal(value) / Decimal("10000")).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

    def _invite_view(self, invite: CompetitionInvite) -> CompetitionInviteView:
        return CompetitionInviteView(
            invite_code=invite.invite_code,
            issued_by=invite.invited_by_user_id,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            max_uses=invite.max_uses,
            uses=invite.uses,
            note=(invite.metadata_json or {}).get("note"),
        )

    def _validate_against_thread_a_domain(self, payload: CompetitionCreateRequest) -> None:
        if payload.capacity < USER_COMPETITION_MIN_PARTICIPANTS:
            raise CompetitionActionError("Competition capacity is below minimum.", reason="capacity_too_low")

    @staticmethod
    def _is_platform_competition(source_type: str | None) -> bool:
        if source_type is None:
            return False
        normalized = source_type.strip().lower()
        return normalized in {"gtex", "platform", "gtex_platform", "gtex_competition", "gtex_hosted"}

    def _host_type_for_payload(self, payload: CompetitionCreateRequest) -> CompetitionHostType:
        if payload.host_type is not None:
            return payload.host_type
        if self._is_platform_competition(payload.source_type):
            return CompetitionHostType.GTEX_HOSTED
        return CompetitionHostType.USER_HOSTED

    def _host_type_for_competition(self, competition: Competition) -> CompetitionHostType:
        metadata = competition.metadata_json if isinstance(competition.metadata_json, dict) else {}
        metadata_host_type = self._normalized_string(metadata.get("host_type"))
        if metadata_host_type:
            normalized = metadata_host_type.lower()
            if normalized in {"gtex", "gtex_hosted", "official", "platform"}:
                return CompetitionHostType.GTEX_HOSTED
            if normalized in {"user", "user_hosted", "creator", "creator_hosted"}:
                return CompetitionHostType.USER_HOSTED
        if self._is_platform_competition(competition.source_type):
            return CompetitionHostType.GTEX_HOSTED
        return CompetitionHostType.USER_HOSTED

    def _match_type_for(self, competition: Competition) -> str:
        if self._host_type_for_competition(competition) is CompetitionHostType.GTEX_HOSTED:
            return "gtex_hosted"
        normalized = self._normalized_string(competition.source_type)
        if normalized in {"fast_match", "fastmatch", "fast"}:
            return "fast_match"
        return "user_hosted"

    @staticmethod
    def _hash_passcode(passcode: str) -> str:
        return sha256(passcode.strip().encode("utf-8")).hexdigest()

    def _requires_passcode(self, competition: Competition) -> bool:
        metadata = competition.metadata_json if isinstance(competition.metadata_json, dict) else {}
        return bool(metadata.get(_REQUIRES_PASSCODE_METADATA_KEY) or metadata.get(_PASSCODE_METADATA_KEY))

    def _passcode_matches(self, competition: Competition, passcode: str | None) -> bool:
        if not self._requires_passcode(competition):
            return True
        candidate = self._normalized_string(passcode)
        if candidate is None:
            return False
        metadata = competition.metadata_json if isinstance(competition.metadata_json, dict) else {}
        stored_hash = self._normalized_string(metadata.get(_PASSCODE_METADATA_KEY))
        if stored_hash is None:
            return False
        return stored_hash == self._hash_passcode(candidate)


def backend_competition_create_request(
    payload: CompetitionCreateRequest,
    *,
    default_platform_fee_pct: Decimal,
) -> CompetitionCoreCreateRequest:
    platform_fee_pct = payload.platform_fee_pct if payload.platform_fee_pct is not None else default_platform_fee_pct
    entry_fee_minor = int((payload.entry_fee * Decimal("10000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    platform_fee_bps = int((platform_fee_pct * Decimal("10000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    payout_percentages = []
    payout_mode = CompetitionPayoutMode.WINNER_TAKE_ALL
    top_n = None
    if payload.payout_structure:
        payout_percentages = [int(rule.percent * Decimal("100")) for rule in payload.payout_structure]
        payout_mode = CompetitionPayoutMode.CUSTOM_PERCENT
        top_n = len(payout_percentages)

    if payload.format == CompetitionFormat.LEAGUE:
        rules = CompetitionRuleSetPayload(
            format=payload.format,
            league_rules=LeagueRuleSetPayload(
                win_points=3,
                draw_points=1,
                loss_points=0,
                tie_break_order=["points", "goal_diff", "goals_for", "head_to_head", "fair_play"],
                home_away=False,
                min_participants=USER_COMPETITION_MIN_PARTICIPANTS,
                max_participants=payload.capacity,
            ),
        )
    else:
        rules = CompetitionRuleSetPayload(
            format=payload.format,
            cup_rules=CupRuleSetPayload(
                single_elimination=True,
                two_leg_tie=False,
                extra_time=False,
                penalties=True,
                min_participants=payload.capacity,
                max_participants=payload.capacity,
                allowed_participant_sizes=[payload.capacity],
            ),
        )

    start_mode = CompetitionStartMode.SCHEDULED if payload.scheduled_start_at else CompetitionStartMode.MANUAL_AFTER_MIN

    core = CompetitionCorePayload(
        host_user_id=payload.creator_id,
        name=payload.name,
        description=payload.rules_summary,
        format=payload.format,
        visibility=payload.visibility,
        start_mode=start_mode,
        scheduled_start_at=payload.scheduled_start_at,
        status=CompetitionStatus.DRAFT,
    )

    financials = CompetitionFinancialsPayload(
        entry_fee_minor=entry_fee_minor,
        currency=payload.currency,
        platform_fee_bps=platform_fee_bps,
        host_creation_fee_minor=0,
        payout_mode=payout_mode,
        top_n=top_n,
        payout_percentages=payout_percentages,
    )

    return CompetitionCoreCreateRequest(core=core, rules=rules, financials=financials)


def get_competition_orchestrator(
    request: Request,
    session: Session = Depends(get_session),
) -> CompetitionOrchestrator:
    return CompetitionOrchestrator(
        session=session,
        event_publisher=getattr(request.app.state, "event_publisher", InMemoryEventPublisher()),
    )


__all__ = ["CompetitionActionError", "CompetitionOrchestrator", "get_competition_orchestrator"]
