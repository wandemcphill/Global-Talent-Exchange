from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from backend.app.common.schemas.base import CommonSchema
from backend.app.common.enums.contract_status import ContractStatus
from backend.app.common.enums.injury_severity import InjurySeverity
from backend.app.common.enums.transfer_bid_status import TransferBidStatus
from backend.app.common.enums.transfer_window_status import TransferWindowStatus


class CareerEntryView(CommonSchema):
    id: str
    player_id: str
    club_id: str | None = None
    club_name: str
    season_label: str
    squad_role: str | None = None
    appearances: int = Field(ge=0)
    goals: int = Field(ge=0)
    assists: int = Field(ge=0)
    average_rating: int | None = None
    honours_json: list[dict[str, object]] = Field(default_factory=list)
    notes: str | None = None
    start_on: date | None = None
    end_on: date | None = None
    updated_at: datetime


class ContractView(CommonSchema):
    id: str
    player_id: str
    club_id: str | None = None
    status: ContractStatus
    wage_amount: Decimal
    bonus_terms: str | None = None
    release_clause_amount: Decimal | None = None
    signed_on: date
    starts_on: date
    ends_on: date
    extension_option_until: date | None = None
    updated_at: datetime


class InjuryCaseView(CommonSchema):
    id: str
    player_id: str
    club_id: str | None = None
    severity: InjurySeverity
    injury_type: str
    occurred_on: date
    expected_return_on: date | None = None
    recovered_on: date | None = None
    source_match_id: str | None = None
    recovery_days: int | None = None
    notes: str | None = None
    updated_at: datetime


class TransferWindowView(CommonSchema):
    id: str
    territory_code: str
    label: str
    status: TransferWindowStatus
    opens_on: date
    closes_on: date
    updated_at: datetime


class TransferBidView(CommonSchema):
    id: str
    window_id: str
    player_id: str
    selling_club_id: str | None = None
    buying_club_id: str | None = None
    status: TransferBidStatus
    bid_amount: Decimal
    wage_offer_amount: Decimal | None = None
    sell_on_clause_pct: Decimal | None = None
    structured_terms_json: dict[str, object] = Field(default_factory=dict)
    notes: str | None = None
    updated_at: datetime


class TransferBidCreateRequest(CommonSchema):
    player_id: str = Field(min_length=1, max_length=36)
    selling_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    buying_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    bid_amount: Decimal = Field(ge=0)
    wage_offer_amount: Decimal | None = Field(default=None, ge=0)
    sell_on_clause_pct: Decimal | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=500)
