from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlayerSeedMode(str, Enum):
    FULL_SEED = "full_seed"
    CLUB_SEED = "club_seed"
    FREE_AGENT_SEED = "free_agent_seed"
    TEST_SEED_SMALL = "test_seed_small"


class PlayerSeedRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    mode: PlayerSeedMode = PlayerSeedMode.FULL_SEED
    target_player_count: int | None = Field(default=None, ge=1)
    provider_name: str | None = None
    random_seed: int = 20260321
    batch_size: int = Field(default=5_000, ge=1)
    free_agent_count: int | None = Field(default=None, ge=0)
    replace_provider_data: bool = True
    resume_from_checkpoint: bool = False
    checkpoint_path: str | None = None
    lookback_days: int | None = Field(default=None, ge=1)
    as_of: datetime | None = None

    @model_validator(mode="after")
    def validate_counts(self) -> "PlayerSeedRequest":
        if self.target_player_count is not None and self.free_agent_count is not None and self.free_agent_count > self.target_player_count:
            raise ValueError("free_agent_count cannot exceed target_player_count")
        return self


class PlayerSeedResult(BaseModel):
    mode: str
    provider_name: str
    target_player_count: int
    random_seed: int
    batch_size: int
    as_of: datetime
    players_seeded: int
    free_agents_seeded: int
    value_snapshots_seeded: int
    checkpoint_phase: str
    universe_seed: dict
    generation: dict
    projection: dict


__all__ = ["PlayerSeedMode", "PlayerSeedRequest", "PlayerSeedResult"]
