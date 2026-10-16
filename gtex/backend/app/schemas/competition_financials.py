from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums.competition_payout_mode import CompetitionPayoutMode


class CompetitionFinancialsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_fee_minor: int = Field(ge=0)
    currency: str = Field(min_length=1, max_length=12)
    platform_fee_bps: int = Field(ge=0, le=10_000)
    host_creation_fee_minor: int = Field(ge=0)
    payout_mode: CompetitionPayoutMode
    top_n: int | None = Field(default=None, ge=1, le=256)
    payout_percentages: list[int] = Field(default_factory=list)


class CompetitionFeeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_fee_minor: int
    currency: str
    platform_fee_bps: int
    host_creation_fee_minor: int
    gross_pool_minor: int
    platform_fee_minor: int
    net_prize_pool_minor: int
