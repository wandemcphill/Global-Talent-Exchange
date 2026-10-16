from __future__ import annotations

from collections import Counter

from .schema import CatalogueRecord

DEFAULT_MAX_PER_COUNTRY = 35


def _completeness_score(record: CatalogueRecord) -> int:
    values = (
        record.country_code,
        record.date_of_birth,
        record.historical_height_cm,
        record.primary_position,
        record.preferred_foot,
        record.era,
        record.signature_traits,
        record.position_candidates,
    )
    return sum(value not in (None, "", []) for value in values)


def select_candidates(
    records: list[CatalogueRecord],
    *,
    target_count: int,
    max_per_country: int = DEFAULT_MAX_PER_COUNTRY,
) -> list[CatalogueRecord]:
    """Select a deterministic, country-diverse candidate set without inventing data.

    Countries are capped, known-country candidates are preferred over unknown-country
    candidates, and records with more sourced identity/football fields are preferred.
    Any shortage is returned as-is so the caller can fail the target-count gate.
    """
    if target_count < 1:
        raise ValueError("target_count must be positive")
    if max_per_country < 1:
        raise ValueError("max_per_country must be positive")

    deduped: dict[str, CatalogueRecord] = {}
    for record in records:
        deduped.setdefault(record.source_id, record)

    ordered = sorted(
        deduped.values(),
        key=lambda record: (
            record.country_code is None,
            -_completeness_score(record),
            record.country_code or "ZZZ",
            record.full_name.casefold(),
            record.source_id,
        ),
    )

    selected: list[CatalogueRecord] = []
    counts: Counter[str] = Counter()
    for record in ordered:
        country = record.country_code or "__UNKNOWN__"
        if counts[country] >= max_per_country:
            continue
        selected.append(record)
        counts[country] += 1
        if len(selected) >= target_count:
            break

    return selected
