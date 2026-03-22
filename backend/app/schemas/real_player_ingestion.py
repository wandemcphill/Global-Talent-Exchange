from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RealPlayerIngestionMode(str, Enum):
    CURATED_SEED = "curated_seed"
    REFRESH_EXISTING = "refresh_existing"
    BATCH_IMPORT = "batch_import"
    TEST_SMALL_REAL_SEED = "test_small_real_seed"


class RealPlayerSeedInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    source_name: str
    source_player_key: str
    canonical_name: str
    known_aliases: list[str] = Field(default_factory=list)
    nationality: str | None = None
    nationality_code: str | None = None
    date_of_birth: date | None = None
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    dominant_foot: str | None = None
    primary_position: str | None = None
    secondary_positions: list[str] = Field(default_factory=list)
    current_real_world_club: str | None = None
    current_real_world_club_key: str | None = None
    current_real_world_league: str | None = None
    current_real_world_league_key: str | None = None
    competition_level: str | None = None
    appearances: int | None = Field(default=None, ge=0)
    minutes_played: int | None = Field(default=None, ge=0)
    goals: int | None = Field(default=None, ge=0)
    assists: int | None = Field(default=None, ge=0)
    clean_sheets: int | None = Field(default=None, ge=0)
    injury_status: str | None = None
    height_cm: int | None = Field(default=None, ge=100, le=250)
    weight_kg: int | None = Field(default=None, ge=40, le=150)
    current_market_reference_value: float | None = Field(default=None, ge=0)
    market_reference_currency: str | None = "EUR"
    source_last_refreshed_at: datetime | None = None
    identity_confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    is_verified_real_player: bool = True
    real_player_tier: str | None = None

    @model_validator(mode="after")
    def normalize_payload(self) -> "RealPlayerSeedInput":
        if self.birth_year is None and self.date_of_birth is not None:
            self.birth_year = self.date_of_birth.year
        if self.market_reference_currency is not None:
            self.market_reference_currency = self.market_reference_currency.upper()
        self.known_aliases = _dedupe_strings(self.known_aliases)
        self.secondary_positions = _dedupe_strings(self.secondary_positions)
        return self


class RealPlayerIngestionRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    mode: RealPlayerIngestionMode = RealPlayerIngestionMode.CURATED_SEED
    players: list[RealPlayerSeedInput] = Field(default_factory=list)
    ingestion_batch_id: str | None = None
    ingestion_source_version: str | None = None
    as_of: datetime | None = None
    lookback_days: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_unique_players(self) -> "RealPlayerIngestionRequest":
        seen: set[tuple[str, str]] = set()
        for player in self.players:
            key = (player.source_name.lower(), player.source_player_key.lower())
            if key in seen:
                raise ValueError(
                    f"Duplicate real-player input detected for source '{player.source_name}' key '{player.source_player_key}'."
                )
            seen.add(key)
        return self


class RealPlayerIngestionItemResult(BaseModel):
    source_name: str
    source_player_key: str
    gtex_player_id: str
    action: str
    pricing_snapshot_id: str
    authoritative_price_credits: float
    identity_confidence_score: float


class RealPlayerBatchIssueCandidate(BaseModel):
    player_id: str
    score: float
    reasons: list[str] = Field(default_factory=list)


class RealPlayerBatchIssue(BaseModel):
    source_name: str
    source_player_key: str
    canonical_name: str
    issue_type: str
    message: str
    gtex_player_id: str | None = None
    candidates: list[RealPlayerBatchIssueCandidate] = Field(default_factory=list)


class RealPlayerDryRunReport(BaseModel):
    mode: str
    ingestion_batch_id: str
    ingestion_source_version: str | None = None
    as_of: datetime
    source_row_count: int
    normalized_row_count: int
    matched_existing_count: int
    new_identity_count: int
    ambiguous_match_count: int
    missing_pricing_snapshot_count: int
    hard_failure_count: int
    staged_player_ids: list[str] = Field(default_factory=list)
    issues: list[RealPlayerBatchIssue] = Field(default_factory=list)


class RealPlayerPostWriteAuditResult(BaseModel):
    duplicate_canonical_identity_count: int
    players_missing_authoritative_price_count: int
    players_missing_market_snapshot_count: int
    players_missing_avatar_seed_count: int
    agency_linkage_required_count: int
    agency_linkage_present_count: int
    agency_linkage_missing_count: int
    all_checks_passed: bool


class RealPlayerWriteReport(BaseModel):
    mode: str
    ingestion_batch_id: str
    ingestion_source_version: str | None = None
    as_of: datetime
    players_processed: int
    players_created: int
    players_updated: int
    identities_linked: int
    duplicates_prevented: int
    pricing_snapshots_resolved: int
    avatars_assigned: int
    agency_profiles_created_or_attached: int
    player_ids: list[str] = Field(default_factory=list)
    results: list[RealPlayerIngestionItemResult] = Field(default_factory=list)
    audit: RealPlayerPostWriteAuditResult | None = None


class RealPlayerIngestionResult(BaseModel):
    mode: str
    ingestion_batch_id: str
    ingestion_source_version: str | None = None
    as_of: datetime
    players_processed: int
    players_created: int
    players_updated: int
    authoritative_snapshots_seeded: int
    player_ids: list[str]
    results: list[RealPlayerIngestionItemResult] = Field(default_factory=list)


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        folded = cleaned.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        deduped.append(cleaned)
    return deduped


__all__ = [
    "RealPlayerBatchIssue",
    "RealPlayerBatchIssueCandidate",
    "RealPlayerDryRunReport",
    "RealPlayerIngestionItemResult",
    "RealPlayerIngestionMode",
    "RealPlayerIngestionRequest",
    "RealPlayerIngestionResult",
    "RealPlayerPostWriteAuditResult",
    "RealPlayerSeedInput",
    "RealPlayerWriteReport",
]
