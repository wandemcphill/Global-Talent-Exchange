from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.analytics.service import AnalyticsService
from app.core.config import Settings, get_settings
from app.feedback_engine.service import FeedbackEngine
from app.models.analytics_event import AnalyticsEvent
from app.models.clip_variant import ClipVariant
from app.models.creator_marketplace import CreatorMarketplaceCampaign
from app.models.creator_profile import CreatorProfile
from app.runtime_config.schemas import RuntimeConfigSnapshot
from app.runtime_config.service import default_runtime_config_snapshot
from app.viral.accounts import build_distribution_accounts
from app.viral.analytics import ViralFeedbackLoopService, track_clip
from app.viral.distribution import boost_distribution
from app.viral.editor import build_content_format_plans
from app.viral.promotion import ViralClipPromotionService
from app.viral.ranking import rank_score
from app.viral.scorer import ViralRankingInput, ViralScoreContext, score_trending_clip
from app.viral.schemas import (
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralClipView,
    ViralContentFormatView,
    ViralDistributionAccountView,
    ViralEditPlanView,
    ViralFeedbackLoopView,
    ViralPersonaView,
    ViralScoreBreakdownView,
)
from app.viral.variant_manager import ViralClipVariantManager

CAMPAIGN_CLIP_CREATED_EVENT = "campaign_clip.created"
CLIP_GENERATED_EVENT = "clip.generated"


def _as_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class CampaignViralIntegrationHook:
    session: Session
    settings: Settings | None = None
    feedback_engine: FeedbackEngine | None = None
    feedback_service: ViralFeedbackLoopService | None = None
    analytics_service: AnalyticsService | None = None
    variant_manager: ViralClipVariantManager | None = None
    promotion_service: ViralClipPromotionService | None = None
    runtime_config: RuntimeConfigSnapshot | None = None

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()
        if self.feedback_engine is None:
            self.feedback_engine = FeedbackEngine(session=self.session)
        if self.feedback_service is None:
            self.feedback_service = ViralFeedbackLoopService.from_settings(self.settings)
        if self.analytics_service is None:
            self.analytics_service = AnalyticsService()
        if self.runtime_config is None:
            self.runtime_config = default_runtime_config_snapshot()
        if self.variant_manager is None or self.promotion_service is None:
            from app.viral.comparator import ViralVariantScoringComparator

            comparator = ViralVariantScoringComparator()
            if self.variant_manager is None:
                self.variant_manager = ViralClipVariantManager(session=self.session, comparator=comparator)
            if self.promotion_service is None:
                self.promotion_service = ViralClipPromotionService(
                    session=self.session,
                    comparator=comparator,
                    distribution_boost_callback=lambda clip_id: boost_distribution(clip_id, settings=self.settings),
                )

    def _has_bound_table(self, table_name: str) -> bool:
        try:
            connection = self.session.connection()
            return bool(inspect(connection).has_table(table_name))
        except SQLAlchemyError:
            return False

    def publish_creator_marketplace_clips(
        self,
        *,
        campaign: CreatorMarketplaceCampaign,
        creator_profile: CreatorProfile,
        clips: list[dict[str, Any]],
    ) -> list[ViralClipView]:
        if (
            not self._has_bound_table(AnalyticsEvent.__tablename__)
            or not self._has_bound_table(ClipVariant.__tablename__)
        ):
            return []
        published: list[ViralClipView] = []
        for clip_payload in clips:
            published.append(
                self._publish_campaign_clip(
                    campaign=campaign,
                    creator_profile=creator_profile,
                    clip_payload=clip_payload,
                )
            )
        return published

    def list_campaign_clips(self, *, limit: int = 20) -> list[ViralClipView]:
        if not self._has_bound_table(AnalyticsEvent.__tablename__):
            return []
        try:
            rows = self.session.scalars(
                select(AnalyticsEvent)
                .where(AnalyticsEvent.name == CAMPAIGN_CLIP_CREATED_EVENT)
                .order_by(AnalyticsEvent.created_at.desc())
                .limit(max(limit * 4, limit))
            ).all()
        except SQLAlchemyError:
            return []
        seen_clip_ids: set[str] = set()
        clips: list[ViralClipView] = []
        for event in rows:
            payload = dict(event.metadata_json or {}).get("clip")
            if not isinstance(payload, dict):
                continue
            try:
                clip = ViralClipView.model_validate(payload)
            except Exception:
                continue
            if clip.clip_id in seen_clip_ids:
                continue
            seen_clip_ids.add(clip.clip_id)
            clip = self._refresh_live_metrics(clip)
            clips.append(clip)
            if len(clips) >= limit:
                break
        return clips

    def _publish_campaign_clip(
        self,
        *,
        campaign: CreatorMarketplaceCampaign,
        creator_profile: CreatorProfile,
        clip_payload: dict[str, Any],
    ) -> ViralClipView:
        now = datetime.now(UTC)
        clip_id = str(clip_payload.get("clip_id") or "").strip()
        if not clip_id:
            raise ValueError("Campaign clip payload must include clip_id.")
        title = str(clip_payload.get("title") or clip_id).strip()
        clip_url = str(clip_payload.get("clip_url") or f"campaign://{campaign.id}/{clip_id}").strip()
        views = max(0, _as_int(clip_payload.get("views")))
        engagement = max(0, _as_int(clip_payload.get("engagement")))
        conversions = max(0, _as_int(clip_payload.get("conversions")))
        metadata = dict(clip_payload.get("metadata") or {})
        duration_seconds = max(5.0, _as_float(metadata.get("duration_seconds"), default=18.0))
        shares = max(0, _as_int(metadata.get("shares"), default=int(round(engagement * 0.45))))
        comments = max(0, _as_int(metadata.get("comments"), default=int(round(engagement * 0.20))))
        completions = max(
            0,
            min(
                views,
                _as_int(
                    metadata.get("completions"),
                    default=int(round(views * min(0.95, 0.48 + ((engagement / max(views, 1)) * 0.75)))),
                ),
            ),
        )
        completion_rate = (completions / views) if views else 0.0
        share_rate = (shares / views) if views else 0.0
        comment_rate = (comments / views) if views else 0.0
        watch_time = round(
            min(duration_seconds * 1.25, duration_seconds * max(completion_rate, 0.35) * 1.05),
            2,
        )
        total_watch_time = round(watch_time * max(views, 1), 2)
        loops = round(max(0.0, views * min(0.35, 0.05 + (share_rate * 1.2))), 2)
        views_last_60min = max(1, min(views or 1, max(int(round(max(views, 1) * 0.55)), 1)))
        views_last_10min = max(1, min(views_last_60min, int(round(views_last_60min * 0.55))))
        ranking_input = ViralRankingInput(
            clip_id=clip_id,
            views=max(views, 1),
            completions=completions,
            total_watch_time=total_watch_time,
            loops=loops,
            shares=shares,
            comments=comments,
            skips=max(max(views, 1) - completions, 0),
            views_last_10min=views_last_10min,
            views_last_60min=views_last_60min,
            age_hours=0.0,
            duration_seconds=duration_seconds,
        )
        ranking_result = score_trending_clip(ranking_input)
        initial_score = ranking_result.score
        if bool(clip_payload.get("is_sponsored")):
            initial_score += float(self.runtime_config.viral_weights.sponsored_boost)
        viral_score = round(min(initial_score, 1.5) * 100.0, 2)
        clip_viral_score = int(round(viral_score))
        engagement_score = round(min(100.0, 30.0 + (share_rate * 220.0) + (comment_rate * 100.0)), 2)
        ranking_score = rank_score(
            viral_score=viral_score,
            engagement=engagement_score,
            freshness=100.0,
            favorite_team_match=False,
            favorite_event_match=False,
        )
        feedback = self.feedback_service.analyze_clip(
            clip_id=clip_id,
            metrics={
                "views": max(views, 1),
                "completions": completions,
                "watch_time": watch_time,
                "total_watch_time": total_watch_time,
                "loops": loops,
                "shares": shares,
                "comments": comments,
                "skips": max(max(views, 1) - completions, 0),
                "completion_rate": completion_rate,
                "views_last_10min": views_last_10min,
                "views_last_60min": views_last_60min,
                "drop_off_point_seconds": round(duration_seconds * max(completion_rate, 0.35), 2),
            },
            clip_context={
                "title": title,
                "event_type": "campaign",
                "team_name": metadata.get("team_name"),
                "player_name": creator_profile.display_name,
                "duration_seconds": duration_seconds,
                "crowd_spike": bool(shares),
                "late_drama": False,
                "comeback": False,
                "go_ahead": False,
                "equalizer": False,
                "upset": False,
                "is_final": False,
            },
        )
        tracked_metrics = track_clip(
            clip_id,
            {
                "views": max(views, 1),
                "completions": completions,
                "watch_time": watch_time,
                "total_watch_time": total_watch_time,
                "loops": loops,
                "shares": shares,
                "comments": comments,
                "skips": max(max(views, 1) - completions, 0),
                "completion_rate": completion_rate,
                "drop_off_point_seconds": round(duration_seconds * max(completion_rate, 0.35), 2),
                "views_last_10min": views_last_10min,
                "views_last_60min": views_last_60min,
            },
        )
        caption_result = {
            "hook": metadata.get("hook") or f"{campaign.title}: {title}",
            "caption": metadata.get("caption") or f"{creator_profile.display_name} for {campaign.title}",
            "cta": "Watch now",
            "hashtags": [campaign.title.replace(" ", ""), "GTEX"],
            "source": "campaign",
        }
        format_plans = build_content_format_plans(
            storage_key=clip_url,
            title=title,
            event_type="campaign",
            overlay_text=caption_result["hook"],
            duration_seconds=duration_seconds,
            team_name=None,
            player_name=creator_profile.display_name,
        )
        distribution_accounts = build_distribution_accounts(
            title=title,
            event_type="campaign",
            minute=0,
            team_name=None,
            player_name=creator_profile.display_name,
            scoreline_label=None,
            default_caption=type("_CampaignCaption", (), caption_result)(),
            context=ViralScoreContext(
                event_type="campaign",
                minute=0,
                crowd_spike=bool(shares),
            ),
        )
        clip_view = ViralClipView(
            clip_id=clip_id,
            match_id=f"campaign:{campaign.id}",
            highlight_id=clip_id,
            title=title,
            reel_title=campaign.title,
            team_name=None,
            player_name=creator_profile.display_name,
            event_type="campaign",
            minute=0,
            scoreline_label=None,
            storage_key=clip_url,
            video_url=clip_url,
            duration_seconds=duration_seconds,
            render_status="ready",
            viral_score=clip_viral_score,
            engagement=engagement_score,
            freshness=100.0,
            ranking_score=round(ranking_score + initial_score, 4),
            tags=["campaign", "creator"] + (["sponsored"] if bool(clip_payload.get("is_sponsored")) else []),
            share_channel="sponsored_feed" if bool(clip_payload.get("is_sponsored")) else "creator_marketplace",
            breakdown=ViralScoreBreakdownView(
                base_event=clip_viral_score,
                crowd_bonus=int(round(share_rate * 100)),
                total=clip_viral_score,
            ),
            caption=ViralCaptionView(
                hook=str(caption_result["hook"]),
                caption=str(caption_result["caption"]),
                cta=str(caption_result["cta"]),
                hashtags=list(caption_result["hashtags"]),
                source=str(caption_result["source"]),
            ),
            distribution_accounts=[
                ViralDistributionAccountView(
                    handle=account.handle,
                    niche=account.niche,
                    target_audience=account.target_audience,
                    fit_score=account.fit_score,
                    persona=ViralPersonaView(
                        name=account.persona.name,
                        tone=account.persona.tone,
                    ),
                    cross_promo_handles=list(account.cross_promo_handles),
                    caption_tests=[],
                )
                for account in distribution_accounts
            ],
            editor=self._edit_plan_view(format_plans[0].editor),
            formats=[
                ViralContentFormatView(
                    format_key=plan.format_key,
                    title=plan.title,
                    description=plan.description,
                    editor=self._edit_plan_view(plan.editor),
                )
                for plan in format_plans
            ],
            analytics=ViralClipAnalyticsView(**tracked_metrics),
            feedback=ViralFeedbackLoopView(
                performance_tier=feedback.performance_tier,
                recommendation=feedback.recommendation,
                increase_similar_clips=feedback.increase_similar_clips,
                adjust_captions=feedback.adjust_captions,
                shorten_clips=feedback.shorten_clips,
                actions=list(feedback.actions),
                viral_analysis=feedback.viral_analysis,
                analysis_source=feedback.analysis_source,
            ),
            metadata={
                **metadata,
                "creator_id": creator_profile.id,
                "creator_user_id": creator_profile.user_id,
                "author_user_id": creator_profile.user_id,
                "campaign_id": campaign.id,
                "brand_id": campaign.brand_id,
                "sponsored": bool(clip_payload.get("is_sponsored")),
                "initial_score": round(initial_score, 6),
                "published_at": now.isoformat(),
                "source": "creator_marketplace",
            },
        )
        self.variant_manager.ensure_variants(
            base_clip_id=clip_id,
            format_plans=format_plans,
            baseline_metrics=tracked_metrics,
            created_at=now,
            clip_metadata={
                "campaign_id": campaign.id,
                "creator_id": creator_profile.id,
                "creator_user_id": creator_profile.user_id,
                "source": "creator_marketplace",
            },
        )
        self.promotion_service.refresh(clip_id)
        self.feedback_engine.record_clip_publication(creator_id=creator_profile.id)
        if self._has_bound_table(AnalyticsEvent.__tablename__):
            self.session.add(
                AnalyticsEvent(
                    name=CAMPAIGN_CLIP_CREATED_EVENT,
                    user_id=creator_profile.user_id,
                    metadata_json={
                        "campaign_id": campaign.id,
                        "creator_id": creator_profile.id,
                        "creator_user_id": creator_profile.user_id,
                        "clip_id": clip_id,
                        "clip": clip_view.model_dump(mode="json"),
                    },
                )
            )
            self.session.add(
                AnalyticsEvent(
                    name=CLIP_GENERATED_EVENT,
                    user_id=creator_profile.user_id,
                    metadata_json={
                        "campaign_id": campaign.id,
                        "creator_id": creator_profile.id,
                        "creator_user_id": creator_profile.user_id,
                        "clip_id": clip_id,
                        "source": "creator_marketplace",
                    },
                )
            )
        self.session.flush()
        return clip_view

    def _refresh_live_metrics(self, clip: ViralClipView) -> ViralClipView:
        snapshot = self.analytics_service.clip_snapshot(
            self.session,
            clip_id=clip.clip_id,
            fallback=clip.analytics.model_dump(mode="python"),
        )
        return clip.model_copy(
            update={
                "analytics": ViralClipAnalyticsView(**snapshot["analytics"]),
                "metadata": {
                    **dict(clip.metadata or {}),
                    "lifecycle": snapshot["lifecycle"],
                    "revenue": snapshot["revenue"],
                },
            }
        )

    @staticmethod
    def _edit_plan_view(plan: Any) -> ViralEditPlanView:
        return ViralEditPlanView(
            format_key=plan.format_key,
            style_preset=plan.style_preset,
            aspect_ratio=plan.aspect_ratio,
            crop_filter=plan.crop_filter,
            overlay_text=plan.overlay_text,
            transcode_command=plan.transcode_command,
            overlay_command=plan.overlay_command,
            audio_mix_profile=plan.audio_mix_profile,
            loop_window_seconds=plan.loop_window_seconds,
            watermark_text=plan.watermark_text,
            share_targets=plan.share_targets,
            narrative_device=plan.narrative_device,
            effect_stack=plan.effect_stack,
            publish_strategy=plan.publish_strategy,
            commentary_prompt=plan.commentary_prompt,
        )


__all__ = ["CAMPAIGN_CLIP_CREATED_EVENT", "CampaignViralIntegrationHook"]
