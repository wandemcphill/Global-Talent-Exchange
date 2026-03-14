from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.models.treasury import DepositStatus, PaymentMode, RateDirection, TreasuryWithdrawalStatus
from backend.app.models.user import KycStatus
from backend.app.models.wallet import LedgerUnit


class TreasuryBankAccountView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    currency_code: str
    bank_name: str
    account_number: str
    account_name: str
    bank_code: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TreasurySettingsView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    settings_key: str
    currency_code: str
    deposit_rate_value: Decimal
    deposit_rate_direction: RateDirection
    withdrawal_rate_value: Decimal
    withdrawal_rate_direction: RateDirection
    min_deposit: Decimal
    max_deposit: Decimal
    min_withdrawal: Decimal
    max_withdrawal: Decimal
    deposit_mode: PaymentMode
    withdrawal_mode: PaymentMode
    maintenance_message: str | None
    whatsapp_number: str | None
    active_bank_account: TreasuryBankAccountView | None = None
    created_at: datetime
    updated_at: datetime


class TreasurySettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency_code: str | None = Field(default=None, max_length=8)
    deposit_rate_value: Decimal | None = None
    deposit_rate_direction: RateDirection | None = None
    withdrawal_rate_value: Decimal | None = None
    withdrawal_rate_direction: RateDirection | None = None
    min_deposit: Decimal | None = None
    max_deposit: Decimal | None = None
    min_withdrawal: Decimal | None = None
    max_withdrawal: Decimal | None = None
    deposit_mode: PaymentMode | None = None
    withdrawal_mode: PaymentMode | None = None
    maintenance_message: str | None = Field(default=None, max_length=255)
    whatsapp_number: str | None = Field(default=None, max_length=32)
    active_bank_account_id: str | None = None


class TreasuryBankAccountCreate(BaseModel):
    bank_name: str = Field(min_length=2, max_length=120)
    account_number: str = Field(min_length=4, max_length=32)
    account_name: str = Field(min_length=2, max_length=120)
    bank_code: str | None = Field(default=None, max_length=32)
    currency_code: str = Field(default="NGN", max_length=8)
    is_active: bool = True

    @field_validator("bank_name", "account_number", "account_name", "bank_code")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None


class TreasuryBankAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank_name: str | None = Field(default=None, max_length=120)
    account_number: str | None = Field(default=None, max_length=32)
    account_name: str | None = Field(default=None, max_length=120)
    bank_code: str | None = Field(default=None, max_length=32)
    currency_code: str | None = Field(default=None, max_length=8)
    is_active: bool | None = None


class DepositQuoteRequest(BaseModel):
    amount: Decimal
    input_unit: str = Field(default="fiat")

    @field_validator("input_unit")
    @classmethod
    def validate_input_unit(cls, value: str) -> str:
        candidate = value.strip().lower()
        if candidate not in {"fiat", "coin"}:
            raise ValueError("input_unit must be fiat or coin")
        return candidate

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Deposit amount must be positive.")
        return value


class DepositRequestView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference: str
    status: DepositStatus
    amount_fiat: Decimal
    amount_coin: Decimal
    currency_code: str
    rate_value: Decimal
    rate_direction: RateDirection
    bank_name: str
    bank_account_number: str
    bank_account_name: str
    bank_code: str | None
    payer_name: str | None
    sender_bank: str | None
    transfer_reference: str | None
    proof_attachment_id: str | None
    admin_notes: str | None
    created_at: datetime
    submitted_at: datetime | None
    reviewed_at: datetime | None
    confirmed_at: datetime | None
    rejected_at: datetime | None
    expires_at: datetime | None


class DepositSubmitRequest(BaseModel):
    payer_name: str | None = Field(default=None, max_length=120)
    sender_bank: str | None = Field(default=None, max_length=120)
    transfer_reference: str | None = Field(default=None, max_length=128)
    proof_attachment_id: str | None = None

    @field_validator("payer_name", "sender_bank", "transfer_reference")
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None


class WithdrawalEligibilityView(BaseModel):
    available_balance: Decimal
    withdrawable_now: Decimal
    remaining_allowance: Decimal
    next_eligible_at: datetime | None
    kyc_status: KycStatus
    requires_kyc: bool
    requires_bank_account: bool
    pending_withdrawals: Decimal = Decimal("0.0000")


class WithdrawalRequestCreate(BaseModel):
    amount_coin: Decimal
    bank_account_id: str | None = None
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("amount_coin")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        return value


class WithdrawalRequestView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    payout_request_id: str
    reference: str
    status: TreasuryWithdrawalStatus
    unit: LedgerUnit
    amount_coin: Decimal
    amount_fiat: Decimal
    currency_code: str
    rate_value: Decimal
    rate_direction: RateDirection
    bank_name: str
    bank_account_number: str
    bank_account_name: str
    bank_code: str | None
    kyc_status_snapshot: str
    kyc_tier_snapshot: str
    fee_amount: Decimal
    total_debit: Decimal
    notes: str | None
    created_at: datetime
    reviewed_at: datetime | None
    approved_at: datetime | None
    processed_at: datetime | None
    paid_at: datetime | None
    rejected_at: datetime | None
    cancelled_at: datetime | None


class KycProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: KycStatus
    nin: str | None
    bvn: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    country: str | None
    id_document_attachment_id: str | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class KycSubmitRequest(BaseModel):
    nin: str | None = Field(default=None, max_length=32)
    bvn: str | None = Field(default=None, max_length=32)
    address_line1: str = Field(min_length=4, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default="Nigeria", max_length=120)
    id_document_attachment_id: str | None = None

    @model_validator(mode="after")
    def require_nin_or_bvn(self) -> "KycSubmitRequest":
        if not (self.nin or self.bvn):
            raise ValueError("Either NIN or BVN is required.")
        return self


class KycReviewRequest(BaseModel):
    status: KycStatus
    rejection_reason: str | None = Field(default=None, max_length=255)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: KycStatus) -> KycStatus:
        if value not in {KycStatus.PARTIAL_VERIFIED_NO_ID, KycStatus.FULLY_VERIFIED, KycStatus.REJECTED}:
            raise ValueError("status must be partial_verified_no_id, fully_verified, or rejected")
        return value


class UserBankAccountView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    currency_code: str
    bank_name: str
    account_number: str
    account_name: str
    bank_code: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserBankAccountCreate(BaseModel):
    bank_name: str = Field(min_length=2, max_length=120)
    account_number: str = Field(min_length=4, max_length=32)
    account_name: str = Field(min_length=2, max_length=120)
    bank_code: str | None = Field(default=None, max_length=32)
    currency_code: str = Field(default="NGN", max_length=8)
    set_active: bool = True


class UserBankAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank_name: str | None = Field(default=None, max_length=120)
    account_number: str | None = Field(default=None, max_length=32)
    account_name: str | None = Field(default=None, max_length=120)
    bank_code: str | None = Field(default=None, max_length=32)
    currency_code: str | None = Field(default=None, max_length=8)
    is_active: bool | None = None


class AdminDepositView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference: str
    status: DepositStatus
    amount_fiat: Decimal
    amount_coin: Decimal
    currency_code: str
    payer_name: str | None
    sender_bank: str | None
    transfer_reference: str | None
    created_at: datetime
    submitted_at: datetime | None
    reviewed_at: datetime | None
    confirmed_at: datetime | None
    rejected_at: datetime | None
    admin_notes: str | None
    user_id: str
    user_email: str
    user_full_name: str | None
    user_phone_number: str | None


class AdminWithdrawalView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference: str
    status: TreasuryWithdrawalStatus
    amount_coin: Decimal
    amount_fiat: Decimal
    currency_code: str
    bank_name: str
    bank_account_number: str
    bank_account_name: str
    created_at: datetime
    reviewed_at: datetime | None
    approved_at: datetime | None
    processed_at: datetime | None
    paid_at: datetime | None
    rejected_at: datetime | None
    cancelled_at: datetime | None
    user_id: str
    user_email: str
    user_full_name: str | None
    user_phone_number: str | None


class AdminKycView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    status: KycStatus
    nin: str | None
    bvn: str | None
    address_line1: str | None
    city: str | None
    state: str | None
    country: str | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    user_email: str
    user_full_name: str | None
    user_phone_number: str | None


class AdminDisputeMessageView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sender_user_id: str | None
    sender_role: str
    message: str
    attachment_id: str | None
    created_at: datetime


class AdminDisputeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    reference: str
    resource_type: str
    resource_id: str
    subject: str | None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    user_id: str
    user_email: str
    user_full_name: str | None
    user_phone_number: str | None
    messages: list[AdminDisputeMessageView] = Field(default_factory=list)


class DisputeCreateRequest(BaseModel):
    resource_type: str = Field(min_length=3, max_length=64)
    resource_id: str = Field(min_length=3, max_length=64)
    reference: str = Field(min_length=3, max_length=64)
    subject: str | None = Field(default=None, max_length=120)
    message: str = Field(min_length=1, max_length=1000)
    attachment_id: str | None = None


class DisputeMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    attachment_id: str | None = None


class AdminQueueView(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


class TreasuryDashboardView(BaseModel):
    total_users: int = 0
    active_users: int = 0
    pending_deposits: int = 0
    pending_withdrawals: int = 0
    pending_kyc: int = 0
    open_disputes: int = 0
    deposits_confirmed_today: int = 0
    withdrawals_paid_today: int = 0
    wallet_liability: Decimal = Decimal("0.0000")
    pending_treasury_exposure: Decimal = Decimal("0.0000")
