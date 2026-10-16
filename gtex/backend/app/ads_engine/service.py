from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, ROUND_FLOOR
import json
import logging
from typing import Any

from fastapi import FastAPI
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.backbone.scale_events import enqueue_ads_feed_refresh
from app.ads_engine.schemas import (
    SponsoredClipCreateRequest,
    SponsoredClipPerformanceResponse,
    SponsoredClipPerformanceSummaryView,
    SponsoredClipPerformanceView,
    SponsoredClipTargetAudienceView,
    SponsoredFeedCampaignView,
    SponsoredFeedItemView,
    SponsoredFeedResponse,
    SponsoredFeedScoreView,
    SponsoredFeedTrackingView,
    SponsoredRevenueAttributionView,
)
from app.ads_engine.unified_ranking import AD_FREQUENCY_WINDOW, UnifiedFeedCandidate, rank_unified_feed
from app.analytics.service import AnalyticsService
from app.core.config import Settings, get_settings
from app.core.trust_middleware import SharedTrustMiddleware
from app.infinite_league.service import ensure_infinite_league_runtime
from app.models.sponsored_clip import SponsoredClip
from app.models.user import User
from app.models.user_affinity_profile import UserAffinityProfile
from app.models.user_region import UserRegionProfile
from app.runtime_config.service import ensure_runtime_config_loader
from app.services.creator_attention_earnings_service import CreatorAttentionEarningsService
from app.services.ads.analytics import build_tracking_token
from app.viral.personalized_feed_service import build_personalized_feed_service
from app.viral.schemas import ViralClipView
from app.viral.service import ViralFeedService
from app.viral.trust_metrics import ClipTrustMetricsReader, ClipTrustSummary, build_clip_trust_metrics_reader

logger = logging.getLogger(__name__)

ACTIVE_AD_SET_KEY = "ad:active"
TRACKING_IMPRESSION_EVENT = "sponsored_clip.impression"
TRACKING_CLICK_EVENT = "sponsored_clip.click"
TRACKING_WATCH_EVENT = "sponsored_clip.watch"
TRACKING_CONVERSION_EVENT = "sponsored_clip.conversion"
IMPRESSION_EVENT_NAMES = frozenset({TRACKING_IMPRESSION_EVENT, "clip.view"})
CLICK_EVENT_NAMES = frozenset({TRACKING_CLICK_EVENT, "clip.click"})
WATCH_EVENT_NAMES = frozenset({TRACKING_WATCH_EVENT, "clip.complete"})
CONVERSION_EVENT_NAMES = frozenset({TRACKING_CONVERSION_EVENT, "clip.conversion"})
MAX_CLIP_LOOKUP = 120
CPM_IMPRESSION_FACTOR = Decimal("1000")
MONEY_QUANTUM = Decimal("0.0001")


class SponsoredClipServiceError(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _clamp(value: float, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _normalize_key(value: Any) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip().lower()
    return candidate or None


def _normalize_region(value: Any) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip().upper()
    return candidate or None


def _dedupe_values(values: list[str], *, region: bool = False) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = _normalize_region(value) if region else _normalize_key(value)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def _normalized_affinity_map(values: dict[str, float] | None) -> dict[str, float]:
    mapping: dict[str, float] = {}
    for key, value in dict(values or {}).items():
        normalized = _normalize_key(key)
        if normalized is None:
            continue
        mapping[normalized] = max(mapping.get(normalized, 0.0), _clamp(_safe_float(value)))
    return mapping


def _cache_payload(ad: SponsoredClip) -> dict[str, Any]:
    return {
        "id": ad.id,
        "advertiser_id": ad.advertiser_id,
        "clip_id": ad.clip_id,
        "budget": str(ad.budget),
        "bid_cpm": str(ad.bid_cpm),
        "start_time": _as_utc(ad.start_time).isoformat(),
        "end_time": _as_utc(ad.end_time).isoformat(),
        "is_active": bool(ad.is_active),
        "impressions_served": int(ad.impressions_served or 0),
        "clicks": int(ad.clicks or 0),
        "conversions": int(ad.conversions or 0),
        "target_audience": {
            "formats": list(ad.target_formats_json or []),
            "creators": list(ad.target_creators_json or []),
            "regions": list(ad.target_regions_json or []),
        },
    }


@dataclass(slots=True)
class SponsoredClipCache:
    redis_url: str | None = None
    _client: Redis | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.redis_url:
            return
        try:
            self._client = Redis.from_url(self.redis_url, decode_responses=True)
            self._client.ping()
        except RedisError:
            logger.warning("ads_engine.redis.unavailable")
            self._client = None

    def active_ids(self) -> set[str] | None:
        if self._client is None:
            return None
        try:
            return {str(item) for item in self._client.smembers(ACTIVE_AD_SET_KEY)}
        except RedisError:
            logger.warning("ads_engine.redis.active_ids_failed")
            return None

    def sync(self, ad: SponsoredClip, *, active: bool) -> None:
        if self._client is None:
            return
        try:
            pipeline = self._client.pipeline()
            pipeline.set(f"ad:{ad.id}", json.dumps(_cache_payload(ad), default=str))
            if active:
                pipeline.sadd(ACTIVE_AD_SET_KEY, ad.id)
            else:
                pipeline.srem(ACTIVE_AD_SET_KEY, ad.id)
            pipeline.execute()
        except RedisError:
            logger.warning("ads_engine.redis.sync_failed ad_id=%s", ad.id)


@dataclass(slots=True)
class AudienceContext:
    user_id: str
    region: str | None
    favorite_formats: dict[str, float]
    favorite_creators: dict[str, float]
    engagement_score: float
    avg_watch_time: float
    skip_rate: float


@dataclass(slots=True)
class OrganicCandidate:
    clip: ViralClipView
    organic_score: float
    organic_rank: int


@dataclass(slots=True)
class RankedSponsoredCandidate:
    ad: SponsoredClip
    clip: ViralClipView
    relevance_score: float
    expected_engagement: float
    ad_score: float
    pacing_state: str
    remaining_impressions: int
    trust_summary: ClipTrustSummary


def build_sponsored_clip_cache(*, settings: Settings | None = None) -> SponsoredClipCache:
    resolved_settings = settings
    if resolved_settings is None:
        try:
            resolved_settings = get_settings()
        except Exception:
            resolved_settings = None
    return SponsoredClipCache(redis_url=(resolved_settings.redis_url if resolved_settings is not None else None))


def ensure_sponsored_clip_cache(app: FastAPI, *, settings: Settings | None = None) -> SponsoredClipCache:
    cache = getattr(app.state, "sponsored_clip_cache", None)
    if cache is None:
        cache = build_sponsored_clip_cache(settings=settings or getattr(app.state, "settings", None))
        app.state.sponsored_clip_cache = cache
    return cache


@dataclass(slots=True)
class SponsoredClipTrackingService:
    session: Session
    app: FastAPI | None = None
    settings: Settings | None = None
    cache: SponsoredClipCache | None = None

    def __post_init__(self) -> None:
        if self.settings is None:
            if self.app is not None:
                self.settings = getattr(self.app.state, "settings", None)
            if self.settings is None:
                try:
                    self.settings = get_settings()
                except Exception:
                    self.settings = None
        if self.cache is None:
            self.cache = ensure_sponsored_clip_cache(self.app, settings=self.settings) if self.app is not None else build_sponsored_clip_cache(settings=self.settings)

    def track_event(self, *, name: str, metadata: dict[str, Any] | None = None) -> SponsoredClip | None:
        payload = dict(metadata or {})
        ad_id = payload.get("ad_id")
        if not isinstance(ad_id, str) or not ad_id.strip():
            return None

        event_name = str(name).strip().lower()
        impression_delta = 1 if event_name in IMPRESSION_EVENT_NAMES else 0
        click_delta = 1 if event_name in CLICK_EVENT_NAMES else 0
        conversion_delta = 1 if event_name in CONVERSION_EVENT_NAMES else 0
        watch_delta = 0.0
        if event_name in WATCH_EVENT_NAMES:
            watch_delta = max(
                _safe_float(payload.get("watch_time_seconds"), default=_safe_float(payload.get("watch_time"), default=0.0)),
                0.0,
            )
        if impression_delta == 0 and click_delta == 0 and conversion_delta == 0 and watch_delta <= 0:
            return self.session.get(SponsoredClip, ad_id)

        result = self.session.execute(
            update(SponsoredClip)
            .where(SponsoredClip.id == ad_id)
            .values(
                impressions_served=func.coalesce(SponsoredClip.impressions_served, 0) + impression_delta,
                clicks=func.coalesce(SponsoredClip.clicks, 0) + click_delta,
                conversions=func.coalesce(SponsoredClip.conversions, 0) + conversion_delta,
                total_watch_time_seconds=func.coalesce(SponsoredClip.total_watch_time_seconds, 0.0) + watch_delta,
                updated_at=_utcnow(),
            )
        )
        if result.rowcount == 0:
            return None
        self.session.flush()
        ad = self.session.get(SponsoredClip, ad_id, populate_existing=True)
        if ad is None:
            return None
        self.cache.sync(ad, active=_is_active_campaign(ad, now=_utcnow()))
        return ad


@dataclass(slots=True)
class SponsoredClipService:
    session: Session
    app: FastAPI | None = None
    settings: Settings | None = None
    analytics: AnalyticsService | None = None
    cache: SponsoredClipCache | None = None
    trust_middleware: SharedTrustMiddleware | None = None
    trust_reader: ClipTrustMetricsReader | None = None
    runtime_config_loader: Any | None = None
    creator_earnings_service: CreatorAttentionEarningsService | None = None

    def __post_init__(self) -> None:
        if self.settings is None:
            if self.app is not None:
                self.settings = getattr(self.app.state, "settings", None)
            if self.settings is None:
                try:
                    self.settings = get_settings()
                except Exception:
                    self.settings = None
        if self.analytics is None:
            self.analytics = AnalyticsService()
        if self.cache is None:
            self.cache = ensure_sponsored_clip_cache(self.app, settings=self.settings) if self.app is not None else build_sponsored_clip_cache(settings=self.settings)
        if self.trust_middleware is None:
            trust_service = getattr(self.app.state, "trust_score_service", None) if self.app is not None else None
            self.trust_middleware = SharedTrustMiddleware(session=self.session, trust_service=trust_service)
        if self.trust_reader is None:
            self.trust_reader = build_clip_trust_metrics_reader(settings=self.settings)
        if self.runtime_config_loader is None and self.app is not None:
            self.runtime_config_loader = ensure_runtime_config_loader(self.app)
        if self.creator_earnings_service is None:
            self.creator_earnings_service = CreatorAttentionEarningsService(
                session=self.session,
                app=self.app,
                settings=self.settings,
            )

    def create_sponsored_clip(self, payload: SponsoredClipCreateRequest) -> SponsoredClip:
        clip = self._resolve_clip(payload.clip_id)
        if clip is None:
            raise SponsoredClipServiceError("Clip was not found in the current feed inventory.")

        ad = SponsoredClip(
            advertiser_id=payload.advertiser_id.strip(),
            clip_id=clip.clip_id,
            budget=_safe_decimal(payload.budget),
            bid_cpm=_safe_decimal(payload.bid_cpm),
            target_formats_json=_dedupe_values(payload.target_audience.formats),
            target_creators_json=_dedupe_values(payload.target_audience.creators),
            target_regions_json=_dedupe_values(payload.target_audience.regions, region=True),
            start_time=_as_utc(payload.start_time),
            end_time=_as_utc(payload.end_time),
            clip_payload_json=clip.model_dump(mode="json"),
            metadata_json=dict(payload.metadata_json or {}),
        )
        self.session.add(ad)
        self.session.flush()
        self.cache.sync(ad, active=_is_active_campaign(ad, now=_utcnow()))
        enqueue_ads_feed_refresh(
            session=self.session,
            ad_id=ad.id,
            advertiser_id=ad.advertiser_id,
            producer="ads-engine",
        )
        return ad

    def sync_cached_ad(self, ad_id: str) -> SponsoredClip | None:
        ad = self.session.get(SponsoredClip, ad_id)
        if ad is None:
            return None
        self.cache.sync(ad, active=_is_active_campaign(ad, now=_utcnow()))
        return ad

    def build_performance_response(
        self,
        *,
        ad_id: str | None = None,
        advertiser_id: str | None = None,
        active_only: bool = False,
    ) -> SponsoredClipPerformanceResponse:
        now = _utcnow()
        stmt = select(SponsoredClip).order_by(SponsoredClip.created_at.desc())
        if ad_id:
            stmt = stmt.where(SponsoredClip.id == ad_id)
        if advertiser_id:
            stmt = stmt.where(SponsoredClip.advertiser_id == advertiser_id)
        ads = list(self.session.scalars(stmt).all())
        views = [self.performance_view(ad, now=now) for ad in ads]
        if active_only:
            views = [view for view in views if view.eligible]
        total_spend = Decimal("0.0000")
        total_impressions = 0
        total_clicks = 0
        total_conversions = 0
        total_creator = Decimal("0.0000")
        total_platform = Decimal("0.0000")
        total_growth = Decimal("0.0000")
        for view in views:
            total_impressions += view.impressions_served
            total_clicks += view.clicks
            total_conversions += view.conversions
            total_spend += view.spend
            total_creator += view.revenue_attribution.creator_share
            total_platform += view.revenue_attribution.platform_share
            total_growth += view.revenue_attribution.growth_pool_share
        return SponsoredClipPerformanceResponse(
            ads=views,
            summary=SponsoredClipPerformanceSummaryView(
                ad_count=len(views),
                impressions=total_impressions,
                clicks=total_clicks,
                conversions=total_conversions,
                spend=total_spend.quantize(MONEY_QUANTUM),
                revenue_attribution=SponsoredRevenueAttributionView(
                    creator_share=total_creator.quantize(MONEY_QUANTUM),
                    platform_share=total_platform.quantize(MONEY_QUANTUM),
                    growth_pool_share=total_growth.quantize(MONEY_QUANTUM),
                ),
            ),
            generated_at=now,
        )

    def performance_view(self, ad: SponsoredClip, *, now: datetime | None = None) -> SponsoredClipPerformanceView:
        resolved_now = now or _utcnow()
        max_impressions = _max_impressions(ad)
        remaining_impressions = max(max_impressions - int(ad.impressions_served or 0), 0)
        pacing_state = _pacing_state(ad, now=resolved_now)
        trust_decision = self._trust_decision_for_ad(ad)
        clip_trust = self._clip_trust_summary_for_ad(ad)
        spend = self._billable_spend(ad, trust_summary=clip_trust, trust_decision=trust_decision)
        revenue = _revenue_split(spend)
        impressions = int(ad.impressions_served or 0)
        clicks = int(ad.clicks or 0)
        conversions = int(ad.conversions or 0)
        ctr = round((clicks / impressions), 6) if impressions else 0.0
        conversion_rate = round((conversions / impressions), 6) if impressions else 0.0
        avg_watch_time_seconds = round((float(ad.total_watch_time_seconds or 0.0) / impressions), 6) if impressions else 0.0
        return SponsoredClipPerformanceView(
            id=ad.id,
            advertiser_id=ad.advertiser_id,
            clip_id=ad.clip_id,
            budget=_safe_decimal(ad.budget).quantize(MONEY_QUANTUM),
            bid_cpm=_safe_decimal(ad.bid_cpm).quantize(MONEY_QUANTUM),
            target_audience=self._target_audience_view(ad),
            impressions_served=impressions,
            clicks=clicks,
            conversions=conversions,
            total_watch_time_seconds=round(float(ad.total_watch_time_seconds or 0.0), 6),
            avg_watch_time_seconds=avg_watch_time_seconds,
            ctr=ctr,
            conversion_rate=conversion_rate,
            spend=spend,
            revenue_attribution=revenue,
            max_impressions=max_impressions,
            remaining_impressions=remaining_impressions,
            pacing_state=pacing_state,
            eligible=(
                _is_eligible_for_feed(ad, now=resolved_now)
                and not trust_decision.blocked
                and trust_decision.monetization_eligible
                and clip_trust.payout_eligible
            ),
            start_time=_as_utc(ad.start_time),
            end_time=_as_utc(ad.end_time),
            is_active=bool(ad.is_active),
        )

    def build_sponsored_feed(
        self,
        *,
        user: User,
        limit: int = 20,
        refresh: bool = False,
        session_id: str | None = None,
        region: str | None = None,
    ) -> SponsoredFeedResponse:
        resolved_limit = max(1, min(int(limit), 50))
        organic_candidates = self._build_organic_candidates(user=user, limit=resolved_limit, refresh=refresh)
        clip_lookup = {candidate.clip.clip_id: candidate.clip for candidate in organic_candidates}
        clip_lookup.update(self._recent_clip_lookup(limit=max(resolved_limit * 3, 24)))

        audience = self._audience_context(user=user, region=region)
        ranked_ads = self._rank_ads(context=audience, clip_lookup=clip_lookup, now=_utcnow())
        resolved_session_id = (session_id or f"user:{user.id}").strip()
        ad_frequency_window = AD_FREQUENCY_WINDOW
        if self.runtime_config_loader is not None:
            try:
                runtime_snapshot = self.runtime_config_loader.get_snapshot()
                ad_frequency_window = max(int(runtime_snapshot.ad_frequency.min_interval), 1)
            except Exception:
                ad_frequency_window = AD_FREQUENCY_WINDOW
        ranked_items = rank_unified_feed(
            self._build_unified_candidates(
                organic_candidates=organic_candidates,
                ranked_ads=ranked_ads,
            ),
            limit=resolved_limit,
            ad_frequency_window=ad_frequency_window,
        )
        items: list[SponsoredFeedItemView] = []
        organic_count = 0
        sponsored_count = 0
        generated_at = _utcnow()

        for slot_index, ranked_item in enumerate(ranked_items):
            if ranked_item.item_type == "sponsored":
                candidate = ranked_item.payload
                tracking = self._record_impression(
                    ad=candidate.ad,
                    user_id=user.id,
                    session_id=resolved_session_id,
                    slot_index=slot_index,
                    clip=candidate.clip,
                )
                items.append(
                    self._sponsored_item(
                        candidate=candidate,
                        slot_index=slot_index,
                        tracking=tracking,
                        final_score=ranked_item.normalized_score,
                    )
                )
                sponsored_count += 1
                continue

            items.append(
                self._organic_item(
                    candidate=ranked_item.payload,
                    slot_index=slot_index,
                    final_score=ranked_item.normalized_score,
                )
            )
            organic_count += 1

        if self.creator_earnings_service is not None:
            for slot_index, item in enumerate(items):
                self.creator_earnings_service.track_impression(
                    clip=item,
                    viewer_user_id=user.id,
                    feed_source="sponsored_feed",
                    session_id=resolved_session_id,
                    slot_index=slot_index,
                    reference_key=(
                        f"sponsored-feed:{user.id}:{resolved_session_id}:{slot_index}:{item.clip_id}:{generated_at.isoformat()}"
                    ),
                )

        return SponsoredFeedResponse(
            items=items,
            generated_at=generated_at,
            session_id=resolved_session_id,
            injection_interval=ad_frequency_window,
            organic_count=organic_count,
            sponsored_count=sponsored_count,
            personalization={
                "region": audience.region,
                "favorite_formats": sorted(audience.favorite_formats, key=audience.favorite_formats.get, reverse=True)[:5],
                "favorite_creators": sorted(audience.favorite_creators, key=audience.favorite_creators.get, reverse=True)[:5],
            },
        )

    def _build_unified_candidates(
        self,
        *,
        organic_candidates: list[OrganicCandidate],
        ranked_ads: list[RankedSponsoredCandidate],
    ) -> list[UnifiedFeedCandidate]:
        candidates: list[UnifiedFeedCandidate] = [
            UnifiedFeedCandidate(
                candidate_key=f"organic:{candidate.clip.clip_id}",
                clip_id=candidate.clip.clip_id,
                item_type="organic",
                payload=candidate,
                raw_score=round(candidate.organic_score, 6),
            )
            for candidate in organic_candidates
        ]
        candidates.extend(
            UnifiedFeedCandidate(
                candidate_key=f"sponsored:{candidate.ad.id}",
                clip_id=candidate.clip.clip_id,
                item_type="sponsored",
                payload=candidate,
                raw_score=round(candidate.ad_score, 6),
            )
            for candidate in ranked_ads
        )
        return candidates

    def _resolve_clip(self, clip_id: str) -> ViralClipView | None:
        lookup = self._recent_clip_lookup(limit=MAX_CLIP_LOOKUP)
        return lookup.get(clip_id)

    def _recent_clip_lookup(self, *, limit: int) -> dict[str, ViralClipView]:
        lookup: dict[str, ViralClipView] = {}
        try:
            response = ViralFeedService(session=self.session, settings=self.settings).build_feed(
                limit=max(limit, 1),
                allocate_impressions=False,
            )
            for clip in response.clips:
                lookup[clip.clip_id] = clip
        except Exception:
            logger.exception("ads_engine.db_clip_lookup_failed")

        if self.app is not None:
            try:
                runtime_response = ensure_infinite_league_runtime(self.app).build_viral_feed(limit=max(limit, 1))
                for clip in runtime_response.clips:
                    lookup.setdefault(clip.clip_id, clip)
            except Exception:
                logger.exception("ads_engine.runtime_clip_lookup_failed")
        return lookup

    def _build_organic_candidates(self, *, user: User, limit: int, refresh: bool) -> list[OrganicCandidate]:
        if self.app is not None:
            try:
                response = build_personalized_feed_service(app=self.app, session=self.session).get_for_you(
                    user_id=user.id,
                    limit=max(limit, 1),
                    refresh=refresh,
                )
                candidates: list[OrganicCandidate] = []
                for clip in response.clips:
                    base_payload = clip.model_dump(mode="python", exclude={"rank", "score", "score_breakdown"})
                    candidates.append(
                        OrganicCandidate(
                            clip=ViralClipView.model_validate(base_payload),
                            organic_score=round(_safe_float(clip.score, default=_safe_float(clip.ranking_score)), 6),
                            organic_rank=int(clip.rank),
                        )
                    )
                if candidates:
                    return candidates
            except Exception:
                logger.exception("ads_engine.personalized_feed_failed")

        lookup = self._recent_clip_lookup(limit=max(limit * 3, 24))
        ranked = sorted(
            lookup.values(),
            key=lambda item: (
                -_safe_float(item.ranking_score),
                -_safe_float(item.viral_score),
                str(item.clip_id),
            ),
        )
        return [
            OrganicCandidate(
                clip=clip,
                organic_score=round(_safe_float(clip.ranking_score), 6),
                organic_rank=index,
            )
            for index, clip in enumerate(ranked[: max(limit, 1)], start=1)
        ]

    def _audience_context(self, *, user: User, region: str | None) -> AudienceContext:
        affinity = self.session.scalar(select(UserAffinityProfile).where(UserAffinityProfile.user_id == user.id))
        region_profile = self.session.scalar(select(UserRegionProfile).where(UserRegionProfile.user_id == user.id))
        resolved_region = _normalize_region(region) or (region_profile.region_code if region_profile is not None else None)
        return AudienceContext(
            user_id=user.id,
            region=_normalize_region(resolved_region),
            favorite_formats=_normalized_affinity_map(affinity.favorite_formats_json if affinity is not None else {}),
            favorite_creators=_normalized_affinity_map(affinity.favorite_creators_json if affinity is not None else {}),
            engagement_score=_clamp(_safe_float(getattr(affinity, "engagement_score", 0.35), default=0.35)),
            avg_watch_time=max(_safe_float(getattr(affinity, "avg_watch_time", 0.0)), 0.0),
            skip_rate=_clamp(_safe_float(getattr(affinity, "skip_rate", 0.25), default=0.25)),
        )

    def _rank_ads(
        self,
        *,
        context: AudienceContext,
        clip_lookup: dict[str, ViralClipView],
        now: datetime,
    ) -> list[RankedSponsoredCandidate]:
        ranked: list[RankedSponsoredCandidate] = []
        for ad in self._candidate_ads():
            if not _is_active_campaign(ad, now=now):
                self.cache.sync(ad, active=False)
                continue
            trust_decision = self._trust_decision_for_ad(ad)
            if trust_decision.blocked or not trust_decision.monetization_eligible:
                continue
            pacing_state = _pacing_state(ad, now=now)
            if pacing_state == "ahead":
                continue
            clip = clip_lookup.get(ad.clip_id) or self._clip_from_snapshot(ad.clip_payload_json)
            if clip is None:
                continue
            clip_trust = self._clip_trust_summary_for_ad(ad, clip=clip)
            if not clip_trust.payout_eligible:
                continue
            relevance_score = self._relevance_score(ad, context=context)
            if relevance_score <= 0:
                continue
            expected_engagement = self._expected_engagement(clip=clip, context=context)
            ad_score = round(
                _safe_float(ad.bid_cpm)
                * relevance_score
                * expected_engagement
                * clip_trust.clip_trust_score,
                6,
            )
            if ad_score <= 0:
                continue
            ranked.append(
                RankedSponsoredCandidate(
                    ad=ad,
                    clip=clip,
                    relevance_score=relevance_score,
                    expected_engagement=expected_engagement,
                    ad_score=ad_score,
                    pacing_state=pacing_state,
                    remaining_impressions=max(_max_impressions(ad) - int(ad.impressions_served or 0), 0),
                    trust_summary=clip_trust,
                )
            )
        ranked.sort(
            key=lambda item: (
                -item.ad_score,
                -_safe_float(item.ad.bid_cpm),
                -item.remaining_impressions,
                item.ad.id,
            )
        )
        return ranked

    def _candidate_ads(self) -> list[SponsoredClip]:
        active_ids = self.cache.active_ids()
        if active_ids is not None:
            if not active_ids:
                return []
            stmt = select(SponsoredClip).where(SponsoredClip.id.in_(tuple(sorted(active_ids))))
        else:
            stmt = select(SponsoredClip).where(SponsoredClip.is_active.is_(True))
        stmt = stmt.order_by(SponsoredClip.bid_cpm.desc(), SponsoredClip.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def _relevance_score(self, ad: SponsoredClip, *, context: AudienceContext) -> float:
        components: list[float] = []

        format_targets = _dedupe_values(list(ad.target_formats_json or []))
        creator_targets = _dedupe_values(list(ad.target_creators_json or []))
        region_targets = _dedupe_values(list(ad.target_regions_json or []), region=True)

        if format_targets:
            format_score = max((context.favorite_formats.get(target, 0.0) for target in format_targets), default=0.0)
            if format_score <= 0:
                return 0.0
            components.append(format_score)
        if creator_targets:
            creator_score = max((context.favorite_creators.get(target, 0.0) for target in creator_targets), default=0.0)
            if creator_score <= 0:
                return 0.0
            components.append(creator_score)
        if region_targets:
            if context.region is None or context.region not in region_targets:
                return 0.0
            components.append(1.0)

        if not components:
            return 1.0
        return round(sum(components) / len(components), 6)

    def _expected_engagement(self, *, clip: ViralClipView, context: AudienceContext) -> float:
        analytics = clip.analytics
        duration = max(_safe_float(clip.duration_seconds, default=15.0), 1.0)
        clip_watch_signal = _clamp(_safe_float(analytics.watch_time, default=0.0) / duration)
        clip_signal = _clamp(
            (_safe_float(analytics.completion_rate) * 0.45)
            + (_clamp(_safe_float(analytics.loop_rate)) * 0.15)
            + (_clamp(_safe_float(analytics.share_rate) * 10.0) * 0.15)
            + (_clamp(_safe_float(analytics.comment_rate) * 10.0) * 0.05)
            + (clip_watch_signal * 0.20),
            minimum=0.05,
            maximum=1.0,
        )
        user_signal = _clamp(
            (_clamp(context.engagement_score, minimum=0.35, maximum=1.0) * 0.55)
            + (_clamp(context.avg_watch_time / 60.0) * 0.25)
            + ((1.0 - _clamp(context.skip_rate)) * 0.20),
            minimum=0.15,
            maximum=1.0,
        )
        return round(_clamp((clip_signal * 0.55) + (user_signal * 0.45), minimum=0.05, maximum=1.0), 6)

    def _organic_item(
        self,
        *,
        candidate: OrganicCandidate,
        slot_index: int,
        final_score: float,
    ) -> SponsoredFeedItemView:
        payload = candidate.clip.model_dump(mode="python")
        return SponsoredFeedItemView(
            **payload,
            item_type="organic",
            slot_index=slot_index,
            final_score=round(final_score, 6),
            organic_rank=candidate.organic_rank,
            organic_score=round(candidate.organic_score, 6),
            ad_score=None,
            campaign=None,
            score_details=SponsoredFeedScoreView(
                source="organic",
                final_score=round(final_score, 6),
                organic_score=round(candidate.organic_score, 6),
                ad_score=None,
                relevance_score=None,
                expected_engagement=None,
            ),
        )

    def _sponsored_item(
        self,
        *,
        candidate: RankedSponsoredCandidate,
        slot_index: int,
        tracking: SponsoredFeedTrackingView,
        final_score: float,
    ) -> SponsoredFeedItemView:
        payload = candidate.clip.model_dump(mode="python")
        metadata = dict(payload.get("metadata", {}) or {})
        metadata.update(
            {
                "sponsored": True,
                "ad_id": candidate.ad.id,
                "advertiser_id": candidate.ad.advertiser_id,
                "tracking_token": tracking.tracking_token,
                "avg_trust_score": round(candidate.trust_summary.avg_trust_score, 4),
                "clip_trust_score": round(candidate.trust_summary.clip_trust_score, 4),
            }
        )
        payload["metadata"] = metadata
        campaign_revenue = _revenue_split(
            self._billable_spend(candidate.ad, trust_summary=candidate.trust_summary)
        )
        return SponsoredFeedItemView(
            **payload,
            item_type="sponsored",
            slot_index=slot_index,
            final_score=round(final_score, 6),
            organic_rank=None,
            organic_score=None,
            ad_score=round(candidate.ad_score, 6),
            campaign=SponsoredFeedCampaignView(
                id=candidate.ad.id,
                advertiser_id=candidate.ad.advertiser_id,
                budget=_safe_decimal(candidate.ad.budget).quantize(MONEY_QUANTUM),
                bid_cpm=_safe_decimal(candidate.ad.bid_cpm).quantize(MONEY_QUANTUM),
                target_audience=self._target_audience_view(candidate.ad),
                impressions_served=int(candidate.ad.impressions_served or 0),
                clicks=int(candidate.ad.clicks or 0),
                conversions=int(candidate.ad.conversions or 0),
                remaining_impressions=max(_max_impressions(candidate.ad) - int(candidate.ad.impressions_served or 0), 0),
                pacing_state=_pacing_state(candidate.ad, now=_utcnow()),
                revenue_attribution=campaign_revenue,
                tracking=tracking,
            ),
            score_details=SponsoredFeedScoreView(
                source="auction",
                final_score=round(final_score, 6),
                organic_score=None,
                ad_score=round(candidate.ad_score, 6),
                relevance_score=round(candidate.relevance_score, 6),
                expected_engagement=round(candidate.expected_engagement, 6),
            ),
        )

    def _trust_decision_for_ad(self, ad: SponsoredClip):
        return self.trust_middleware.decision_for_user_id(ad.advertiser_id)

    def _clip_trust_summary_for_ad(
        self,
        ad: SponsoredClip,
        *,
        clip: ViralClipView | None = None,
    ) -> ClipTrustSummary:
        ad_metadata = dict(ad.metadata_json or {})
        clip_payload = dict(ad.clip_payload_json or {})
        payload_metadata = clip_payload.get("metadata") if isinstance(clip_payload.get("metadata"), dict) else {}
        clip_metadata = dict(clip.metadata or {}) if clip is not None else {}
        return self.trust_reader.resolve(
            clip_id=ad.clip_id,
            metadata={**payload_metadata, **clip_metadata, **ad_metadata},
        )

    def _billable_spend(
        self,
        ad: SponsoredClip,
        *,
        trust_summary: ClipTrustSummary | None = None,
        trust_decision=None,
    ) -> Decimal:
        decision = trust_decision or self._trust_decision_for_ad(ad)
        summary = trust_summary or self._clip_trust_summary_for_ad(ad)
        if decision.blocked or not decision.monetization_eligible or not summary.payout_eligible:
            return Decimal("0.0000")
        base_spend = _spend_for_ad(
            ad,
            trust_multiplier=summary.avg_trust_score,
            billing_eligible=summary.payout_eligible,
        )
        return (base_spend * Decimal(str(decision.weight))).quantize(MONEY_QUANTUM)

    def _record_impression(
        self,
        *,
        ad: SponsoredClip,
        user_id: str,
        session_id: str,
        slot_index: int,
        clip: ViralClipView,
    ) -> SponsoredFeedTrackingView:
        tracking_token = build_tracking_token(
            match_id=clip.match_id or "feed",
            ad_id=ad.id,
            action="impression",
            user_id=user_id,
        )
        self.analytics.track_event(
            self.session,
            name=TRACKING_IMPRESSION_EVENT,
            user_id=user_id,
            metadata={
                "ad_id": ad.id,
                "advertiser_id": ad.advertiser_id,
                "clip_id": ad.clip_id,
                "match_id": clip.match_id,
                "creator_id": (dict(clip.metadata or {}).get("creator_id") if isinstance(clip.metadata, dict) else None),
                "session_id": session_id,
                "slot_index": slot_index,
                "tracking_token": tracking_token,
            },
        )
        return SponsoredFeedTrackingView(tracking_token=tracking_token)

    def _target_audience_view(self, ad: SponsoredClip) -> SponsoredClipTargetAudienceView:
        return SponsoredClipTargetAudienceView(
            formats=list(ad.target_formats_json or []),
            creators=list(ad.target_creators_json or []),
            regions=list(ad.target_regions_json or []),
        )

    def _clip_from_snapshot(self, payload: dict[str, Any] | None) -> ViralClipView | None:
        if not isinstance(payload, dict) or not payload:
            return None
        try:
            return ViralClipView.model_validate(payload)
        except Exception:
            return None


def _max_impressions(ad: SponsoredClip) -> int:
    budget = _safe_decimal(ad.budget)
    bid_cpm = _safe_decimal(ad.bid_cpm)
    if budget <= 0 or bid_cpm <= 0:
        return 0
    return int(((budget * CPM_IMPRESSION_FACTOR) / bid_cpm).to_integral_value(rounding=ROUND_FLOOR))


def _spend_for_ad(
    ad: SponsoredClip,
    *,
    trust_multiplier: float = 1.0,
    billing_eligible: bool = True,
) -> Decimal:
    if not billing_eligible:
        return Decimal("0.0000")
    bid_cpm = _safe_decimal(ad.bid_cpm)
    impressions = Decimal(str(int(ad.impressions_served or 0)))
    gross = ((impressions * bid_cpm) / CPM_IMPRESSION_FACTOR) * Decimal(str(_clamp(trust_multiplier)))
    budget = _safe_decimal(ad.budget)
    return min(gross, budget).quantize(MONEY_QUANTUM)


def _revenue_split(spend: Decimal) -> SponsoredRevenueAttributionView:
    creator_share = (spend * Decimal("0.50")).quantize(MONEY_QUANTUM)
    platform_share = (spend * Decimal("0.30")).quantize(MONEY_QUANTUM)
    growth_pool_share = (spend * Decimal("0.20")).quantize(MONEY_QUANTUM)
    return SponsoredRevenueAttributionView(
        creator_share=creator_share,
        platform_share=platform_share,
        growth_pool_share=growth_pool_share,
    )


def _is_active_campaign(ad: SponsoredClip, *, now: datetime) -> bool:
    if not bool(ad.is_active):
        return False
    if _max_impressions(ad) <= int(ad.impressions_served or 0):
        return False
    return _as_utc(ad.start_time) <= now < _as_utc(ad.end_time)


def _is_eligible_for_feed(ad: SponsoredClip, *, now: datetime) -> bool:
    return _is_active_campaign(ad, now=now) and _pacing_state(ad, now=now) != "ahead"


def _pacing_state(ad: SponsoredClip, *, now: datetime) -> str:
    if not bool(ad.is_active):
        return "paused"
    max_impressions = _max_impressions(ad)
    if max_impressions <= 0 or int(ad.impressions_served or 0) >= max_impressions:
        return "exhausted"

    start_time = _as_utc(ad.start_time)
    end_time = _as_utc(ad.end_time)
    if now < start_time:
        return "scheduled"
    if now >= end_time:
        return "ended"

    duration_seconds = max((end_time - start_time).total_seconds(), 1.0)
    elapsed_ratio = _clamp((now - start_time).total_seconds() / duration_seconds)
    allowed_ratio = 1.0 if elapsed_ratio >= 0.95 else min(elapsed_ratio + 0.05, 1.0)
    allowed_impressions = max(1, int(max_impressions * allowed_ratio))
    served = int(ad.impressions_served or 0)

    if elapsed_ratio < 0.95 and served >= allowed_impressions:
        return "ahead"

    behind_threshold = int(max_impressions * max(elapsed_ratio - 0.10, 0.0))
    if served < behind_threshold:
        return "behind"
    return "on_track"
__all__ = [
    "SponsoredClipCache",
    "SponsoredClipService",
    "SponsoredClipServiceError",
    "SponsoredClipTrackingService",
    "build_sponsored_clip_cache",
    "ensure_sponsored_clip_cache",
]
