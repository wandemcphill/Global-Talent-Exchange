from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
from app.models.admin_runtime_state import AdminRuntimeState
from app.models.share_code import ShareCode

from app.schemas.referral_admin import (
    AttributionChainEntryView,
    CreatorAdminSummaryView,
    CreatorRewardFreezeRequest,
    PendingRewardView,
    ReferralAdminDashboardView,
    ReferralFlagView,
    RewardReviewDecisionView,
    RewardReviewRequest,
    ShareCodeModerationRequest,
    ShareCodeUsageSummaryView,
)
from app.schemas.referral_analytics import CreatorLeaderboardResponse, ReferralAnalyticsSummaryView
from app.services.creator_leaderboard_service import CreatorLeaderboardService
from app.services.referral_analytics_service import ReferralAnalyticsService
from app.services.referral_orchestrator import (
    ReferralActionError,
    ReferralOrchestrator,
    ReferralRuntimeStore,
    RewardRecord,
    utcnow,
)
from app.services.referral_risk_service import ReferralRiskService

_FOUR_PLACES = Decimal("0.0001")
_SHARE_CODE_MODERATION_STATE_PREFIX = "referral_share_code_moderation:"
_CREATOR_REWARD_FREEZE_STATE_PREFIX = "referral_creator_reward_freeze:"


@dataclass(slots=True)
class ShareCodeModerationState:
    share_code_id: str
    blocked: bool
    reason: str
    updated_by_admin_id: str
    updated_at: datetime


@dataclass(slots=True)
class CreatorRewardFreezeState:
    creator_id: str
    frozen: bool
    reason: str
    updated_by_admin_id: str
    updated_at: datetime


@dataclass(slots=True)
class ReferralAdminRuntimeStore:
    blocked_share_codes: dict[str, ShareCodeModerationState] = field(default_factory=dict)
    creator_reward_freezes: dict[str, CreatorRewardFreezeState] = field(default_factory=dict)


class ReferralAdminService:
    def __init__(
        self,
        orchestrator: ReferralOrchestrator,
        *,
        runtime_store: ReferralAdminRuntimeStore | None = None,
        session: Session | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.runtime_store = runtime_store or ReferralAdminRuntimeStore()
        self.session = session
        self.analytics = ReferralAnalyticsService(orchestrator)
        self.risk = ReferralRiskService(orchestrator)
        self.leaderboard = CreatorLeaderboardService(orchestrator)
        self._share_code_state_cache: dict[str, ShareCodeModerationState] | None = None
        self._creator_freeze_state_cache: dict[str, CreatorRewardFreezeState] | None = None

    def dashboard(self) -> ReferralAdminDashboardView:
        share_codes = self.analytics.share_code_metrics()
        flags = self.list_flags()
        pending_rewards = len(self.list_pending_rewards())
        blocked_states = self._share_code_moderation_states()
        frozen_states = self._creator_reward_freeze_states()
        return ReferralAdminDashboardView(
            total_share_codes=len(share_codes),
            active_share_codes=sum(1 for metric in share_codes.values() if metric.active),
            pending_rewards=pending_rewards,
            blocked_share_codes=sum(1 for state in blocked_states.values() if state.blocked),
            frozen_creators=sum(1 for state in frozen_states.values() if state.frozen),
            total_flags=len(flags),
            high_severity_flags=sum(1 for flag in flags if flag.severity == "high"),
            recent_flags=flags[:5],
        )

    def list_share_codes(self) -> list[ShareCodeUsageSummaryView]:
        share_code_metrics = self.analytics.share_code_metrics()
        total_signups = sum(item.attributed_signups for item in share_code_metrics.values()) or 1
        flags_by_entity = self._flags_by_entity()
        items = [
            self._build_share_code_summary(metric, total_signups, flags_by_entity)
            for metric in share_code_metrics.values()
        ]
        return sorted(items, key=lambda item: (item.current_uses, item.attributed_signups, item.code), reverse=True)

    def get_share_code(self, share_code_id: str) -> ShareCodeUsageSummaryView | None:
        share_code_metrics = self.analytics.share_code_metrics()
        metric = share_code_metrics.get(share_code_id)
        if metric is None:
            return None
        total_signups = sum(item.attributed_signups for item in share_code_metrics.values()) or 1
        return self._build_share_code_summary(metric, total_signups, self._flags_by_entity())

    def block_share_code(
        self,
        *,
        share_code_id: str,
        admin_user_id: str,
        payload: ShareCodeModerationRequest,
    ) -> ShareCodeUsageSummaryView:
        changed_at = utcnow()
        if self.session is not None:
            share_code = self.session.get(ShareCode, share_code_id)
            if share_code is None:
                raise ReferralActionError("share_code_not_found")
            share_code.is_active = not payload.disable_code
            share_code.updated_at = changed_at
            self.session.flush()
        else:
            with self.orchestrator.store.lock:
                share_code = self.orchestrator.store.share_codes_by_id.get(share_code_id)
                if share_code is None:
                    raise ReferralActionError("share_code_not_found")
                share_code.active = not payload.disable_code
                share_code.updated_at = changed_at

        state = ShareCodeModerationState(
            share_code_id=share_code_id,
            blocked=payload.disable_code,
            reason=payload.reason,
            updated_by_admin_id=admin_user_id,
            updated_at=changed_at,
        )
        self._save_share_code_moderation_state(state)
        result = self.get_share_code(share_code_id)
        if result is None:
            raise ReferralActionError("share_code_not_found")
        return result

    def list_creators(self) -> list[CreatorAdminSummaryView]:
        creator_metrics = self.analytics.creator_metrics()
        share_codes = self.list_share_codes()
        flags_by_entity = self._flags_by_entity()
        items = [
            self._build_creator_summary(creator_id, metric, share_codes, flags_by_entity)
            for creator_id, metric in creator_metrics.items()
        ]
        return sorted(items, key=lambda item: (item.attributed_signups, item.retained_users, item.handle), reverse=True)

    def get_creator(self, creator_id: str) -> CreatorAdminSummaryView | None:
        creator_metrics = self.analytics.creator_metrics()
        metric = creator_metrics.get(creator_id)
        if metric is None:
            return None
        share_codes = self.list_share_codes()
        return self._build_creator_summary(creator_id, metric, share_codes, self._flags_by_entity())

    def set_creator_reward_freeze(
        self,
        *,
        creator_id: str,
        admin_user_id: str,
        payload: CreatorRewardFreezeRequest,
    ) -> CreatorAdminSummaryView:
        creator = self.get_creator(creator_id)
        if creator is None:
            raise ReferralActionError("creator_not_found")
        state = CreatorRewardFreezeState(
            creator_id=creator_id,
            frozen=payload.freeze,
            reason=payload.reason,
            updated_by_admin_id=admin_user_id,
            updated_at=utcnow(),
        )
        self._save_creator_reward_freeze_state(state)
        refreshed = self.get_creator(creator_id)
        if refreshed is None:
            raise ReferralActionError("creator_not_found")
        return refreshed

    def list_attributions(
        self,
        *,
        share_code_id: str | None = None,
        creator_id: str | None = None,
        attribution_status: str | None = None,
    ) -> list[AttributionChainEntryView]:
        rewards = self.orchestrator.rewards.list_all()
        attributions = self.orchestrator.attributions.list_all()

        rewards_by_attribution: dict[str, list[RewardRecord]] = {}
        for reward in rewards:
            rewards_by_attribution.setdefault(reward.attribution_id, []).append(reward)

        items = []
        for attribution in attributions:
            if share_code_id is not None and attribution.share_code_id != share_code_id:
                continue
            if creator_id is not None and attribution.creator_profile_id != creator_id:
                continue
            if attribution_status is not None and attribution.attribution_status != attribution_status:
                continue
            related_rewards = rewards_by_attribution.get(attribution.attribution_id, [])
            items.append(
                AttributionChainEntryView(
                    attribution_id=attribution.attribution_id,
                    referred_user_id=attribution.referred_user_id,
                    referrer_user_id=attribution.referrer_user_id,
                    creator_profile_id=attribution.creator_profile_id,
                    share_code_id=attribution.share_code_id,
                    share_code=attribution.share_code,
                    source_channel=attribution.source_channel,
                    attribution_status=attribution.attribution_status,
                    campaign_name=attribution.campaign_name,
                    linked_competition_id=attribution.linked_competition_id,
                    first_touched_at=attribution.first_touched_at,
                    milestones=list(attribution.milestones),
                    reward_ids=[reward.reward_id for reward in related_rewards],
                    reward_statuses=[reward.status for reward in related_rewards],
                )
            )
        return sorted(items, key=lambda item: item.first_touched_at, reverse=True)

    def list_pending_rewards(self) -> list[PendingRewardView]:
        rewards = self.orchestrator.rewards.list_all()
        attributions = {
            attribution.attribution_id: attribution
            for attribution in self.orchestrator.attributions.list_all()
        }
        items = []
        for reward in rewards:
            if reward.status != "pending":
                continue
            attribution = attributions.get(reward.attribution_id)
            creator_id = reward.beneficiary_creator_id or (attribution.creator_profile_id if attribution is not None else None)
            items.append(
                PendingRewardView(
                    reward_id=reward.reward_id,
                    attribution_id=reward.attribution_id,
                    beneficiary_user_id=reward.beneficiary_user_id,
                    beneficiary_creator_id=reward.beneficiary_creator_id,
                    reward_type=reward.reward_type,
                    status=reward.status,
                    trigger_milestone=reward.trigger_milestone,
                    amount=reward.amount,
                    unit=reward.unit,
                    label=reward.label,
                    hold_until=reward.hold_until,
                    review_reason=reward.review_reason,
                    created_at=reward.created_at,
                    updated_at=reward.updated_at,
                    approval_frozen=self._creator_frozen(creator_id),
                )
            )
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def review_reward(
        self,
        *,
        reward_id: str,
        admin_user_id: str,
        payload: RewardReviewRequest,
    ) -> RewardReviewDecisionView:
        reward = self.orchestrator.rewards.get_by_id(reward_id)
        if reward is None:
            raise ReferralActionError("reward_not_found")
        attribution = self.orchestrator.attributions.get_by_id(reward.attribution_id)
        creator_id = reward.beneficiary_creator_id or (attribution.creator_profile_id if attribution is not None else None)
        if payload.action == "approve" and self._creator_frozen(creator_id):
            raise ReferralActionError("creator_rewards_frozen")
        updated = self.orchestrator.rewards.apply_review_decision(
            reward_id=reward_id,
            action=payload.action,
            reason=payload.reason,
            reference=payload.reference,
            admin_user_id=admin_user_id,
        )
        return RewardReviewDecisionView(
            reward_id=reward_id,
            action=payload.action,
            status_after=updated.status,
            reason=payload.reason,
            reference=payload.reference,
            performed_by_admin_id=admin_user_id,
            performed_at=updated.updated_at,
        )

    def list_flags(self) -> list[ReferralFlagView]:
        automated = self.risk.scan()
        manual = self._manual_flags()
        deduped = {flag.flag_id: flag for flag in [*automated, *manual]}
        return sorted(deduped.values(), key=lambda item: (item.flagged_at, item.flag_id), reverse=True)

    def analytics_summary(self) -> ReferralAnalyticsSummaryView:
        return self.analytics.build_summary()

    def creator_leaderboard(self) -> CreatorLeaderboardResponse:
        return self.leaderboard.build()

    def _build_share_code_summary(self, metric, total_signups: int, flags_by_entity: dict[tuple[str, str], list[ReferralFlagView]]) -> ShareCodeUsageSummaryView:
        flags = flags_by_entity.get(("share_code", metric.share_code_id), [])
        return ShareCodeUsageSummaryView(
            code_id=metric.share_code_id,
            code=metric.code,
            share_code_type=metric.share_code_type,
            owner_user_id=metric.owner_user_id,
            owner_creator_id=metric.owner_creator_id,
            linked_competition_id=metric.linked_competition_id,
            active=metric.active,
            max_uses=metric.max_uses,
            current_uses=metric.current_uses,
            usage_share=(Decimal(metric.attributed_signups) / Decimal(total_signups)).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP),
            attributed_signups=metric.attributed_signups,
            qualified_referrals=metric.qualified_referrals,
            creator_competition_joins=metric.creator_competition_joins,
            retained_users=metric.retained_users,
            reward_cost=metric.reward_cost.quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP),
            blocked_rewards=metric.blocked_rewards,
            approval_frozen=self._creator_frozen(metric.owner_creator_id),
            flagged=bool(flags),
            flags=flags,
        )

    def _build_creator_summary(self, creator_id: str, metric, share_codes: list[ShareCodeUsageSummaryView], flags_by_entity: dict[tuple[str, str], list[ReferralFlagView]]) -> CreatorAdminSummaryView:
        creator_share_codes = [item for item in share_codes if item.owner_creator_id == creator_id]
        flags = [
            *flags_by_entity.get(("creator_profile", creator_id), []),
            *[flag for share_code in creator_share_codes for flag in share_code.flags],
        ]
        return CreatorAdminSummaryView(
            creator_id=creator_id,
            user_id=metric.user_id,
            handle=metric.handle,
            display_name=metric.display_name,
            tier=metric.tier,
            status=metric.status,
            default_share_code=metric.default_share_code,
            default_competition_id=metric.default_competition_id,
            share_code_count=len(metric.share_code_ids),
            attributed_signups=metric.attributed_signups,
            qualified_participants=metric.qualified_participants,
            creator_competition_joins=metric.creator_competition_joins,
            retained_users=metric.retained_users,
            reward_cost=metric.reward_cost.quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP),
            pending_rewards=metric.pending_rewards,
            blocked_rewards=metric.blocked_rewards,
            approval_frozen=self._creator_frozen(creator_id),
            top_share_codes=creator_share_codes[:3],
            flags=flags,
        )

    def _manual_flags(self) -> list[ReferralFlagView]:
        flags: list[ReferralFlagView] = []
        for state in self._share_code_moderation_states().values():
            if not state.blocked:
                continue
            flags.append(
                ReferralFlagView(
                    flag_id=f"manual_share_code_block:{state.share_code_id}",
                    flag_type="manual_share_code_block",
                    severity="high",
                    entity_type="share_code",
                    entity_id=state.share_code_id,
                    title="Share code manually blocked",
                    description=state.reason,
                    recommended_action="inspect_share_code",
                    evidence={"admin_user_id": state.updated_by_admin_id},
                    flagged_at=state.updated_at,
                )
            )
        for state in self._creator_reward_freeze_states().values():
            if not state.frozen:
                continue
            flags.append(
                ReferralFlagView(
                    flag_id=f"manual_creator_reward_freeze:{state.creator_id}",
                    flag_type="manual_creator_reward_freeze",
                    severity="high",
                    entity_type="creator_profile",
                    entity_id=state.creator_id,
                    title="Creator reward approval frozen",
                    description=state.reason,
                    recommended_action="review_pending_rewards",
                    evidence={"admin_user_id": state.updated_by_admin_id},
                    flagged_at=state.updated_at,
                )
            )
        return flags

    def _flags_by_entity(self) -> dict[tuple[str, str], list[ReferralFlagView]]:
        grouped: dict[tuple[str, str], list[ReferralFlagView]] = {}
        for flag in self.list_flags():
            grouped.setdefault((flag.entity_type, flag.entity_id), []).append(flag)
        return grouped

    def _creator_frozen(self, creator_id: str | None) -> bool:
        if creator_id is None:
            return False
        state = self._creator_reward_freeze_states().get(creator_id)
        return state.frozen if state is not None else False

    def _share_code_moderation_states(self) -> dict[str, ShareCodeModerationState]:
        if self._share_code_state_cache is not None:
            return self._share_code_state_cache
        if self.session is None:
            self._share_code_state_cache = dict(self.runtime_store.blocked_share_codes)
            return self._share_code_state_cache
        rows = tuple(
            self.session.scalars(
                select(AdminRuntimeState).where(
                    AdminRuntimeState.state_key.like(f"{_SHARE_CODE_MODERATION_STATE_PREFIX}%")
                )
            ).all()
        )
        states: dict[str, ShareCodeModerationState] = {}
        for row in rows:
            state = self._share_code_moderation_state_from_row(row)
            if state is not None:
                states[state.share_code_id] = state
        self.runtime_store.blocked_share_codes = dict(states)
        self._share_code_state_cache = states
        return states

    def _creator_reward_freeze_states(self) -> dict[str, CreatorRewardFreezeState]:
        if self._creator_freeze_state_cache is not None:
            return self._creator_freeze_state_cache
        if self.session is None:
            self._creator_freeze_state_cache = dict(self.runtime_store.creator_reward_freezes)
            return self._creator_freeze_state_cache
        rows = tuple(
            self.session.scalars(
                select(AdminRuntimeState).where(
                    AdminRuntimeState.state_key.like(f"{_CREATOR_REWARD_FREEZE_STATE_PREFIX}%")
                )
            ).all()
        )
        states: dict[str, CreatorRewardFreezeState] = {}
        for row in rows:
            state = self._creator_reward_freeze_state_from_row(row)
            if state is not None:
                states[state.creator_id] = state
        self.runtime_store.creator_reward_freezes = dict(states)
        self._creator_freeze_state_cache = states
        return states

    def _save_share_code_moderation_state(self, state: ShareCodeModerationState) -> None:
        self._share_code_moderation_states()[state.share_code_id] = state
        self.runtime_store.blocked_share_codes[state.share_code_id] = state
        if self.session is not None:
            self._save_runtime_state_record(
                state_key=f"{_SHARE_CODE_MODERATION_STATE_PREFIX}{state.share_code_id}",
                payload_json={
                    "share_code_id": state.share_code_id,
                    "blocked": state.blocked,
                    "reason": state.reason,
                    "updated_by_admin_id": state.updated_by_admin_id,
                    "updated_at": state.updated_at.isoformat(),
                },
            )

    def _save_creator_reward_freeze_state(self, state: CreatorRewardFreezeState) -> None:
        self._creator_reward_freeze_states()[state.creator_id] = state
        self.runtime_store.creator_reward_freezes[state.creator_id] = state
        if self.session is not None:
            self._save_runtime_state_record(
                state_key=f"{_CREATOR_REWARD_FREEZE_STATE_PREFIX}{state.creator_id}",
                payload_json={
                    "creator_id": state.creator_id,
                    "frozen": state.frozen,
                    "reason": state.reason,
                    "updated_by_admin_id": state.updated_by_admin_id,
                    "updated_at": state.updated_at.isoformat(),
                },
            )

    def _save_runtime_state_record(self, *, state_key: str, payload_json: dict[str, object]) -> None:
        if self.session is None:
            return
        row = self.session.scalar(select(AdminRuntimeState).where(AdminRuntimeState.state_key == state_key))
        if row is None:
            self.session.add(AdminRuntimeState(state_key=state_key, payload_json=dict(payload_json)))
            self.session.flush()
            return
        row.payload_json = dict(payload_json)
        self.session.flush()

    @staticmethod
    def _share_code_moderation_state_from_row(row: AdminRuntimeState) -> ShareCodeModerationState | None:
        payload = dict(row.payload_json or {})
        share_code_id = str(payload.get("share_code_id") or row.state_key.removeprefix(_SHARE_CODE_MODERATION_STATE_PREFIX))
        if not share_code_id:
            return None
        return ShareCodeModerationState(
            share_code_id=share_code_id,
            blocked=bool(payload.get("blocked", False)),
            reason=str(payload.get("reason") or ""),
            updated_by_admin_id=str(payload.get("updated_by_admin_id") or ""),
            updated_at=_parse_state_timestamp(payload.get("updated_at")),
        )

    @staticmethod
    def _creator_reward_freeze_state_from_row(row: AdminRuntimeState) -> CreatorRewardFreezeState | None:
        payload = dict(row.payload_json or {})
        creator_id = str(payload.get("creator_id") or row.state_key.removeprefix(_CREATOR_REWARD_FREEZE_STATE_PREFIX))
        if not creator_id:
            return None
        return CreatorRewardFreezeState(
            creator_id=creator_id,
            frozen=bool(payload.get("frozen", False)),
            reason=str(payload.get("reason") or ""),
            updated_by_admin_id=str(payload.get("updated_by_admin_id") or ""),
            updated_at=_parse_state_timestamp(payload.get("updated_at")),
        )


def get_referral_admin_service(
    request: Request,
    session: Session = Depends(get_session),
) -> ReferralAdminService:
    runtime_store = getattr(request.app.state, "referral_admin_runtime_store", None)
    if runtime_store is None:
        runtime_store = getattr(request.app.state, "referral_admin_store", None)
    if runtime_store is None:
        runtime_store = ReferralAdminRuntimeStore()
    request.app.state.referral_admin_runtime_store = runtime_store

    orchestrator = getattr(request.app.state, "referral_orchestrator", None)
    if orchestrator is None:
        runtime_referral_store = getattr(request.app.state, "referral_runtime_store", None)
        if runtime_referral_store is None:
            runtime_referral_store = getattr(request.app.state, "referral_store", None)
        if runtime_referral_store is None:
            runtime_referral_store = ReferralRuntimeStore()
        request.app.state.referral_runtime_store = runtime_referral_store
        orchestrator = ReferralOrchestrator(store=runtime_referral_store, session=session)
    elif session is not None and getattr(orchestrator, "session", None) is None:
        orchestrator = ReferralOrchestrator(store=orchestrator.store, session=session)

    return ReferralAdminService(orchestrator, runtime_store=runtime_store, session=session)


def _parse_state_timestamp(value: object) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return utcnow()
