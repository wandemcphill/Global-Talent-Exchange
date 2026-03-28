from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.agents.agent_brain import AgentDecision, AgentProfile
from app.agents.variant_planner import VariantPlan
from app.viral.schemas import (
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralClipDistributionView,
    ViralContentFormatView,
    ViralDistributionAccountView,
    ViralEditPlanView,
    ViralFeedbackLoopView,
    ViralPersonaView,
    ViralScoreBreakdownView,
    ViralTrendingClipView,
    ViralTrendingMetricsView,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _slug(value: str) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in value).strip("_")


@dataclass(frozen=True, slots=True)
class AgentGeneratedClip:
    clip_id: str
    agent_id: str
    candidate_id: str
    base_clip_id: str
    primary_format: str
    variant_formats: tuple[str, ...]
    boost_amount: float
    payload: dict[str, Any]
    trending_clip: ViralTrendingClipView
    created_at: datetime


class AgentContentGenerator:
    def generate(
        self,
        *,
        profile: AgentProfile,
        decision: AgentDecision,
        variants: list[VariantPlan],
        boost_amount: float = 0.0,
    ) -> AgentGeneratedClip:
        if decision.candidate is None or not variants:
            raise ValueError("Agent content generation requires a candidate and at least one variant.")

        candidate = decision.candidate
        created_at = _utcnow()
        highlight_id = candidate.source_event_id or candidate.candidate_id
        base_clip_id = f"{candidate.match_id}::{highlight_id}"
        primary_variant = variants[0]
        primary_format = primary_variant.format_key
        clip_id = f"{base_clip_id}::{_slug(profile.identity.agent_id)}::{primary_format}"
        caption_view = self._caption(profile=profile, decision=decision)
        breakdown = ViralScoreBreakdownView(
            base_event=int(round(max(candidate.priority_score, 0.1) * 100)),
            chaos_bonus=18 if primary_format == "meme_version" else 0,
            importance_bonus=12 if candidate.event_type in {"goal", "winner", "equalizer"} else 0,
            total=int(round(max(candidate.priority_score, 0.1) * 100 + (decision.risk_level * 25))),
        )
        distribution_account = ViralDistributionAccountView(
            handle=profile.identity.handle,
            niche=profile.identity.style,
            target_audience=profile.identity.target,
            fit_score=min(int(round(72 + (decision.confidence * 10))), 100),
            persona=ViralPersonaView(
                name=profile.identity.display_name,
                tone=profile.identity.style.replace("_", " "),
            ),
            cross_promo_handles=[],
            caption_tests=[],
        )
        primary_editor = self._editor(
            variant=primary_variant,
            decision=decision,
            watermark_text=profile.identity.display_name,
        )
        format_views = [
            ViralContentFormatView(
                format_key=variant.format_key,
                title=variant.title,
                description=variant.description,
                editor=self._editor(variant=variant, decision=decision, watermark_text=profile.identity.display_name),
            )
            for variant in variants
        ]
        analytics = ViralClipAnalyticsView(
            clip_id=clip_id,
            views_last_10min=max(int(round(max(candidate.priority_score, 0.1) * 12)), 1),
            views_last_60min=max(int(round(max(candidate.priority_score, 0.1) * 20)), 1),
        )
        ranking_score = round(max(candidate.priority_score, 0.1) * (1.0 + (decision.risk_level * 0.30)), 4)
        velocity = round(max(candidate.priority_score, 0.1) * (1.0 + (decision.risk_level * 0.20)), 4)
        metadata = {
            "origin": "creator_agent",
            "agent_id": profile.identity.agent_id,
            "creator_id": profile.identity.handle,
            "creator_user_id": profile.identity.agent_id,
            "style": profile.identity.style,
            "target": profile.identity.target,
            "base_clip_id": base_clip_id,
            "selected_formats": [variant.format_key for variant in variants],
            "boost_amount": round(max(boost_amount, 0.0), 2),
            "risk_level": round(decision.risk_level, 4),
            "caption_seed": decision.caption_seed,
            "candidate_id": candidate.candidate_id,
            "published_at": created_at.isoformat(),
            "is_agent_generated": True,
            "distribution_stage": "test",
            "source_event_id": candidate.source_event_id,
        }
        feedback = ViralFeedbackLoopView(
            performance_tier="explore" if decision.risk_level >= 0.60 else "test",
            recommendation="Ship fast, watch the first engagement window, then either double down or rotate formats.",
            increase_similar_clips=decision.risk_level >= 0.50,
            shorten_clips=decision.duration_seconds <= 10,
            actions=["publish_now", "variant_test", "track_reward"],
            viral_analysis=f"Agent {profile.identity.agent_id} is testing {primary_format} against live attention.",
            analysis_source="creator_agent",
        )
        trending_clip = ViralTrendingClipView(
            clip_id=clip_id,
            match_id=candidate.match_id,
            highlight_id=highlight_id,
            title=self._title(profile=profile, candidate=candidate, primary_format=primary_format),
            reel_title=caption_view.hook,
            team_name=candidate.team_name,
            player_name=candidate.player_name,
            event_type=candidate.event_type,
            minute=candidate.minute,
            scoreline_label=candidate.scoreline_label,
            storage_key=candidate.storage_key,
            video_url=candidate.video_url,
            duration_seconds=float(decision.duration_seconds),
            render_status=candidate.render_status or "manifest_ready",
            viral_score=breakdown.total,
            engagement=round(max(candidate.priority_score, 0.1) * 0.6, 4),
            freshness=1.0,
            ranking_score=ranking_score,
            tags=list(candidate.detected_events),
            share_channel="creator_agent",
            breakdown=breakdown,
            caption=caption_view,
            distribution_accounts=[distribution_account],
            editor=primary_editor,
            formats=format_views,
            analytics=analytics,
            feedback=feedback,
            distribution=ViralClipDistributionView(
                impressions_served=0,
                impressions_cap=100,
                expansion_stage="test",
                frozen=False,
                eligible=True,
                remaining_impressions=100,
            ),
            metadata=metadata,
            rank=1,
            trending_score=ranking_score,
            age_hours=0.0,
            recompute_bucket="hot",
            last_ranked_at=created_at,
            trending_metrics=ViralTrendingMetricsView(
                completion_rate=0.0,
                avg_watch_time=0.0,
                avg_watch_time_normalized=0.0,
                loop_rate=0.0,
                share_rate=0.0,
                comment_rate=0.0,
                skip_rate=0.0,
                velocity=velocity,
                views_last_10min=analytics.views_last_10min,
                views_last_60min=analytics.views_last_60min,
                velocity_boost_applied=decision.risk_level >= 0.65,
                decay_multiplier=1.0,
            ),
        )
        payload = {
            "match_id": candidate.match_id,
            "moment_id": candidate.candidate_id,
            "clip_id": clip_id,
            "source_event_id": candidate.source_event_id,
            "event_type": candidate.event_type,
            "detected_events": list(candidate.detected_events),
            "priority_score": round(max(candidate.priority_score, 0.1), 4),
            "storage_key": candidate.storage_key,
            "render_status": candidate.render_status,
            "agent_id": profile.identity.agent_id,
            "variant_formats": [variant.format_key for variant in variants],
            "metadata": metadata,
            "seed_clip": trending_clip.model_dump(mode="json"),
        }
        return AgentGeneratedClip(
            clip_id=clip_id,
            agent_id=profile.identity.agent_id,
            candidate_id=candidate.candidate_id,
            base_clip_id=base_clip_id,
            primary_format=primary_format,
            variant_formats=tuple(variant.format_key for variant in variants),
            boost_amount=round(max(boost_amount, 0.0), 2),
            payload=payload,
            trending_clip=trending_clip,
            created_at=created_at,
        )

    @staticmethod
    def _editor(*, variant: VariantPlan, decision: AgentDecision, watermark_text: str) -> ViralEditPlanView:
        return ViralEditPlanView(
            format_key=variant.format_key,
            style_preset=variant.style_preset,
            crop_filter="scale=1080:1920",
            overlay_text=variant.overlay_text,
            transcode_command=[],
            overlay_command=[],
            loop_window_seconds=max(min(int(round(decision.duration_seconds / 2)), 8), 4),
            watermark_text=watermark_text,
            share_targets=["trending_feed", "for_you_seed"],
            narrative_device=variant.narrative_device,
            effect_stack=[variant.style_preset],
            publish_strategy="post_now" if decision.risk_level >= 0.45 else "staggered_drop",
            commentary_prompt=variant.commentary_prompt,
        )

    @staticmethod
    def _caption(*, profile: AgentProfile, decision: AgentDecision) -> ViralCaptionView:
        candidate = decision.candidate
        assert candidate is not None
        subject = candidate.player_name or candidate.team_name or "This play"
        if profile.identity.style == "chaotic_meme":
            caption = f"{subject} just detonated the timeline. No one is defending this."
            hook = "WHAT JUST HAPPENED"
        elif profile.identity.style == "tactical_breakdown":
            caption = f"{subject} changed the shape of the game in one sequence."
            hook = "Pause here. This is the move."
        elif profile.identity.style == "cinematic_story":
            caption = f"{subject} turned a live moment into a clean narrative beat."
            hook = "Every angle tells the same story."
        else:
            caption = f"{subject} shifted the match in seconds."
            hook = "This is where it flipped."
        return ViralCaptionView(
            hook=hook,
            caption=caption,
            hashtags=["#GTEX", "#AICreator", f"#{candidate.event_type.title().replace('_', '')}"],
            source="creator_agent",
        )

    @staticmethod
    def _title(*, profile: AgentProfile, candidate, primary_format: str) -> str:  # noqa: ANN001
        format_label = primary_format.replace("_", " ")
        if candidate.player_name:
            return f"{candidate.player_name} | {format_label.title()}"
        if candidate.team_name:
            return f"{candidate.team_name} | {format_label.title()}"
        return f"{profile.identity.display_name} | {format_label.title()}"


__all__ = [
    "AgentContentGenerator",
    "AgentGeneratedClip",
]
