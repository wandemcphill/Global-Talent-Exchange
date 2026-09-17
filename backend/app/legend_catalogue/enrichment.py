from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .schema import CatalogueBundle, CatalogueRecord, CatalogueStatus, EditorialStatus, Evidence, RightsStatus


class EnrichmentPatch(BaseModel):
    source_id: str = Field(min_length=2, max_length=128)
    full_name: str | None = None
    country_code: str | None = None
    date_of_birth: date | None = None
    historical_height_cm: int | None = Field(default=None, ge=120, le=230)
    position_candidates: list[str] | None = None
    primary_position: str | None = None
    secondary_positions: list[str] | None = None
    preferred_foot: Literal["left", "right", "both"] | None = None
    era: str | None = None
    legendary_classification: str | None = None
    signature_traits: list[str] | None = None
    signature_role: str | None = None
    technical_profile: dict[str, Any] | None = None
    physical_profile: dict[str, Any] | None = None
    mental_profile: dict[str, Any] | None = None
    football_evidence: list[Evidence] | None = None
    source_evidence: list[Evidence] | None = None
    portrait_metadata: dict[str, Any] | None = None
    editorial_status: EditorialStatus | None = None
    rights_status: RightsStatus | None = None
    catalogue_status: CatalogueStatus | None = None
    source_notes: str | None = None
    metadata: dict[str, Any] | None = None


class EnrichmentBundle(BaseModel):
    schema_version: str = "legendary-enrichment-v1"
    generated_at: datetime
    patches: list[EnrichmentPatch]


def apply_enrichment(bundle: CatalogueBundle, patches: EnrichmentBundle) -> CatalogueBundle:
    by_source_id = {record.source_id: deepcopy(record) for record in bundle.records}
    unknown_ids = [patch.source_id for patch in patches.patches if patch.source_id not in by_source_id]
    if unknown_ids:
        raise ValueError(f"Enrichment references unknown source IDs: {unknown_ids[:10]}")

    for patch in patches.patches:
        record = by_source_id[patch.source_id]
        values = patch.model_dump(exclude_none=True)
        values.pop("source_id", None)
        updated = record.model_copy(update=values)
        updated = CatalogueRecord.model_validate(updated.model_dump())
        by_source_id[patch.source_id] = updated

    ordered = [by_source_id[record.source_id] for record in bundle.records]
    return CatalogueBundle.model_validate(bundle.model_copy(update={"records": ordered}).model_dump())
