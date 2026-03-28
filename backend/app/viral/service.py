from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.feedback_engine.service import FeedbackEngine
from app.models.competition_match import CompetitionMatch
from app.models.manager_duel import ManagerDuel
from app.runtime_config.service import default_runtime_config_snapshot
from app.viral.accounts import build_distribution_accounts
from app.viral.analytics import ViralFeedbackLoopService, track_clip
from app.viral.campaign_integration import CampaignViralIntegrationHook
from app.viral.cascade import ViralCascadeEngine
from app.viral.captions import ViralCaptionService
from app.viral.cold_start import ColdStartManager
from app.viral.distribution import ClipDistributionManager, ClipDistributionState, build_clip_distribution_manager
from app.viral.editor import build_content_format_plans
from app.viral.promotion import VariantPromotionDecision, ViralClipPromotionService
from app.viral.ranking import rank_score
from app.viral.scorer import ViralScoreContext, score_clip
from app.viral.schemas import (
    ViralCaptionTestView,
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralClipDistributionView,
    ViralClipVariantView,
    ViralDistributionAccountView,
    ViralClipView,
    ViralClipVariantsResponse,
    ViralClipWinnerResponse,
    ViralContentFormatView,
    ViralEditPlanView,
    ViralFeedbackLoopView,
    ViralFeedResponse,
    ViralPersonaView,
    ViralScoreBreakdownView,
)
from app.viral.variant_manager import ViralClipVariantManager, build_base_clip_id, parse_base_clip_id

if TYPE_CHECKING:
    from app.match_engine.schemas import MatchReplayPayloadView
    from app.match_engine.services.highlight_manifest import MatchHighlightManifestBuilder


class ViralFeedError(ValueError):
    pass


def _table_exists(session: Session, table_name: str) -> bool:
    try:
        return bool(inspect(session.get_bind()).has_table(table_name))
    except Exception:
        return False


def load_replay_payload(session: Session, match_key: str) -> MatchReplayPayloadView:
    from app.match_engine.schemas import MatchReplayPayloadView

    match = session.get(CompetitionMatch, match_key)
    if match is not None:
        payload = (match.metadata_json or {}).get("replay_payload")
        if isinstance(payload, dict):
            return MatchReplayPayloadView.model_validate(payload)

    if _table_exists(session, ManagerDuel.__tablename__):
        duel = session.get(ManagerDuel, match_key)
        if duel is not None:
            payload = (duel.metadata_json or {}).get("replay_payload")
            if isinstance(payload, dict):
                return MatchReplayPayloadView.model_validate(payload)

    raise ViralFeedError(f"Replay payload for {match_key} was not found.")


@dataclass(slots=True)
class _ReplayEnvelope:
    match_id: str
    payload: MatchReplayPayloadView
    updated_at: datetime


@dataclass(slots=True)
class ViralFeedService:
    session: Session
    settings: Settings | None = None
    manifest_builder: MatchHighlightManifestBuilder | None = None
    caption_service: ViralCaptionService | None = None
    feedback_service: ViralFeedbackLoopService | None = None
    variant_manager: ViralClipVariantManager | None = None
    promotion_service: ViralClipPromotionService | None = None
    distribution_manager: ClipDistributionManager | None = None
    cascade_engine: ViralCascadeEngine | None = None
    feedback_engine: FeedbackEngine | None = None
    cold_start_manager: ColdStartManager | None = None
    campaign_integration_hook: CampaignViralIntegrationHook | None = None
    runtime_config_loader: Any | None = None

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()
        if self.feedback_engine is None:
            self.feedback_engine = FeedbackEngine(session=self.session)
        if self.cold_start_manager is None:
            self.cold_start_manager = ColdStartManager(
                session=self.session,
                feedback_engine=self.feedback_engine,
            )
        if self.manifest_builder is None:
            from app.match_engine.services.highlight_manifest import MatchHighlightManifestBuilder

            self.manifest_builder = MatchHighlightManifestBuilder(settings=self.settings)
        if self.caption_service is None:
            self.caption_service = ViralCaptionService.from_settings(self.settings)
        if self.feedback_service is None:
            self.feedback_service = ViralFeedbackLoopService.from_settings(self.settings)
        if self.distribution_manager is None:
            self.distribution_manager = build_clip_distribution_manager(settings=self.settings)
        if self.variant_manager is None or self.promotion_service is None:
            comparator = self.promotion_service.comparator if self.promotion_service is not None else None
            if comparator is None and self.variant_manager is not None:
                comparator = self.variant_manager.comparator
            if comparator is None:
                from app.viral.comparator import ViralVariantScoringComparator

                comparator = ViralVariantScoringComparator()
            if self.variant_manager is None:
                self.variant_manager = ViralClipVariantManager(session=self.session, comparator=comparator)
            if self.promotion_service is None:
                self.promotion_service = ViralClipPromotionService(session=self.session, comparator=comparator)
        if self.campaign_integration_hook is None:
            self.campaign_integration_hook = CampaignViralIntegrationHook(
                session=self.session,
                settings=self.settings,
                feedback_engine=self.feedback_engine,
                feedback_service=self.feedback_service,
            )

    def build_feed(
        self,
        *,
        limit: int = 20,
        match_ids: list[str] | None = None,
        favorite_team: str | None = None,
        favorite_event_types: list[str] | None = None,
        allocate_impressions: bool = True,
    ) -> ViralFeedResponse:
        envelopes = self._resolve_replays(match_ids=match_ids, limit=max(limit, 1))
        clips: list[ViralClipView] = []
        for envelope in envelopes:
            clips.extend(
                self._build_match_clips(
                    envelope.payload,
                    updated_at=envelope.updated_at,
                    favorite_team=favorite_team,
                    favorite_event_types=favorite_event_types or [],
                )
            )
        if not match_ids:
            clips.extend(self.campaign_integration_hook.list_campaign_clips(limit=max(limit, 1)))
        clips = self._finalize_distribution(
            clips,
            limit=max(limit, 1),
            allocate_impressions=allocate_impressions,
        )
        return ViralFeedResponse(
            clips=clips,
            generated_at=datetime.now(UTC),
            personalization={
                "favorite_team": favorite_team,
                "favorite_event_types": list(favorite_event_types or []),
            },
        )

    def build_match_feed(
        self,
        match_key: str,
        *,
        favorite_team: str | None = None,
        favorite_event_types: list[str] | None = None,
        allocate_impressions: bool = True,
    ) -> ViralFeedResponse:
        payload = load_replay_payload(self.session, match_key)
        record = self.session.get(CompetitionMatch, match_key)
        duel = None
        if record is None and _table_exists(self.session, ManagerDuel.__tablename__):
            duel = self.session.get(ManagerDuel, match_key)
        updated_at = datetime.now(UTC)
        if record is not None:
            updated_at = record.completed_at or record.updated_at or record.created_at or updated_at
        elif duel is not None:
            updated_at = duel.completed_at or duel.updated_at or duel.created_at or updated_at
        clips = self._build_match_clips(
            payload,
            updated_at=updated_at,
            favorite_team=favorite_team,
            favorite_event_types=favorite_event_types or [],
        )
        clips = self._finalize_distribution(
            clips,
            limit=None,
            allocate_impressions=allocate_impressions,
        )
        return ViralFeedResponse(
            clips=clips,
            generated_at=datetime.now(UTC),
            personalization={
                "favorite_team": favorite_team,
                "favorite_event_types": list(favorite_event_types or []),
            },
        )

    def get_clip_variants(self, clip_id: str) -> ViralClipVariantsResponse:
        variants, decision = self._load_variant_competition(clip_id)
        return ViralClipVariantsResponse(
            clip_id=clip_id,
            variants=[self._variant_view(variant) for variant in variants],
            resolved=decision.resolved,
            leading_variant_id=decision.leading_variant_id,
            generated_at=datetime.now(UTC),
        )

    def get_clip_winner(self, clip_id: str) -> ViralClipWinnerResponse:
        variants, decision = self._load_variant_competition(clip_id)
        variant_views = {variant.variant_id: self._variant_view(variant) for variant in variants}
        return ViralClipWinnerResponse(
            clip_id=clip_id,
            resolved=decision.resolved,
            decision_reason=decision.decision_reason,
            winner=variant_views.get(decision.winner_variant_id) if decision.winner_variant_id is not None else None,
            leading_variant=variant_views.get(decision.leading_variant_id) if decision.leading_variant_id is not None else None,
            generated_at=datetime.now(UTC),
        )

    def _resolve_replays(self, *, match_ids: list[str] | None, limit: int) -> list[_ReplayEnvelope]:
        if match_ids:
            envelopes: list[_ReplayEnvelope] = []
            for match_id in match_ids:
                payload = load_replay_payload(self.session, match_id)
                record = self.session.get(CompetitionMatch, match_id)
                duel = None
                if record is None and _table_exists(self.session, ManagerDuel.__tablename__):
                    duel = self.session.get(ManagerDuel, match_id)
                updated_at = datetime.now(UTC)
                if record is not None:
                    updated_at = record.completed_at or record.updated_at or record.created_at or updated_at
                elif duel is not None:
                    updated_at = duel.completed_at or duel.updated_at or duel.created_at or updated_at
                envelopes.append(_ReplayEnvelope(match_id=match_id, payload=payload, updated_at=updated_at))
            return envelopes
        return self._recent_replay_envelopes(limit=max(limit * 2, 6))

    def _recent_replay_envelopes(self, *, limit: int) -> list[_ReplayEnvelope]:
        envelopes: list[_ReplayEnvelope] = []
        competition_matches = list(
            self.session.scalars(
                select(CompetitionMatch).order_by(CompetitionMatch.updated_at.desc()).limit(limit)
            ).all()
        )
        manager_duels: list[ManagerDuel] = []
        if _table_exists(self.session, ManagerDuel.__tablename__):
            manager_duels = list(
                self.session.scalars(
                    select(ManagerDuel).order_by(ManagerDuel.updated_at.desc()).limit(limit)
                ).all()
            )
        for row in competition_matches:
            payload = (row.metadata_json or {}).get("replay_payload")
            if isinstance(payload, dict):
                from app.match_engine.schemas import MatchReplayPayloadView

                envelopes.append(
                    _ReplayEnvelope(
                        match_id=row.id,
                        payload=MatchReplayPayloadView.model_validate(payload),
                        updated_at=row.completed_at or row.updated_at or row.created_at or datetime.now(UTC),
                    )
                )
        for row in manager_duels:
            payload = (row.metadata_json or {}).get("replay_payload")
            if isinstance(payload, dict):
                from app.match_engine.schemas import MatchReplayPayloadView

                envelopes.append(
                    _ReplayEnvelope(
                        match_id=row.id,
                        payload=MatchReplayPayloadView.model_validate(payload),
                        updated_at=row.completed_at or row.updated_at or row.created_at or datetime.now(UTC),
                    )
                )
        envelopes.sort(key=lambda item: item.updated_at, reverse=True)
        return envelopes[:limit]

    def _finalize_distribution(
        self,
        clips: list[ViralClipView],
        *,
        limit: int | None,
        allocate_impressions: bool,
    ) -> list[ViralClipView]:
        runtime_snapshot = (
            self.runtime_config_loader.get_snapshot()
            if self.runtime_config_loader is not None
            else default_runtime_config_snapshot()
        )
        self.distribution_manager.freeze_completion_floor = float(runtime_snapshot.trust_thresholds.freeze_completion_floor)
        self.distribution_manager.freeze_share_floor = float(runtime_snapshot.trust_thresholds.freeze_share_floor)
        self.distribution_manager.freeze_skip_ceiling = float(runtime_snapshot.trust_thresholds.freeze_skip_ceiling)
        eligible_clips: list[ViralClipView] = []
        for clip in clips:
            cascade_metadata = clip.metadata.get("cascade") if isinstance(clip.metadata, dict) else None
            cap_multiplier = 1
            if isinstance(cascade_metadata, dict) and bool(cascade_metadata.get("cascade")):
                actions = cascade_metadata.get("actions")
                if isinstance(actions, dict):
                    try:
                        cap_multiplier = max(int(actions.get("distribution_cap_multiplier", 1) or 1), 1)
                    except (TypeError, ValueError):
                        cap_multiplier = 1
            creator_id = self._creator_id(clip)
            cap_boost = self.feedback_engine.creator_distribution_weight(creator_id)
            cap_boost += self.cold_start_manager.creator_boost(creator_id)
            minimum_cap = self.cold_start_manager.initial_impression_floor(
                clip_id=clip.clip_id,
                observed_views=int(getattr(clip.analytics, "view_count", 0) or 0),
            )
            state = self.distribution_manager.refresh_distribution(
                clip_id=clip.clip_id,
                viral_score=clip.viral_score,
                analytics=clip.analytics.model_dump(mode="python"),
                performance_tier=clip.feedback.performance_tier,
                cap_multiplier=cap_multiplier,
                cap_boost=max(cap_boost, 1.0),
                minimum_cap=minimum_cap,
            )
            clip.distribution = self._distribution_view(state)
            clip.metadata["distribution_key"] = self.distribution_manager.distribution_key(clip.clip_id)
            clip.metadata["distribution_stage"] = state.expansion_stage
            clip.metadata["distribution_frozen"] = state.frozen
            clip.metadata["distribution_cap_multiplier"] = cap_multiplier
            if self.distribution_manager.is_eligible(state):
                eligible_clips.append(clip)

        eligible_clips.sort(key=self._clip_sort_key)
        if limit is not None:
            eligible_clips = eligible_clips[: max(limit, 1)]

        if not allocate_impressions:
            return eligible_clips

        allocated: list[ViralClipView] = []
        for clip in eligible_clips:
            allocation = self.distribution_manager.allocate_impressions(clip.clip_id, count=1)
            clip.distribution = self._distribution_view(allocation.state)
            if allocation.allocated:
                allocated.append(clip)
        return allocated

    @staticmethod
    def _clip_sort_key(item: ViralClipView) -> tuple[float, float, int, str]:
        return (-item.ranking_score, -item.viral_score, item.minute, item.highlight_id)

    def _distribution_view(self, state: ClipDistributionState) -> ViralClipDistributionView:
        return ViralClipDistributionView(
            impressions_served=int(state.impressions_served),
            impressions_cap=int(state.impressions_cap),
            expansion_stage=state.expansion_stage,
            frozen=bool(state.frozen),
            eligible=bool(state.eligible),
            remaining_impressions=int(state.remaining_impressions),
            freeze_reason=state.freeze_reason,
        )

    def _build_match_clips(
        self,
        payload: MatchReplayPayloadView,
        *,
        updated_at: datetime,
        favorite_team: str | None,
        favorite_event_types: list[str],
    ) -> list[ViralClipView]:
        manifest = self.manifest_builder.build_from_replay_payload(payload)
        event_lookup = {event.event_id: event for event in payload.timeline.events}
        favorite_event_set = {item.strip().lower() for item in favorite_event_types if item.strip()}
        clips: list[ViralClipView] = []
        for clip in manifest.highlights:
            event = event_lookup.get(clip.highlight_id)
            if event is None:
                continue
            context = self._score_context(payload=payload, clip=clip, event=event)
            breakdown = score_clip(context)
            caption_result = self.caption_service.generate_caption(
                {
                    "event_type": clip.event_type,
                    "minute": clip.minute,
                    "team_name": clip.team_name,
                    "player_name": clip.player_name,
                    "comeback": context.comeback,
                    "go_ahead": context.go_ahead,
                    "equalizer": context.equalizer,
                }
            )
            distribution_accounts = build_distribution_accounts(
                title=clip.title,
                event_type=clip.event_type,
                minute=clip.minute,
                team_name=clip.team_name,
                player_name=clip.player_name,
                scoreline_label=clip.scoreline_label,
                default_caption=caption_result,
                context=context,
            )
            format_plans = build_content_format_plans(
                storage_key=clip.storage_key,
                title=clip.title,
                event_type=clip.event_type,
                overlay_text=caption_result.hook,
                duration_seconds=clip.duration_seconds,
                team_name=clip.team_name,
                player_name=clip.player_name,
            )
            primary_plan = format_plans[0].editor
            baseline_metrics = self._baseline_clip_metrics(
                clip=clip,
                breakdown_total=breakdown.total,
                payload=payload,
                updated_at=updated_at,
                context=context,
            )
            clip_id = build_base_clip_id(payload.match_id, clip.highlight_id)
            self.variant_manager.ensure_variants(
                base_clip_id=clip_id,
                format_plans=format_plans,
                baseline_metrics=baseline_metrics,
                created_at=updated_at,
                clip_metadata={
                    "match_id": payload.match_id,
                    "highlight_id": clip.highlight_id,
                    "event_type": clip.event_type,
                    "title": clip.title,
                },
            )
            variant_decision = self.promotion_service.refresh(clip_id)
            tracked_metrics = track_clip(clip.highlight_id, baseline_metrics)
            feedback_context = self._feedback_context(
                payload=payload,
                clip=clip,
                context=context,
            )
            feedback = self.feedback_service.analyze_clip(
                clip_id=clip.highlight_id,
                metrics=baseline_metrics,
                clip_context=feedback_context,
            )
            engagement = self._engagement_score(clip=clip, breakdown=breakdown.total, payload=payload)
            freshness = self._freshness_score(updated_at)
            favorite_team_match = bool(
                favorite_team
                and clip.team_name
                and clip.team_name.strip().lower() == favorite_team.strip().lower()
            )
            ranking = rank_score(
                viral_score=breakdown.total,
                engagement=engagement,
                freshness=freshness,
                favorite_team_match=favorite_team_match,
                favorite_event_match=clip.event_type.strip().lower() in favorite_event_set,
            )
            if variant_decision.resolved and variant_decision.winner_variant_id is not None:
                ranking = round(ranking + 12.0, 2)
            clip_view = ViralClipView(
                clip_id=clip_id,
                match_id=payload.match_id,
                highlight_id=clip.highlight_id,
                title=clip.title,
                reel_title=manifest.reel.title if manifest.reel is not None else None,
                team_name=clip.team_name,
                player_name=clip.player_name,
                event_type=clip.event_type,
                minute=clip.minute,
                scoreline_label=clip.scoreline_label,
                storage_key=clip.storage_key,
                video_url=clip.cdn_path,
                duration_seconds=round(float(clip.duration_seconds or 0.0), 2),
                render_status=clip.render_status,
                viral_score=breakdown.total,
                engagement=engagement,
                freshness=freshness,
                ranking_score=ranking,
                tags=self._tags(payload=payload, clip=clip, context=context),
                share_channel="whatsapp",
                breakdown=ViralScoreBreakdownView(**breakdown.as_dict()),
                caption=ViralCaptionView(
                    hook=caption_result.hook,
                    caption=caption_result.caption,
                    cta=caption_result.cta,
                    hashtags=caption_result.hashtags,
                    source=caption_result.source,
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
                        caption_tests=[
                            ViralCaptionTestView(
                                variant_key=variant.variant_key,
                                audience=variant.audience,
                                hook=variant.hook,
                                caption=variant.caption,
                                hashtags=list(variant.hashtags),
                                source=variant.source,
                                hypothesis=variant.hypothesis,
                            )
                            for variant in account.caption_tests
                        ],
                    )
                    for account in distribution_accounts
                ],
                editor=self._edit_plan_view(primary_plan),
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
                    "home_team_name": payload.summary.home_stats.team_name,
                    "away_team_name": payload.summary.away_stats.team_name,
                    "summary_line": payload.summary.summary_line,
                    "upset": payload.summary.upset,
                    "is_final": payload.summary.is_final,
                    "flywheel_stage": "ai_learns",
                    "variant_competition_resolved": variant_decision.resolved,
                    "variant_leading_id": variant_decision.leading_variant_id,
                    "variant_winner_id": variant_decision.winner_variant_id,
                    "variant_decision_reason": variant_decision.decision_reason,
                    "trending": bool(variant_decision.resolved and variant_decision.winner_variant_id),
                },
            )
            if self.cascade_engine is not None:
                clip_view = self.cascade_engine.apply_to_clip(clip_view)
            clips.append(clip_view)
        return clips

    def _load_variant_competition(self, clip_id: str) -> tuple[list, VariantPromotionDecision]:
        self._ensure_variant_records(clip_id)
        decision = self.promotion_service.refresh(clip_id)
        variants = self.variant_manager.list_variants(clip_id)
        if not variants:
            raise ViralFeedError(f"Clip variant competition for {clip_id} was not found.")
        return variants, decision

    def _ensure_variant_records(self, clip_id: str) -> None:
        variants = self.variant_manager.list_variants(clip_id)
        if variants:
            return
        parsed = parse_base_clip_id(clip_id)
        if parsed is None:
            raise ViralFeedError(f"Clip variant competition for {clip_id} was not found.")
        match_id, _highlight_id = parsed
        self.build_match_feed(match_id, allocate_impressions=False)

    def _variant_view(self, variant) -> ViralClipVariantView:
        return ViralClipVariantView(
            base_clip_id=variant.base_clip_id,
            variant_id=variant.variant_id,
            format_type=variant.format_type,
            created_at=variant.created_at,
            viral_score=round(float(variant.viral_score or 0.0), 2),
            distribution_weight=round(float(variant.distribution_weight or 0.0), 4),
            promotion_status=variant.promotion_status,
            promotion_enabled=bool(variant.promotion_enabled),
            pushed_to_trending=bool(variant.pushed_to_trending),
            is_winner=bool(variant.is_winner),
            analytics=ViralClipAnalyticsView(
                clip_id=variant.variant_id,
                view_count=int(variant.view_count or 0),
                watch_time=round(float(variant.watch_time or 0.0), 2),
                loop_rate=round(float(variant.loop_rate or 0.0), 4),
                shares=int(variant.shares or 0),
                comments=int(variant.comments or 0),
                completion_rate=round(float(variant.completion_rate or 0.0), 4),
                drop_off_point_seconds=round(float(variant.drop_off_point_seconds), 2)
                if variant.drop_off_point_seconds is not None
                else None,
                share_rate=round(float(variant.share_rate or 0.0), 4),
                comment_rate=round(float(variant.comment_rate or 0.0), 4),
            ),
            metadata=dict(variant.metadata_json or {}),
        )

    def _baseline_clip_metrics(
        self,
        *,
        clip: Any,
        breakdown_total: int,
        payload: MatchReplayPayloadView,
        updated_at: datetime,
        context: ViralScoreContext,
    ) -> dict[str, Any]:
        completion_rate = min(
            0.96,
            0.46
            + min(breakdown_total, 120) / 260.0
            + (0.08 if clip.crowd_spike else 0.0)
            + (0.05 if payload.summary.upset else 0.0)
            + (0.04 if clip.importance >= 4 else 0.0),
        )
        loop_rate = min(
            0.55,
            0.05
            + max(0, breakdown_total - 40) / 220.0
            + (0.06 if context.late_drama else 0.0)
            + (0.04 if context.comeback or context.equalizer or context.go_ahead else 0.0),
        )
        freshness = self._freshness_score(updated_at)
        estimated_views = max(150, int(220 + (breakdown_total * 14) + (freshness * 3)))
        share_rate = min(
            0.08,
            0.008
            + (0.018 if clip.crowd_spike else 0.0)
            + (0.012 if payload.summary.upset else 0.0)
            + max(0, breakdown_total - 45) / 3000.0,
        )
        comment_rate = min(
            0.05,
            0.006
            + (0.01 if context.comeback or context.equalizer or context.go_ahead else 0.0)
            + (0.009 if payload.summary.is_final else 0.0)
            + max(0, breakdown_total - 50) / 4500.0,
        )
        shares = max(0, int(round(estimated_views * share_rate)))
        comments = max(0, int(round(estimated_views * comment_rate)))
        duration_seconds = max(1.0, float(clip.duration_seconds or 1))
        average_watch_time = min(
            duration_seconds * 1.45,
            duration_seconds * completion_rate * (1.0 + loop_rate),
        )
        total_watch_time = round(average_watch_time * estimated_views, 2)
        completions = max(0, min(estimated_views, int(round(estimated_views * completion_rate))))
        skips = max(0, estimated_views - completions)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        age_hours = max((datetime.now(UTC) - updated_at.astimezone(UTC)).total_seconds() / 3600.0, 0.0)
        freshness_signal = max(0.04, min(1.0, 1.0 / (1.0 + (age_hours / 2.5))))
        recent_view_share = min(
            0.72,
            0.07
            + (freshness_signal * 0.48)
            + (0.05 if clip.crowd_spike else 0.0)
            + (0.03 if context.late_drama else 0.0),
        )
        views_last_60min = max(1, min(estimated_views, int(round(estimated_views * recent_view_share))))
        ten_minute_share = min(
            0.88,
            0.10
            + (share_rate * 4.0)
            + (loop_rate * 0.40)
            + (completion_rate * 0.15)
            + (0.08 if clip.crowd_spike else 0.0)
            + (0.05 if context.late_drama else 0.0),
        )
        views_last_10min = max(1, min(views_last_60min, int(round(views_last_60min * ten_minute_share))))
        drop_off_ratio = max(
            completion_rate,
            min(0.98, completion_rate + (0.08 if clip.crowd_spike else 0.03)),
        )
        return {
            "views": estimated_views,
            "completions": completions,
            "watch_time": round(average_watch_time, 2),
            "total_watch_time": total_watch_time,
            "loops": round(loop_rate * estimated_views, 2),
            "shares": shares,
            "comments": comments,
            "skips": skips,
            "completion": completion_rate,
            "drop_off_point_seconds": round(duration_seconds * drop_off_ratio, 2),
            "views_last_10min": views_last_10min,
            "views_last_60min": views_last_60min,
        }

    def _feedback_context(
        self,
        *,
        payload: MatchReplayPayloadView,
        clip: Any,
        context: ViralScoreContext,
    ) -> dict[str, Any]:
        return {
            "title": clip.title,
            "event_type": clip.event_type,
            "team_name": clip.team_name,
            "player_name": clip.player_name,
            "duration_seconds": clip.duration_seconds or 0,
            "crowd_spike": clip.crowd_spike,
            "late_drama": context.late_drama,
            "comeback": context.comeback,
            "go_ahead": context.go_ahead,
            "equalizer": context.equalizer,
            "upset": payload.summary.upset,
            "is_final": payload.summary.is_final,
        }

    def _edit_plan_view(self, plan) -> ViralEditPlanView:
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

    def _score_context(self, *, payload: MatchReplayPayloadView, clip: Any, event) -> ViralScoreContext:
        xg = float(event.metadata.get("xg", event.metadata.get("chance_quality", 0.0)) or 0.0)
        normalized_event = clip.event_type.strip().lower()
        previous_event = None
        for candidate in payload.timeline.events:
            if candidate.sequence < event.sequence:
                previous_event = candidate
            else:
                break
        prev_home = previous_event.home_score if previous_event is not None else 0
        prev_away = previous_event.away_score if previous_event is not None else 0
        lead_before = self._leader(prev_home, prev_away)
        lead_after = self._leader(event.home_score, event.away_score)
        scoring_side = self._leader_delta(prev_home, prev_away, event.home_score, event.away_score)
        comeback = lead_before not in {None, scoring_side} and lead_after == scoring_side and scoring_side is not None
        go_ahead = lead_before is None and lead_after is not None and normalized_event in {"goal", "penalty_goal", "penalty_scored"}
        equalizer = lead_before is not None and lead_after is None and normalized_event in {"goal", "penalty_goal", "penalty_scored"}
        rivalry = "rivalry" in (payload.atmosphere_summary or "").lower() or payload.atmosphere_profile in {"heated", "derby"}
        return ViralScoreContext(
            event_type=normalized_event,
            minute=clip.minute,
            xg=xg,
            importance=clip.importance,
            comeback=comeback,
            go_ahead=go_ahead,
            equalizer=equalizer,
            rivalry=rivalry,
            upset=payload.summary.upset,
            is_final=payload.summary.is_final,
            decided_by_penalties=payload.summary.decided_by_penalties,
            crowd_spike=clip.crowd_spike,
            total_goals=payload.summary.home_score + payload.summary.away_score,
            late_drama=clip.minute >= 75,
        )

    def _engagement_score(self, *, clip: Any, breakdown: int, payload: MatchReplayPayloadView) -> float:
        base = min(100.0, 24.0 + (breakdown * 0.35))
        if clip.crowd_spike:
            base += 8.0
        if payload.summary.upset:
            base += 6.0
        if clip.importance >= 4:
            base += 5.0
        return round(min(base, 100.0), 2)

    def _freshness_score(self, updated_at: datetime) -> float:
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        age_hours = max((datetime.now(UTC) - updated_at.astimezone(UTC)).total_seconds() / 3600.0, 0.0)
        freshness = max(12.0, 100.0 - (age_hours * 6.0))
        return round(min(freshness, 100.0), 2)

    def _tags(self, *, payload: MatchReplayPayloadView, clip: Any, context: ViralScoreContext) -> list[str]:
        tags = [clip.event_type.replace("_", " ")]
        if context.comeback:
            tags.append("comeback")
        if context.equalizer:
            tags.append("equalizer")
        if context.go_ahead:
            tags.append("winner")
        if payload.summary.is_final:
            tags.append("final")
        if payload.summary.upset:
            tags.append("upset")
        tags.append("shareable")
        return tags

    def _leader(self, home_score: int, away_score: int) -> str | None:
        if home_score > away_score:
            return "home"
        if away_score > home_score:
            return "away"
        return None

    def _leader_delta(
        self,
        previous_home: int,
        previous_away: int,
        current_home: int,
        current_away: int,
    ) -> str | None:
        if current_home > previous_home:
            return "home"
        if current_away > previous_away:
            return "away"
        return None

    @staticmethod
    def _creator_id(clip: ViralClipView) -> str | None:
        metadata = dict(clip.metadata or {})
        creator_id = metadata.get("creator_id")
        if isinstance(creator_id, str) and creator_id.strip():
            return creator_id.strip()
        return None
