from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from statistics import fmean
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.feedback_engine.service import FeedbackEngine
from app.models.creator_marketplace import (
    CreatorMarketplaceCampaign,
    CreatorMarketplaceParticipation,
    CreatorMarketplaceReputationScore,
)
from app.models.creator_profile import CreatorProfile


@dataclass(frozen=True, slots=True)
class CampaignMatchResult:
    match_score: float
    format_strength_score: float
    audience_match_score: float
    past_performance_score: float
    reasons: tuple[str, ...]


class CreatorMarketplaceMatchingEngine:
    def build_match(
        self,
        session: Session,
        *,
        creator_profile: CreatorProfile,
        campaign: CreatorMarketplaceCampaign,
    ) -> CampaignMatchResult:
        history = session.execute(
            select(CreatorMarketplaceParticipation, CreatorMarketplaceCampaign)
            .join(
                CreatorMarketplaceCampaign,
                CreatorMarketplaceCampaign.id == CreatorMarketplaceParticipation.campaign_id,
            )
            .where(CreatorMarketplaceParticipation.creator_id == creator_profile.id)
        ).all()
        reputation = session.get(CreatorMarketplaceReputationScore, creator_profile.id)

        format_strength_score = self._format_strength_score(
            creator_profile=creator_profile,
            campaign=campaign,
            history=history,
        )
        audience_match_score = self._audience_match_score(creator_profile=creator_profile, campaign=campaign)
        past_performance_score = self._past_performance_score(history=history, reputation=reputation)
        marketplace_rank_boost = FeedbackEngine(session).creator_marketplace_rank_boost(creator_profile.id)
        match_score = round(
            (format_strength_score * 0.45)
            + (audience_match_score * 0.25)
            + (past_performance_score * 0.30),
            2,
        )
        match_score = round(min(100.0, match_score + marketplace_rank_boost), 2)
        reasons = self._build_reasons(
            creator_profile=creator_profile,
            campaign=campaign,
            history=history,
            format_strength_score=format_strength_score,
            audience_match_score=audience_match_score,
            past_performance_score=past_performance_score,
            marketplace_rank_boost=marketplace_rank_boost,
        )
        return CampaignMatchResult(
            match_score=match_score,
            format_strength_score=format_strength_score,
            audience_match_score=audience_match_score,
            past_performance_score=past_performance_score,
            reasons=tuple(reasons),
        )

    def _format_strength_score(
        self,
        *,
        creator_profile: CreatorProfile,
        campaign: CreatorMarketplaceCampaign,
        history: list[tuple[CreatorMarketplaceParticipation, CreatorMarketplaceCampaign]],
    ) -> float:
        formats = self._normalize_tags(campaign.target_formats)
        strengths = self._profile_format_strengths(creator_profile)
        if not formats and not strengths:
            return 50.0

        scores: list[float] = []
        if not formats:
            scores.extend(strengths.values())
        for target_format in formats:
            explicit_score = strengths.get(target_format)
            historical_score = self._historical_format_score(target_format=target_format, history=history)
            if explicit_score is not None and historical_score is not None:
                scores.append(round((explicit_score * 0.7) + (historical_score * 0.3), 2))
            elif explicit_score is not None:
                scores.append(explicit_score)
            elif historical_score is not None:
                scores.append(historical_score)
            else:
                scores.append(50.0)
        return round(fmean(scores), 2) if scores else 50.0

    def _audience_match_score(
        self,
        *,
        creator_profile: CreatorProfile,
        campaign: CreatorMarketplaceCampaign,
    ) -> float:
        creator_tags = self._normalize_tags(self._profile_payload(creator_profile).get("audience_tags"))
        creator_tags.update(self._normalize_tags(self._profile_payload(creator_profile).get("audience_segments")))
        audience = campaign.target_audience or {}
        campaign_tags = self._normalize_tags(audience.get("tags") if isinstance(audience, dict) else audience)
        if isinstance(audience, dict):
            campaign_tags.update(self._normalize_tags(audience.get("interests")))
            campaign_tags.update(self._normalize_tags(audience.get("regions")))
            campaign_tags.update(self._normalize_tags(audience.get("age_bands")))
        if not creator_tags and not campaign_tags:
            return 50.0
        if not creator_tags or not campaign_tags:
            return 50.0
        overlap = creator_tags & campaign_tags
        if not overlap:
            return 0.0
        score = ((len(overlap) / len(campaign_tags)) * 0.7) + ((len(overlap) / len(creator_tags)) * 0.3)
        return round(min(100.0, score * 100.0), 2)

    def _past_performance_score(
        self,
        *,
        history: list[tuple[CreatorMarketplaceParticipation, CreatorMarketplaceCampaign]],
        reputation: CreatorMarketplaceReputationScore | None,
    ) -> float:
        completed_scores = [
            self._score_participation_metrics(participation.performance_metrics)
            for participation, _campaign in history
            if self._has_completed_delivery(participation)
        ]
        if completed_scores:
            baseline = fmean(completed_scores)
            if reputation is None:
                return round(baseline, 2)
            return round(
                (baseline * 0.6)
                + (reputation.campaign_performance_score * 0.25)
                + (reputation.delivery_success_score * 0.15),
                2,
            )
        if reputation is not None:
            return round((reputation.campaign_performance_score * 0.7) + (reputation.reputation_score * 0.3), 2)
        return 50.0

    def _build_reasons(
        self,
        *,
        creator_profile: CreatorProfile,
        campaign: CreatorMarketplaceCampaign,
        history: list[tuple[CreatorMarketplaceParticipation, CreatorMarketplaceCampaign]],
        format_strength_score: float,
        audience_match_score: float,
        past_performance_score: float,
        marketplace_rank_boost: float,
    ) -> list[str]:
        reasons: list[str] = []
        formats = self._normalize_tags(campaign.target_formats)
        if formats:
            reasons.append(
                f"Format strength is {format_strength_score:.1f}/100 for {', '.join(sorted(formats)[:3])}."
            )
        audience_tags = self._normalize_tags((campaign.target_audience or {}).get("tags") if isinstance(campaign.target_audience, dict) else campaign.target_audience)
        creator_audience = self._normalize_tags(self._profile_payload(creator_profile).get("audience_tags"))
        overlap = audience_tags & creator_audience
        if overlap:
            reasons.append(f"Audience overlap covers {', '.join(sorted(overlap)[:3])}.")
        elif audience_match_score > 0:
            reasons.append(f"Audience match scores {audience_match_score:.1f}/100 from creator audience segments.")
        completed_campaigns = sum(1 for participation, _campaign in history if self._has_completed_delivery(participation))
        if completed_campaigns:
            reasons.append(
                f"Past sponsored performance averages {past_performance_score:.1f}/100 across {completed_campaigns} completed campaign(s)."
            )
        else:
            reasons.append("No completed marketplace history yet, so the match leans on declared strengths.")
        if marketplace_rank_boost > 0:
            reasons.append(f"Feedback engine added a {marketplace_rank_boost:.1f} marketplace boost from recent creator wins.")
        return reasons

    def _historical_format_score(
        self,
        *,
        target_format: str,
        history: list[tuple[CreatorMarketplaceParticipation, CreatorMarketplaceCampaign]],
    ) -> float | None:
        scores = [
            self._score_participation_metrics(participation.performance_metrics)
            for participation, campaign in history
            if target_format in self._normalize_tags(campaign.target_formats) and self._has_completed_delivery(participation)
        ]
        if not scores:
            return None
        return round(fmean(scores), 2)

    def _profile_format_strengths(self, creator_profile: CreatorProfile) -> dict[str, float]:
        raw_strengths = self._profile_payload(creator_profile).get("format_strengths") or {}
        if not isinstance(raw_strengths, dict):
            return {}
        strengths: dict[str, float] = {}
        for raw_format, raw_score in raw_strengths.items():
            if not isinstance(raw_format, str):
                continue
            normalized_score = self._normalize_score(raw_score)
            strengths[raw_format.strip().lower()] = normalized_score
        return strengths

    @staticmethod
    def _profile_payload(creator_profile: CreatorProfile) -> dict[str, Any]:
        return creator_profile.payout_config_json or {}

    @staticmethod
    def _has_completed_delivery(participation: CreatorMarketplaceParticipation) -> bool:
        metrics = participation.performance_metrics or {}
        if participation.clips_submitted:
            return True
        return any(bool(metrics.get(key)) for key in ("views", "engagement", "conversions"))

    def _score_participation_metrics(self, metrics: dict[str, Any] | None) -> float:
        payload = metrics or {}
        views = max(0, int(payload.get("views") or 0))
        engagement = max(0, int(payload.get("engagement") or 0))
        conversions = max(0, int(payload.get("conversions") or 0))
        engagement_rate = float(payload.get("engagement_rate") or ((engagement / views) if views else 0.0))
        conversion_rate = float(payload.get("conversion_rate") or ((conversions / views) if views else 0.0))
        engagement_score = min(100.0, engagement_rate * 400.0)
        conversion_score = min(100.0, conversion_rate * 1000.0)
        delivery_bonus = 20.0 if views > 0 else 0.0
        return round((engagement_score * 0.55) + (conversion_score * 0.35) + (delivery_bonus * 0.10), 2)

    @staticmethod
    def _normalize_score(value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 50.0
        if score <= 1:
            score *= 100.0
        return round(max(0.0, min(100.0, score)), 2)

    @classmethod
    def _normalize_tags(cls, value: Any) -> set[str]:
        if value is None:
            return set()
        if isinstance(value, str):
            cleaned = value.strip().lower()
            return {cleaned} if cleaned else set()
        if isinstance(value, dict):
            tags: set[str] = set()
            for nested_value in value.values():
                tags.update(cls._normalize_tags(nested_value))
            return tags
        if isinstance(value, Iterable):
            tags: set[str] = set()
            for item in value:
                tags.update(cls._normalize_tags(item))
            return tags
        return set()
