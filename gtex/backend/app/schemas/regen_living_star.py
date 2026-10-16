from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.schemas.player_agency import PlayerAgencyStateView, PlayerPersonalityView


class RegenArchetypeView(CommonSchema):
    code: str
    label: str
    summary: str
    dominant_traits: tuple[str, ...] = Field(default_factory=tuple)


class RegenMoodStatusView(CommonSchema):
    code: str
    label: str
    severity: int = Field(ge=0, le=3)
    drivers: tuple[str, ...] = Field(default_factory=tuple)


class RegenInnerMonologueView(CommonSchema):
    voice_line: str
    tone: str
    generated_at: datetime
    seed: str


class RegenExitLadderView(CommonSchema):
    stage: str
    label: str
    severity: int = Field(ge=0, le=5)
    next_stage: str | None = None
    can_petition_termination: bool = False
    owner_actions: tuple[str, ...] = Field(default_factory=tuple)


class RegenPromiseMemoryView(CommonSchema):
    key: str
    statement: str
    status: str
    broken: bool = False


class RegenMatchBehaviorBriefView(CommonSchema):
    player_id: str
    risk_appetite: float = Field(ge=0, le=1)
    pressing_intensity: float = Field(ge=0, le=1)
    big_game_nerves: float = Field(ge=0, le=1)
    celebration_hunger: float = Field(ge=0, le=1)
    captaincy_willingness: float = Field(ge=0, le=1)
    shot_greed: float = Field(ge=0, le=1)
    discipline_risk: float = Field(ge=0, le=1)
    notes: tuple[str, ...] = Field(default_factory=tuple)


class RegenHeirSparkView(CommonSchema):
    status: str
    trigger_key: str | None = None
    successor_count: int = 0
    prospect_ids: tuple[str, ...] = Field(default_factory=tuple)
    exceptional: bool = False


class RegenLivingStarView(CommonSchema):
    player_id: str
    regen_id: str | None = None
    is_unique_collectible: bool = True
    archetype: RegenArchetypeView
    mood: RegenMoodStatusView
    monologue: RegenInnerMonologueView
    exit_ladder: RegenExitLadderView
    personality: PlayerPersonalityView
    agency: PlayerAgencyStateView
    promises: tuple[RegenPromiseMemoryView, ...] = Field(default_factory=tuple)
    grievances: tuple[str, ...] = Field(default_factory=tuple)
    behavior_brief: RegenMatchBehaviorBriefView
    heir_spark: RegenHeirSparkView | None = None
    inbox_notes: tuple[str, ...] = Field(default_factory=tuple)


class RegenExitPetitionRequest(CommonSchema):
    reason: str | None = Field(default=None, max_length=280)


class RegenExitPetitionView(CommonSchema):
    player_id: str
    previous_stage: str
    stage: str
    accepted: bool
    message: str
    living_star: RegenLivingStarView
