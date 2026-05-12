from __future__ import annotations

from dataclasses import dataclass, field

from app.ingestion.models import Player
from app.value_engine.config import ValueEngineConfig, get_value_engine_config
from app.value_engine.models import (
    PlayerProfileContext,
    RealPlayerValuationBridgeResult,
    ReferenceValueContext,
)
from app.value_engine.read_models import PlayerValueSnapshotRecord
from app.value_engine.scoring import ValueEngine, credits_from_real_world_value


@dataclass(slots=True)
class RealPlayerValuationAdapter:
    config: ValueEngineConfig = field(default_factory=get_value_engine_config)
    scorer: ValueEngine = field(init=False)

    def __post_init__(self) -> None:
        self.scorer = ValueEngine(config=self.config)

    def build(
        self,
        *,
        player: Player,
        profile: PlayerProfileContext,
        reference_context: ReferenceValueContext,
        reference_market_value_eur: float,
        previous_snapshot: PlayerValueSnapshotRecord | None,
    ) -> RealPlayerValuationBridgeResult | None:
        if not player.is_real_player or not self.config.real_player_bridge_enabled:
            return None
        if reference_context.confidence_tier == "heuristic_only" or reference_context.source == "heuristic_profile_baseline":
            return None

        source_market_value_eur = round(max(reference_market_value_eur, 1.0), 2)
        reference_weight = self._reference_weight(reference_context.confidence_tier)
        profile_baseline_market_value_eur = round(
            max(self.scorer._profile_baseline_market_value_eur(profile), 250_000.0),
            2,
        )
        scarcity_multiplier = self._scarcity_multiplier(player.real_player_tier)
        profile_completeness_multiplier = self._profile_completeness_multiplier(profile.profile_completeness_score)
        age_curve_multiplier = self.scorer._age_curve_multiplier(profile.age_years)
        competition_quality_multiplier = self.scorer._competition_quality_multiplier(profile)
        club_quality_multiplier = self.scorer._club_quality_multiplier(profile)
        visibility_multiplier = self.scorer._visibility_multiplier(profile)

        unclamped_market_value_eur = round(
            (
                (source_market_value_eur * reference_weight)
                + (profile_baseline_market_value_eur * (1.0 - reference_weight))
            )
            * scarcity_multiplier
            * profile_completeness_multiplier,
            2,
        )
        floor_market_value_eur = round(source_market_value_eur * self.config.real_player_bridge_floor_ratio, 2)
        ceiling_market_value_eur = round(source_market_value_eur * self.config.real_player_bridge_ceiling_ratio, 2)

        clamped_market_value_eur = unclamped_market_value_eur
        actions: list[str] = []
        if unclamped_market_value_eur < floor_market_value_eur:
            clamped_market_value_eur = floor_market_value_eur
            actions.append("floor_guard")
        elif unclamped_market_value_eur > ceiling_market_value_eur:
            clamped_market_value_eur = ceiling_market_value_eur
            actions.append("ceiling_guard")

        previous_bridge_market_value_eur = self._previous_bridge_market_value_eur(previous_snapshot)
        bridge_market_value_eur = clamped_market_value_eur
        smoothing_factor = 0.0
        if previous_bridge_market_value_eur is not None and previous_bridge_market_value_eur > 0:
            smoothing_factor = self.config.real_player_bridge_smoothing_factor
            bridge_market_value_eur = round(
                previous_bridge_market_value_eur
                + ((clamped_market_value_eur - previous_bridge_market_value_eur) * smoothing_factor),
                2,
            )
            bridge_market_value_eur = round(
                min(max(bridge_market_value_eur, floor_market_value_eur), ceiling_market_value_eur),
                2,
            )
            if abs(bridge_market_value_eur - clamped_market_value_eur) >= 0.01:
                actions.append("smoothed")

        base_value_credits = credits_from_real_world_value(
            bridge_market_value_eur,
            eur_per_credit=self.config.baseline_eur_per_credit,
        )
        floor_credits = credits_from_real_world_value(
            floor_market_value_eur,
            eur_per_credit=self.config.baseline_eur_per_credit,
        )
        ceiling_credits = credits_from_real_world_value(
            ceiling_market_value_eur,
            eur_per_credit=self.config.baseline_eur_per_credit,
        )

        normalized_tier = self._normalized_tier(player.real_player_tier)
        return RealPlayerValuationBridgeResult(
            adapter_code="real_player_market_value_bridge",
            adapter_version=self.config.real_player_bridge_version,
            source_market_value_eur=source_market_value_eur,
            source_reference_weight=reference_weight,
            source_reference_tier=reference_context.confidence_tier,
            source_reference_origin=reference_context.source,
            profile_baseline_market_value_eur=profile_baseline_market_value_eur,
            scarcity_multiplier=scarcity_multiplier,
            profile_completeness_multiplier=profile_completeness_multiplier,
            age_curve_multiplier=age_curve_multiplier,
            competition_quality_multiplier=competition_quality_multiplier,
            club_quality_multiplier=club_quality_multiplier,
            visibility_multiplier=visibility_multiplier,
            floor_market_value_eur=floor_market_value_eur,
            ceiling_market_value_eur=ceiling_market_value_eur,
            unclamped_market_value_eur=unclamped_market_value_eur,
            bridge_market_value_eur=bridge_market_value_eur,
            base_value_credits=base_value_credits,
            floor_credits=floor_credits,
            ceiling_credits=ceiling_credits,
            previous_bridge_market_value_eur=previous_bridge_market_value_eur,
            smoothing_factor=smoothing_factor,
            actions=tuple(actions),
            inputs={
                "player_id": player.id,
                "player_name": player.full_name,
                "source_provider": player.source_provider,
                "provider_external_id": player.provider_external_id,
                "reference_market_value_eur": source_market_value_eur,
                "reference_confidence_tier": reference_context.confidence_tier,
                "reference_source": reference_context.source,
                "position_family": profile.position_family,
                "position_subrole": profile.position_subrole,
                "age_years": round(profile.age_years, 2) if profile.age_years is not None else None,
                "competition_tier": profile.competition_tier,
                "club_tier": profile.club_tier,
                "player_class": profile.player_class,
                "real_player_tier": normalized_tier,
                "profile_completeness_score": profile.profile_completeness_score,
            },
            components={
                "reference_weight": round(reference_weight, 4),
                "profile_weight": round(1.0 - reference_weight, 4),
                "scarcity_multiplier": round(scarcity_multiplier, 4),
                "profile_completeness_multiplier": round(profile_completeness_multiplier, 4),
                "age_curve_multiplier": round(age_curve_multiplier, 4),
                "competition_quality_multiplier": round(competition_quality_multiplier, 4),
                "club_quality_multiplier": round(club_quality_multiplier, 4),
                "visibility_multiplier": round(visibility_multiplier, 4),
            },
            explanation=self._explanation(
                source_market_value_eur=source_market_value_eur,
                reference_context=reference_context,
                reference_weight=reference_weight,
                profile_baseline_market_value_eur=profile_baseline_market_value_eur,
                normalized_tier=normalized_tier,
                scarcity_multiplier=scarcity_multiplier,
                profile_completeness_multiplier=profile_completeness_multiplier,
                floor_market_value_eur=floor_market_value_eur,
                ceiling_market_value_eur=ceiling_market_value_eur,
                previous_bridge_market_value_eur=previous_bridge_market_value_eur,
                bridge_market_value_eur=bridge_market_value_eur,
                actions=tuple(actions),
            ),
        )

    def _reference_weight(self, confidence_tier: str) -> float:
        lookup_key = self.scorer._normalize_lookup_key(confidence_tier or "heuristic_only")
        default_weight = 0.30
        return round(self.config.real_player_bridge_reference_weights.get(lookup_key, default_weight), 4)

    def _scarcity_multiplier(self, real_player_tier: str | None) -> float:
        normalized_tier = self._normalized_tier(real_player_tier)
        return round(self.config.real_player_bridge_tier_multipliers.get(normalized_tier, 1.0), 4)

    def _normalized_tier(self, real_player_tier: str | None) -> str:
        if not real_player_tier:
            return "core"
        return self.scorer._normalize_lookup_key(real_player_tier)

    def _profile_completeness_multiplier(self, profile_completeness_score: float | None) -> float:
        if profile_completeness_score is None:
            return 1.0
        normalized_score = float(profile_completeness_score)
        if normalized_score > 1.0:
            normalized_score = normalized_score / 100.0
        normalized_score = min(max(normalized_score, 0.55), 1.0)
        return round(min(max(0.95 + (normalized_score * 0.08), 0.96), 1.03), 4)

    def _previous_bridge_market_value_eur(self, previous_snapshot: PlayerValueSnapshotRecord | None) -> float | None:
        if previous_snapshot is None or not isinstance(previous_snapshot.breakdown_json, dict):
            return None
        valuation_payload = previous_snapshot.breakdown_json.get("real_player_valuation")
        if not isinstance(valuation_payload, dict):
            return None
        raw_value = valuation_payload.get("bridge_market_value_eur")
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            return None
        if value <= 0:
            return None
        return round(value, 2)

    def _explanation(
        self,
        *,
        source_market_value_eur: float,
        reference_context: ReferenceValueContext,
        reference_weight: float,
        profile_baseline_market_value_eur: float,
        normalized_tier: str,
        scarcity_multiplier: float,
        profile_completeness_multiplier: float,
        floor_market_value_eur: float,
        ceiling_market_value_eur: float,
        previous_bridge_market_value_eur: float | None,
        bridge_market_value_eur: float,
        actions: tuple[str, ...],
    ) -> tuple[str, ...]:
        explanations = [
            (
                f"Input reference {source_market_value_eur:.2f} EUR from {reference_context.source} "
                f"carries {reference_weight:.0%} of the bridge weight."
            ),
            (
                f"Structural baseline {profile_baseline_market_value_eur:.2f} EUR contributes the remaining "
                f"{(1.0 - reference_weight):.0%} through age, position, club, and competition context."
            ),
            (
                f"Real-player tier '{normalized_tier}' applies a scarcity multiplier of {scarcity_multiplier:.3f} "
                f"and profile completeness applies {profile_completeness_multiplier:.3f}."
            ),
            (
                f"Bridge output is bounded between {floor_market_value_eur:.2f} EUR and "
                f"{ceiling_market_value_eur:.2f} EUR before GTEX conversion."
            ),
        ]
        if previous_bridge_market_value_eur is not None:
            explanations.append(
                f"Previous authoritative bridge anchor {previous_bridge_market_value_eur:.2f} EUR is used for smoothing."
            )
        if actions:
            explanations.append(
                f"Applied bridge actions: {', '.join(actions)}. Final bridge anchor is {bridge_market_value_eur:.2f} EUR."
            )
        else:
            explanations.append(f"Final bridge anchor is {bridge_market_value_eur:.2f} EUR without extra guards.")
        return tuple(explanations)


__all__ = ["RealPlayerValuationAdapter"]
