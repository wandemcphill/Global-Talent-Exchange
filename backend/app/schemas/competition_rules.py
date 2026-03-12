from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.common.enums.competition_format import CompetitionFormat


class LeagueRuleSetPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    win_points: int = Field(ge=0, le=10)
    draw_points: int = Field(ge=0, le=10)
    loss_points: int = Field(ge=0, le=10)
    tie_break_order: list[str] = Field(default_factory=list)
    home_away: bool = True
    min_participants: int = Field(ge=2, le=256)
    max_participants: int = Field(ge=2, le=256)


class CupRuleSetPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    single_elimination: bool = True
    two_leg_tie: bool = False
    extra_time: bool = False
    penalties: bool = True
    min_participants: int = Field(ge=2, le=256)
    max_participants: int = Field(ge=2, le=256)
    allowed_participant_sizes: list[int] = Field(default_factory=list)


class CompetitionRuleSetPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: CompetitionFormat
    league_rules: LeagueRuleSetPayload | None = None
    cup_rules: CupRuleSetPayload | None = None

    @model_validator(mode="after")
    def _validate_format_pairing(self) -> "CompetitionRuleSetPayload":
        if self.format == CompetitionFormat.LEAGUE and self.league_rules is None:
            raise ValueError("league_rules is required when format is league")
        if self.format == CompetitionFormat.CUP and self.cup_rules is None:
            raise ValueError("cup_rules is required when format is cup")
        return self
