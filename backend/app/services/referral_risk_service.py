from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Mapping

from app.schemas.referral_admin import ReferralFlagView
from app.services.referral_analytics_service import ReferralAnalyticsService
from app.services.referral_orchestrator import AttributionRecord, ReferralOrchestrator, utcnow

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class ReferralRiskContext:
    device_fingerprint: str | None = None
    joined_at: datetime | None = None
    funded_at: datetime | None = None


class ReferralRiskService:
    def __init__(self, orchestrator: ReferralOrchestrator) -> None:
        self.orchestrator = orchestrator
        self.analytics = ReferralAnalyticsService(orchestrator)

    def scan(self, *, user_contexts: Mapping[str, ReferralRiskContext] | None = None) -> list[ReferralFlagView]:
        flags: dict[str, ReferralFlagView] = {}
        share_code_metrics = self.analytics.share_code_metrics()
        creator_metrics = self.analytics.creator_metrics()
        attributions = self._attributions()
        blocked_actions = self._blocked_actions()
        total_redemptions = max(sum(metric.attributed_signups for metric in share_code_metrics.values()), 1)

        for user_id, attempts in self._blocked_self_referral_attempts(blocked_actions).items():
            flag = self._build_flag(
                flag_type="self_referral_pattern",
                severity="high" if attempts >= 2 else "medium",
                entity_type="referred_user",
                entity_id=user_id,
                title="Repeated blocked self-referral attempts",
                description="The user repeatedly attempted to redeem a community share code tied to their own account.",
                recommended_action="block_reward_review",
                evidence={"blocked_attempts": attempts},
            )
            flags[flag.flag_id] = flag

        for attribution in attributions:
            if attribution.referred_user_id == attribution.referrer_user_id:
                flag = self._build_flag(
                    flag_type="self_referral_pattern",
                    severity="high",
                    entity_type="referred_user",
                    entity_id=attribution.referred_user_id,
                    title="Repeated self-referral pattern",
                    description="The referred user appears to match the referrer identity and should be reviewed before reward approval.",
                    recommended_action="block_reward_review",
                    evidence={
                        "attribution_id": attribution.attribution_id,
                        "share_code": attribution.share_code,
                    },
                )
                flags[flag.flag_id] = flag

        for metric in share_code_metrics.values():
            usage_share = Decimal(metric.attributed_signups) / Decimal(total_redemptions)
            if metric.attributed_signups >= 3 and usage_share >= Decimal("0.7000"):
                flag = self._build_flag(
                    flag_type="redemption_concentration",
                    severity="medium",
                    entity_type="share_code",
                    entity_id=metric.share_code_id,
                    title="Unusual share-code redemption concentration",
                    description="One share code is driving a disproportionate share of invite redemptions, which warrants campaign quality review.",
                    recommended_action="inspect_share_code",
                    evidence={
                        "share_code": metric.code,
                        "usage_share": str(usage_share.quantize(Decimal("0.0001"))),
                        "attributed_signups": metric.attributed_signups,
                    },
                )
                flags[flag.flag_id] = flag

            if metric.blocked_rewards >= 2:
                flag = self._build_flag(
                    flag_type="repeated_blocked_rewards",
                    severity="high",
                    entity_type="share_code",
                    entity_id=metric.share_code_id,
                    title="Repeated blocked rewards on share code",
                    description="This share code has multiple blocked reward decisions and should remain under review.",
                    recommended_action="disable_share_code",
                    evidence={
                        "share_code": metric.code,
                        "blocked_rewards": metric.blocked_rewards,
                    },
                )
                flags[flag.flag_id] = flag

        for creator_id, metric in creator_metrics.items():
            retention_rate = (
                Decimal(metric.retained_users) / Decimal(metric.attributed_signups)
                if metric.attributed_signups > 0
                else _ZERO
            )
            quality_rate = (
                Decimal(metric.qualified_participants) / Decimal(metric.attributed_signups)
                if metric.attributed_signups > 0
                else _ZERO
            )

            if metric.attributed_signups >= 4 and retention_rate < Decimal("0.2000"):
                flag = self._build_flag(
                    flag_type="abnormal_low_retention",
                    severity="medium",
                    entity_type="creator_profile",
                    entity_id=creator_id,
                    title="Low retention on creator campaign traffic",
                    description="Creator invite traffic is converting into signups but not enough retained participants.",
                    recommended_action="review_campaign_quality",
                    evidence={
                        "creator_id": creator_id,
                        "retention_rate": str(retention_rate.quantize(Decimal("0.0001"))),
                        "attributed_signups": metric.attributed_signups,
                    },
                )
                flags[flag.flag_id] = flag

            if metric.attributed_signups >= 3 and metric.reward_cost >= Decimal("5") and quality_rate < Decimal("0.3500"):
                flag = self._build_flag(
                    flag_type="high_reward_cost_low_quality",
                    severity="high",
                    entity_type="creator_profile",
                    entity_id=creator_id,
                    title="High reward cost with weak participation quality",
                    description="Reward cost is rising faster than qualified contest participation for this creator profile.",
                    recommended_action="freeze_creator_rewards",
                    evidence={
                        "creator_id": creator_id,
                        "reward_cost": str(metric.reward_cost),
                        "quality_rate": str(quality_rate.quantize(Decimal("0.0001"))),
                    },
                )
                flags[flag.flag_id] = flag

            if metric.blocked_rewards >= 2:
                flag = self._build_flag(
                    flag_type="repeated_blocked_rewards",
                    severity="high",
                    entity_type="creator_profile",
                    entity_id=creator_id,
                    title="Repeated blocked creator rewards",
                    description="This creator profile has multiple blocked rewards and should stay under manual review.",
                    recommended_action="freeze_creator_rewards",
                    evidence={
                        "creator_id": creator_id,
                        "blocked_rewards": metric.blocked_rewards,
                    },
                )
                flags[flag.flag_id] = flag

        for share_code_id, cluster in self._burst_clusters(attributions).items():
            flag = self._build_flag(
                flag_type="instant_signup_join_burst",
                severity="medium",
                entity_type="share_code",
                entity_id=share_code_id,
                title="Rapid signup and join burst",
                description="Multiple invite signups clustered into a short window around contest-join milestones.",
                recommended_action="inspect_attribution_chain",
                evidence={
                    "share_code_id": share_code_id,
                    "cluster_size": cluster,
                },
            )
            flags[flag.flag_id] = flag

        if user_contexts:
            for share_code_id, evidence in self._same_device_clusters(attributions, user_contexts).items():
                flag = self._build_flag(
                    flag_type="same_device_multi_account_cluster",
                    severity="high",
                    entity_type="share_code",
                    entity_id=share_code_id,
                    title="Same-device multi-account invite cluster",
                    description="Multiple referred accounts on the same device are linked to one share code.",
                    recommended_action="disable_share_code",
                    evidence=evidence,
                )
                flags[flag.flag_id] = flag

        return sorted(flags.values(), key=lambda item: (item.severity, item.flagged_at, item.flag_id), reverse=True)

    def _attributions(self) -> tuple[AttributionRecord, ...]:
        with self.orchestrator.store.lock:
            return tuple(self.orchestrator.store.attributions_by_id.values())

    def _blocked_actions(self):
        with self.orchestrator.store.lock:
            return tuple(self.orchestrator.store.blocked_actions)

    @staticmethod
    def _blocked_self_referral_attempts(blocked_actions) -> dict[str, int]:
        attempts: dict[str, int] = {}
        for action in blocked_actions:
            if action.reason_code != "self_referral_blocked":
                continue
            attempts[action.user_id] = attempts.get(action.user_id, 0) + 1
        return attempts

    @staticmethod
    def _burst_clusters(attributions: tuple[AttributionRecord, ...]) -> dict[str, int]:
        share_code_times: dict[str, list[datetime]] = {}
        for attribution in attributions:
            if not any(
                milestone in attribution.milestones
                for milestone in ("wallet_funded", "first_competition_joined", "first_creator_competition_joined")
            ):
                continue
            share_code_times.setdefault(attribution.share_code_id, []).append(attribution.first_touched_at)

        bursts: dict[str, int] = {}
        window = timedelta(minutes=30)
        for share_code_id, timestamps in share_code_times.items():
            ordered = sorted(timestamps)
            for index, started_at in enumerate(ordered):
                cluster = 1
                for candidate in ordered[index + 1 :]:
                    if candidate - started_at > window:
                        break
                    cluster += 1
                if cluster >= 3:
                    bursts[share_code_id] = cluster
                    break
        return bursts

    @staticmethod
    def _same_device_clusters(
        attributions: tuple[AttributionRecord, ...],
        user_contexts: Mapping[str, ReferralRiskContext],
    ) -> dict[str, dict[str, str | int]]:
        grouped: dict[tuple[str, str], set[str]] = {}
        for attribution in attributions:
            context = user_contexts.get(attribution.referred_user_id)
            if context is None or not context.device_fingerprint:
                continue
            key = (attribution.share_code_id, context.device_fingerprint)
            grouped.setdefault(key, set()).add(attribution.referred_user_id)

        clusters: dict[str, dict[str, str | int]] = {}
        for (share_code_id, fingerprint), user_ids in grouped.items():
            if len(user_ids) < 3:
                continue
            clusters[share_code_id] = {
                "device_fingerprint": fingerprint,
                "cluster_size": len(user_ids),
            }
        return clusters

    @staticmethod
    def _build_flag(
        *,
        flag_type: str,
        severity: str,
        entity_type: str,
        entity_id: str,
        title: str,
        description: str,
        recommended_action: str,
        evidence: dict[str, str | int],
    ) -> ReferralFlagView:
        return ReferralFlagView(
            flag_id=f"{flag_type}:{entity_type}:{entity_id}",
            flag_type=flag_type,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            description=description,
            recommended_action=recommended_action,
            evidence=evidence,
            flagged_at=utcnow(),
        )
