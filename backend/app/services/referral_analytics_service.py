from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.referral_analytics import (
    CommunityGrowthEfficiencyView,
    CreatorCampaignPerformanceView,
    ReferralAnalyticsDailyView,
    ReferralAnalyticsSummaryView,
    ReferralSourceRetentionView,
)
from app.services.referral_orchestrator import (
    AttributionRecord,
    CreatorProfileRecord,
    ReferralOrchestrator,
    RewardRecord,
    ShareCodeRecord,
    utcnow,
)

_FOUR_PLACES = Decimal("0.0001")
_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_QUALIFYING_MILESTONES = frozenset(
    {
        "verification_completed",
        "wallet_funded",
        "first_competition_joined",
        "first_paid_competition_joined",
        "first_creator_competition_joined",
        "retained_day_7",
        "retained_day_30",
        "first_trade",
    }
)


@dataclass(slots=True)
class ShareCodePerformanceMetrics:
    share_code_id: str
    code: str
    share_code_type: str
    owner_user_id: str | None
    owner_creator_id: str | None
    linked_competition_id: str | None
    active: bool
    max_uses: int
    current_uses: int
    attributed_signups: int = 0
    qualified_referrals: int = 0
    creator_competition_joins: int = 0
    retained_users: int = 0
    reward_cost: Decimal = _ZERO
    blocked_rewards: int = 0


@dataclass(slots=True)
class CreatorPerformanceMetrics:
    creator_id: str
    user_id: str
    handle: str
    display_name: str
    tier: str
    status: str
    default_share_code: str | None
    default_competition_id: str | None
    share_code_ids: set[str] = field(default_factory=set)
    attributed_signups: int = 0
    qualified_participants: int = 0
    creator_competition_joins: int = 0
    retained_users: int = 0
    reward_cost: Decimal = _ZERO
    pending_rewards: int = 0
    blocked_rewards: int = 0


@dataclass(slots=True)
class CampaignPerformanceMetrics:
    creator_id: str | None
    creator_handle: str | None
    share_code_id: str | None
    share_code: str | None
    campaign_name: str | None
    linked_competition_id: str | None
    attributed_signups: int = 0
    qualified_participants: int = 0
    creator_competition_joins: int = 0
    retained_users: int = 0
    pending_rewards: int = 0
    approved_rewards: int = 0
    blocked_rewards: int = 0
    reward_cost: Decimal = _ZERO


class ReferralAnalyticsService:
    def __init__(self, orchestrator: ReferralOrchestrator) -> None:
        self.orchestrator = orchestrator

    def build_summary(self) -> ReferralAnalyticsSummaryView:
        share_code_metrics = self.share_code_metrics()
        attributions = self._attributions()
        rewards = self._rewards()
        reward_cost = self._sum_reward_cost(rewards)
        qualified_referrals = sum(1 for attribution in attributions if self._is_qualified(attribution))
        creator_competition_joins = sum(
            1 for attribution in attributions if "first_creator_competition_joined" in attribution.milestones
        )
        retained_users = sum(1 for attribution in attributions if self._is_retained(attribution))
        pending_rewards = sum(1 for reward in rewards if reward.status == "pending")
        approved_rewards = sum(1 for reward in rewards if reward.status == "approved")
        blocked_rewards = sum(1 for reward in rewards if reward.status == "blocked")

        return ReferralAnalyticsSummaryView(
            generated_at=utcnow(),
            codes_created=len(self._share_codes()),
            codes_redeemed=sum(metric.current_uses for metric in share_code_metrics.values()),
            attributed_signups=len(attributions),
            qualified_referrals=qualified_referrals,
            creator_competition_joins=creator_competition_joins,
            retained_users=retained_users,
            reward_cost=reward_cost,
            approved_rewards=approved_rewards,
            blocked_rewards=blocked_rewards,
            pending_rewards=pending_rewards,
            retention_by_source=self.retention_by_source(),
            top_campaigns=self.top_campaigns(),
            daily=self.daily_rollup(),
            efficiency=self.efficiency(),
        )

    def share_code_metrics(self) -> dict[str, ShareCodePerformanceMetrics]:
        share_codes = self._share_codes()
        attributions = self._attributions()
        rewards = self._rewards()

        metrics = {
            share_code.share_code_id: ShareCodePerformanceMetrics(
                share_code_id=share_code.share_code_id,
                code=share_code.code,
                share_code_type=share_code.share_code_type,
                owner_user_id=share_code.owner_user_id,
                owner_creator_id=share_code.owner_creator_id,
                linked_competition_id=share_code.linked_competition_id,
                active=share_code.active,
                max_uses=share_code.max_uses,
                current_uses=share_code.current_uses,
            )
            for share_code in share_codes
        }

        for attribution in attributions:
            metric = metrics.get(attribution.share_code_id)
            if metric is None:
                continue
            metric.attributed_signups += 1
            if self._is_qualified(attribution):
                metric.qualified_referrals += 1
            if "first_creator_competition_joined" in attribution.milestones:
                metric.creator_competition_joins += 1
            if self._is_retained(attribution):
                metric.retained_users += 1

        attribution_by_id = {attribution.attribution_id: attribution for attribution in attributions}
        for reward in rewards:
            attribution = attribution_by_id.get(reward.attribution_id)
            if attribution is None:
                continue
            metric = metrics.get(attribution.share_code_id)
            if metric is None:
                continue
            if reward.status == "blocked":
                metric.blocked_rewards += 1
                continue
            metric.reward_cost += self._reward_amount(reward)

        return metrics

    def creator_metrics(self) -> dict[str, CreatorPerformanceMetrics]:
        creators = self._creators()
        metrics = {
            creator.creator_id: CreatorPerformanceMetrics(
                creator_id=creator.creator_id,
                user_id=creator.user_id,
                handle=creator.handle,
                display_name=creator.display_name,
                tier=creator.tier,
                status=creator.status,
                default_share_code=creator.default_share_code,
                default_competition_id=creator.default_competition_id,
            )
            for creator in creators
        }

        for share_code in self._share_codes():
            if share_code.owner_creator_id is None:
                continue
            metric = metrics.get(share_code.owner_creator_id)
            if metric is not None:
                metric.share_code_ids.add(share_code.share_code_id)

        attributions = self._attributions()
        for attribution in attributions:
            if attribution.creator_profile_id is None:
                continue
            metric = metrics.get(attribution.creator_profile_id)
            if metric is None:
                continue
            metric.attributed_signups += 1
            if self._is_qualified(attribution):
                metric.qualified_participants += 1
            if "first_creator_competition_joined" in attribution.milestones:
                metric.creator_competition_joins += 1
            if self._is_retained(attribution):
                metric.retained_users += 1

        attribution_by_id = {attribution.attribution_id: attribution for attribution in attributions}
        for reward in self._rewards():
            creator_id = reward.beneficiary_creator_id
            if creator_id is None:
                attribution = attribution_by_id.get(reward.attribution_id)
                creator_id = attribution.creator_profile_id if attribution is not None else None
            if creator_id is None:
                continue
            metric = metrics.get(creator_id)
            if metric is None:
                continue
            if reward.status == "pending":
                metric.pending_rewards += 1
            if reward.status == "blocked":
                metric.blocked_rewards += 1
                continue
            metric.reward_cost += self._reward_amount(reward)

        return metrics

    def top_campaigns(self) -> list[CreatorCampaignPerformanceView]:
        campaigns: dict[tuple[str | None, str | None, str | None, str | None], CampaignPerformanceMetrics] = {}
        creators = {creator.creator_id: creator for creator in self._creators()}
        share_codes = {share_code.share_code_id: share_code for share_code in self._share_codes()}
        attributions = self._attributions()

        for attribution in attributions:
            creator = creators.get(attribution.creator_profile_id) if attribution.creator_profile_id is not None else None
            share_code = share_codes.get(attribution.share_code_id)
            key = (
                attribution.creator_profile_id,
                attribution.share_code_id,
                attribution.campaign_name,
                attribution.linked_competition_id,
            )
            metric = campaigns.setdefault(
                key,
                CampaignPerformanceMetrics(
                    creator_id=attribution.creator_profile_id,
                    creator_handle=creator.handle if creator is not None else None,
                    share_code_id=attribution.share_code_id,
                    share_code=share_code.code if share_code is not None else attribution.share_code,
                    campaign_name=attribution.campaign_name,
                    linked_competition_id=attribution.linked_competition_id,
                ),
            )
            metric.attributed_signups += 1
            if self._is_qualified(attribution):
                metric.qualified_participants += 1
            if "first_creator_competition_joined" in attribution.milestones:
                metric.creator_competition_joins += 1
            if self._is_retained(attribution):
                metric.retained_users += 1

        attribution_by_id = {attribution.attribution_id: attribution for attribution in attributions}
        for reward in self._rewards():
            attribution = attribution_by_id.get(reward.attribution_id)
            if attribution is None:
                continue
            key = (
                attribution.creator_profile_id,
                attribution.share_code_id,
                attribution.campaign_name,
                attribution.linked_competition_id,
            )
            metric = campaigns.get(key)
            if metric is None:
                continue
            if reward.status == "pending":
                metric.pending_rewards += 1
            elif reward.status == "approved":
                metric.approved_rewards += 1
            elif reward.status == "blocked":
                metric.blocked_rewards += 1
                continue
            metric.reward_cost += self._reward_amount(reward)

        views = [
            CreatorCampaignPerformanceView(
                creator_id=metric.creator_id,
                creator_handle=metric.creator_handle,
                share_code_id=metric.share_code_id,
                share_code=metric.share_code,
                campaign_name=metric.campaign_name,
                linked_competition_id=metric.linked_competition_id,
                attributed_signups=metric.attributed_signups,
                qualified_participants=metric.qualified_participants,
                creator_competition_joins=metric.creator_competition_joins,
                retained_users=metric.retained_users,
                pending_rewards=metric.pending_rewards,
                approved_rewards=metric.approved_rewards,
                blocked_rewards=metric.blocked_rewards,
                reward_cost=metric.reward_cost,
                participation_quality_rate=self._ratio(metric.qualified_participants, metric.attributed_signups),
                retention_rate=self._ratio(metric.retained_users, metric.attributed_signups),
            )
            for metric in campaigns.values()
        ]
        return sorted(
            views,
            key=lambda item: (
                item.qualified_participants,
                item.retained_users,
                -item.reward_cost,
                item.attributed_signups,
            ),
            reverse=True,
        )

    def retention_by_source(self) -> list[ReferralSourceRetentionView]:
        rollup: dict[str, dict[str, int]] = {}
        for attribution in self._attributions():
            bucket = rollup.setdefault(
                attribution.source_channel,
                {"signups": 0, "retained_day_7": 0, "retained_day_30": 0},
            )
            bucket["signups"] += 1
            if "retained_day_7" in attribution.milestones:
                bucket["retained_day_7"] += 1
            if "retained_day_30" in attribution.milestones:
                bucket["retained_day_30"] += 1

        views = [
            ReferralSourceRetentionView(
                source_channel=source_channel,
                signups=bucket["signups"],
                retained_day_7=bucket["retained_day_7"],
                retained_day_30=bucket["retained_day_30"],
                retention_rate_day_7=self._ratio(bucket["retained_day_7"], bucket["signups"]),
                retention_rate_day_30=self._ratio(bucket["retained_day_30"], bucket["signups"]),
            )
            for source_channel, bucket in rollup.items()
        ]
        return sorted(views, key=lambda item: item.signups, reverse=True)

    def daily_rollup(self) -> list[ReferralAnalyticsDailyView]:
        buckets: dict[date, dict[str, Decimal | int]] = {}

        for share_code in self._share_codes():
            bucket = buckets.setdefault(share_code.created_at.date(), self._new_daily_bucket())
            bucket["codes_created"] += 1

        for attribution in self._attributions():
            bucket = buckets.setdefault(attribution.first_touched_at.date(), self._new_daily_bucket())
            bucket["codes_redeemed"] += 1
            bucket["attributed_signups"] += 1
            if self._is_qualified(attribution):
                bucket["qualified_referrals"] += 1
            if "first_creator_competition_joined" in attribution.milestones:
                bucket["creator_competition_joins"] += 1
            if self._is_retained(attribution):
                bucket["retained_users"] += 1

        for reward in self._rewards():
            bucket = buckets.setdefault(reward.created_at.date(), self._new_daily_bucket())
            if reward.status == "approved":
                bucket["approved_rewards"] += 1
            elif reward.status == "blocked":
                bucket["blocked_rewards"] += 1
                continue
            bucket["reward_cost"] += self._reward_amount(reward)

        return [
            ReferralAnalyticsDailyView(
                metric_date=metric_date,
                analytics_date=metric_date,
                scope="global",
                codes_created=int(bucket["codes_created"]),
                codes_redeemed=int(bucket["codes_redeemed"]),
                attributed_signups=int(bucket["attributed_signups"]),
                qualified_referrals=int(bucket["qualified_referrals"]),
                creator_competition_joins=int(bucket["creator_competition_joins"]),
                retained_users=int(bucket["retained_users"]),
                approved_rewards=int(bucket["approved_rewards"]),
                blocked_rewards=int(bucket["blocked_rewards"]),
                reward_cost=Decimal(bucket["reward_cost"]),
            )
            for metric_date, bucket in sorted(buckets.items())
        ]

    def efficiency(self) -> CommunityGrowthEfficiencyView:
        attributions = self._attributions()
        rewards = self._rewards()
        reward_cost = self._sum_reward_cost(rewards)
        qualified_referrals = sum(1 for attribution in attributions if self._is_qualified(attribution))
        retained_users = sum(1 for attribution in attributions if self._is_retained(attribution))
        blocked_rewards = sum(1 for reward in rewards if reward.status == "blocked")

        cost_per_qualified = (
            (reward_cost / Decimal(qualified_referrals)).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)
            if qualified_referrals > 0
            else reward_cost
        )
        retained_per_100 = (
            ((Decimal(retained_users) * _HUNDRED) / reward_cost).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)
            if reward_cost > 0
            else _ZERO
        )
        efficiency = (
            (
                (Decimal(qualified_referrals) * Decimal("2"))
                + (Decimal(retained_users) * Decimal("3"))
                - Decimal(blocked_rewards)
            )
            / (reward_cost if reward_cost > 0 else Decimal("1"))
        ).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)

        return CommunityGrowthEfficiencyView(
            reward_cost=reward_cost,
            qualified_referrals=qualified_referrals,
            retained_users=retained_users,
            blocked_rewards=blocked_rewards,
            cost_per_qualified_referral=cost_per_qualified,
            retained_users_per_100_credits=retained_per_100,
            net_community_growth_efficiency=efficiency,
        )

    def _share_codes(self) -> tuple[ShareCodeRecord, ...]:
        with self.orchestrator.store.lock:
            return tuple(self.orchestrator.store.share_codes_by_id.values())

    def _creators(self) -> tuple[CreatorProfileRecord, ...]:
        with self.orchestrator.store.lock:
            return tuple(self.orchestrator.store.creators_by_id.values())

    def _attributions(self) -> tuple[AttributionRecord, ...]:
        with self.orchestrator.store.lock:
            return tuple(self.orchestrator.store.attributions_by_id.values())

    def _rewards(self) -> tuple[RewardRecord, ...]:
        with self.orchestrator.store.lock:
            return tuple(self.orchestrator.store.rewards_by_id.values())

    @staticmethod
    def _is_qualified(attribution: AttributionRecord) -> bool:
        return attribution.attribution_status == "qualified" or any(
            milestone in _QUALIFYING_MILESTONES for milestone in attribution.milestones
        )

    @staticmethod
    def _is_retained(attribution: AttributionRecord) -> bool:
        return "retained_day_7" in attribution.milestones or "retained_day_30" in attribution.milestones

    @staticmethod
    def _reward_amount(reward: RewardRecord) -> Decimal:
        return _ZERO if reward.amount is None else Decimal(reward.amount)

    def _sum_reward_cost(self, rewards: tuple[RewardRecord, ...]) -> Decimal:
        total = _ZERO
        for reward in rewards:
            if reward.status in {"blocked", "reversed"}:
                continue
            total += self._reward_amount(reward)
        return total.quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> Decimal:
        if denominator <= 0:
            return _ZERO
        return (Decimal(numerator) / Decimal(denominator)).quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)

    @staticmethod
    def _new_daily_bucket() -> dict[str, Decimal | int]:
        return {
            "codes_created": 0,
            "codes_redeemed": 0,
            "attributed_signups": 0,
            "qualified_referrals": 0,
            "creator_competition_joins": 0,
            "retained_users": 0,
            "approved_rewards": 0,
            "blocked_rewards": 0,
            "reward_cost": _ZERO,
        }
