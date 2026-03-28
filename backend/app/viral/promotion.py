from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import random

from sqlalchemy.orm import Session

from app.models.clip_variant import ClipVariant
from app.viral.comparator import ViralVariantScoringComparator
from app.viral.variant_manager import ViralClipVariantManager


@dataclass(slots=True)
class VariantPromotionDecision:
    base_clip_id: str
    resolved: bool
    decision_reason: str | None
    leading_variant_id: str | None
    winner_variant_id: str | None


@dataclass(slots=True)
class ViralClipPromotionService:
    session: Session
    comparator: ViralVariantScoringComparator = field(default_factory=ViralVariantScoringComparator)
    winner_window: timedelta = field(default_factory=lambda: timedelta(minutes=10))
    moment_winner_window: timedelta = field(default_factory=lambda: timedelta(minutes=3))
    winner_view_threshold: int = 1000
    exploitation_weight: float = 0.8

    def refresh(self, base_clip_id: str) -> VariantPromotionDecision:
        manager = ViralClipVariantManager(session=self.session, comparator=self.comparator)
        variants = manager.list_variants(base_clip_id)
        if not variants:
            return VariantPromotionDecision(
                base_clip_id=base_clip_id,
                resolved=False,
                decision_reason=None,
                leading_variant_id=None,
                winner_variant_id=None,
            )

        for variant in variants:
            variant.viral_score = self.comparator.score_variant(variant).total

        leading_variant = self.comparator.best_variant(variants)
        decision_reason = self._decision_reason(variants)
        if decision_reason is not None:
            self._promote_winner(variants=variants, winner=leading_variant)
        else:
            self._apply_exploration_weights(variants=variants, leading_variant=leading_variant)

        self.session.commit()
        return VariantPromotionDecision(
            base_clip_id=base_clip_id,
            resolved=decision_reason is not None,
            decision_reason=decision_reason,
            leading_variant_id=leading_variant.variant_id,
            winner_variant_id=leading_variant.variant_id if decision_reason is not None else None,
        )

    def select_delivery_variant(
        self,
        base_clip_id: str,
        *,
        random_source: random.Random | None = None,
    ) -> ClipVariant | None:
        decision = self.refresh(base_clip_id)
        manager = ViralClipVariantManager(session=self.session, comparator=self.comparator)
        variants = manager.list_variants(base_clip_id)
        if not variants:
            return None
        if decision.resolved and decision.winner_variant_id is not None:
            return next((variant for variant in variants if variant.variant_id == decision.winner_variant_id), variants[0])

        leading_variant = next((variant for variant in variants if variant.variant_id == decision.leading_variant_id), variants[0])
        alternatives = [variant for variant in variants if variant.variant_id != leading_variant.variant_id]
        if not alternatives:
            return leading_variant

        rng = random_source or random.Random()
        if rng.random() < self.exploitation_weight:
            return leading_variant
        return alternatives[rng.randrange(len(alternatives))]

    def _decision_reason(self, variants: list[ClipVariant]) -> str | None:
        if any(variant.view_count >= self.winner_view_threshold for variant in variants):
            return "view_threshold"

        oldest_variant = min(variants, key=lambda variant: variant.created_at)
        created_at = oldest_variant.created_at.astimezone(UTC) if oldest_variant.created_at.tzinfo is not None else oldest_variant.created_at.replace(tzinfo=UTC)
        if datetime.now(UTC) - created_at >= self._winner_window_for(variants):
            return "time_threshold"
        return None

    def _winner_window_for(self, variants: list[ClipVariant]) -> timedelta:
        if any(self._is_moment_variant(variant) for variant in variants):
            return self.moment_winner_window
        return self.winner_window

    @staticmethod
    def _is_moment_variant(variant: ClipVariant) -> bool:
        metadata = dict(variant.metadata_json or {})
        source = str(metadata.get("source") or "").strip().lower()
        if source in {"moment", "moments_engine"}:
            return True
        return str(variant.base_clip_id).strip().lower().startswith("moment")

    def _apply_exploration_weights(self, *, variants: list[ClipVariant], leading_variant: ClipVariant) -> None:
        if len(variants) == 1:
            leading_variant.distribution_weight = 1.0
        else:
            exploration_weight = round((1.0 - self.exploitation_weight) / max(len(variants) - 1, 1), 4)
            for variant in variants:
                variant.distribution_weight = exploration_weight
            leading_variant.distribution_weight = self.exploitation_weight

        for variant in variants:
            variant.promotion_enabled = True
            variant.pushed_to_trending = False
            variant.is_winner = False
            variant.winner_selected_at = None
            variant.promotion_status = "exploring_leader" if variant.variant_id == leading_variant.variant_id else "exploring"

    def _promote_winner(self, *, variants: list[ClipVariant], winner: ClipVariant) -> None:
        selected_at = datetime.now(UTC)
        for variant in variants:
            variant.is_winner = variant.variant_id == winner.variant_id
            variant.winner_selected_at = selected_at if variant.variant_id == winner.variant_id else None
            variant.pushed_to_trending = variant.variant_id == winner.variant_id
            variant.promotion_enabled = variant.variant_id == winner.variant_id
            variant.distribution_weight = 1.0 if variant.variant_id == winner.variant_id else 0.0
            variant.promotion_status = "boosted" if variant.variant_id == winner.variant_id else "killed"


__all__ = ["VariantPromotionDecision", "ViralClipPromotionService"]
