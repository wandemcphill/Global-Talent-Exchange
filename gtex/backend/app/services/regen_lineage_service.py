from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.regen import RegenLineageProfile, RegenRelationshipTag, RegenTwinsGroup
from app.services.regen_service import LineageSelection


@dataclass(slots=True)
class RegenLineageService:
    session: Session

    def attach_lineage(self, *, regen_id: str, selection: LineageSelection) -> RegenLineageProfile:
        record = self.session.scalar(
            select(RegenLineageProfile).where(RegenLineageProfile.regen_id == regen_id)
        )
        if record is None:
            record = RegenLineageProfile(
                regen_id=regen_id,
                relationship_type=selection.relationship_type,
                related_legend_type=selection.related_legend_type,
                related_legend_ref_id=selection.related_legend_ref_id,
                lineage_country_code=selection.lineage_country_code,
                lineage_hometown_code=selection.lineage_hometown_code,
                is_owner_son=selection.is_owner_son,
                is_retired_regen_lineage=selection.is_retired_regen_lineage,
                is_real_legend_lineage=selection.is_real_legend_lineage,
                is_celebrity_lineage=selection.is_celebrity_lineage,
                is_celebrity_licensed=selection.is_celebrity_licensed,
                lineage_tier=selection.lineage_tier,
                narrative_text=selection.narrative_text,
                metadata_json=dict(selection.metadata),
            )
            self.session.add(record)
        for tag in selection.tags:
            self.session.add(
                RegenRelationshipTag(
                    regen_id=regen_id,
                    tag=tag,
                    relationship_type=selection.relationship_type,
                    related_entity_type=selection.related_legend_type,
                    related_entity_id=selection.related_legend_ref_id,
                    display_text=selection.narrative_text,
                    metadata_json={"source": "lineage_service"},
                )
            )
        self.session.flush()
        return record

    def attach_twins_group(
        self,
        *,
        regen_ids: tuple[str, ...],
        club_id: str | None,
        season_label: str,
        visual_seed: str,
        similarity_score: float,
    ) -> str:
        group_key = f"twins-{uuid4().hex[:10]}"
        for regen_id in regen_ids:
            self.session.add(
                RegenTwinsGroup(
                    twins_group_key=group_key,
                    regen_id=regen_id,
                    club_id=club_id,
                    season_label=season_label,
                    visual_seed=visual_seed,
                    similarity_score=similarity_score,
                    metadata_json={"source": "lineage_service"},
                )
            )
        self.session.flush()
        return group_key


__all__ = ["RegenLineageService"]
