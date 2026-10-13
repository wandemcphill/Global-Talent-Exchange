"""Validated import boundary for the Legendary Player registry.

The registry is data, not a second player, ownership, market, transfer, or
national-team model.  Every accepted row is materialized as one normal
``ingestion_players`` row by :mod:`player_foundation`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.legend_layer.player_foundation import LegendaryPlayerFoundationService, LegendaryPlayerSeed
from app.models.user import User


LAUNCH_REGISTRY_SIZE = 2_000
REGISTRY_SCHEMA_VERSION = "gtex.legendary-registry.v1"


class LegendaryRegistryError(ValueError):
    pass


class LegendaryRegistryRecord(BaseModel):
    legendary_profile_id: str = Field(min_length=1, max_length=128)
    full_name: str = Field(min_length=1, max_length=160)
    nationality: str = Field(min_length=1, max_length=128)
    nationality_code: str = Field(min_length=2, max_length=3)
    primary_position: str = Field(min_length=1, max_length=32)
    market_value_eur: float = Field(gt=0)
    date_of_birth: date | None = None
    is_active: bool
    is_tradable: bool
    rental_policy: str

    @field_validator("legendary_profile_id", "full_name", "nationality", "primary_position")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("nationality_code")
    @classmethod
    def _normalize_country_code(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) not in {2, 3} or not value.isalpha():
            raise ValueError("must be a two- or three-letter country code")
        return value

    @model_validator(mode="after")
    def _require_launch_lifecycle(self) -> "LegendaryRegistryRecord":
        if not self.is_active:
            raise ValueError("launch legendary players must be active")
        if not self.is_tradable:
            raise ValueError("launch legendary players must be tradable")
        if self.rental_policy != "existing_rules":
            raise ValueError("rental_policy must be existing_rules")
        return self

    def to_seed(self) -> LegendaryPlayerSeed:
        return LegendaryPlayerSeed(
            key=self.legendary_profile_id,
            full_name=self.full_name,
            nationality_name=self.nationality,
            nationality_code=self.nationality_code,
            position=self.primary_position,
            market_value_eur=self.market_value_eur,
            date_of_birth=self.date_of_birth,
        )


@dataclass(frozen=True, slots=True)
class LegendaryRegistry:
    records: tuple[LegendaryRegistryRecord, ...]
    source_path: Path | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any], *, expected_count: int = LAUNCH_REGISTRY_SIZE) -> "LegendaryRegistry":
        if payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
            raise LegendaryRegistryError(f"schema_version must be {REGISTRY_SCHEMA_VERSION!r}")
        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            raise LegendaryRegistryError("records must be a list")
        if len(raw_records) != expected_count:
            raise LegendaryRegistryError(f"expected {expected_count} registry rows, found {len(raw_records)}")
        try:
            records = tuple(LegendaryRegistryRecord.model_validate(item) for item in raw_records)
        except Exception as exc:
            raise LegendaryRegistryError(f"invalid registry record: {exc}") from exc
        ids = [record.legendary_profile_id for record in records]
        if len(ids) != len(set(ids)):
            raise LegendaryRegistryError("duplicate legendary_profile_id in registry")
        return cls(records=tuple(sorted(records, key=lambda record: record.legendary_profile_id)))

    @classmethod
    def from_file(cls, path: str | Path, *, expected_count: int = LAUNCH_REGISTRY_SIZE) -> "LegendaryRegistry":
        source_path = Path(path)
        try:
            payload = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LegendaryRegistryError(f"cannot read registry: {exc}") from exc
        registry = cls.from_payload(payload, expected_count=expected_count)
        return cls(records=registry.records, source_path=source_path)


def seed_legendary_registry(
    session: Session, *, registry: LegendaryRegistry, actor: User
) -> dict[str, int]:
    """Materialize a validated registry through normal player and market services."""
    return LegendaryPlayerFoundationService(session).seed_many(
        seeds=(record.to_seed() for record in registry.records), actor=actor
    )


def registry_ids(records: Iterable[LegendaryRegistryRecord]) -> set[str]:
    return {record.legendary_profile_id for record in records}
