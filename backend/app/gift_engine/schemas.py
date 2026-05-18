from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class GiftSendRequest(BaseModel):
    recipient_user_id: str | None = Field(default=None, min_length=1, max_length=36)
    gift_key: str = Field(min_length=2, max_length=64)
    quantity: Decimal = Field(default=Decimal("1.0000"), gt=0, le=1000)
    note: str | None = Field(default=None, max_length=500)
    source_scope: str = Field(default="user_hosted", max_length=32)
    idempotency_key: str | None = Field(default=None, max_length=128)
    chat_thread_id: str | None = Field(default=None, max_length=36)
    discussion_thread_id: str | None = Field(default=None, max_length=36)
    discussion_reply_id: str | None = Field(default=None, max_length=36)
    match_id: str | None = Field(default=None, max_length=64)
    competition_id: str | None = Field(default=None, max_length=64)


class GiftCatalogItemView(BaseModel):
    id: str
    code: str
    display_name: str
    fallback_display_name: str | None = None
    description: str | None = None
    cost_amount: Decimal
    currency: str
    currency_label: str
    rarity: str
    tier: str
    animation_key: str | None = None
    sound_key: str | None = None
    duration_ms: int
    is_active: bool
    is_award_pack: bool
    legal_status: str
    sort_order: int


class GiftTransactionView(BaseModel):
    id: str
    sender_user_id: str
    recipient_user_id: str
    gift_key: str
    gift_display_name: str
    fallback_gift_name: str | None = None
    rarity: str | None = None
    quantity: Decimal
    unit_price: Decimal
    gross_amount: Decimal
    platform_rake_amount: Decimal
    recipient_net_amount: Decimal
    recipient_type: str = "user"
    recipient_entity_id: str | None = None
    chat_thread_id: str | None = None
    discussion_thread_id: str | None = None
    discussion_reply_id: str | None = None
    match_id: str | None = None
    competition_id: str | None = None
    source_scope: str
    ledger_unit: str
    currency_label: str | None = None
    ledger_transaction_id: str | None = None
    wallet_debit_ledger_id: str | None = None
    wallet_credit_ledger_id: str | None = None
    platform_fee_ledger_id: str | None = None
    idempotency_key: str | None = None
    animation_key: str | None = None
    sound_key: str | None = None
    duration_ms: int | None = None
    abuse_status: str = "clean"
    animation_payload: dict[str, object] = Field(default_factory=dict)
    note: str | None = None
    status: str
    created_at: datetime


class GiftEngineSummaryView(BaseModel):
    sent_total: Decimal
    received_total: Decimal
    rake_total: Decimal
    recent_transactions: list[GiftTransactionView]


class GiftComboEventView(BaseModel):
    id: str
    gift_transaction_id: str
    sender_user_id: str
    recipient_user_id: str
    gift_key: str
    gift_display_name: str
    combo_rule_key: str
    combo_count: int
    window_seconds: int
    bonus_bps: int
    bonus_amount: Decimal
    created_at: datetime


class GiftComboSummaryView(BaseModel):
    total_combos: int
    total_bonus_amount: Decimal
    recent_combos: list[GiftComboEventView]


class GiftStatsView(BaseModel):
    entity_type: str
    entity_id: str
    total_gifts_received: int
    total_fan_coin_received: Decimal
    total_unique_senders: int
    top_gift_code: str | None = None
    mythic_gifts_received: int


class GiftCatalogAdminUpsertRequest(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=64)
    key: str | None = Field(default=None, min_length=2, max_length=64)
    display_name: str = Field(min_length=2, max_length=160)
    fallback_display_name: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    cost_amount: Decimal | None = Field(default=None, ge=0)
    fancoin_price: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="credit", max_length=16)
    rarity: str = Field(default="common", max_length=32)
    tier: str = Field(default="standard", max_length=32)
    animation_key: str | None = Field(default=None, max_length=64)
    sound_key: str | None = Field(default=None, max_length=64)
    duration_ms: int = Field(default=2500, ge=0, le=30000)
    is_active: bool = True
    active: bool | None = None
    is_award_pack: bool = False
    legal_status: str = Field(default="safe", max_length=32)
    sort_order: int = Field(default=0, ge=0, le=100000)

    @property
    def resolved_key(self) -> str:
        return (self.code or self.key or "").strip()

    @property
    def resolved_price(self) -> Decimal:
        return self.cost_amount if self.cost_amount is not None else self.fancoin_price or Decimal("0.0000")

    @property
    def resolved_active(self) -> bool:
        return self.active if self.active is not None else self.is_active


class GiftCatalogAdminPatchRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    fallback_display_name: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    cost_amount: Decimal | None = Field(default=None, ge=0)
    fancoin_price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=16)
    rarity: str | None = Field(default=None, max_length=32)
    tier: str | None = Field(default=None, max_length=32)
    animation_key: str | None = Field(default=None, max_length=64)
    sound_key: str | None = Field(default=None, max_length=64)
    duration_ms: int | None = Field(default=None, ge=0, le=30000)
    is_active: bool | None = None
    active: bool | None = None
    is_award_pack: bool | None = None
    legal_status: str | None = Field(default=None, max_length=32)
    sort_order: int | None = Field(default=None, ge=0, le=100000)


class GiftAbuseFlagView(BaseModel):
    id: str
    flag_key: str
    sender_user_id: str
    recipient_type: str
    recipient_id: str
    gift_transaction_id: str | None = None
    flag_type: str
    severity: str
    description: str
    status: str
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
