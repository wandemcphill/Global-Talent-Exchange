from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ClubView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    short_name: str | None
    country_name: str | None
    player_count: int
    updated_at: datetime


class MoraleScoreView(BaseModel):
    score: int = Field(ge=0, le=100)
    label: str
    trend: str | None = None
    source: str | None = None


class ChemistryFitView(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    position_fit: int = Field(ge=0, le=100)
    team_fit: int = Field(ge=0, le=100)
    warnings: list[str] = Field(default_factory=list)
    source: str | None = None


class InjuryView(BaseModel):
    player_id: str | None = None
    player_name: str | None = None
    type: str | None = None
    expected_return: datetime | None = None
    severity: str | None = None
    injury_date: datetime | None = None


class ContractStatusView(BaseModel):
    player_id: str | None = None
    player_name: str | None = None
    end_date: datetime | None = None
    status: str | None = None
    weeks_remaining: int | None = None
    alert: str | None = None
    source: str | None = None


class ScoutingNoteView(BaseModel):
    player_id: str | None = None
    author_id: str | None = None
    content: str
    created_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class PlayerStatsView(BaseModel):
    appearances: int | None = None
    rating: float | None = None


class SquadPlayerView(BaseModel):
    id: str
    name: str
    position: str
    age: int | None = Field(default=None, ge=0)
    nationality: str | None = None
    availability: str
    injury_detail: InjuryView | None = None
    medical_status: str | None = None
    medical_source: str | None = None
    morale: MoraleScoreView | None = None
    chemistry_fit: ChemistryFitView | None = None
    contract_status: ContractStatusView | None = None
    selection_ready: bool
    scouting_notes: list[ScoutingNoteView] = Field(default_factory=list)
    stats: PlayerStatsView


class SquadRosterView(BaseModel):
    players: list[SquadPlayerView] = Field(default_factory=list)
    selection_ready_count: int = Field(ge=0)


class AvailabilityMatrixPlayerView(BaseModel):
    player_id: str
    name: str
    position: str


class AvailabilityFixtureView(BaseModel):
    fixture_id: str
    label: str


class AvailabilityCellView(BaseModel):
    player_id: str
    fixture_id: str
    status: str


class AvailabilityRowView(BaseModel):
    player_id: str
    name: str
    position: str
    statuses: list[str] = Field(default_factory=list)


class AvailabilityMatrixView(BaseModel):
    players: list[AvailabilityMatrixPlayerView] = Field(default_factory=list)
    fixtures: list[AvailabilityFixtureView] = Field(default_factory=list)
    cells: list[AvailabilityCellView] = Field(default_factory=list)
    rows: list[AvailabilityRowView] = Field(default_factory=list)


class ChemistryReportView(BaseModel):
    overall_score: int | None = Field(default=None, ge=0, le=100)
    warnings: list[str] = Field(default_factory=list)


class SquadInjuriesView(BaseModel):
    injuries: list[InjuryView] = Field(default_factory=list)


class SquadContractsView(BaseModel):
    contracts: list[ContractStatusView] = Field(default_factory=list)


class SquadScoutingView(BaseModel):
    scouting_notes: list[ScoutingNoteView] = Field(default_factory=list)


class FormationSlotView(BaseModel):
    slot_id: str
    position: str
    assigned_player_id: str | None = None
    x: float
    y: float
    role: str = "balanced"
    filled: bool = False


FormationStatus = Literal["draft", "published", "archived"]


class FormationView(BaseModel):
    id: str
    club_id: str
    name: str
    scheme: str
    slots: list[FormationSlotView] = Field(default_factory=list)
    chemistry_score: float = Field(ge=0, le=100)
    warnings: list[str] = Field(default_factory=list)
    status: FormationStatus
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    audit_ref: str | None = None


class FormationHistoryView(BaseModel):
    formations: list[FormationView] = Field(default_factory=list)


class FormationSaveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scheme: str = Field(default="4-3-3", min_length=3, max_length=24)
    slots: list[FormationSlotView] = Field(default_factory=list)
    source_formation_id: str | None = None


class FormationSelectionReadyPlayerView(BaseModel):
    id: str
    name: str
    position: str
    eligible: bool


class FormationSelectionReadyView(BaseModel):
    players: list[FormationSelectionReadyPlayerView] = Field(default_factory=list)


class FormationEnvelope(BaseModel):
    formation: FormationView


class FormationBlockedResponse(BaseModel):
    reason: str
    eligible_player_count: int
    required_player_count: int = 11
    details: dict[str, Any] = Field(default_factory=dict)
