from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from threading import RLock
from uuid import uuid4

from pydantic import ValidationError

from backend.app.common.enums.competition_format import CompetitionFormat
from backend.app.common.enums.competition_payout_mode import CompetitionPayoutMode
from backend.app.common.enums.competition_start_mode import CompetitionStartMode
from backend.app.common.enums.competition_status import CompetitionStatus
from backend.app.common.enums.competition_visibility import CompetitionVisibility
from backend.app.config.competition_constants import USER_COMPETITION_MIN_PARTICIPANTS
from backend.app.schemas.competition_core import CompetitionCorePayload
from backend.app.schemas.competition_financials import CompetitionFinancialsPayload
from backend.app.schemas.competition_requests import (
    CompetitionCreateRequest,
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
from backend.app.services.competition_invite_service import CompetitionInvite, CompetitionInviteService
from backend.app.services.competition_join_service import CompetitionJoinService, CompetitionParticipant, JoinDecision

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
class CompetitionRecord:
    id: str
    name: str
    format: CompetitionFormat
    visibility: CompetitionVisibility
    status: CompetitionStatus
    creator_id: str
    creator_name: str | None
    entry_fee: Decimal
    currency: str
    capacity: int
    participants: tuple[CompetitionParticipant, ...]
    payout_structure: tuple[tuple[int, Decimal], ...]
    platform_fee_pct: Decimal
    host_fee_pct: Decimal
    rules_summary: str
    beginner_friendly: bool | None
    created_at: datetime
    updated_at: datetime

    @property
    def participant_count(self) -> int:
        return len(self.participants)

    @property
    def fill_rate(self) -> Decimal:
        if self.capacity <= 0:
            return Decimal("0")
        return (Decimal(self.participant_count) / Decimal(self.capacity)).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)


@dataclass(slots=True)
class CompetitionStore:
    _competitions: dict[str, CompetitionRecord] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def save(self, record: CompetitionRecord) -> CompetitionRecord:
        with self._lock:
            self._competitions[record.id] = record
        return record

    def get(self, competition_id: str) -> CompetitionRecord | None:
        with self._lock:
            return self._competitions.get(competition_id)

    def list_all(self) -> tuple[CompetitionRecord, ...]:
        with self._lock:
            return tuple(self._competitions.values())


@dataclass(slots=True)
class CompetitionOrchestrator:
    store: CompetitionStore = field(default_factory=CompetitionStore)
    invite_service: CompetitionInviteService = field(default_factory=lambda: CompetitionInviteService({}))
    join_service: CompetitionJoinService = field(default_factory=CompetitionJoinService)
    fee_service: CompetitionFeeService = field(default_factory=CompetitionFeeService)
    discovery_service: CompetitionDiscoveryService = field(default_factory=CompetitionDiscoveryService)
    creation_service: CompetitionCreationService = field(default_factory=CompetitionCreationService)

    def create(self, payload: CompetitionCreateRequest) -> CompetitionSummaryView:
        self._validate_against_thread_a_domain(payload)
        now = payload.created_at or datetime.now(timezone.utc)
        payout_structure = self._resolve_payout_structure(payload.payout_structure)
        fees = self.fee_service.resolve_fees(
            entry_fee=payload.entry_fee,
            participant_count=0,
            platform_fee_pct=payload.platform_fee_pct,
            host_fee_pct=payload.host_fee_pct,
        )
        record = CompetitionRecord(
            id=f"ugc-{uuid4().hex[:12]}",
            name=payload.name,
            format=payload.format,
            visibility=payload.visibility,
            status=CompetitionStatus.DRAFT,
            creator_id=payload.creator_id,
            creator_name=payload.creator_name,
            entry_fee=fees.entry_fee,
            currency=payload.currency,
            capacity=payload.capacity,
            participants=(),
            payout_structure=payout_structure,
            platform_fee_pct=fees.platform_fee_pct,
            host_fee_pct=fees.host_fee_pct,
            rules_summary=payload.rules_summary or _DEFAULT_RULES,
            beginner_friendly=payload.beginner_friendly,
            created_at=now,
            updated_at=now,
        )
        self.store.save(record)
        return self._to_summary(record, user_id=payload.creator_id)

    def update(self, competition_id: str, payload: CompetitionUpdateRequest) -> CompetitionSummaryView | None:
        record = self.store.get(competition_id)
        if record is None:
            return None
        if record.status in {
            CompetitionStatus.LOCKED,
            CompetitionStatus.IN_PROGRESS,
            CompetitionStatus.COMPLETED,
            CompetitionStatus.CANCELLED,
        }:
            return self._to_summary(record)
        if payload.capacity is not None and payload.capacity < record.participant_count:
            raise CompetitionActionError(
                "Capacity cannot be reduced below the current participant count.",
                reason="capacity_too_low",
            )
        validate_format_capacity_for_update(record.format, payload.capacity)

        merged = CompetitionCreateRequest(
            name=payload.name or record.name,
            format=record.format,
            visibility=payload.visibility or record.visibility,
            entry_fee=payload.entry_fee if payload.entry_fee is not None else record.entry_fee,
            currency=record.currency,
            capacity=payload.capacity if payload.capacity is not None else record.capacity,
            creator_id=record.creator_id,
            creator_name=record.creator_name,
            payout_structure=payload.payout_structure or self._payout_rules_from_record(record),
            platform_fee_pct=payload.platform_fee_pct if payload.platform_fee_pct is not None else record.platform_fee_pct,
            host_fee_pct=payload.host_fee_pct if payload.host_fee_pct is not None else record.host_fee_pct,
            rules_summary=payload.rules_summary or record.rules_summary,
            beginner_friendly=payload.beginner_friendly if payload.beginner_friendly is not None else record.beginner_friendly,
            created_at=record.created_at,
        )
        self._validate_against_thread_a_domain(merged)

        payout_structure = self._resolve_payout_structure(merged.payout_structure)
        fees = self.fee_service.resolve_fees(
            entry_fee=merged.entry_fee,
            participant_count=record.participant_count,
            platform_fee_pct=merged.platform_fee_pct,
            host_fee_pct=merged.host_fee_pct,
        )
        updated = replace(
            record,
            name=merged.name,
            visibility=merged.visibility,
            entry_fee=fees.entry_fee,
            capacity=merged.capacity,
            payout_structure=payout_structure,
            platform_fee_pct=fees.platform_fee_pct,
            host_fee_pct=fees.host_fee_pct,
            rules_summary=merged.rules_summary or record.rules_summary,
            beginner_friendly=merged.beginner_friendly,
            updated_at=datetime.now(timezone.utc),
        )
        self.store.save(updated)
        return self._to_summary(updated)

    def publish(self, competition_id: str, *, open_for_join: bool = True) -> CompetitionSummaryView | None:
        record = self.store.get(competition_id)
        if record is None:
            return None
        if record.status in {CompetitionStatus.LOCKED, CompetitionStatus.IN_PROGRESS, CompetitionStatus.COMPLETED}:
            return self._to_summary(record)
        new_status = CompetitionStatus.OPEN_FOR_JOIN if open_for_join else CompetitionStatus.PUBLISHED
        if record.participant_count >= record.capacity:
            new_status = CompetitionStatus.FILLED
        updated = replace(record, status=new_status, updated_at=datetime.now(timezone.utc))
        self.store.save(updated)
        return self._to_summary(updated)

    def get(
        self,
        competition_id: str,
        *,
        user_id: str | None = None,
        invite_code: str | None = None,
    ) -> CompetitionSummaryView | None:
        record = self.store.get(competition_id)
        if record is None:
            return None
        return self._to_summary(record, user_id=user_id, invite_code=invite_code)

    def summary(
        self,
        competition_id: str,
        *,
        user_id: str | None = None,
        invite_code: str | None = None,
    ) -> CompetitionSummaryView | None:
        return self.get(competition_id, user_id=user_id, invite_code=invite_code)

    def list(self, *, filters: CompetitionDiscoveryFilter) -> CompetitionListResponse:
        competitions = self.store.list_all()
        filtered = self.discovery_service.apply_filters(
            competitions,
            filters=filters,
            prize_pool_lookup=lambda item: self._fees_for(item).prize_pool,
            fill_rate_lookup=lambda item: item.fill_rate,
        )
        items = tuple(self._to_summary(item) for item in filtered)
        return CompetitionListResponse(total=len(items), items=items)

    def join(
        self,
        competition_id: str,
        *,
        user_id: str,
        user_name: str | None,
        invite_code: str | None,
    ) -> CompetitionSummaryView | None:
        record = self.store.get(competition_id)
        if record is None:
            return None

        already_joined = any(participant.user_id == user_id for participant in record.participants)
        invite_valid = already_joined or record.visibility is not CompetitionVisibility.INVITE_ONLY
        if record.visibility is CompetitionVisibility.INVITE_ONLY and not already_joined:
            invite_valid = self.invite_service.has_valid_invite(competition_id, invite_code)

        decision = self.join_service.evaluate_join(
            status=record.status,
            visibility=record.visibility,
            participant_count=record.participant_count,
            capacity=record.capacity,
            already_joined=already_joined,
            invite_valid=invite_valid,
        )
        if not decision.eligible:
            return self._to_summary(record, user_id=user_id, invite_code=invite_code, join_override=decision)

        if record.visibility is CompetitionVisibility.INVITE_ONLY and not already_joined and invite_code is not None:
            redeemed = self.invite_service.redeem_invite(competition_id, invite_code)
            if redeemed is None:
                denied = JoinDecision(eligible=False, reason="invite_required", requires_invite=True)
                return self._to_summary(record, user_id=user_id, invite_code=invite_code, join_override=denied)

        updated_participants = self.join_service.join(
            participants=record.participants,
            user_id=user_id,
            user_name=user_name,
        )
        new_status = CompetitionStatus.FILLED if len(updated_participants) >= record.capacity else CompetitionStatus.OPEN_FOR_JOIN
        updated = replace(
            record,
            participants=updated_participants,
            status=new_status,
            updated_at=datetime.now(timezone.utc),
        )
        self.store.save(updated)
        return self._to_summary(updated, user_id=user_id, invite_code=invite_code)

    def leave(self, competition_id: str, *, user_id: str) -> CompetitionSummaryView | None:
        record = self.store.get(competition_id)
        if record is None:
            return None
        updated_participants = self.join_service.leave(participants=record.participants, user_id=user_id)
        next_status = record.status
        if record.status in {CompetitionStatus.FILLED, CompetitionStatus.OPEN_FOR_JOIN}:
            next_status = CompetitionStatus.OPEN_FOR_JOIN
        updated = replace(
            record,
            participants=updated_participants,
            status=next_status,
            updated_at=datetime.now(timezone.utc),
        )
        self.store.save(updated)
        return self._to_summary(updated, user_id=user_id)

    def create_invite(
        self,
        competition_id: str,
        *,
        issued_by: str,
        max_uses: int,
        expires_at: datetime | None,
        note: str | None,
    ) -> CompetitionInviteView | None:
        record = self.store.get(competition_id)
        if record is None:
            return None
        if issued_by != record.creator_id:
            raise CompetitionActionError(
                "Only the competition creator can issue invites.",
                reason="invite_forbidden",
            )
        invite = self.invite_service.create_invite(
            competition_id=competition_id,
            issued_by=issued_by,
            max_uses=max_uses,
            expires_at=expires_at,
            note=note,
        )
        return self._invite_view(invite)

    def list_invites(self, competition_id: str) -> CompetitionInvitesResponse | None:
        record = self.store.get(competition_id)
        if record is None:
            return None
        invites = tuple(self._invite_view(invite) for invite in self.invite_service.list_invites(competition_id))
        return CompetitionInvitesResponse(competition_id=competition_id, invites=invites)

    def financials(self, competition_id: str) -> CompetitionFinancialSummaryView | None:
        record = self.store.get(competition_id)
        if record is None:
            return None
        fees = self._fees_for(record)
        gross_pool = (record.entry_fee * Decimal(record.participant_count)).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)
        payouts = self.fee_service.build_payouts(
            prize_pool=fees.prize_pool,
            payout_structure=record.payout_structure,
        )
        return CompetitionFinancialSummaryView(
            competition_id=record.id,
            participant_count=record.participant_count,
            entry_fee=record.entry_fee,
            gross_pool=gross_pool,
            platform_fee_pct=fees.platform_fee_pct,
            platform_fee_amount=fees.platform_fee_amount,
            host_fee_pct=fees.host_fee_pct,
            host_fee_amount=fees.host_fee_amount,
            prize_pool=fees.prize_pool,
            payout_structure=payouts,
            currency=record.currency,
        )

    def _fees_for(self, record: CompetitionRecord) -> CompetitionFeesView:
        return self.fee_service.resolve_fees(
            entry_fee=record.entry_fee,
            participant_count=record.participant_count,
            platform_fee_pct=record.platform_fee_pct,
            host_fee_pct=record.host_fee_pct,
        )

    def _to_summary(
        self,
        record: CompetitionRecord,
        *,
        user_id: str | None = None,
        invite_code: str | None = None,
        join_override: JoinDecision | None = None,
    ) -> CompetitionSummaryView:
        fees = self._fees_for(record)
        decision = join_override or self._join_decision_for(record, user_id=user_id, invite_code=invite_code)
        payouts = self.fee_service.build_payouts(
            prize_pool=fees.prize_pool,
            payout_structure=record.payout_structure,
        )
        return CompetitionSummaryView(
            id=record.id,
            name=record.name,
            format=record.format,
            visibility=record.visibility,
            status=record.status,
            creator_id=record.creator_id,
            creator_name=record.creator_name,
            participant_count=record.participant_count,
            capacity=record.capacity,
            currency=record.currency,
            entry_fee=fees.entry_fee,
            platform_fee_pct=fees.platform_fee_pct,
            host_fee_pct=fees.host_fee_pct,
            platform_fee_amount=fees.platform_fee_amount,
            host_fee_amount=fees.host_fee_amount,
            prize_pool=fees.prize_pool,
            payout_structure=payouts,
            rules_summary=record.rules_summary,
            join_eligibility=JoinEligibilityView(
                eligible=decision.eligible,
                reason=decision.reason,
                requires_invite=decision.requires_invite,
            ),
            beginner_friendly=record.beginner_friendly,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _join_decision_for(
        self,
        record: CompetitionRecord,
        *,
        user_id: str | None,
        invite_code: str | None,
    ) -> JoinDecision:
        already_joined = user_id is not None and any(participant.user_id == user_id for participant in record.participants)
        invite_valid = record.visibility is not CompetitionVisibility.INVITE_ONLY or already_joined
        if record.visibility is CompetitionVisibility.INVITE_ONLY and not already_joined:
            invite_valid = self.invite_service.has_valid_invite(record.id, invite_code)
        return self.join_service.evaluate_join(
            status=record.status,
            visibility=record.visibility,
            participant_count=record.participant_count,
            capacity=record.capacity,
            already_joined=already_joined,
            invite_valid=invite_valid,
        )

    def _validate_against_thread_a_domain(self, payload: CompetitionCreateRequest) -> None:
        domain_payload = backend_competition_create_request(
            payload,
            default_platform_fee_pct=self.fee_service.default_platform_fee_pct,
        )
        try:
            self.creation_service.build_competition(domain_payload)
        except (ValidationError, ValueError) as exc:
            raise CompetitionActionError(str(exc), reason="invalid_competition") from exc

    @staticmethod
    def _invite_view(invite: CompetitionInvite) -> CompetitionInviteView:
        return CompetitionInviteView(
            invite_code=invite.invite_code,
            issued_by=invite.issued_by,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            max_uses=invite.max_uses,
            uses=invite.uses,
            note=invite.note,
        )

    @staticmethod
    def _resolve_payout_structure(payouts: tuple[PayoutRuleRequest, ...] | None) -> tuple[tuple[int, Decimal], ...]:
        if not payouts:
            return (
                (1, Decimal("0.50")),
                (2, Decimal("0.30")),
                (3, Decimal("0.20")),
            )
        return tuple((rule.place, rule.percent) for rule in payouts)

    @staticmethod
    def _payout_rules_from_record(record: CompetitionRecord) -> tuple[PayoutRuleRequest, ...]:
        return tuple(PayoutRuleRequest(place=place, percent=percent) for place, percent in record.payout_structure)


def backend_competition_create_request(
    payload: CompetitionCreateRequest,
    *,
    default_platform_fee_pct: Decimal,
):
    effective_platform_fee = payload.platform_fee_pct if payload.platform_fee_pct is not None else default_platform_fee_pct
    payout_structure = CompetitionOrchestrator._resolve_payout_structure(payload.payout_structure)
    payout_percentages = [int((percent * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) for _, percent in payout_structure]

    core = CompetitionCorePayload(
        host_user_id=payload.creator_id,
        name=payload.name,
        description=payload.rules_summary,
        format=payload.format,
        visibility=payload.visibility,
        start_mode=CompetitionStartMode.WHEN_FULL,
        scheduled_start_at=None,
        status=CompetitionStatus.DRAFT,
    )
    if payload.format is CompetitionFormat.LEAGUE:
        rules = CompetitionRuleSetPayload(
            format=payload.format,
            league_rules=LeagueRuleSetPayload(
                win_points=3,
                draw_points=1,
                loss_points=0,
                tie_break_order=["points", "goal_diff", "goals_for"],
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
                penalties=False,
                min_participants=payload.capacity,
                max_participants=payload.capacity,
                allowed_participant_sizes=[payload.capacity],
            ),
        )
    financials = CompetitionFinancialsPayload(
        entry_fee_minor=_to_minor_units(payload.entry_fee),
        currency=payload.currency,
        platform_fee_bps=int((effective_platform_fee * Decimal("10000")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        host_creation_fee_minor=0,
        payout_mode=CompetitionPayoutMode.CUSTOM_PERCENT,
        top_n=len(payout_percentages),
        payout_percentages=payout_percentages,
    )

    from backend.app.schemas.competition_core import CompetitionCreateRequest as DomainCompetitionCreateRequest

    return DomainCompetitionCreateRequest(core=core, rules=rules, financials=financials)


def _to_minor_units(value: Decimal) -> int:
    return int((value * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


_DEFAULT_ORCHESTRATOR: CompetitionOrchestrator | None = None


def get_competition_orchestrator() -> CompetitionOrchestrator:
    global _DEFAULT_ORCHESTRATOR
    if _DEFAULT_ORCHESTRATOR is None:
        _DEFAULT_ORCHESTRATOR = CompetitionOrchestrator()
    return _DEFAULT_ORCHESTRATOR
