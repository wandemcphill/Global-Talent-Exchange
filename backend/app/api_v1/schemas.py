from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiEnvelope(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ApiError | None = None


class MarketBidRequest(BaseModel):
    listing_id: str
    amount: int = Field(ge=1)


class TournamentRentRequest(BaseModel):
    player_id: str


class TournamentSquadSubmitRequest(BaseModel):
    player_ids: list[str] = Field(min_length=1)


class BroadcastPayRequest(BaseModel):
    match_id: str
    amount: int | None = Field(default=None, ge=0)


class ClubSaleRequest(BaseModel):
    club_id: str
    asking_price: int | None = Field(default=None, ge=0)
    note: str | None = None


class ClubOfferRequest(BaseModel):
    listing_id: str
    amount: int = Field(ge=1)


class StoryGenerateRequest(BaseModel):
    title: str | None = None
    story_type: str = "dynamic_moment"
    subject_id: str | None = None


class FederationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    region: str | None = None


class FederationVoteRequest(BaseModel):
    federation_id: str | None = None
    proposal_id: str = Field(min_length=1)
    vote: Literal["yes", "no", "abstain"] = "yes"
