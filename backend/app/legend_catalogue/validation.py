from __future__ import annotations

from collections import Counter

from .schema import CatalogueBundle, CatalogueRecord, ReleaseGateResult


REQUIRED_FOR_RELEASE = (
    "country_code",
    "date_of_birth",
    "historical_height_cm",
    "primary_position",
    "preferred_foot",
    "era",
    "legendary_classification",
)
FORBIDDEN_PORTRAIT_SOURCE_KEYS = frozenset(
    {"source_image_ref", "image", "image_url", "reference_image_url", "portrait_url"}
)


def record_blockers(record: CatalogueRecord) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FOR_RELEASE:
        if getattr(record, field) in (None, "", []):
            errors.append(f"missing_{field}")
    if not record.signature_traits:
        errors.append("missing_signature_traits")
    if not record.technical_profile:
        errors.append("missing_technical_profile")
    if not record.physical_profile:
        errors.append("missing_physical_profile")
    if not record.mental_profile:
        errors.append("missing_mental_profile")
    if not record.source_evidence:
        errors.append("missing_source_evidence")
    if not record.football_evidence:
        errors.append("missing_football_evidence")
    if record.editorial_status != "approved":
        errors.append("editorial_not_approved")
    if record.rights_status != "approved":
        errors.append("rights_not_approved")

    portrait = record.portrait_metadata
    if portrait.get("is_fictional_non_replicative") is not True:
        errors.append("portrait_not_approved_non_replicative")
    if FORBIDDEN_PORTRAIT_SOURCE_KEYS.intersection(portrait):
        errors.append("portrait_contains_source_image_reference")

    return errors


def evaluate_release(bundle: CatalogueBundle, *, target_count: int | None = None) -> ReleaseGateResult:
    target = int(target_count or bundle.target_count)
    by_id = Counter(record.source_id for record in bundle.records)
    duplicates = sum(1 for count in by_id.values() if count > 1)
    eligible = 0
    errors: list[str] = []

    for record in bundle.records:
        blockers = record_blockers(record)
        if blockers:
            errors.extend(f"{record.source_id}:{reason}" for reason in blockers)
        else:
            eligible += 1

    if len(bundle.records) != target:
        errors.append(f"catalogue_count={len(bundle.records)} expected={target}")
    if duplicates:
        errors.append(f"duplicate_source_ids={duplicates}")

    blocked = len(bundle.records) - eligible
    return ReleaseGateResult(
        target_count=target,
        eligible_count=eligible,
        blocked_count=blocked,
        duplicate_count=duplicates,
        ready=not errors and eligible == target,
        errors=errors,
    )
