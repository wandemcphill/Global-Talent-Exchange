from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.copilot.feature_builder import CopilotFeatureBuilder
from app.copilot.prediction_service import CopilotPredictionService
from app.copilot.recommendation_engine import CopilotRecommendationEngine
from app.copilot.strategy_builder import CopilotStrategyBuilder
from app.copilot.timing_engine import CopilotTimingEngine
from app.models.user import User


class CreatorCopilotService:
    def __init__(
        self,
        session: Session,
        *,
        feature_builder: CopilotFeatureBuilder | None = None,
        prediction_service: CopilotPredictionService | None = None,
        recommendation_engine: CopilotRecommendationEngine | None = None,
        timing_engine: CopilotTimingEngine | None = None,
        strategy_builder: CopilotStrategyBuilder | None = None,
    ) -> None:
        self.session = session
        self.feature_builder = feature_builder or CopilotFeatureBuilder(session=session)
        self.prediction_service = prediction_service or CopilotPredictionService()
        self.recommendation_engine = recommendation_engine or CopilotRecommendationEngine()
        self.timing_engine = timing_engine or CopilotTimingEngine()
        self.strategy_builder = strategy_builder or CopilotStrategyBuilder()

    def analyze_draft(
        self,
        *,
        actor: User,
        creator_id: str,
        draft: Mapping[str, Any],
    ) -> dict[str, Any]:
        features = self.feature_builder.build(
            actor=actor,
            creator_id=creator_id,
            draft=draft,
        )
        prediction_bundle = self.prediction_service.analyze(features=features)
        public_prediction = dict(prediction_bundle["prediction"])
        hook_analysis = dict(prediction_bundle["hook_analysis"])
        format_scores = dict(prediction_bundle["format_scores"])

        variant_strategy = self.recommendation_engine.recommend(
            features=features,
            prediction=public_prediction,
            format_scores=format_scores,
        )
        timing = self.timing_engine.evaluate(
            features=features,
            prediction=public_prediction,
            hook_analysis=hook_analysis,
        )
        strategy_profile = self.strategy_builder.build(
            creator_id=creator_id,
            features={
                "creator_history": features.creator_history,
                "current_trends": features.current_trends,
                "audience_affinity": features.audience_affinity,
                "clip_metadata": features.clip_metadata,
            },
            prediction=public_prediction,
            variant_strategy=variant_strategy,
        )
        live_coaching = self._live_coaching(
            prediction=public_prediction,
            variant_strategy=variant_strategy,
        )
        action_plan = self._action_plan(
            prediction=public_prediction,
            hook_analysis=hook_analysis,
            timing=timing,
            variant_strategy=variant_strategy,
        )
        return {
            "creator_id": creator_id,
            "draft": dict(features.clip_metadata),
            "prediction": public_prediction,
            "variant_strategy": variant_strategy,
            "timing": timing,
            "hook_analysis": hook_analysis,
            "strategy_profile": strategy_profile,
            "live_coaching": live_coaching,
            "action_plan": action_plan,
        }

    def _live_coaching(
        self,
        *,
        prediction: Mapping[str, Any],
        variant_strategy: Mapping[str, Any],
    ) -> dict[str, Any]:
        leading_variant = next(
            (
                item.get("type")
                for item in (variant_strategy.get("recommended_variants") or [])
                if isinstance(item, Mapping)
            ),
            prediction.get("best_format"),
        )
        threshold = 65 if float(prediction.get("viral_probability", 0.0)) >= 0.7 else 55
        return {
            "event_name": "copilot.alert.triggered",
            "headline": "Switch fast if first-minute pace softens",
            "message": f"If the first 60 seconds land below {threshold}% of expected pace, shift emphasis to {leading_variant}.",
            "recommended_action": f"Promote the {leading_variant} variant and trim the intro immediately.",
        }

    def _action_plan(
        self,
        *,
        prediction: Mapping[str, Any],
        hook_analysis: Mapping[str, Any],
        timing: Mapping[str, Any],
        variant_strategy: Mapping[str, Any],
    ) -> list[str]:
        actions: list[str] = [f"Lead with the {prediction['best_format']} format."]
        if prediction.get("risk_flags"):
            for risk_flag in prediction["risk_flags"]:
                if risk_flag == "too long":
                    actions.append("Trim the draft before the first upload pass.")
                elif risk_flag == "low hook strength":
                    actions.append(str(hook_analysis.get("suggestion")))
                elif risk_flag == "high competition window":
                    actions.append(
                        f"Wait {timing['best_time_in_minutes']} minutes before posting."
                    )
                elif risk_flag == "format mismatch":
                    actions.append("Do not force the current format; follow the model recommendation.")
        leading_variant = next(
            (
                item.get("type")
                for item in (variant_strategy.get("recommended_variants") or [])
                if isinstance(item, Mapping) and not item.get("exploratory")
            ),
            None,
        )
        if leading_variant is not None:
            actions.append(f"Keep {leading_variant} ready as the first performance fallback.")
        deduped: list[str] = []
        for action in actions:
            if action not in deduped:
                deduped.append(action)
        return deduped[:5]


__all__ = ["CreatorCopilotService"]
