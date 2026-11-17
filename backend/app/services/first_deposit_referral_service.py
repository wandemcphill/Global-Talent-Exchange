"""First-deposit referral attribution, bonus, commission, and payouts.

Qualifying base
---------------
Both rewards use the verified gross fiat amount persisted on the settlement
record (``amount_fiat`` / credited fiat), in that record's currency.

They do not use the net wallet credit, the platform coin fee, or the payment
processor fee. Those amounts are stored on the reward payload so a reviewer
can see what was excluded.

Rounding
--------
The shared fiat reward is ``gross_fiat * bps / 10000``, quantized HALF_UP to
0.01. When the bonus and commission rates match, both rewards therefore start
from the same rounded fiat figure.

The referred user's wallet bonus converts that fiat figure with the deposit's
own ``rate_value`` and ``rate_direction``:

- ``fiat_per_coin``: wallet units = fiat / rate
- ``coin_per_fiat``: wallet units = fiat * rate

The wallet amount is quantized HALF_UP to 0.0001, which is the ledger quantum.
The referrer's commission stays in the fiat currency as a liability. It is not
paid when the deposit settles.

Historical rewards store ``policy_version`` and ``applied_rate_bps``. Changing
programme settings never rewrites them.
"""

from __future__ import annotations

import csv
import hashlib
import io
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.enums.referral_event_type import ReferralEventType
from app.common.enums.referral_reward_status import ReferralRewardStatus
from app.common.enums.referral_reward_type import ReferralRewardType
from app.common.enums.referral_source_channel import ReferralSourceChannel
from app.common.enums.share_code_type import ShareCodeType
from app.models.base import generate_uuid, utcnow
from app.models.creator_profile import CreatorProfile
from app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from app.models.referral_affiliate import (
    ReferralAdminAudit,
    ReferralCampaign,
    ReferralClick,
    ReferralPartner,
    ReferralPayoutBatch,
    ReferralPayoutItem,
    ReferralProgrammeSettings,
    ReferralRecoveryCase,
)
from app.models.referral_attribution import ReferralAttribution
from app.models.referral_event import ReferralEvent
from app.models.referral_flag import ReferralFlag
from app.models.referral_reward import ReferralReward
from app.models.referral_reward_ledger import ReferralRewardLedger
from app.models.share_code import ShareCode
from app.models.treasury import DepositRequest, DepositStatus, RateDirection
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

FIAT_QUANTUM = Decimal("0.01")
COIN_QUANTUM = Decimal("0.0001")
PUBLIC_SIGNUP_URL = "https://playgtex.app/signup"
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
MANDATORY_ACCOUNT_TYPES = ("user", "creator", "coin_trader", "club_owner")
DEFAULT_DEPOSIT_TYPES = ("purchase_order", "treasury_deposit", "owner_deposit")
BONUS_TYPE = ReferralRewardType.FIRST_DEPOSIT_BONUS
COMMISSION_TYPE = ReferralRewardType.FIRST_DEPOSIT_COMMISSION
HASH_PEPPER = "gtex-referral-v1"


class FirstDepositReferralError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class SettledDeposit:
    user_id: str
    account_type: str
    deposit_kind: str
    deposit_id: str
    payment_reference: str | None
    provider_reference: str | None
    gross_fiat: Decimal
    wallet_credit: Decimal
    platform_fee: Decimal
    processor_fee: Decimal
    currency_code: str
    wallet_unit: str
    rate_value: Decimal
    rate_direction: str
    settled_at: datetime
    settled: bool
    purchase_order_id: str | None = None


def referral_link(code: str) -> str:
    return f"{PUBLIC_SIGNUP_URL}?ref={code}"


def bonus_explanation(bonus_bps: int) -> str:
    if int(bonus_bps) == 1000:
        return "Register with this referral code and receive a 10% bonus on your first qualifying deposit."
    percent = (Decimal(int(bonus_bps)) / Decimal(100)).quantize(FIAT_QUANTUM, rounding=ROUND_HALF_UP)
    return f"Register with this referral code and receive a {percent}% bonus on your first qualifying deposit."


def _money(value: Decimal | int | str | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(FIAT_QUANTUM, rounding=ROUND_HALF_UP)


def _coin(value: Decimal | int | str | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(COIN_QUANTUM, rounding=ROUND_HALF_UP)


def _percent(amount: Decimal, bps: int) -> Decimal:
    return (Decimal(amount) * Decimal(int(bps)) / Decimal(10000)).quantize(FIAT_QUANTUM, rounding=ROUND_HALF_UP)


def _direction(value: Any) -> str:
    return str(getattr(value, "value", value) or RateDirection.FIAT_PER_COIN.value)


def _unit(value: Any) -> LedgerUnit:
    return LedgerUnit(str(getattr(value, "value", value)))


def fiat_to_wallet(fiat_amount: Decimal, rate_value: Decimal, rate_direction: Any) -> Decimal:
    rate = Decimal(rate_value)
    if rate <= 0:
        raise FirstDepositReferralError("rate_not_configured", "The deposit has no conversion rate.")
    if _direction(rate_direction) == RateDirection.FIAT_PER_COIN.value:
        return (Decimal(fiat_amount) / rate).quantize(COIN_QUANTUM, rounding=ROUND_HALF_UP)
    return (Decimal(fiat_amount) * rate).quantize(COIN_QUANTUM, rounding=ROUND_HALF_UP)


def _hash_value(value: str | None) -> str | None:
    if not value:
        return None
    digest = hashlib.sha256(f"{HASH_PEPPER}|{value.strip()}".encode("utf-8")).hexdigest()
    return digest[:40]


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "value") and not isinstance(value, str):
        return str(value.value)
    return value


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class FirstDepositReferralService:
    def __init__(self, session: Session, wallet_service: WalletService | None = None) -> None:
        self.session = session
        self.wallet_service = wallet_service or WalletService()

    def ensure_programme(self) -> ReferralProgrammeSettings:
        settings = self.session.scalar(
            select(ReferralProgrammeSettings).where(ReferralProgrammeSettings.settings_key == "default")
        )
        if settings is not None:
            return settings
        settings = ReferralProgrammeSettings(
            settings_key="default",
            is_active=True,
            user_bonus_bps=1000,
            referrer_commission_bps=1000,
            hold_days=7,
            payout_weekday=0,
            min_payout_thresholds_json={"NGN": "10000.00"},
            eligible_account_types_json=list(MANDATORY_ACCOUNT_TYPES),
            qualifying_deposit_types_json=list(DEFAULT_DEPOSIT_TYPES),
            version=1,
        )
        self.session.add(settings)
        self.session.flush()
        return settings

    def update_settings(self, actor: User, payload: dict[str, Any]) -> dict[str, Any]:
        settings = self.ensure_programme()
        if "user_bonus_bps" in payload:
            settings.user_bonus_bps = self._bps(payload["user_bonus_bps"])
        if "referrer_commission_bps" in payload:
            settings.referrer_commission_bps = self._bps(payload["referrer_commission_bps"])
        if "is_active" in payload:
            settings.is_active = bool(payload["is_active"])
        if "hold_days" in payload:
            hold_days = int(payload["hold_days"])
            if hold_days < 0 or hold_days > 90:
                raise FirstDepositReferralError("invalid_hold", "Hold duration must be between 0 and 90 days.")
            settings.hold_days = hold_days
        if "payout_weekday" in payload:
            weekday = int(payload["payout_weekday"])
            if weekday < 0 or weekday > 6:
                raise FirstDepositReferralError("invalid_weekday", "Payout weekday must be 0 (Monday) through 6.")
            settings.payout_weekday = weekday
        if "min_payout_thresholds" in payload:
            settings.min_payout_thresholds_json = {
                str(currency).upper(): format(_money(amount), "f")
                for currency, amount in dict(payload["min_payout_thresholds"] or {}).items()
            }
        if "eligible_account_types" in payload:
            configured = [str(item) for item in payload["eligible_account_types"] or []]
            settings.eligible_account_types_json = list(dict.fromkeys([*MANDATORY_ACCOUNT_TYPES, *configured]))
        if "qualifying_deposit_types" in payload:
            allowed = set(DEFAULT_DEPOSIT_TYPES)
            chosen = [str(item) for item in payload["qualifying_deposit_types"] or [] if str(item) in allowed]
            if not chosen:
                raise FirstDepositReferralError(
                    "invalid_deposit_types", "Choose at least one qualifying deposit type."
                )
            settings.qualifying_deposit_types_json = chosen
        settings.version = int(settings.version or 1) + 1
        settings.updated_by_user_id = actor.id
        self.session.flush()
        self._audit(actor, "programme_settings_updated", "programme", settings.id, payload.get("reason"), {
            "version": settings.version
        })
        return self._settings_view(settings)

    def settings_view(self) -> dict[str, Any]:
        return self._settings_view(self.ensure_programme())

    def record_click(
        self,
        code: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        self._enforce_attempt_limit(ip_address)
        try:
            share, campaign = self._resolve_active_code(code)
        except FirstDepositReferralError as exc:
            self._click(None, None, False, ip_address, user_agent, exc.code)
            raise
        self._click(share.id, campaign.id if campaign else None, True, ip_address, user_agent, None)
        settings = self.ensure_programme()
        return {
            "valid": True,
            "code": share.code,
            "link": referral_link(share.code),
            "message": bonus_explanation(settings.user_bonus_bps),
        }

    def preview_code(self, code: str, *, ip_address: str | None = None) -> dict[str, Any]:
        self._enforce_attempt_limit(ip_address)
        settings = self.ensure_programme()
        try:
            share, campaign = self._resolve_active_code(code)
        except FirstDepositReferralError as exc:
            self._click(None, None, False, ip_address, None, exc.code)
            return {"valid": False, "code": None, "message": exc.message, "reason": exc.code}
        self._click(share.id, campaign.id if campaign else None, True, ip_address, None, None)
        return {
            "valid": True,
            "code": share.code,
            "campaign_name": campaign.name if campaign else None,
            "message": bonus_explanation(settings.user_bonus_bps),
        }

    def attribute_signup(
        self,
        user: User,
        code: str,
        *,
        account_type: str,
        creates_club: bool = False,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ReferralAttribution:
        self._enforce_attempt_limit(ip_address)
        settings = self.ensure_programme()
        if not settings.is_active:
            raise FirstDepositReferralError("programme_inactive", "The referral programme is not active.")
        try:
            share, campaign = self._resolve_active_code(code, for_update=True)
        except FirstDepositReferralError:
            self._click(None, None, False, ip_address, user_agent, "signup_rejected")
            raise
        partner = self.session.get(ReferralPartner, share.referral_partner_id) if share.referral_partner_id else None
        self._reject_self_referral(user, share, partner)
        existing = self._attribution_for_user(user.id)
        if existing is not None:
            if existing.locked_at is not None:
                raise FirstDepositReferralError(
                    "attribution_locked", "A qualifying deposit already locked this referral."
                )
            if existing.share_code_id != share.id:
                raise FirstDepositReferralError(
                    "attribution_conflict", "This account is already attributed to another referral code."
                )
            self._stamp_partner(existing, share)
            return existing
        claimed = self.session.execute(
            update(ShareCode)
            .where(ShareCode.id == share.id)
            .where(ShareCode.is_active.is_(True))
            .where(or_(ShareCode.max_uses.is_(None), ShareCode.current_uses < ShareCode.max_uses))
            .values(current_uses=ShareCode.current_uses + 1)
        )
        if claimed.rowcount != 1:
            raise FirstDepositReferralError("referral_code_exhausted", "This referral code has reached its limit.")
        snapshot = "club_owner" if creates_club else account_type
        attribution = ReferralAttribution(
            referred_user_id=user.id,
            referrer_user_id=share.owner_user_id or (partner.owner_user_id if partner else None),
            creator_profile_id=share.owner_creator_id or (partner.creator_profile_id if partner else None),
            share_code_id=share.id,
            source_channel=ReferralSourceChannel.DIRECT_LINK,
            first_touch_at=utcnow(),
            attribution_status="attributed",
            campaign_name=campaign.name if campaign else None,
            referral_partner_id=share.referral_partner_id,
            referral_campaign_id=share.referral_campaign_id,
            account_type_snapshot=snapshot,
            metadata_json={
                "share_code": share.code,
                "entry": "signup",
                "real_account_type": account_type,
                "creates_club": creates_club,
                "signup_ip_hash": _hash_value(ip_address),
                "signup_user_agent_hash": _hash_value(user_agent),
            },
        )
        self.session.add(attribution)
        self.session.flush()
        self._event(
            attribution,
            ReferralEventType.SIGNUP_COMPLETED,
            {"share_code": share.code, "account_type": snapshot},
        )
        return attribution

    def record_failed_attempt(self, ip_address: str | None, reason: str) -> None:
        self._click(None, None, False, ip_address, None, reason)

    def prepare_redeem(self, *, user_id: str, share_code_id: str) -> None:
        attribution = self._attribution_for_user(user_id)
        if attribution is None:
            return
        if attribution.locked_at is not None and attribution.share_code_id != share_code_id:
            raise FirstDepositReferralError(
                "attribution_locked", "A qualifying deposit already locked this referral."
            )
        if attribution.share_code_id != share_code_id:
            raise FirstDepositReferralError(
                "attribution_conflict", "This account is already attributed to another referral code."
            )

    def stamp_redeemed_partner(self, *, user_id: str, share_code_id: str) -> None:
        attribution = self._attribution_for_user(user_id)
        share = self.session.get(ShareCode, share_code_id)
        if attribution is None or share is None or attribution.share_code_id != share.id:
            return
        self._stamp_partner(attribution, share)

    def on_purchase_order_settled(self, order: FancoinPurchaseOrder) -> list[ReferralReward]:
        if order.status != PurchaseOrderStatus.SETTLED or not order.ledger_transaction_id:
            return []
        return self.apply_settled_deposit(
            SettledDeposit(
                user_id=order.user_id,
                account_type=str(order.account_type_snapshot or ""),
                deposit_kind="purchase_order",
                deposit_id=order.id,
                payment_reference=order.reference,
                provider_reference=order.provider_reference,
                gross_fiat=_money(order.amount_fiat),
                wallet_credit=_coin(order.net_amount),
                platform_fee=_coin(order.fee_amount),
                processor_fee=_coin(order.processor_fee),
                currency_code=(order.currency_code or "NGN").upper(),
                wallet_unit=str(getattr(order.unit, "value", order.unit)),
                rate_value=Decimal(order.rate_value),
                rate_direction=_direction(order.rate_direction),
                settled_at=_aware(order.settled_at) or utcnow(),
                settled=True,
                purchase_order_id=order.id,
            )
        )

    def on_treasury_deposit_confirmed(self, request: DepositRequest) -> list[ReferralReward]:
        if request.status != DepositStatus.CONFIRMED or not request.ledger_transaction_id:
            return []
        user = self.session.get(User, request.user_id)
        account_type = str(getattr(getattr(user, "account_type", None), "value", getattr(user, "account_type", "user")))
        return self.apply_settled_deposit(
            SettledDeposit(
                user_id=request.user_id,
                account_type=account_type,
                deposit_kind="treasury_deposit",
                deposit_id=request.id,
                payment_reference=request.reference,
                provider_reference=request.transfer_reference,
                gross_fiat=_money(request.amount_fiat),
                wallet_credit=_coin(request.amount_coin),
                platform_fee=Decimal("0.0000"),
                processor_fee=Decimal("0.0000"),
                currency_code=(request.currency_code or "NGN").upper(),
                wallet_unit=LedgerUnit.COIN.value,
                rate_value=Decimal(request.rate_value),
                rate_direction=_direction(request.rate_direction),
                settled_at=_aware(request.confirmed_at) or utcnow(),
                settled=True,
            )
        )

    def on_owner_deposit_credited(
        self,
        intent: Any,
        *,
        fiat_amount: Decimal,
        rate_value: Decimal,
        rate_direction: Any,
        wallet_credit: Decimal,
    ) -> list[ReferralReward]:
        if str(getattr(intent, "status", "")) != "credited":
            return []
        user = self.session.get(User, intent.user_id)
        account_type = str(getattr(getattr(user, "account_type", None), "value", "user"))
        return self.apply_settled_deposit(
            SettledDeposit(
                user_id=intent.user_id,
                account_type=account_type,
                deposit_kind="owner_deposit",
                deposit_id=str(intent.id),
                payment_reference=str(intent.reference),
                provider_reference=str(getattr(intent, "provider", "") or ""),
                gross_fiat=_money(fiat_amount),
                wallet_credit=_coin(wallet_credit),
                platform_fee=Decimal("0.0000"),
                processor_fee=Decimal("0.0000"),
                currency_code="NGN",
                wallet_unit=LedgerUnit.COIN.value,
                rate_value=Decimal(rate_value),
                rate_direction=_direction(rate_direction),
                settled_at=utcnow(),
                settled=True,
            )
        )

    def apply_settled_deposit(self, deposit: SettledDeposit) -> list[ReferralReward]:
        if not deposit.settled or deposit.gross_fiat <= 0:
            return []
        settings = self.ensure_programme()
        if not settings.is_active:
            return []
        if deposit.deposit_kind not in set(settings.qualifying_deposit_types_json or []):
            return []
        attribution = self._lock_attribution(deposit.user_id)
        if attribution is None:
            return []
        if attribution.referrer_user_id == deposit.user_id:
            return []
        existing = self._first_deposit_rewards(deposit.user_id)
        if existing:
            return existing
        if attribution.locked_at is not None:
            return []
        created = self._insert_reward_pair(attribution, deposit, settings)
        if not created:
            return self._first_deposit_rewards(deposit.user_id)
        rewards = self._first_deposit_rewards(deposit.user_id)
        bonus = next(item for item in rewards if item.reward_type == BONUS_TYPE)
        self._credit_bonus(bonus, deposit)
        self._screen_fraud(attribution, bonus)
        attribution.locked_at = utcnow()
        attribution.attribution_status = "qualified"
        merged = dict(attribution.metadata_json or {})
        merged["qualifying_deposit_id"] = deposit.deposit_id
        merged["qualifying_deposit_kind"] = deposit.deposit_kind
        attribution.metadata_json = merged
        self.session.flush()
        return self._first_deposit_rewards(deposit.user_id)

    def on_deposit_reversed(
        self,
        *,
        user_id: str,
        deposit_kind: str,
        deposit_id: str,
        reversal_status: str,
        wallet_reversal_completed: bool,
    ) -> None:
        rewards = [
            reward
            for reward in self._first_deposit_rewards(user_id)
            if reward.deposit_id == deposit_id and reward.deposit_kind == deposit_kind
        ]
        if not rewards:
            rewards = self._first_deposit_rewards(user_id)
            rewards = [reward for reward in rewards if reward.deposit_id == deposit_id]
        if not rewards:
            return
        for reward in rewards:
            if reward.reward_type == COMMISSION_TYPE:
                self._reverse_commission(reward, reversal_status, wallet_reversal_completed)
            elif reward.reward_type == BONUS_TYPE:
                self._reverse_bonus(reward, reversal_status, wallet_reversal_completed)
        self.session.flush()

    def on_purchase_order_reversed(
        self,
        order: FancoinPurchaseOrder,
        *,
        reversal_status: str,
        wallet_reversal_completed: bool,
    ) -> None:
        self.on_deposit_reversed(
            user_id=order.user_id,
            deposit_kind="purchase_order",
            deposit_id=order.id,
            reversal_status=reversal_status,
            wallet_reversal_completed=wallet_reversal_completed,
        )

    def decide_commission(
        self,
        actor: User,
        reward_id: str,
        *,
        decision: str,
        reason: str,
        hold_days: int | None = None,
    ) -> dict[str, Any]:
        reason = (reason or "").strip()
        if len(reason) < 3:
            raise FirstDepositReferralError("reason_required", "A review reason is required.")
        reward = self.session.get(ReferralReward, reward_id)
        if reward is None or reward.reward_type != COMMISSION_TYPE:
            raise FirstDepositReferralError("reward_not_found", "Commission reward not found.")
        choice = decision.strip().lower()
        now = utcnow()
        if choice == "approve":
            if reward.status != ReferralRewardStatus.PENDING:
                raise FirstDepositReferralError("reward_not_pending", "Only a pending commission can be approved.")
            if reward.hold_until is not None and now < _aware(reward.hold_until):
                raise FirstDepositReferralError("hold_active", "The fraud hold has not expired.")
            reward.status = ReferralRewardStatus.APPROVED
            reward.approved_at = now
            reward.review_reason = reason
            self._ledger(reward, "decision_approve", reward.status, reason)
        elif choice == "block":
            if reward.status == ReferralRewardStatus.PAID:
                raise FirstDepositReferralError("reward_already_paid", "A paid commission cannot be blocked.")
            reward.status = ReferralRewardStatus.BLOCKED
            reward.blocked_at = now
            reward.review_reason = reason
            self._ledger(reward, "decision_block", reward.status, reason)
        elif choice == "hold":
            if reward.status != ReferralRewardStatus.PENDING:
                raise FirstDepositReferralError("reward_not_pending", "Only a pending commission can be held.")
            extra = int(hold_days if hold_days is not None else 7)
            if extra < 1 or extra > 90:
                raise FirstDepositReferralError("invalid_hold", "Extra hold must be between 1 and 90 days.")
            base = _aware(reward.hold_until) or now
            reward.hold_until = base + timedelta(days=extra)
            reward.review_reason = reason
            self._ledger(reward, "decision_hold", reward.status, reason)
        elif choice == "reverse":
            if reward.status == ReferralRewardStatus.PAID:
                self._open_recovery(
                    reward,
                    kind="paid_commission_recovery",
                    amount=_money(reward.reward_amount),
                    currency=reward.qualifying_currency or "NGN",
                    notes=reason,
                )
                self._ledger(reward, "recovery_opened", reward.status, reason)
            else:
                reward.status = ReferralRewardStatus.REVERSED
                reward.reversed_at = now
                reward.review_reason = reason
                self._ledger(reward, "decision_reverse", reward.status, reason)
        else:
            raise FirstDepositReferralError("invalid_decision", "Decision must be approve, block, hold, or reverse.")
        self.session.flush()
        self._audit(actor, f"commission_{choice}", "referral_reward", reward.id, reason, {"decision": choice})
        return self._reward_view(reward)

    def create_payout_batch(
        self,
        actor: User,
        *,
        reward_ids: list[str],
        payout_method: str,
        destination_label: str | None = None,
        off_cycle_reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if idempotency_key:
            existing = self.session.scalar(
                select(ReferralPayoutBatch).where(ReferralPayoutBatch.idempotency_key == idempotency_key)
            )
            if existing is not None:
                return self._batch_view(existing)
        method = payout_method.strip().lower()
        if method not in {"external_transfer", "internal_wallet"}:
            raise FirstDepositReferralError("invalid_payout_method", "Payout method is not supported.")
        rewards = self._load_payout_rewards(reward_ids)
        settings = self.ensure_programme()
        today = datetime.now(timezone.utc).weekday()
        if today != int(settings.payout_weekday) and not (off_cycle_reason or "").strip():
            raise FirstDepositReferralError(
                "payout_not_scheduled",
                "Payouts are run on the configured weekday unless an off-cycle reason is recorded.",
            )
        beneficiary = self._beneficiary_key(rewards[0])
        currency = (rewards[0].qualifying_currency or "").upper()
        total = Decimal("0.00")
        for reward in rewards:
            if self._beneficiary_key(reward) != beneficiary:
                raise FirstDepositReferralError(
                    "payout_beneficiary_mismatch",
                    "A payout batch can contain only one beneficiary.",
                )
            if (reward.qualifying_currency or "").upper() != currency:
                raise FirstDepositReferralError(
                    "payout_currency_mismatch",
                    "A payout batch can contain only one currency.",
                )
            self._assert_payable(reward)
            total += _money(reward.reward_amount)
        total = _money(total)
        thresholds = dict(settings.min_payout_thresholds_json or {})
        if currency not in thresholds:
            raise FirstDepositReferralError(
                "threshold_not_configured",
                f"No payout threshold is configured for {currency}.",
            )
        if total < _money(thresholds[currency]):
            raise FirstDepositReferralError(
                "below_payout_threshold",
                f"The batch total is below the {currency} {_money(thresholds[currency])} threshold.",
            )
        kind, beneficiary_id = beneficiary
        linked_user_id = beneficiary_id if kind == "user" else None
        if kind == "partner":
            partner = self.session.get(ReferralPartner, beneficiary_id)
            linked_user_id = partner.owner_user_id if partner else None
        if method == "internal_wallet" and not linked_user_id:
            raise FirstDepositReferralError(
                "internal_payout_unavailable",
                "Internal wallet payout requires a GTEX user. Record an external payment reference instead.",
            )
        batch = ReferralPayoutBatch(
            beneficiary_user_id=linked_user_id,
            beneficiary_partner_id=beneficiary_id if kind == "partner" else None,
            currency_code=currency,
            total_amount=total,
            status="draft",
            payout_method=method,
            destination_label=(destination_label or "").strip() or self._destination_label(kind, beneficiary_id),
            idempotency_key=(idempotency_key or "").strip() or None,
            created_by_user_id=actor.id,
            notes=(off_cycle_reason or "").strip() or None,
        )
        self.session.add(batch)
        self.session.flush()
        for reward in rewards:
            self.session.add(
                ReferralPayoutItem(
                    batch_id=batch.id,
                    reward_id=reward.id,
                    amount=_money(reward.reward_amount),
                    currency_code=currency,
                )
            )
            reward.payout_batch_id = batch.id
            self._ledger(reward, "payout_reserved", reward.status, batch.id)
        self.session.flush()
        self._audit(actor, "payout_batch_created", "referral_payout_batch", batch.id, off_cycle_reason, {
            "total": format(total, "f"),
            "currency": currency,
            "method": method,
            "reward_ids": [reward.id for reward in rewards],
        })
        return self._batch_view(batch)

    def confirm_payout_batch(
        self,
        actor: User,
        batch_id: str,
        *,
        external_reference: str | None = None,
    ) -> dict[str, Any]:
        batch = self.session.get(ReferralPayoutBatch, batch_id)
        if batch is None:
            raise FirstDepositReferralError("batch_not_found", "Payout batch not found.")
        reference = (external_reference or "").strip()
        if batch.status == "confirmed":
            if batch.payout_method == "external_transfer" and reference and reference != (batch.external_reference or ""):
                raise FirstDepositReferralError(
                    "duplicate_payout_confirmation",
                    "This payout was already confirmed with a different payment reference.",
                )
            return self._batch_view(batch)
        if batch.status != "draft":
            raise FirstDepositReferralError("batch_not_draft", "Only a draft payout batch can be confirmed.")
        items = list(
            self.session.scalars(select(ReferralPayoutItem).where(ReferralPayoutItem.batch_id == batch.id)).all()
        )
        if not items:
            raise FirstDepositReferralError("batch_empty", "The payout batch has no commissions.")
        rewards = []
        for item in items:
            reward = self.session.get(ReferralReward, item.reward_id)
            if reward is None:
                raise FirstDepositReferralError("reward_not_found", "A payout item is missing its commission.")
            if self._beneficiary_key(reward) != self._batch_beneficiary(batch):
                raise FirstDepositReferralError(
                    "payout_beneficiary_mismatch",
                    "This payout reference cannot mark another recipient's commission as paid.",
                )
            if (reward.qualifying_currency or "").upper() != batch.currency_code:
                raise FirstDepositReferralError(
                    "payout_currency_mismatch", "The commission currency does not match the payout batch."
                )
            self._assert_payable(reward)
            rewards.append(reward)
        if batch.payout_method == "external_transfer":
            if len(reference) < 3:
                raise FirstDepositReferralError(
                    "payment_reference_required",
                    "Record the bank, wallet, or provider reference for the completed transfer. GTEX has not moved this money.",
                )
            self._reject_reused_reference(batch, reference)
            batch.external_reference = reference
        else:
            ledger_reference = self._pay_internal_wallet(batch, rewards)
            batch.external_reference = ledger_reference
            batch.ledger_transaction_id = ledger_reference.removeprefix("ledger:")
        now = utcnow()
        batch.status = "confirmed"
        batch.confirmed_at = now
        batch.confirmed_by_user_id = actor.id
        for reward in rewards:
            reward.status = ReferralRewardStatus.PAID
            reward.paid_at = now
            reward.reward_reference = batch.external_reference
            self._ledger(reward, "payout_paid", reward.status, batch.external_reference or batch.id)
        self.session.flush()
        self._audit(actor, "payout_batch_confirmed", "referral_payout_batch", batch.id, reference or None, {
            "method": batch.payout_method,
            "reference": batch.external_reference,
        })
        return self._batch_view(batch)

    def create_partner(self, actor: User, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("display_name") or "").strip()
        campaign_name = str(payload.get("campaign_name") or "").strip()
        if len(name) < 2 or len(campaign_name) < 2:
            raise FirstDepositReferralError("partner_invalid", "Partner name and campaign name are required.")
        owner_user_id = (payload.get("owner_user_id") or None) or None
        creator_profile_id = (payload.get("creator_profile_id") or None) or None
        owner = self.session.get(User, owner_user_id) if owner_user_id else None
        if owner_user_id and owner is None:
            raise FirstDepositReferralError("owner_not_found", "The linked GTEX user does not exist.")
        creator = self.session.get(CreatorProfile, creator_profile_id) if creator_profile_id else None
        if creator_profile_id and creator is None:
            raise FirstDepositReferralError("creator_not_found", "The linked creator profile does not exist.")
        if creator is not None and owner is None:
            owner_user_id = creator.user_id
            owner = self.session.get(User, owner_user_id)
        code = self._normalize_code(payload.get("code")) if payload.get("code") else self._generate_code()
        self._ensure_code_available(code)
        email = (payload.get("contact_email") or None)
        email = email.strip().lower() if isinstance(email, str) and email.strip() else None
        destination = (payload.get("payout_destination_label") or None)
        destination = destination.strip() if isinstance(destination, str) and destination.strip() else None
        currency = str(payload.get("payout_currency") or "NGN").strip().upper()
        starts_at = _aware(payload.get("starts_at")) if isinstance(payload.get("starts_at"), datetime) else None
        ends_at = _aware(payload.get("ends_at")) if isinstance(payload.get("ends_at"), datetime) else None
        if starts_at and ends_at and ends_at <= starts_at:
            raise FirstDepositReferralError("invalid_campaign_window", "The campaign end must be after the start.")
        max_registrations = payload.get("max_registrations")
        if max_registrations is not None:
            max_registrations = int(max_registrations)
            if max_registrations < 1:
                raise FirstDepositReferralError("invalid_max_uses", "Maximum registrations must be at least 1.")
        partner = ReferralPartner(
            display_name=name,
            contact_email=email,
            social_handle=(payload.get("social_handle") or None),
            campaign_name=campaign_name,
            status="active",
            is_active=True,
            owner_user_id=owner.id if owner else None,
            creator_profile_id=creator.id if creator else None,
            notes=payload.get("notes"),
            contractual_terms=payload.get("contractual_terms"),
            payout_destination_label=destination,
            payout_destination_fingerprint=_hash_value(destination) if destination else None,
            payout_currency=currency,
            created_by_user_id=actor.id,
        )
        self.session.add(partner)
        self.session.flush()
        code_type = ShareCodeType.PROMO_CODE
        if creator is not None:
            code_type = ShareCodeType.CREATOR_SHARE
        elif owner is not None:
            code_type = ShareCodeType.USER_REFERRAL
        share = ShareCode(
            code=code,
            code_type=code_type,
            owner_user_id=owner.id if owner else None,
            owner_creator_id=creator.id if creator else None,
            is_active=True,
            max_uses=max_registrations,
            current_uses=0,
            starts_at=starts_at,
            ends_at=ends_at,
            referral_partner_id=partner.id,
            metadata_json={"origin": "referral_partner"},
        )
        self.session.add(share)
        self.session.flush()
        campaign = ReferralCampaign(
            partner_id=partner.id,
            name=campaign_name,
            share_code_id=share.id,
            status="active",
            starts_at=starts_at,
            ends_at=ends_at,
            max_registrations=max_registrations,
            notes=payload.get("notes"),
            public_link=referral_link(code),
        )
        self.session.add(campaign)
        self.session.flush()
        share.referral_campaign_id = campaign.id
        self.session.flush()
        self._audit(actor, "partner_created", "referral_partner", partner.id, None, {
            "code": code,
            "campaign_id": campaign.id,
        })
        return self._partner_view(partner, include_private=True)

    def update_partner(self, actor: User, partner_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        partner = self._partner_or_raise(partner_id)
        for field in ("display_name", "social_handle", "notes", "contractual_terms"):
            if field in payload and payload[field] is not None:
                setattr(partner, field, str(payload[field]).strip())
        if "contact_email" in payload:
            email = payload["contact_email"]
            partner.contact_email = email.strip().lower() if isinstance(email, str) and email.strip() else None
        if "payout_destination_label" in payload:
            label = payload["payout_destination_label"]
            partner.payout_destination_label = label.strip() if isinstance(label, str) and label.strip() else None
            partner.payout_destination_fingerprint = _hash_value(partner.payout_destination_label)
        if "payout_currency" in payload and payload["payout_currency"]:
            partner.payout_currency = str(payload["payout_currency"]).upper()
        if payload.get("owner_user_id"):
            owner = self.session.get(User, payload["owner_user_id"])
            if owner is None:
                raise FirstDepositReferralError("owner_not_found", "The linked GTEX user does not exist.")
            partner.owner_user_id = owner.id
        self.session.flush()
        self._audit(actor, "partner_updated", "referral_partner", partner.id, payload.get("reason"), {})
        return self._partner_view(partner, include_private=True)

    def set_partner_status(self, actor: User, partner_id: str, *, active: bool, reason: str) -> dict[str, Any]:
        if len((reason or "").strip()) < 3:
            raise FirstDepositReferralError("reason_required", "A reason is required.")
        partner = self._partner_or_raise(partner_id)
        partner.status = "active" if active else "suspended"
        partner.is_active = active
        campaigns = list(
            self.session.scalars(select(ReferralCampaign).where(ReferralCampaign.partner_id == partner.id)).all()
        )
        for campaign in campaigns:
            campaign.status = "active" if active else "disabled"
            share = self.session.get(ShareCode, campaign.share_code_id)
            if share is not None:
                share.is_active = active
        self.session.flush()
        self._audit(
            actor,
            "partner_reactivated" if active else "partner_suspended",
            "referral_partner",
            partner.id,
            reason,
            {},
        )
        return self._partner_view(partner, include_private=True)

    def set_campaign_status(self, actor: User, campaign_id: str, *, active: bool, reason: str) -> dict[str, Any]:
        if len((reason or "").strip()) < 3:
            raise FirstDepositReferralError("reason_required", "A reason is required.")
        campaign = self.session.get(ReferralCampaign, campaign_id)
        if campaign is None:
            raise FirstDepositReferralError("campaign_not_found", "Campaign not found.")
        partner = self._partner_or_raise(campaign.partner_id)
        if active and partner.status != "active":
            raise FirstDepositReferralError("partner_suspended", "Reactivate the partner before enabling the campaign.")
        campaign.status = "active" if active else "disabled"
        share = self.session.get(ShareCode, campaign.share_code_id)
        if share is not None:
            share.is_active = active
        self.session.flush()
        self._audit(actor, "campaign_status_changed", "referral_campaign", campaign.id, reason, {"active": active})
        return self._campaign_view(campaign)

    def list_partners(self) -> list[dict[str, Any]]:
        partners = list(self.session.scalars(select(ReferralPartner).order_by(ReferralPartner.created_at.desc())).all())
        return [self._partner_view(partner, include_private=True) for partner in partners]

    def partner_detail(self, partner_id: str) -> dict[str, Any]:
        partner = self._partner_or_raise(partner_id)
        view = self._partner_view(partner, include_private=True)
        view["performance"] = self.partner_performance(partner_id)
        view["attributions"] = self.attributions_for_partner(partner_id)
        return view

    def partner_performance(self, partner_id: str) -> dict[str, Any]:
        partner = self._partner_or_raise(partner_id)
        return self._performance_for(partner_id=partner.id, share_code_ids=self._partner_share_ids(partner.id))

    def attributions_for_partner(self, partner_id: str) -> list[dict[str, Any]]:
        self._partner_or_raise(partner_id)
        rows = list(
            self.session.scalars(
                select(ReferralAttribution)
                .where(ReferralAttribution.referral_partner_id == partner_id)
                .order_by(ReferralAttribution.created_at.desc())
            ).all()
        )
        return [self._attribution_admin_view(row) for row in rows]

    def list_links(self) -> list[dict[str, Any]]:
        campaigns = list(self.session.scalars(select(ReferralCampaign).order_by(ReferralCampaign.created_at.desc())).all())
        return [self._campaign_view(campaign) for campaign in campaigns]

    def list_attributions(self) -> list[dict[str, Any]]:
        rows = list(
            self.session.scalars(select(ReferralAttribution).order_by(ReferralAttribution.created_at.desc())).all()
        )
        return [self._attribution_admin_view(row) for row in rows[:500]]

    def attribution_history(self, attribution_id: str) -> dict[str, Any]:
        attribution = self.session.get(ReferralAttribution, attribution_id)
        if attribution is None:
            raise FirstDepositReferralError("attribution_not_found", "Attribution not found.")
        clicks = []
        if attribution.share_code_id:
            clicks = list(
                self.session.scalars(
                    select(ReferralClick)
                    .where(ReferralClick.share_code_id == attribution.share_code_id, ReferralClick.succeeded.is_(True))
                    .order_by(ReferralClick.created_at.asc())
                ).all()
            )
        events = list(
            self.session.scalars(
                select(ReferralEvent)
                .where(ReferralEvent.referral_attribution_id == attribution.id)
                .order_by(ReferralEvent.occurred_at.asc())
            ).all()
        )
        rewards = list(
            self.session.scalars(
                select(ReferralReward).where(ReferralReward.referral_attribution_id == attribution.id)
            ).all()
        )
        steps = []
        if clicks:
            steps.append({"step": "referral_link_clicked", "at": clicks[0].created_at, "count": len(clicks)})
        steps.append({"step": "account_registered", "at": attribution.created_at})
        steps.append({"step": "referral_attributed", "at": attribution.first_touch_at, "status": attribution.attribution_status})
        for reward in rewards:
            label = "user_bonus_issued" if reward.reward_type == BONUS_TYPE else "commission_generated"
            steps.append({"step": label, "at": reward.created_at, "status": reward.status.value, "reward_id": reward.id})
            if reward.reward_type == COMMISSION_TYPE:
                if reward.hold_until:
                    steps.append({"step": "hold_until", "at": reward.hold_until, "status": reward.status.value})
                if reward.approved_at:
                    steps.append({"step": "commission_approved", "at": reward.approved_at})
                if reward.paid_at:
                    steps.append({"step": "commission_paid", "at": reward.paid_at, "reference": reward.reward_reference})
        for event in events:
            if event.event_type == ReferralEventType.FIRST_QUALIFYING_DEPOSIT:
                steps.append({"step": "first_deposit_settled", "at": event.occurred_at, "payload": event.event_payload_json})
        steps.sort(key=lambda item: _aware(item.get("at")) or datetime.min.replace(tzinfo=timezone.utc))
        view = self._attribution_admin_view(attribution)
        view["timeline"] = _jsonable(steps)
        view["rewards"] = [self._reward_view(reward) for reward in rewards]
        return view

    def list_conversions(self) -> list[dict[str, Any]]:
        rewards = list(
            self.session.scalars(
                select(ReferralReward)
                .where(ReferralReward.reward_type == BONUS_TYPE)
                .order_by(ReferralReward.created_at.desc())
            ).all()
        )
        return [self._reward_view(reward) for reward in rewards[:500]]

    def list_commissions(self, status: str | None = None) -> list[dict[str, Any]]:
        statement = select(ReferralReward).where(ReferralReward.reward_type == COMMISSION_TYPE)
        if status:
            statement = statement.where(ReferralReward.status == ReferralRewardStatus(status))
        rewards = list(self.session.scalars(statement.order_by(ReferralReward.created_at.desc())).all())
        return [self._reward_view(reward) for reward in rewards[:500]]

    def list_batches(self) -> list[dict[str, Any]]:
        batches = list(
            self.session.scalars(select(ReferralPayoutBatch).order_by(ReferralPayoutBatch.created_at.desc())).all()
        )
        return [self._batch_view(batch) for batch in batches]

    def payout_preview(self) -> list[dict[str, Any]]:
        settings = self.ensure_programme()
        now = utcnow()
        rewards = list(
            self.session.scalars(
                select(ReferralReward).where(
                    ReferralReward.reward_type == COMMISSION_TYPE,
                    ReferralReward.status == ReferralRewardStatus.APPROVED,
                    ReferralReward.payout_batch_id.is_(None),
                )
            ).all()
        )
        grouped: dict[tuple[str, str, str], list[ReferralReward]] = {}
        for reward in rewards:
            if reward.hold_until is not None and now < _aware(reward.hold_until):
                continue
            kind, beneficiary_id = self._beneficiary_key(reward)
            currency = (reward.qualifying_currency or "").upper()
            grouped.setdefault((kind, beneficiary_id, currency), []).append(reward)
        preview = []
        thresholds = dict(settings.min_payout_thresholds_json or {})
        for (kind, beneficiary_id, currency), items in grouped.items():
            total = _money(sum((_money(item.reward_amount) for item in items), Decimal("0")))
            threshold = thresholds.get(currency)
            preview.append({
                "beneficiary_kind": kind,
                "beneficiary_id": beneficiary_id,
                "currency": currency,
                "commission_count": len(items),
                "total": format(total, "f"),
                "reward_ids": [item.id for item in items],
                "threshold": threshold,
                "meets_threshold": threshold is not None and total >= _money(threshold),
                "destination_label": self._destination_label(kind, beneficiary_id),
            })
        return preview

    def list_fraud(self) -> list[dict[str, Any]]:
        flags = list(self.session.scalars(select(ReferralFlag).order_by(ReferralFlag.created_at.desc())).all())
        return [
            {
                "id": flag.id,
                "flag_type": flag.flag_type,
                "severity": flag.severity,
                "subject_kind": flag.subject_kind,
                "subject_id": flag.subject_id,
                "status": flag.status,
                "reason_codes": list(flag.reason_codes or []),
                "created_at": flag.created_at.isoformat() if flag.created_at else None,
            }
            for flag in flags[:500]
        ]

    def overview(self) -> dict[str, Any]:
        performance = self._performance_for(partner_id=None, share_code_ids=None)
        performance["partners"] = int(
            self.session.scalar(select(func.count()).select_from(ReferralPartner)) or 0
        )
        performance["active_campaigns"] = int(
            self.session.scalar(
                select(func.count()).select_from(ReferralCampaign).where(ReferralCampaign.status == "active")
            )
            or 0
        )
        return performance

    def analytics(self) -> dict[str, Any]:
        overview = self.overview()
        partners = []
        for partner in self.session.scalars(select(ReferralPartner).order_by(ReferralPartner.display_name.asc())).all():
            item = self.partner_performance(partner.id)
            item["partner_id"] = partner.id
            item["display_name"] = partner.display_name
            item["status"] = partner.status
            partners.append(item)
        overview["partners_performance"] = partners
        return overview

    def export_csv(self, kind: str) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        if kind == "rewards":
            writer.writerow([
                "reward_id", "type", "status", "referred_user_id", "beneficiary_user_id", "partner_id",
                "qualifying_amount", "qualifying_currency", "reward_amount", "reward_unit", "applied_rate_bps",
                "policy_version", "deposit_kind", "deposit_id", "payment_reference", "created_at", "paid_at",
            ])
            rewards = self.session.scalars(select(ReferralReward).order_by(ReferralReward.created_at.asc())).all()
            for reward in rewards:
                if reward.reward_type not in {BONUS_TYPE, COMMISSION_TYPE}:
                    continue
                payload = reward.reward_payload_json or {}
                writer.writerow([
                    reward.id, reward.reward_type.value, reward.status.value, reward.referred_user_id,
                    reward.beneficiary_user_id or "", reward.referral_partner_id or "",
                    reward.qualifying_amount, reward.qualifying_currency, reward.reward_amount, reward.reward_unit,
                    reward.applied_rate_bps, reward.policy_version, reward.deposit_kind, reward.deposit_id,
                    payload.get("payment_reference", ""), reward.created_at, reward.paid_at or "",
                ])
        elif kind == "attributions":
            writer.writerow([
                "attribution_id", "referred_user_id", "referrer_user_id", "partner_id", "share_code_id",
                "account_type", "status", "locked_at", "created_at",
            ])
            for row in self.session.scalars(select(ReferralAttribution).order_by(ReferralAttribution.created_at.asc())).all():
                writer.writerow([
                    row.id, row.referred_user_id, row.referrer_user_id or "", row.referral_partner_id or "",
                    row.share_code_id or "", row.account_type_snapshot or "", row.attribution_status,
                    row.locked_at or "", row.created_at,
                ])
        elif kind == "payouts":
            writer.writerow([
                "batch_id", "status", "method", "beneficiary_user_id", "beneficiary_partner_id", "currency",
                "total", "external_reference", "confirmed_at",
            ])
            for batch in self.session.scalars(select(ReferralPayoutBatch).order_by(ReferralPayoutBatch.created_at.asc())).all():
                writer.writerow([
                    batch.id, batch.status, batch.payout_method, batch.beneficiary_user_id or "",
                    batch.beneficiary_partner_id or "", batch.currency_code, batch.total_amount,
                    batch.external_reference or "", batch.confirmed_at or "",
                ])
        else:
            raise FirstDepositReferralError("unknown_report", "Report must be rewards, attributions, or payouts.")
        return buffer.getvalue()

    def list_audits(self) -> list[dict[str, Any]]:
        rows = list(
            self.session.scalars(select(ReferralAdminAudit).order_by(ReferralAdminAudit.created_at.desc())).all()
        )
        return [
            {
                "id": row.id,
                "actor_user_id": row.actor_user_id,
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "reason": row.reason,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows[:500]
        ]

    def ensure_personal_code(self, user: User) -> ShareCode:
        existing = self.session.scalar(
            select(ShareCode)
            .where(ShareCode.owner_user_id == user.id, ShareCode.is_active.is_(True))
            .order_by(ShareCode.created_at.asc())
        )
        if existing is not None:
            return existing
        creator = self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == user.id))
        code = self._generate_code()
        share = ShareCode(
            code=code,
            code_type=ShareCodeType.CREATOR_SHARE if creator else ShareCodeType.USER_REFERRAL,
            owner_user_id=user.id,
            owner_creator_id=creator.id if creator else None,
            is_active=True,
            max_uses=100000,
            current_uses=0,
            metadata_json={"origin": "account_referral"},
        )
        self.session.add(share)
        self.session.flush()
        return share

    def my_affiliate(self, user: User) -> dict[str, Any]:
        share = self.ensure_personal_code(user)
        partner = self.session.scalar(select(ReferralPartner).where(ReferralPartner.owner_user_id == user.id))
        share_ids = [item.id for item in self.session.scalars(select(ShareCode).where(ShareCode.owner_user_id == user.id)).all()]
        if partner is not None:
            share_ids.extend(self._partner_share_ids(partner.id))
        attributions = self._attributions_for_owner(user.id, partner.id if partner else None, share_ids)
        bonuses = self._rewards_for_attributions(attributions, BONUS_TYPE)
        commissions = self._owner_commissions(user.id, partner.id if partner else None)
        batches = self._owner_batches(user.id, partner.id if partner else None)
        volume: dict[str, Decimal] = {}
        for bonus in bonuses:
            currency = bonus.qualifying_currency or ""
            volume[currency] = _money(volume.get(currency, Decimal("0")) + _money(bonus.qualifying_amount))
        def total(status: ReferralRewardStatus) -> dict[str, str]:
            amounts: dict[str, Decimal] = {}
            for reward in commissions:
                if reward.status != status:
                    continue
                currency = reward.qualifying_currency or ""
                amounts[currency] = _money(amounts.get(currency, Decimal("0")) + _money(reward.reward_amount))
            return {currency: format(amount, "f") for currency, amount in amounts.items()}
        return {
            "code": share.code,
            "link": referral_link(share.code),
            "explanation": bonus_explanation(self.ensure_programme().user_bonus_bps),
            "registrations": len(attributions),
            "qualifying_deposits": len(bonuses),
            "referred_deposit_volume": {currency: format(amount, "f") for currency, amount in volume.items()},
            "pending_commission": total(ReferralRewardStatus.PENDING),
            "approved_commission": total(ReferralRewardStatus.APPROVED),
            "paid_commission": total(ReferralRewardStatus.PAID),
            "reversed_commission": total(ReferralRewardStatus.REVERSED),
            "blocked_commission": total(ReferralRewardStatus.BLOCKED),
            "payouts": [
                {
                    "id": batch.id,
                    "status": batch.status,
                    "currency": batch.currency_code,
                    "total": format(_money(batch.total_amount), "f"),
                    "reference": batch.external_reference,
                    "confirmed_at": batch.confirmed_at.isoformat() if batch.confirmed_at else None,
                }
                for batch in batches
            ],
        }

    def _insert_reward_pair(
        self,
        attribution: ReferralAttribution,
        deposit: SettledDeposit,
        settings: ReferralProgrammeSettings,
    ) -> bool:
        bonus_bps = int(settings.user_bonus_bps)
        commission_bps = int(settings.referrer_commission_bps)
        bonus_fiat = _percent(deposit.gross_fiat, bonus_bps)
        commission_fiat = _percent(deposit.gross_fiat, commission_bps)
        bonus_wallet = fiat_to_wallet(bonus_fiat, deposit.rate_value, deposit.rate_direction)
        partner = self.session.get(ReferralPartner, attribution.referral_partner_id) if attribution.referral_partner_id else None
        beneficiary_user_id = attribution.referrer_user_id or (partner.owner_user_id if partner else None)
        payload = {
            "qualifying_base": "gross_verified_fiat",
            "gross_fiat": format(deposit.gross_fiat, "f"),
            "wallet_credit": format(deposit.wallet_credit, "f"),
            "platform_fee_wallet": format(deposit.platform_fee, "f"),
            "processor_fee_wallet": format(deposit.processor_fee, "f"),
            "excluded_from_reward_base": ["platform_fee", "processor_fee", "net_wallet_credit"],
            "rounding": "HALF_UP fiat 0.01, then wallet conversion HALF_UP 0.0001 using the deposit rate",
            "rate_value": format(deposit.rate_value, "f"),
            "rate_direction": deposit.rate_direction,
            "wallet_unit": deposit.wallet_unit,
            "payment_reference": deposit.payment_reference,
            "provider_reference": deposit.provider_reference,
            "purchase_order_id": deposit.purchase_order_id,
            "account_type": deposit.account_type or attribution.account_type_snapshot,
            "policy_version": int(settings.version or 1),
            "user_bonus_bps": bonus_bps,
            "referrer_commission_bps": commission_bps,
            "shared_bonus_fiat": format(bonus_fiat, "f"),
            "shared_commission_fiat": format(commission_fiat, "f"),
            "settled_at": deposit.settled_at.isoformat(),
        }
        hold_until = deposit.settled_at + timedelta(days=int(settings.hold_days or 0))
        bonus = ReferralReward(
            reward_key=f"first_deposit_bonus:{deposit.user_id}",
            referral_attribution_id=attribution.id,
            referred_user_id=deposit.user_id,
            beneficiary_user_id=deposit.user_id,
            beneficiary_creator_id=None,
            trigger_event_type=ReferralEventType.FIRST_QUALIFYING_DEPOSIT,
            reward_type=BONUS_TYPE,
            status=ReferralRewardStatus.PENDING,
            reward_amount=bonus_wallet,
            reward_unit=deposit.wallet_unit,
            referral_partner_id=attribution.referral_partner_id,
            qualifying_amount=deposit.gross_fiat,
            qualifying_currency=deposit.currency_code,
            applied_rate_bps=bonus_bps,
            policy_version=int(settings.version or 1),
            deposit_kind=deposit.deposit_kind,
            deposit_id=deposit.deposit_id,
            reward_payload_json=payload,
        )
        commission = ReferralReward(
            reward_key=f"first_deposit_commission:{deposit.user_id}",
            referral_attribution_id=attribution.id,
            referred_user_id=deposit.user_id,
            beneficiary_user_id=beneficiary_user_id,
            beneficiary_creator_id=attribution.creator_profile_id,
            trigger_event_type=ReferralEventType.FIRST_QUALIFYING_DEPOSIT,
            reward_type=COMMISSION_TYPE,
            status=ReferralRewardStatus.PENDING,
            reward_amount=commission_fiat,
            reward_unit=deposit.currency_code,
            hold_until=hold_until,
            review_reason="fraud_hold",
            referral_partner_id=attribution.referral_partner_id,
            qualifying_amount=deposit.gross_fiat,
            qualifying_currency=deposit.currency_code,
            applied_rate_bps=commission_bps,
            policy_version=int(settings.version or 1),
            deposit_kind=deposit.deposit_kind,
            deposit_id=deposit.deposit_id,
            reward_payload_json=payload,
        )
        try:
            with self.session.begin_nested():
                self.session.add(bonus)
                self.session.add(commission)
                self.session.flush()
        except IntegrityError:
            return False
        self._event(
            attribution,
            ReferralEventType.FIRST_QUALIFYING_DEPOSIT,
            {"deposit_id": deposit.deposit_id, "deposit_kind": deposit.deposit_kind, "gross_fiat": format(deposit.gross_fiat, "f")},
        )
        self._ledger(bonus, "reward_created", bonus.status, deposit.deposit_id)
        self._ledger(commission, "reward_created", commission.status, deposit.deposit_id)
        self._ledger(commission, "hold_applied", commission.status, hold_until.isoformat())
        return True

    def _credit_bonus(self, reward: ReferralReward, deposit: SettledDeposit) -> None:
        amount = _coin(reward.reward_amount)
        if amount <= 0:
            reward.status = ReferralRewardStatus.PAID
            reward.paid_at = utcnow()
            reward.reward_payload_json = {**(reward.reward_payload_json or {}), "rounding_to_zero": True}
            self._ledger(reward, "bonus_credited", reward.status, "zero")
            return
        user = self.session.get(User, reward.referred_user_id)
        if user is None:
            raise FirstDepositReferralError("user_not_found", "Referred user is missing.")
        unit = _unit(deposit.wallet_unit)
        user_account = self.wallet_service.get_user_account(self.session, user, unit)
        operations = self.wallet_service.ensure_operations_account(self.session, unit)
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=user_account,
                    amount=amount,
                    transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT,
                ),
                LedgerPosting(
                    account=operations,
                    amount=-amount,
                    transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.PROMO_POOL_CREDIT,
            transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT,
            reference=f"referral-bonus:{user.id}",
            description="First-deposit referral bonus",
            actor=user,
            idempotency_key=f"referral-first-deposit-bonus:{user.id}",
            metadata={
                "referral_reward_id": reward.id,
                "deposit_id": deposit.deposit_id,
                "deposit_kind": deposit.deposit_kind,
                "gross_fiat": format(deposit.gross_fiat, "f"),
                "bonus_fiat": (reward.reward_payload_json or {}).get("shared_bonus_fiat"),
            },
        )
        reward.status = ReferralRewardStatus.PAID
        reward.paid_at = utcnow()
        reward.reward_reference = entries[0].transaction_id if entries else None
        payload = dict(reward.reward_payload_json or {})
        payload["ledger_transaction_id"] = reward.reward_reference
        reward.reward_payload_json = payload
        self._ledger(reward, "bonus_credited", reward.status, reward.reward_reference)

    def _reverse_commission(self, reward: ReferralReward, reversal_status: str, wallet_completed: bool) -> None:
        note = f"{reversal_status}:wallet_reversed={wallet_completed}"
        if reward.status == ReferralRewardStatus.PAID:
            self._open_recovery(
                reward,
                kind="paid_commission_recovery",
                amount=_money(reward.reward_amount),
                currency=reward.qualifying_currency or "NGN",
                notes=note,
            )
            self._ledger(reward, "recovery_opened", reward.status, note)
            self._flag("paid_commission_recovery", "high", "referral_reward", reward.id, ["deposit_reversed_after_payout"])
            return
        if reward.status in {ReferralRewardStatus.REVERSED, ReferralRewardStatus.BLOCKED}:
            self._ledger(reward, "deposit_reversal_noted", reward.status, note)
            return
        if reward.status == ReferralRewardStatus.PENDING:
            reward.status = ReferralRewardStatus.BLOCKED
            reward.blocked_at = utcnow()
        else:
            reward.status = ReferralRewardStatus.REVERSED
            reward.reversed_at = utcnow()
        reward.review_reason = "deposit_reversed"
        self._ledger(reward, "deposit_reversed", reward.status, note)

    def _reverse_bonus(self, reward: ReferralReward, reversal_status: str, wallet_completed: bool) -> None:
        note = f"{reversal_status}:wallet_reversed={wallet_completed}"
        if reward.status == ReferralRewardStatus.REVERSED:
            self._ledger(reward, "deposit_reversal_noted", reward.status, note)
            return
        amount = _coin(reward.reward_amount)
        clawed = Decimal("0.0000")
        if amount > 0 and reward.reward_reference:
            user = self.session.get(User, reward.referred_user_id)
            if user is not None:
                unit = _unit(reward.reward_unit or LedgerUnit.COIN.value)
                account = self.wallet_service.get_user_account(self.session, user, unit)
                available = _coin(self.wallet_service.get_balance(self.session, account))
                clawed = min(available, amount)
                if clawed > 0:
                    operations = self.wallet_service.ensure_operations_account(self.session, unit)
                    self.wallet_service.append_transaction(
                        self.session,
                        postings=[
                            LedgerPosting(account=account, amount=-clawed, transaction_type=LedgerTransactionType.ADJUSTMENT),
                            LedgerPosting(account=operations, amount=clawed, transaction_type=LedgerTransactionType.ADJUSTMENT),
                        ],
                        reason=LedgerEntryReason.ADJUSTMENT,
                        source_tag=LedgerSourceTag.PROMO_POOL_CREDIT,
                        transaction_type=LedgerTransactionType.ADJUSTMENT,
                        reference=f"referral-bonus-reversal:{user.id}",
                        description="Reverse first-deposit referral bonus",
                        actor=user,
                        idempotency_key=f"referral-first-deposit-bonus-clawback:{user.id}",
                        metadata={"referral_reward_id": reward.id, "reversal_status": reversal_status},
                    )
        shortfall = _coin(amount - clawed)
        payload = dict(reward.reward_payload_json or {})
        payload["clawback_amount"] = format(clawed, "f")
        payload["shortfall_amount"] = format(shortfall, "f")
        reward.reward_payload_json = payload
        if shortfall > 0:
            self._open_recovery(
                reward,
                kind="spent_bonus_shortfall",
                amount=shortfall,
                currency=reward.reward_unit or LedgerUnit.COIN.value,
                notes=note,
            )
            self._flag("spent_bonus_shortfall", "high", "referral_reward", reward.id, ["bonus_spent"])
            self._ledger(reward, "shortfall_recorded", reward.status, format(shortfall, "f"))
        if shortfall == 0:
            reward.status = ReferralRewardStatus.REVERSED
            reward.reversed_at = utcnow()
        reward.review_reason = "deposit_reversed"
        self._ledger(reward, "bonus_clawback", reward.status, note)
        if not wallet_completed:
            self._flag("deposit_reversal_incomplete", "high", "referral_reward", reward.id, ["wallet_debit_incomplete"])

    def _open_recovery(
        self,
        reward: ReferralReward,
        *,
        kind: str,
        amount: Decimal,
        currency: str,
        notes: str,
    ) -> None:
        existing = self.session.scalar(
            select(ReferralRecoveryCase).where(
                ReferralRecoveryCase.reward_id == reward.id,
                ReferralRecoveryCase.kind == kind,
            )
        )
        if existing is not None:
            return
        self.session.add(
            ReferralRecoveryCase(
                reward_id=reward.id,
                referred_user_id=reward.referred_user_id,
                kind=kind,
                amount=amount,
                currency_code=currency,
                status="open",
                deposit_kind=reward.deposit_kind,
                deposit_id=reward.deposit_id,
                notes=notes[:1000],
            )
        )
        self.session.flush()

    def _screen_fraud(self, attribution: ReferralAttribution, bonus: ReferralReward) -> None:
        metadata = attribution.metadata_json or {}
        ip_hash = metadata.get("signup_ip_hash")
        if ip_hash:
            recent = list(
                self.session.scalars(
                    select(ReferralAttribution)
                    .where(ReferralAttribution.created_at >= utcnow() - timedelta(days=7))
                    .order_by(ReferralAttribution.created_at.desc())
                    .limit(500)
                ).all()
            )
            matches = sum(1 for row in recent if (row.metadata_json or {}).get("signup_ip_hash") == ip_hash)
            if matches >= 4:
                self._flag("duplicate_signup_ip", "medium", "referral_attribution", attribution.id, ["shared_ip"])
                commission = self._commission_for_user(attribution.referred_user_id)
                if commission is not None:
                    commission.review_reason = "fraud_review_required"
                    self._ledger(commission, "fraud_flagged", commission.status, "shared_ip")
        if attribution.referral_partner_id:
            partner = self.session.get(ReferralPartner, attribution.referral_partner_id)
            if partner and partner.payout_destination_fingerprint:
                others = self.session.scalar(
                    select(func.count()).select_from(ReferralPartner).where(
                        ReferralPartner.payout_destination_fingerprint == partner.payout_destination_fingerprint,
                        ReferralPartner.id != partner.id,
                    )
                )
                if int(others or 0) > 0:
                    self._flag(
                        "shared_payout_destination",
                        "high",
                        "referral_partner",
                        partner.id,
                        ["duplicate_payout_destination"],
                    )
            day_count = self.session.scalar(
                select(func.count()).select_from(ReferralReward).where(
                    ReferralReward.referral_partner_id == attribution.referral_partner_id,
                    ReferralReward.reward_type == BONUS_TYPE,
                    ReferralReward.created_at >= utcnow() - timedelta(days=1),
                )
            )
            if int(day_count or 0) >= 10:
                self._flag("unusual_referral_velocity", "medium", "referral_partner", attribution.referral_partner_id, ["velocity"])
        if attribution.referrer_user_id == attribution.referred_user_id:
            self._flag("self_referral", "high", "referral_reward", bonus.id, ["self_referral"])

    def _flag(self, flag_type: str, severity: str, subject_kind: str, subject_id: str, reasons: list[str]) -> None:
        existing = self.session.scalar(
            select(ReferralFlag).where(
                ReferralFlag.flag_type == flag_type,
                ReferralFlag.subject_kind == subject_kind,
                ReferralFlag.subject_id == subject_id,
                ReferralFlag.status == "open",
            )
        )
        if existing is not None:
            return
        self.session.add(
            ReferralFlag(
                flag_type=flag_type,
                severity=severity,
                subject_kind=subject_kind,
                subject_id=subject_id,
                status="open",
                reason_codes=reasons,
                payload_json={},
            )
        )
        self.session.flush()

    def _resolve_active_code(self, code: str, *, for_update: bool = False) -> tuple[ShareCode, ReferralCampaign | None]:
        normalized = self._normalize_code(code)
        statement = select(ShareCode).where(
            or_(func.lower(ShareCode.code) == normalized.lower(), func.lower(ShareCode.vanity_code) == normalized.lower())
        )
        bind = self.session.get_bind()
        if for_update and bind is not None and bind.dialect.name != "sqlite":
            statement = statement.with_for_update()
        share = self.session.scalar(statement)
        if share is None:
            raise FirstDepositReferralError("referral_code_invalid", "This referral code is not recognised.")
        campaign = None
        if share.referral_campaign_id:
            campaign = self.session.get(ReferralCampaign, share.referral_campaign_id)
        elif share.referral_partner_id:
            campaign = self.session.scalar(
                select(ReferralCampaign).where(ReferralCampaign.share_code_id == share.id)
            )
        now = utcnow()
        if not share.is_active or (campaign is not None and campaign.status != "active"):
            raise FirstDepositReferralError("referral_code_inactive", "This referral code is not active.")
        if share.referral_partner_id:
            partner = self.session.get(ReferralPartner, share.referral_partner_id)
            if partner is None or partner.status != "active":
                raise FirstDepositReferralError("referral_code_inactive", "This referral code is not active.")
        starts_at = _aware(share.starts_at or (campaign.starts_at if campaign else None))
        ends_at = _aware(share.ends_at or (campaign.ends_at if campaign else None))
        if starts_at is not None and now < starts_at:
            raise FirstDepositReferralError("referral_code_not_started", "This referral code is not active yet.")
        if ends_at is not None and now >= ends_at:
            raise FirstDepositReferralError("referral_code_expired", "This referral code has expired.")
        limit = share.max_uses if share.max_uses is not None else (campaign.max_registrations if campaign else None)
        if limit is not None and int(share.current_uses or 0) >= int(limit):
            raise FirstDepositReferralError("referral_code_exhausted", "This referral code has reached its limit.")
        return share, campaign

    def _reject_self_referral(self, user: User, share: ShareCode, partner: ReferralPartner | None) -> None:
        email = (user.email or "").strip().lower()
        if share.owner_user_id and share.owner_user_id == user.id:
            raise FirstDepositReferralError("self_referral_blocked", "You cannot use your own referral code.")
        if partner and partner.owner_user_id == user.id:
            raise FirstDepositReferralError("self_referral_blocked", "You cannot use your own referral code.")
        if share.owner_user_id:
            owner = self.session.get(User, share.owner_user_id)
            if owner and owner.email and owner.email.strip().lower() == email:
                raise FirstDepositReferralError("self_referral_blocked", "You cannot use your own referral code.")
        if partner and partner.contact_email and partner.contact_email.strip().lower() == email:
            raise FirstDepositReferralError("self_referral_blocked", "You cannot use your own referral code.")

    def _enforce_attempt_limit(self, ip_address: str | None) -> None:
        ip_hash = _hash_value(ip_address)
        if ip_hash is None:
            return
        cutoff = utcnow() - timedelta(minutes=10)
        count = self.session.scalar(
            select(func.count()).select_from(ReferralClick).where(
                ReferralClick.ip_hash == ip_hash,
                ReferralClick.succeeded.is_(False),
                ReferralClick.created_at >= cutoff,
            )
        )
        if int(count or 0) >= 30:
            raise FirstDepositReferralError(
                "referral_code_rate_limited",
                "Too many referral code attempts. Please wait and try again.",
            )

    def _click(
        self,
        share_code_id: str | None,
        campaign_id: str | None,
        succeeded: bool,
        ip_address: str | None,
        user_agent: str | None,
        failure_reason: str | None,
    ) -> None:
        self.session.add(
            ReferralClick(
                share_code_id=share_code_id,
                campaign_id=campaign_id,
                succeeded=succeeded,
                ip_hash=_hash_value(ip_address),
                user_agent_hash=_hash_value(user_agent),
                failure_reason=failure_reason,
            )
        )
        self.session.flush()

    def _stamp_partner(self, attribution: ReferralAttribution, share: ShareCode) -> None:
        if attribution.referral_partner_id or not share.referral_partner_id:
            return
        attribution.referral_partner_id = share.referral_partner_id
        attribution.referral_campaign_id = share.referral_campaign_id
        if attribution.referrer_user_id is None:
            partner = self.session.get(ReferralPartner, share.referral_partner_id)
            if partner is not None:
                attribution.referrer_user_id = partner.owner_user_id
                attribution.creator_profile_id = attribution.creator_profile_id or partner.creator_profile_id
        self.session.flush()

    def _attribution_for_user(self, user_id: str) -> ReferralAttribution | None:
        return self.session.scalar(select(ReferralAttribution).where(ReferralAttribution.referred_user_id == user_id))

    def _lock_attribution(self, user_id: str) -> ReferralAttribution | None:
        statement = select(ReferralAttribution).where(ReferralAttribution.referred_user_id == user_id)
        bind = self.session.get_bind()
        if bind is not None and bind.dialect.name != "sqlite":
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def _first_deposit_rewards(self, user_id: str) -> list[ReferralReward]:
        return list(
            self.session.scalars(
                select(ReferralReward).where(
                    ReferralReward.referred_user_id == user_id,
                    ReferralReward.reward_type.in_([BONUS_TYPE, COMMISSION_TYPE]),
                )
            ).all()
        )

    def _commission_for_user(self, user_id: str) -> ReferralReward | None:
        return self.session.scalar(
            select(ReferralReward).where(
                ReferralReward.referred_user_id == user_id,
                ReferralReward.reward_type == COMMISSION_TYPE,
            )
        )

    def _event(self, attribution: ReferralAttribution, event_type: ReferralEventType, payload: dict[str, Any]) -> None:
        event_key = f"{attribution.id}:{event_type.value}"[:96]
        existing = self.session.scalar(select(ReferralEvent).where(ReferralEvent.event_key == event_key))
        if existing is not None:
            return
        self.session.add(
            ReferralEvent(
                event_key=event_key,
                referral_attribution_id=attribution.id,
                referred_user_id=attribution.referred_user_id,
                referrer_user_id=attribution.referrer_user_id,
                creator_profile_id=attribution.creator_profile_id,
                share_code_id=attribution.share_code_id,
                event_type=event_type,
                source_channel=attribution.source_channel,
                occurred_at=utcnow(),
                event_payload_json=_jsonable(payload),
            )
        )
        self.session.flush()

    def _ledger(self, reward: ReferralReward, entry_type: str, status: ReferralRewardStatus, reference: str | None) -> None:
        entry_key = f"{reward.id}:{entry_type}:{reference or 'none'}"[:128]
        existing = self.session.scalar(select(ReferralRewardLedger).where(ReferralRewardLedger.entry_key == entry_key))
        if existing is not None:
            return
        self.session.add(
            ReferralRewardLedger(
                entry_key=entry_key,
                reward_id=reward.id,
                entry_type=entry_type,
                amount=reward.reward_amount,
                unit=reward.reward_unit,
                status_after=status,
                reference_id=(reference or "")[:64] or None,
                payload_json={"entry_type": entry_type},
            )
        )
        self.session.flush()

    def _load_payout_rewards(self, reward_ids: list[str]) -> list[ReferralReward]:
        if not reward_ids:
            raise FirstDepositReferralError("payout_empty", "Select at least one commission.")
        rewards = []
        for reward_id in dict.fromkeys(reward_ids):
            reward = self.session.get(ReferralReward, reward_id)
            if reward is None or reward.reward_type != COMMISSION_TYPE:
                raise FirstDepositReferralError("reward_not_found", "One of the selected commissions does not exist.")
            rewards.append(reward)
        return rewards

    def _assert_payable(self, reward: ReferralReward) -> None:
        if reward.status != ReferralRewardStatus.APPROVED:
            raise FirstDepositReferralError("reward_not_approved", "Only an approved commission can be paid.")
        if reward.hold_until is not None and utcnow() < _aware(reward.hold_until):
            raise FirstDepositReferralError("hold_active", "The fraud hold has not expired.")
        if _money(reward.reward_amount) <= 0:
            raise FirstDepositReferralError("reward_amount_zero", "A zero commission cannot be paid.")

    def _beneficiary_key(self, reward: ReferralReward) -> tuple[str, str]:
        if reward.referral_partner_id:
            return ("partner", reward.referral_partner_id)
        if reward.beneficiary_user_id:
            return ("user", reward.beneficiary_user_id)
        raise FirstDepositReferralError("beneficiary_missing", "The commission has no beneficiary.")

    def _batch_beneficiary(self, batch: ReferralPayoutBatch) -> tuple[str, str]:
        if batch.beneficiary_partner_id:
            return ("partner", batch.beneficiary_partner_id)
        if batch.beneficiary_user_id:
            return ("user", batch.beneficiary_user_id)
        raise FirstDepositReferralError("beneficiary_missing", "The payout batch has no beneficiary.")

    def _destination_label(self, kind: str, beneficiary_id: str) -> str | None:
        if kind == "partner":
            partner = self.session.get(ReferralPartner, beneficiary_id)
            return partner.payout_destination_label if partner else None
        return None

    def _reject_reused_reference(self, batch: ReferralPayoutBatch, reference: str) -> None:
        other = self.session.scalar(
            select(ReferralPayoutBatch).where(
                ReferralPayoutBatch.external_reference == reference,
                ReferralPayoutBatch.status == "confirmed",
                ReferralPayoutBatch.id != batch.id,
            )
        )
        if other is None:
            return
        if (
            other.beneficiary_partner_id != batch.beneficiary_partner_id
            or other.beneficiary_user_id != batch.beneficiary_user_id
            or other.currency_code != batch.currency_code
        ):
            raise FirstDepositReferralError(
                "payout_reference_conflict",
                "That payment reference is already linked to a different recipient or currency.",
            )

    def _pay_internal_wallet(self, batch: ReferralPayoutBatch, rewards: list[ReferralReward]) -> str:
        user_id = batch.beneficiary_user_id
        if not user_id:
            raise FirstDepositReferralError(
                "internal_payout_unavailable",
                "Internal wallet payout requires a GTEX user.",
            )
        user = self.session.get(User, user_id)
        if user is None:
            raise FirstDepositReferralError("owner_not_found", "The referrer account no longer exists.")
        units = {str((reward.reward_payload_json or {}).get("wallet_unit") or LedgerUnit.COIN.value) for reward in rewards}
        if len(units) != 1:
            raise FirstDepositReferralError(
                "payout_wallet_unit_mismatch",
                "Internal payout cannot mix wallet units. Pay this batch externally or split it.",
            )
        wallet_amount = Decimal("0.0000")
        for reward in rewards:
            payload = reward.reward_payload_json or {}
            wallet_amount += fiat_to_wallet(
                _money(reward.reward_amount),
                Decimal(str(payload.get("rate_value") or "0")),
                payload.get("rate_direction"),
            )
        wallet_amount = _coin(wallet_amount)
        if wallet_amount <= 0:
            raise FirstDepositReferralError("rate_not_configured", "The original deposit rate cannot convert this payout.")
        unit = _unit(next(iter(units)))
        account = self.wallet_service.get_user_account(self.session, user, unit)
        operations = self.wallet_service.ensure_operations_account(self.session, unit)
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=account, amount=wallet_amount, transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT),
                LedgerPosting(account=operations, amount=-wallet_amount, transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.PROMO_POOL_CREDIT,
            transaction_type=LedgerTransactionType.PROMO_POOL_CREDIT,
            reference=f"referral-payout:{batch.id}",
            description=f"Referral commission payout {batch.currency_code} {format(_money(batch.total_amount), 'f')}",
            actor=user,
            idempotency_key=f"referral-payout:{batch.id}",
            metadata={
                "payout_batch_id": batch.id,
                "fiat_amount": format(_money(batch.total_amount), "f"),
                "fiat_currency": batch.currency_code,
                "conversion": "original deposit rate stored on the commission",
            },
        )
        transaction_id = entries[0].transaction_id if entries else generate_uuid()
        return f"ledger:{transaction_id}"

    def _performance_for(self, *, partner_id: str | None, share_code_ids: list[str] | None) -> dict[str, Any]:
        click_query = select(func.count()).select_from(ReferralClick).where(ReferralClick.succeeded.is_(True))
        attribution_query = select(ReferralAttribution)
        if partner_id is not None:
            click_query = click_query.where(ReferralClick.share_code_id.in_(share_code_ids or ["__none__"]))
            attribution_query = attribution_query.where(ReferralAttribution.referral_partner_id == partner_id)
        elif share_code_ids is not None:
            click_query = click_query.where(ReferralClick.share_code_id.in_(share_code_ids or ["__none__"]))
            attribution_query = attribution_query.where(ReferralAttribution.share_code_id.in_(share_code_ids or ["__none__"]))
        clicks = int(self.session.scalar(click_query) or 0)
        attributions = list(self.session.scalars(attribution_query).all())
        attribution_ids = [row.id for row in attributions] or ["__none__"]
        rewards = list(
            self.session.scalars(
                select(ReferralReward).where(ReferralReward.referral_attribution_id.in_(attribution_ids))
            ).all()
        )
        bonuses = [reward for reward in rewards if reward.reward_type == BONUS_TYPE]
        commissions = [reward for reward in rewards if reward.reward_type == COMMISSION_TYPE]
        volume: dict[str, Decimal] = {}
        bonus_totals: dict[str, Decimal] = {}
        for bonus in bonuses:
            currency = bonus.qualifying_currency or ""
            volume[currency] = volume.get(currency, Decimal("0")) + _money(bonus.qualifying_amount)
            unit = bonus.reward_unit or ""
            bonus_totals[unit] = bonus_totals.get(unit, Decimal("0")) + _coin(bonus.reward_amount)
        commission_status: dict[str, dict[str, Decimal]] = {}
        for reward in commissions:
            currency = reward.qualifying_currency or ""
            bucket = commission_status.setdefault(reward.status.value, {})
            bucket[currency] = bucket.get(currency, Decimal("0")) + _money(reward.reward_amount)
        registrations = len(attributions)
        deposits = len(bonuses)
        fraud_query = select(func.count()).select_from(ReferralFlag).where(ReferralFlag.status == "open")
        if partner_id is not None:
            fraud_query = fraud_query.where(
                ReferralFlag.subject_kind == "referral_partner",
                ReferralFlag.subject_id == partner_id,
            )
        return {
            "clicks": clicks,
            "registrations": registrations,
            "conversion_rate": format((Decimal(deposits) / Decimal(registrations)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP), "f") if registrations else "0.0000",
            "first_deposits": deposits,
            "qualifying_volume": {currency: format(_money(amount), "f") for currency, amount in volume.items()},
            "user_bonuses": {unit: format(_coin(amount), "f") for unit, amount in bonus_totals.items()},
            "commissions": {
                status: {currency: format(_money(amount), "f") for currency, amount in amounts.items()}
                for status, amounts in commission_status.items()
            },
            "pending_commissions": self._status_total(commissions, ReferralRewardStatus.PENDING),
            "approved_commissions": self._status_total(commissions, ReferralRewardStatus.APPROVED),
            "paid_commissions": self._status_total(commissions, ReferralRewardStatus.PAID),
            "reversed_commissions": self._status_total(commissions, ReferralRewardStatus.REVERSED),
            "blocked_commissions": self._status_total(commissions, ReferralRewardStatus.BLOCKED),
            "fraud_flags": int(self.session.scalar(fraud_query) or 0),
        }

    def _status_total(self, rewards: list[ReferralReward], status: ReferralRewardStatus) -> dict[str, str]:
        totals: dict[str, Decimal] = {}
        for reward in rewards:
            if reward.status != status:
                continue
            currency = reward.qualifying_currency or ""
            totals[currency] = totals.get(currency, Decimal("0")) + _money(reward.reward_amount)
        return {currency: format(amount, "f") for currency, amount in totals.items()}

    def _partner_share_ids(self, partner_id: str) -> list[str]:
        return list(
            self.session.scalars(select(ShareCode.id).where(ShareCode.referral_partner_id == partner_id)).all()
        )

    def _partner_or_raise(self, partner_id: str) -> ReferralPartner:
        partner = self.session.get(ReferralPartner, partner_id)
        if partner is None:
            raise FirstDepositReferralError("partner_not_found", "Referral partner not found.")
        return partner

    def _normalize_code(self, code: str | None) -> str:
        candidate = "".join(str(code or "").strip().upper().split())
        if len(candidate) < 4 or len(candidate) > 16 or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for character in candidate):
            raise FirstDepositReferralError("referral_code_invalid", "This referral code is not recognised.")
        return candidate

    def _ensure_code_available(self, code: str) -> None:
        existing = self.session.scalar(
            select(ShareCode.id).where(
                or_(func.lower(ShareCode.code) == code.lower(), func.lower(ShareCode.vanity_code) == code.lower())
            )
        )
        if existing is not None:
            raise FirstDepositReferralError("code_taken", "That referral code is already in use.")

    def _generate_code(self) -> str:
        for _ in range(20):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
            try:
                self._ensure_code_available(code)
            except FirstDepositReferralError:
                continue
            return code
        raise FirstDepositReferralError("code_generation_failed", "Could not generate a unique referral code.")

    def _bps(self, value: Any) -> int:
        bps = int(value)
        if bps < 0 or bps > 5000:
            raise FirstDepositReferralError("invalid_rate", "Rates must be between 0 and 50 percent.")
        return bps

    def _audit(
        self,
        actor: User | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        reason: str | None,
        payload: dict[str, Any],
    ) -> None:
        self.session.add(
            ReferralAdminAudit(
                actor_user_id=actor.id if actor else None,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                reason=(reason or None),
                payload_json=_jsonable(payload),
            )
        )
        self.session.flush()

    def _settings_view(self, settings: ReferralProgrammeSettings) -> dict[str, Any]:
        return {
            "is_active": settings.is_active,
            "user_bonus_bps": settings.user_bonus_bps,
            "referrer_commission_bps": settings.referrer_commission_bps,
            "user_bonus_percent": format(Decimal(settings.user_bonus_bps) / Decimal(100), "f"),
            "referrer_commission_percent": format(Decimal(settings.referrer_commission_bps) / Decimal(100), "f"),
            "hold_days": settings.hold_days,
            "payout_weekday": settings.payout_weekday,
            "min_payout_thresholds": dict(settings.min_payout_thresholds_json or {}),
            "eligible_account_types": list(settings.eligible_account_types_json or []),
            "qualifying_deposit_types": list(settings.qualifying_deposit_types_json or []),
            "version": settings.version,
            "explanation": bonus_explanation(settings.user_bonus_bps),
        }

    def _partner_view(self, partner: ReferralPartner, *, include_private: bool) -> dict[str, Any]:
        campaigns = [
            self._campaign_view(campaign)
            for campaign in self.session.scalars(
                select(ReferralCampaign).where(ReferralCampaign.partner_id == partner.id)
            ).all()
        ]
        view = {
            "id": partner.id,
            "display_name": partner.display_name,
            "social_handle": partner.social_handle,
            "status": partner.status,
            "owner_user_id": partner.owner_user_id,
            "creator_profile_id": partner.creator_profile_id,
            "campaigns": campaigns,
        }
        if include_private:
            view.update({
                "contact_email": partner.contact_email,
                "notes": partner.notes,
                "contractual_terms": partner.contractual_terms,
                "payout_destination_label": partner.payout_destination_label,
                "payout_currency": partner.payout_currency,
            })
        return view

    def _campaign_view(self, campaign: ReferralCampaign) -> dict[str, Any]:
        share = self.session.get(ShareCode, campaign.share_code_id)
        code = share.code if share else None
        return {
            "id": campaign.id,
            "partner_id": campaign.partner_id,
            "name": campaign.name,
            "status": campaign.status,
            "code": code,
            "link": referral_link(code) if code else campaign.public_link,
            "starts_at": campaign.starts_at.isoformat() if campaign.starts_at else None,
            "ends_at": campaign.ends_at.isoformat() if campaign.ends_at else None,
            "max_registrations": campaign.max_registrations,
            "current_uses": share.current_uses if share else 0,
            "active": bool(share and share.is_active and campaign.status == "active"),
        }

    def _reward_view(self, reward: ReferralReward) -> dict[str, Any]:
        payload = reward.reward_payload_json or {}
        return {
            "id": reward.id,
            "type": reward.reward_type.value,
            "status": reward.status.value,
            "referred_user_id": reward.referred_user_id,
            "beneficiary_user_id": reward.beneficiary_user_id,
            "partner_id": reward.referral_partner_id,
            "attribution_id": reward.referral_attribution_id,
            "share_code_id": payload.get("share_code_id"),
            "qualifying_amount": format(_money(reward.qualifying_amount), "f") if reward.qualifying_amount is not None else None,
            "qualifying_currency": reward.qualifying_currency,
            "reward_amount": format(Decimal(reward.reward_amount), "f") if reward.reward_amount is not None else None,
            "reward_unit": reward.reward_unit,
            "applied_rate_bps": reward.applied_rate_bps,
            "policy_version": reward.policy_version,
            "deposit_kind": reward.deposit_kind,
            "deposit_id": reward.deposit_id,
            "payment_reference": payload.get("payment_reference"),
            "provider_reference": payload.get("provider_reference"),
            "purchase_order_id": payload.get("purchase_order_id"),
            "gross_fiat": payload.get("gross_fiat"),
            "wallet_credit": payload.get("wallet_credit"),
            "rate_value": payload.get("rate_value"),
            "rate_direction": payload.get("rate_direction"),
            "hold_until": reward.hold_until.isoformat() if reward.hold_until else None,
            "approved_at": reward.approved_at.isoformat() if reward.approved_at else None,
            "paid_at": reward.paid_at.isoformat() if reward.paid_at else None,
            "reversed_at": reward.reversed_at.isoformat() if reward.reversed_at else None,
            "blocked_at": reward.blocked_at.isoformat() if reward.blocked_at else None,
            "review_reason": reward.review_reason,
            "payment_reference_recorded": reward.reward_reference,
            "ledger_transaction_id": payload.get("ledger_transaction_id"),
            "shortfall_amount": payload.get("shortfall_amount"),
            "created_at": reward.created_at.isoformat() if reward.created_at else None,
        }

    def _attribution_admin_view(self, row: ReferralAttribution) -> dict[str, Any]:
        user = self.session.get(User, row.referred_user_id)
        share = self.session.get(ShareCode, row.share_code_id) if row.share_code_id else None
        rewards = list(
            self.session.scalars(select(ReferralReward).where(ReferralReward.referral_attribution_id == row.id)).all()
        )
        bonus = next((reward for reward in rewards if reward.reward_type == BONUS_TYPE), None)
        return {
            "id": row.id,
            "referred_user_id": row.referred_user_id,
            "referred_username": user.username if user else None,
            "account_type": row.account_type_snapshot,
            "referrer_user_id": row.referrer_user_id,
            "partner_id": row.referral_partner_id,
            "share_code": share.code if share else (row.metadata_json or {}).get("share_code"),
            "status": row.attribution_status,
            "locked_at": row.locked_at.isoformat() if row.locked_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "qualifying_amount": format(_money(bonus.qualifying_amount), "f") if bonus and bonus.qualifying_amount is not None else None,
            "qualifying_currency": bonus.qualifying_currency if bonus else None,
            "bonus_status": bonus.status.value if bonus else None,
            "commission_status": next((reward.status.value for reward in rewards if reward.reward_type == COMMISSION_TYPE), None),
        }

    def _batch_view(self, batch: ReferralPayoutBatch) -> dict[str, Any]:
        items = list(self.session.scalars(select(ReferralPayoutItem).where(ReferralPayoutItem.batch_id == batch.id)).all())
        return {
            "id": batch.id,
            "status": batch.status,
            "payout_method": batch.payout_method,
            "beneficiary_user_id": batch.beneficiary_user_id,
            "beneficiary_partner_id": batch.beneficiary_partner_id,
            "currency": batch.currency_code,
            "total": format(_money(batch.total_amount), "f"),
            "destination_label": batch.destination_label,
            "external_reference": batch.external_reference,
            "ledger_transaction_id": batch.ledger_transaction_id,
            "confirmed_at": batch.confirmed_at.isoformat() if batch.confirmed_at else None,
            "reward_ids": [item.reward_id for item in items],
            "transferred_by_gtex": batch.payout_method == "internal_wallet" and batch.status == "confirmed",
        }

    def _attributions_for_owner(
        self, user_id: str, partner_id: str | None, share_ids: list[str]
    ) -> list[ReferralAttribution]:
        filters = [ReferralAttribution.referrer_user_id == user_id]
        if partner_id:
            filters.append(ReferralAttribution.referral_partner_id == partner_id)
        if share_ids:
            filters.append(ReferralAttribution.share_code_id.in_(share_ids))
        return list(self.session.scalars(select(ReferralAttribution).where(or_(*filters))).all())

    def _rewards_for_attributions(self, attributions: list[ReferralAttribution], reward_type: ReferralRewardType) -> list[ReferralReward]:
        ids = [row.id for row in attributions]
        if not ids:
            return []
        return list(
            self.session.scalars(
                select(ReferralReward).where(
                    ReferralReward.referral_attribution_id.in_(ids),
                    ReferralReward.reward_type == reward_type,
                )
            ).all()
        )

    def _owner_commissions(self, user_id: str, partner_id: str | None) -> list[ReferralReward]:
        filters = [ReferralReward.beneficiary_user_id == user_id]
        if partner_id:
            filters.append(ReferralReward.referral_partner_id == partner_id)
        return list(
            self.session.scalars(
                select(ReferralReward).where(ReferralReward.reward_type == COMMISSION_TYPE, or_(*filters))
            ).all()
        )

    def _owner_batches(self, user_id: str, partner_id: str | None) -> list[ReferralPayoutBatch]:
        filters = [ReferralPayoutBatch.beneficiary_user_id == user_id]
        if partner_id:
            filters.append(ReferralPayoutBatch.beneficiary_partner_id == partner_id)
        return list(
            self.session.scalars(select(ReferralPayoutBatch).where(or_(*filters)).order_by(ReferralPayoutBatch.created_at.desc())).all()
        )
