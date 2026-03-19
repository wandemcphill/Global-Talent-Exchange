from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
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
from backend.app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
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
from backend.app.schemas.competition_core import CompetitionCorePayload, CompetitionCreateRequest as CompetitionCoreCreateRequest
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
    CompetitionUpdateRequest,
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
from backend.app.services.competition_discovery_service import CompetitionDiscoveryFilter
from backend.app.services.competition_fee_service import CompetitionFeeService
from backend.app.services.competition_join_service import CompetitionJoinService, JoinDecision
from backend.app.services.competition_lifecycle_service import CompetitionLifecycleService
from backend.app.services.competition_rules_engine import CompetitionRulesEngine
from backend.app.services.competition_validation_service import CompetitionValidationService
from backend.app.services.competition_visibility_service import CompetitionVisibilityService

_DEFAULT_RULES = (
    "Skill-based, player-versus-player contest with transparent entry fees, disclosed platform service fees, "
    "and a rules-based prize pool. No odds, house-banked outcomes, or prediction markets."
)
_DISCOVERY_SKIP_REASONS = frozenset({"invalid_summary_state", "rules_missing"})
_TWO_PLACES = Decimal("0.01")
_FOUR_PLACES = Decimal("0.0001")


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
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)

    def __post_init__(self) -> None:
        self.lifecycle_service = CompetitionLifecycleService(self.session, event_publisher=self.event_publisher)

    def create(self, payload: CompetitionCreateRequest) -> CompetitionSummaryView:
        self._validate_against_thread_a_domain(payload)
        is_platform_competition = self._is_platform_competition(payload.source_type)
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
            competition.metadata_json = {**(competition.metadata_json or {}), "beginner_friendly": payload.beginner_friendly}
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

        pool_amount_minor = 0 if is_platform_competition else self._projected_reward_pool_minor(
            competition=competition,
            rule_set=rule_set,
        )
        reward_pool = CompetitionRewardPool(
            competition_id=competition.id,
            pool_type="promo_pool" if is_platform_competition else "entry_fee",
            currency=competition.currency,
            amount_minor=pool_amount_minor,
            status="planned",
            metadata_json={},
        )
        self.session.add(reward_pool)
        self.session.commit()
        self.session.refresh(competition)
        self.event_publisher.publish(
            DomainEvent(
                name="competition_created",
                payload={
                    "competition_id": competition.id,
                    "source_type": competition.source_type,
                    "entry_fee_minor": competition.entry_fee_minor,
                    "currency": competition.currency,
                    "reward_pool_type": reward_pool.pool_type,
                },
            )
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

        items: list[CompetitionSummaryView] = []
        for item in competitions:
            summary = self._safe_list_summary(item)
            if summary is not None:
                items.append(summary)
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

    def join(
        self,
        competition_id: str,
        *,
        user_id: str,
        user_name: str | None,
        invite_code: str | None,
    ) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None

        rule_set = self._rule_set(competition.id)
        participant = self._participant(competition.id, user_id)
        participant_count = self._participant_count(competition.id)
        join_decision = self._join_decision_for(
            competition,
            user_id=user_id,
            invite_code=invite_code,
            participant_count=participant_count,
            already_joined=participant is not None,
        )
        if not join_decision.eligible:
            return self._to_summary(competition, user_id=user_id, invite_code=invite_code)
        if participant is not None:
            return self._to_summary(competition, user_id=user_id, invite_code=invite_code)

        invite_used = None
        if invite_code:
            invite_used = self._resolve_invite(competition.id, invite_code=invite_code, club_id=user_id, consume=True)
            if invite_used is None and join_decision.requires_invite:
                return self._to_summary(competition, user_id=user_id, invite_code=invite_code)

        entry = CompetitionEntry(
            competition_id=competition.id,
            club_id=user_id,
            user_id=user_id,
            entry_type="invite" if invite_used else "direct",
            status="accepted",
            invite_id=invite_used.id if invite_used else None,
            responded_at=datetime.now(timezone.utc),
            metadata_json={**({"user_name": user_name} if user_name else {}), **({"invite_code": invite_code} if invite_code else {})},
        )
        self.session.add(entry)
        self.session.flush()
        participant = CompetitionParticipant(
            competition_id=competition.id,
            club_id=user_id,
            entry_id=entry.id,
            status="joined",
            paid_entry_fee_minor=competition.entry_fee_minor,
            paid_at=datetime.now(timezone.utc) if competition.entry_fee_minor > 0 else None,
        )
        self.session.add(participant)
        self._refresh_financials(competition, rule_set, participant_count=participant_count + 1)
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition, user_id=user_id, invite_code=invite_code)

    def leave(self, competition_id: str, *, user_id: str) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        rule_set = self._rule_set(competition.id)
        participant = self._participant(competition.id, user_id)
        if participant is None:
            return self._to_summary(competition, user_id=user_id)
        entry = self.session.get(CompetitionEntry, participant.entry_id) if participant.entry_id else None
        if entry is not None:
            entry.status = "withdrawn"
            entry.responded_at = datetime.now(timezone.utc)
        self.session.delete(participant)
        participant_count = max(0, self._participant_count(competition.id) - 1)
        self._refresh_financials(competition, rule_set, participant_count=participant_count)
        self.session.commit()
        self.session.refresh(competition)
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
        return CompetitionInvitesResponse(competition_id=competition_id, invites=tuple(self._invite_view(item) for item in invites))

    def accept_invite(
        self,
        competition_id: str,
        payload: CompetitionInviteAcceptRequest,
    ) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        rule_set = self._rule_set(competition.id)
        club_id = payload.club_id
        participant = self._participant(competition.id, club_id)
        if participant is not None:
            return self._to_summary(competition, user_id=club_id, invite_code=payload.invite_code)
        invite = self._resolve_invite(
            competition.id,
            invite_code=payload.invite_code,
            invite_id=payload.invite_id,
            club_id=club_id,
            consume=True,
        )
        if invite is None:
            raise CompetitionActionError("Invite is invalid or expired.", reason="invite_invalid")
        entry = CompetitionEntry(
            competition_id=competition.id,
            club_id=club_id,
            user_id=payload.user_id or club_id,
            entry_type="invite",
            status="accepted",
            invite_id=invite.id,
            responded_at=datetime.now(timezone.utc),
            metadata_json={"invite_code": invite.invite_code},
        )
        self.session.add(entry)
        self.session.flush()
        participant = CompetitionParticipant(
            competition_id=competition.id,
            club_id=club_id,
            entry_id=entry.id,
            status="joined",
            paid_entry_fee_minor=competition.entry_fee_minor,
            paid_at=datetime.now(timezone.utc) if competition.entry_fee_minor > 0 else None,
        )
        self.session.add(participant)
        participant_count = self._participant_count(competition.id) + 1
        self._refresh_financials(competition, rule_set, participant_count=participant_count)
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition, user_id=club_id, invite_code=invite.invite_code)

    def financials(self, competition_id: str) -> CompetitionFinancialSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        participant_count = self._participant_count(competition.id)
        fees = self._fees_for(competition, participant_count=participant_count)
        payout_structure = self._payout_breakdown(
            competition=competition,
            prize_pool=fees.prize_pool,
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
            prize_pool=fees.prize_pool,
            payout_structure=payout_structure,
            currency=competition.currency,
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

    def standings(self, competition_id: str, *, group_key: str | None = None) -> tuple[CompetitionStandingView, ...] | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        rule_set = self._rule_set(competition.id)
        standings = self.lifecycle_service.match_service.standings(
            competition_id=competition.id,
            rule_set=rule_set,
            group_key=group_key,
        )
        views: list[CompetitionStandingView] = []
        for index, participant in enumerate(standings, start=1):
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
                )
            )
        return tuple(views)

    def seed_competition(self, competition_id: str, payload: CompetitionSeedRequest) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        if CompetitionStatus(competition.status) in {CompetitionStatus.LIVE, CompetitionStatus.COMPLETED, CompetitionStatus.SETTLED}:
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
        if CompetitionStatus(competition.status) in {CompetitionStatus.LIVE, CompetitionStatus.COMPLETED, CompetitionStatus.SETTLED}:
            return self._to_summary(competition)
        try:
            self.lifecycle_service.launch_competition(competition)
        except ValueError as exc:
            raise CompetitionActionError(str(exc), reason="competition_launch_blocked") from exc
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition)

    def advance_competition(self, competition_id: str, payload: CompetitionAdvanceRequest) -> CompetitionSummaryView | None:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            return None
        if CompetitionStatus(competition.status) not in {CompetitionStatus.LIVE, CompetitionStatus.SEEDED}:
            return self._to_summary(competition)
        self.lifecycle_service.advance_competition(competition, force=payload.force)
        self.session.commit()
        self.session.refresh(competition)
        return self._to_summary(competition)

    def finalize_competition(self, competition_id: str, payload: CompetitionFinalizeRequest) -> CompetitionSummaryView | None:
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

    def schedule_job_status(self, competition_id: str, *, job_id: str | None = None) -> CompetitionScheduleJobView | None:
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
    ) -> CompetitionSummaryView:
        participant_count = self._participant_count(competition.id)
        rule_set = self._rule_set(competition.id)
        fees = self._fees_for(competition, participant_count=participant_count)
        payout_structure = self._payout_breakdown(competition=competition, prize_pool=fees.prize_pool)
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
        )
        return CompetitionSummaryView(
            id=competition.id,
            name=competition.name,
            format=self._coerce_enum(CompetitionFormat, competition.format, field_name="format"),
            visibility=self._coerce_enum(CompetitionVisibility, competition.visibility, field_name="visibility"),
            status=self._coerce_enum(CompetitionStatus, competition.status, field_name="status"),
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
            prize_pool=fees.prize_pool,
            payout_structure=payout_structure,
            rules_summary=competition.description or _DEFAULT_RULES,
            join_eligibility=JoinEligibilityView(
                eligible=join_decision.eligible,
                reason=join_decision.reason,
                requires_invite=join_decision.requires_invite,
            ),
            beginner_friendly=metadata.get("beginner_friendly"),
            created_at=competition.created_at,
            updated_at=competition.updated_at,
        )

    def _safe_list_summary(self, competition: Competition) -> CompetitionSummaryView | None:
        try:
            return self._to_summary(competition)
        except CompetitionActionError as exc:
            if exc.reason in _DISCOVERY_SKIP_REASONS:
                return None
            raise
        except ValidationError:
            return None

    def _payout_breakdown(
        self,
        *,
        competition: Competition,
        prize_pool: Decimal,
    ) -> tuple:
        prize_rule = self._prize_rule(competition.id)
        payouts = [
            (index + 1, (Decimal(percent) / Decimal("100")).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP))
            for index, percent in enumerate(prize_rule.payout_percentages or [])
        ]
        if not payouts:
            return ()
        return self.fee_service.build_payouts(prize_pool=prize_pool, payout_structure=tuple(payouts))

    def _participant_count(self, competition_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count()).where(CompetitionParticipant.competition_id == competition_id)
            )
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
        rule_set = self.session.scalar(select(CompetitionRuleSet).where(CompetitionRuleSet.competition_id == competition_id))
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
        invite_code: str | None = None,
        participant_count: int | None = None,
        already_joined: bool | None = None,
    ) -> JoinDecision:
        rule_set = self._rule_set(competition.id)
        user_id = self._normalized_string(user_id)
        invite_code = self._normalized_string(invite_code)
        participant_count = participant_count if participant_count is not None else self._participant_count(competition.id)
        already_joined = already_joined if already_joined is not None else (
            self._participant(competition.id, user_id) is not None if user_id else False
        )
        invite_valid = self._resolve_invite(competition.id, invite_code=invite_code, club_id=user_id, consume=False) is not None
        join_decision = self.join_service.evaluate_join(
            status=self._coerce_enum(CompetitionStatus, competition.status, field_name="status"),
            visibility=self._coerce_enum(CompetitionVisibility, competition.visibility, field_name="visibility"),
            participant_count=participant_count,
            capacity=self._summary_capacity(rule_set),
            already_joined=already_joined,
            invite_valid=invite_valid,
        )
        if join_decision.eligible and not already_joined:
            rules = list(
                self.session.scalars(
                    select(CompetitionVisibilityRule).where(CompetitionVisibilityRule.competition_id == competition.id)
                ).all()
            )
            visibility_decision = self.visibility_service.evaluate(
                competition,
                club_id=user_id or "anonymous",
                invite_valid=invite_valid,
                rules=rules,
                context={},
            )
            if not visibility_decision.allowed:
                return JoinDecision(
                    eligible=False,
                    reason=visibility_decision.reason,
                    requires_invite=visibility_decision.requires_invite,
                )
        return join_decision

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
            league_id=self._normalized_string(metadata.get("creator_league_config_id")) or self._normalized_string(competition.source_id),
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
            raise CompetitionActionError(f"Competition {field_name} is invalid.", reason="invalid_summary_state") from exc

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
        if invite.expires_at and datetime.now(timezone.utc) >= invite.expires_at:
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
            exists = self.session.scalar(
                select(CompetitionInvite).where(CompetitionInvite.invite_code == invite_code)
            )
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
                    reward_pool.amount_minor = 0
            return
        participant_count = participant_count if participant_count is not None else self._participant_count(competition.id)
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
    session: Session = Depends(get_session),
) -> CompetitionOrchestrator:
    return CompetitionOrchestrator(session=session)


__all__ = ["CompetitionActionError", "CompetitionOrchestrator", "get_competition_orchestrator"]
