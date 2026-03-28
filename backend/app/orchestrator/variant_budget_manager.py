from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.clip_variant import ClipVariant
from app.orchestrator.global_state import AttentionOrchestratorConfig, ClipGlobalState
from app.viral.variant_manager import parse_base_clip_id


@dataclass(frozen=True, slots=True)
class VariantBudgetSplit:
    variant_id: str
    share: float
    allocated_impressions: int
    locked: bool = False
    viral_score: float = 0.0
    global_exposure_feedback: float = 0.0


@dataclass(slots=True)
class VariantBudgetManager:
    session: Session | None = None
    config: AttentionOrchestratorConfig = AttentionOrchestratorConfig()

    def sync(self, state: ClipGlobalState) -> list[VariantBudgetSplit]:
        if self.session is None:
            return []
        base_clip_id = state.base_clip_id or self._base_clip_id(state.clip_id)
        if base_clip_id is None or not self._has_variant_table():
            return []
        variants = list(
            self.session.scalars(
                select(ClipVariant)
                .where(ClipVariant.base_clip_id == base_clip_id)
                .order_by(ClipVariant.is_winner.desc(), ClipVariant.viral_score.desc(), ClipVariant.variant_id.asc())
            ).all()
        )
        if not variants:
            return []

        winner = next((variant for variant in variants if bool(variant.is_winner)), None)
        leader = winner or variants[0]
        locked = winner is not None
        leader_score = self._normalized_variant_score(float(leader.viral_score or 0.0))
        exposure_feedback = self._global_exposure_feedback(state)
        winner_share = 1.0 if locked else min(
            max(float(self.config.winner_share) + (leader_score * 0.12) + exposure_feedback, 0.0),
            1.0,
        )
        exploration_share = 0.0 if locked else min(max(float(self.config.exploration_share), 0.0), 1.0)
        residual_share = max(0.0, 1.0 - winner_share)
        if not locked and exploration_share > 0.0 and residual_share > 0.0:
            residual_share = min(residual_share, exploration_share)

        non_leaders = [variant for variant in variants if variant.variant_id != leader.variant_id]
        exploration_unit = (residual_share / len(non_leaders)) if non_leaders else 0.0

        splits: list[VariantBudgetSplit] = []
        for variant in variants:
            share = winner_share if variant.variant_id == leader.variant_id else exploration_unit
            if locked and variant.variant_id != leader.variant_id:
                share = 0.0
            variant.distribution_weight = round(share, 4)
            metadata = dict(variant.metadata_json or {})
            metadata["global_exposure_feedback"] = round(exposure_feedback, 4)
            metadata["variant_winner_score"] = round(leader_score, 4)
            metadata["orchestrator_stage"] = state.stage
            metadata["orchestrator_allocated_impressions"] = int(state.allocated_impressions)
            variant.metadata_json = metadata
            if locked:
                variant.is_winner = variant.variant_id == leader.variant_id
            splits.append(
                VariantBudgetSplit(
                    variant_id=variant.variant_id,
                    share=round(share, 4),
                    allocated_impressions=int(round(max(state.allocated_impressions, 0) * max(share, 0.0))),
                    locked=locked,
                    viral_score=round(float(variant.viral_score or 0.0), 4),
                    global_exposure_feedback=round(exposure_feedback, 4),
                )
            )
        self.session.flush()
        return splits

    def resolve_winner_variant_id(self, clip_id: str) -> str | None:
        if self.session is None or not self._has_variant_table():
            return None
        base_clip_id = self._base_clip_id(clip_id)
        if base_clip_id is None:
            return None
        winner = self.session.scalar(
            select(ClipVariant.variant_id)
            .where(ClipVariant.base_clip_id == base_clip_id, ClipVariant.is_winner.is_(True))
            .limit(1)
        )
        return str(winner).strip() if winner is not None and str(winner).strip() else None

    def _has_variant_table(self) -> bool:
        if self.session is None:
            return False
        bind = self.session.get_bind()
        if bind is None:
            return False
        try:
            return bool(inspect(bind).has_table(ClipVariant.__tablename__))
        except SQLAlchemyError:
            return False
        except Exception:
            return False

    @staticmethod
    def _base_clip_id(clip_id: str) -> str | None:
        parsed = parse_base_clip_id(clip_id)
        if parsed is None:
            return clip_id if clip_id.strip() else None
        match_id, highlight_id = parsed
        if "::" in highlight_id:
            highlight_id = highlight_id.split("::", 1)[0]
        return f"{match_id}::{highlight_id}"

    @staticmethod
    def _normalized_variant_score(score: float) -> float:
        normalized = score if score <= 1.0 else (score / 100.0)
        return min(max(normalized, 0.0), 1.0)

    @staticmethod
    def _global_exposure_feedback(state: ClipGlobalState) -> float:
        stage_bonus = {"test": 0.0, "expand": 0.06, "viral": 0.14, "decay": -0.08}.get(state.stage, 0.0)
        utilization = state.consumed_impressions / max(state.allocated_impressions, 1)
        velocity = min(max(float(state.velocity_score), 0.0), 2.0)
        return round(min(max(stage_bonus + (utilization * 0.10) + (velocity * 0.05), 0.0), 0.35), 4)


__all__ = ["VariantBudgetManager", "VariantBudgetSplit"]
