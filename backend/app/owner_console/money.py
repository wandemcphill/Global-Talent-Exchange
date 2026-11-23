from __future__ import annotations

import os
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.club_profile import ClubProfile
from app.owner_console import ledger
from app.wallets.service import COIN_TO_CREDIT_RATE
from app.owner_console.models import (
    LedgerEvent,
    OwnerDepositIntent,
    OwnerSquadPlayer,
    OwnerWithdrawal,
    RelatedPartyTransfer,
    SupportUnitHolding,
)
from app.owner_console.service import (
    OwnerError,
    get_state,
    integrity_score,
    now,
    open_high_flags,
    raise_flag,
    require_state,
)

GIFTS = {
    "stadium_roar": {"name": "Stadium Roar", "cost": 10, "tier": "common"},
    "captains_armband": {"name": "Captain's Armband", "cost": 20, "tier": "rare"},
    "home_end_banner": {"name": "Home End Banner", "cost": 30, "tier": "rare"},
    "golden_boot": {"name": "Golden Boot", "cost": 50, "tier": "epic"},
    "floodlights": {"name": "Floodlights", "cost": 100, "tier": "epic"},
    "legendary_stadium": {"name": "Legendary Stadium", "cost": 1000, "tier": "legendary"},
}
GIFT_PLATFORM_BPS = 3000
SUPPORT_UNIT_PRICE = 100
SUPPORT_TIERS = (
    (
        50,
        "Founders' Circle",
        ["Vote on club kit & anthem polls", "Supporter-only competitions", "Name on the Founders' Wall"],
    ),
    (10, "Patron", ["Supporter-only competitions", "Patron badge on club page"]),
    (1, "Supporter", ["Supporter badge", "Club supporter leaderboard"]),
)
FAN_COIN_PER_GTEX = COIN_TO_CREDIT_RATE


def treasury_rates(session: Session) -> dict[str, Any]:
    """Admin-controlled NGN rates from the repo's TreasurySettings (single source for fiat conversion)."""
    from app.treasury.service import TreasuryService

    s = TreasuryService().ensure_settings(session)
    return {
        "deposit_rate": Decimal(s.deposit_rate_value),
        "deposit_direction": str(getattr(s.deposit_rate_direction, "value", s.deposit_rate_direction)),
        "withdrawal_rate": Decimal(s.withdrawal_rate_value),
        "withdrawal_direction": str(getattr(s.withdrawal_rate_direction, "value", s.withdrawal_rate_direction)),
        "fan_coin_deposit_rate": Decimal(s.fan_coin_deposit_rate_value),
        "trader_withdrawal_rate": Decimal(s.trader_withdrawal_rate_value),
    }


def fiat_to_coin(fiat: Decimal, rate: Decimal, direction: str) -> Decimal:
    return ledger.D(fiat / rate if direction == "fiat_per_coin" else fiat * rate)


def coin_to_fiat(coin: Decimal, rate: Decimal, direction: str) -> Decimal:
    return ledger.D(coin * rate if direction == "fiat_per_coin" else coin / rate)


def display_rates(session: Session) -> dict[str, str]:
    """Naira value of one GTEX Coin and one Fan Coin, from the treasury deposit rate."""
    rates = treasury_rates(session)
    per_gtex = coin_to_fiat(Decimal("1"), rates["deposit_rate"], rates["deposit_direction"])
    per_fan = ledger.D(rates["fan_coin_deposit_rate"])
    return {
        "naira_per_gtex": str(per_gtex),
        "naira_per_fan": str(per_fan),
        "fan_coin_per_gtex": str(FAN_COIN_PER_GTEX),
    }


SISTER_CAPITAL_CAP_BPS = 2500
FAIR_BAND = (Decimal("0.8"), Decimal("1.3"))
RECIPROCAL_COOLDOWN = timedelta(days=14)


def paystack_secret() -> str | None:
    for name in ("GTE_PAYSTACK_SECRET_KEY", "PAYSTACK_SECRET_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def _secret() -> str:
    value = paystack_secret()
    if not value:
        raise OwnerError("paystack_secret_key_not_configured", 503)
    return value


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise OwnerError(f"{name.lower()}_not_configured", 503)
    return value


# ---------- withdrawals ----------


def withdrawal_eligibility(session: Session, user, amount: Decimal) -> dict[str, Any]:
    classes = ledger.wallet_classes(session, user.id)
    countries = {c.strip().upper() for c in _env("GTEX_WITHDRAWAL_COUNTRIES").split(",")}
    kyc_threshold = Decimal(_env("GTEX_KYC_THRESHOLD_COIN"))
    min_score = int(_env("GTEX_WITHDRAWAL_MIN_INTEGRITY"))
    club_countries = {
        (c.country_code or "").upper()
        for c in session.scalars(select(ClubProfile).where(ClubProfile.owner_user_id == user.id)).all()
    }
    score = integrity_score(session, user.id)
    kyc = str(getattr(user.kyc_status, "value", user.kyc_status))
    checks = {
        "country_supported": bool(club_countries & countries),
        "withdrawable_balance": Decimal(classes["withdrawable"]) >= amount,
        "kyc_ok": amount <= kyc_threshold or kyc == "verified",
        "integrity_ok": score >= min_score,
        "no_open_high_flags": open_high_flags(session, user.id) == 0,
    }
    return {
        "checks": checks,
        "eligible": all(checks.values()),
        "integrity_score": score,
        "kyc_status": kyc,
        "kyc_threshold": str(kyc_threshold),
        "withdrawable": classes["withdrawable"],
        "supported_countries": sorted(countries),
    }


def request_withdrawal(session: Session, user, payload: dict[str, Any]) -> OwnerWithdrawal:
    amount = ledger.D(payload["amount_coin"])
    if amount <= 0:
        raise OwnerError("amount_must_be_positive")
    result = withdrawal_eligibility(session, user, amount)
    if not result["eligible"]:
        raise OwnerError("withdrawal_not_eligible", 403, result)
    from app.treasury.service import TreasuryService

    treasury_service = TreasuryService()
    settings = treasury_service.ensure_settings(session)
    withdrawal_rate, withdrawal_direction = treasury_service.withdrawal_rate_for_user(settings, user)
    withdrawal_direction_value = str(getattr(withdrawal_direction, "value", withdrawal_direction))
    account_age_days = (
        now() - (user.created_at if user.created_at.tzinfo else user.created_at.replace(tzinfo=now().tzinfo))
    ).days
    risk = {"new_account": account_age_days < 7, "large_amount": amount > Decimal(result["kyc_threshold"])}
    withdrawal = OwnerWithdrawal(
        user_id=user.id,
        amount_coin=amount,
        amount_ngn=coin_to_fiat(amount, withdrawal_rate, withdrawal_direction_value),
        bank_name=payload["bank_name"],
        account_number=payload["account_number"],
        account_name=payload["account_name"],
        checks_json={**result, "risk": risk},
    )
    session.add(withdrawal)
    session.flush()
    event = ledger.record(
        session,
        event_type="withdrawal",
        source=ledger.user_account(user.id),
        destination=ledger.BANK_OUT,
        currency=ledger.GTEX,
        gross=amount,
        status="pending_review",
        user_id=user.id,
        related_type="withdrawal",
        related_id=withdrawal.id,
        memo=f"Withdrawal to {payload['bank_name']} ****{payload['account_number'][-4:]}",
        check_funds=False,
    )
    withdrawal.ledger_event_id = event.id
    session.flush()
    return withdrawal


def review_withdrawal(session: Session, admin, withdrawal_id: str, decision: str, note: str | None) -> OwnerWithdrawal:
    w = session.get(OwnerWithdrawal, withdrawal_id)
    if w is None:
        raise OwnerError("withdrawal_not_found", 404)
    if w.status not in ("pending_review", "held"):
        raise OwnerError("withdrawal_already_reviewed", 409)
    event = session.get(LedgerEvent, w.ledger_event_id)
    mapping = {"approve": ("approved", "completed"), "reject": ("rejected", "reversed"), "hold": ("held", "held")}
    if decision not in mapping:
        raise OwnerError("invalid_decision")
    w.status = mapping[decision][0]
    ledger.transition(session, event, mapping[decision][1])
    w.review_note, w.reviewed_by, w.reviewed_at = note, admin.id, now()
    session.flush()
    return w


def withdrawal_dict(w: OwnerWithdrawal) -> dict[str, Any]:
    return {
        "id": w.id,
        "user_id": w.user_id,
        "amount_coin": str(w.amount_coin),
        "amount_ngn": str(w.amount_ngn),
        "bank_name": w.bank_name,
        "account_last4": w.account_number[-4:],
        "account_name": w.account_name,
        "status": w.status,
        "checks": w.checks_json,
        "review_note": w.review_note,
        "created_at": w.created_at.isoformat(),
        "reviewed_at": w.reviewed_at.isoformat() if w.reviewed_at else None,
    }


def release_payout(session: Session, ledger_event_id: str) -> LedgerEvent:
    event = session.get(LedgerEvent, ledger_event_id)
    if event is None or event.status != "held" or event.event_type == "withdrawal":
        raise OwnerError("payout_not_held", 409)
    return ledger.transition(session, event, "completed")


# ---------- Paystack deposits ----------


SUPPORTED_DEPOSIT_PROVIDERS = {"paystack", "korapay"}


def _deposit_product(reference: str | None) -> str:
    return "fan" if str(reference or "").startswith("fan_") else "gtex"


def paystack_init(
    session: Session,
    user,
    amount_ngn: int,
    callback_url: str,
    provider: str = "paystack",
    currency: str = "gtex",
) -> dict[str, Any]:
    from app.wallets.providers.registry import get_live_provider_adapter

    provider = str(provider or "paystack").strip().lower()
    if provider not in SUPPORTED_DEPOSIT_PROVIDERS:
        raise OwnerError("unsupported_deposit_provider", 400)
    if amount_ngn < 100:
        raise OwnerError("minimum_deposit_100_ngn")
    product = "fan" if str(currency or "gtex").strip().lower() in {"fan", "fan_coin"} else "gtex"
    reference = f"{product}_{uuid.uuid4().hex[:18]}"
    product_name = "Fan Coin" if product == "fan" else "GTEX"
    try:
        adapter = get_live_provider_adapter(provider)
        checkout_session = adapter.initialize_checkout(
            order_reference=reference,
            amount=Decimal(str(amount_ngn)),
            currency="NGN",
            customer_email=user.email,
            customer_name=user.full_name or user.username or user.email,
            callback_url=callback_url,
            metadata={"user_id": user.id, "product": f"{product}_coin", "provider": provider},
            narration=f"{product_name} {reference}",
        )
        session.add(
            OwnerDepositIntent(
                provider=provider,
                reference=reference,
                user_id=user.id,
                requested_amount_ngn=Decimal(str(amount_ngn)),
                status="pending",
            )
        )
        session.flush()
        return {"authorization_url": checkout_session.checkout_url, "reference": reference}
    except Exception as exc:
        raise OwnerError(f"{provider}_init_failed", 502, str(exc)) from exc


def _load_deposit_intent(session: Session, provider: str | None, reference: str) -> OwnerDepositIntent | None:
    statement = select(OwnerDepositIntent).where(OwnerDepositIntent.reference == reference)
    if provider is not None:
        statement = statement.where(OwnerDepositIntent.provider == provider)
    else:
        statement = statement.order_by(OwnerDepositIntent.created_at.desc())
    bind = session.get_bind()
    if bind is not None and bind.dialect.name != "sqlite":
        statement = statement.with_for_update()
    return session.scalar(statement)


def _deposit_wallet_key(provider: str, reference: str) -> str:
    return f"oc:deposit:{provider}:{reference}:settle"


def _credit_deposit(session: Session, intent: OwnerDepositIntent, amount_kobo: int, provider: str) -> LedgerEvent:
    """Credit the initiating user once. Amount is the provider figure, not the client quote."""
    session.refresh(intent)
    if intent.status == "credited" and intent.ledger_event_id:
        existing = session.get(LedgerEvent, intent.ledger_event_id)
        if existing is not None:
            return existing
    existing = session.scalar(
        select(LedgerEvent).where(
            LedgerEvent.related_object_type == provider,
            LedgerEvent.related_object_id == intent.reference,
            LedgerEvent.event_type == "deposit",
            LedgerEvent.user_id == intent.user_id,
        )
    )
    if existing is not None:
        intent.status = "credited"
        intent.ledger_event_id = existing.id
        session.flush()
        return existing
    if amount_kobo <= 0:
        raise OwnerError("deposit_amount_missing", 400)
    claimed = session.execute(
        update(OwnerDepositIntent)
        .where(OwnerDepositIntent.id == intent.id, OwnerDepositIntent.status == "pending")
        .values(status="crediting")
    )
    if claimed.rowcount != 1:
        session.refresh(intent)
        if intent.ledger_event_id:
            existing = session.get(LedgerEvent, intent.ledger_event_id)
            if existing is not None:
                return existing
        raise OwnerError("deposit_already_processing", 409)
    ngn = Decimal(amount_kobo) / Decimal(100)
    rates = treasury_rates(session)
    product = _deposit_product(intent.reference)
    if product == "fan":
        fan_rate = ledger.D(rates["fan_coin_deposit_rate"])
        if fan_rate <= 0:
            raise OwnerError("fan_deposit_rate_missing", 500, "Fan Coin does not have a naira rate yet.")
        coins = fiat_to_coin(ngn, fan_rate, "fiat_per_coin")
        currency = ledger.FAN
        balance_class = "non_withdrawable"
        memo = f"Fan Coin {provider.title()} deposit NGN {ngn:,.2f}"
    else:
        coins = fiat_to_coin(ngn, rates["deposit_rate"], rates["deposit_direction"])
        currency = ledger.GTEX
        balance_class = "deposited"
        memo = f"GTEX {provider.title()} deposit NGN {ngn:,.2f}"
        rate_value = Decimal(str(rates["deposit_rate"]))
        rate_direction = rates["deposit_direction"]
    event = ledger.record(
        session,
        event_type="deposit",
        source=f"platform:{provider}",
        destination=ledger.user_account(intent.user_id),
        currency=currency,
        gross=coins,
        balance_class=balance_class,
        user_id=intent.user_id,
        related_type=provider,
        related_id=intent.reference,
        memo=memo,
        wallet_idempotency_key=_deposit_wallet_key(provider, intent.reference),
    )
    intent.status = "credited"
    intent.ledger_event_id = event.id
    intent.credited_amount_kobo = amount_kobo
    session.flush()
    if product == "gtex":
        from app.services.first_deposit_referral_service import FirstDepositReferralService

        FirstDepositReferralService(session).on_owner_deposit_credited(
            intent,
            fiat_amount=ngn,
            rate_value=rate_value,
            rate_direction=rate_direction,
            wallet_credit=coins,
        )
    return event


def _verification_amount_kobo(verification: Any) -> int:
    amount = getattr(verification, "amount_paid", None)
    if amount is None:
        amount = getattr(verification, "amount", None)
    if amount is None:
        return 0
    return int((Decimal(str(amount)) * Decimal(100)).to_integral_value())


def _verification_succeeded(verification: Any) -> bool:
    if bool(getattr(verification, "is_successful", False)):
        return True
    return str(getattr(verification, "status", "") or "").strip().lower() == "success"


def paystack_verify(session: Session, user, reference: str, provider: str | None = None) -> dict[str, Any]:
    from app.wallets.providers.registry import get_provider_adapter

    if provider is not None:
        provider = str(provider).strip().lower()
        if provider not in SUPPORTED_DEPOSIT_PROVIDERS:
            raise OwnerError("unsupported_deposit_provider", 400)
    intent = _load_deposit_intent(session, provider, reference)
    if intent is None:
        raise OwnerError("deposit_not_found", 404)
    if intent.user_id != user.id:
        raise OwnerError("deposit_user_conflict", 409)
    resolved_provider = intent.provider
    if resolved_provider not in SUPPORTED_DEPOSIT_PROVIDERS:
        raise OwnerError("unsupported_deposit_provider", 400)
    if intent.status == "credited" and intent.ledger_event_id:
        existing = session.get(LedgerEvent, intent.ledger_event_id)
        if existing is not None:
            return {"status": "success", "ledger_event": ledger.serialize(existing)}
    try:
        adapter = get_provider_adapter(resolved_provider)
        verification = adapter.verify_payment(reference=reference)
    except Exception as exc:
        return {"status": "failed", "message": str(exc)}
    if not _verification_succeeded(verification):
        message = getattr(verification, "gateway_response", None) or "Payment not verified"
        return {"status": "failed", "message": message}
    event = _credit_deposit(session, intent, _verification_amount_kobo(verification), resolved_provider)
    return {"status": "success", "ledger_event": ledger.serialize(event)}


def paystack_webhook(session: Session, raw: bytes, signature: str | None, event: dict[str, Any]) -> None:
    from app.wallets.providers.registry import get_provider_adapter

    adapter = get_provider_adapter("paystack")
    try:
        signature_ok = adapter.verify_webhook_signature(
            payload=event, raw_body=raw, headers={"x-paystack-signature": signature or ""}
        )
    except Exception as exc:
        raise OwnerError("invalid_signature", 401) from exc
    if not signature_ok:
        raise OwnerError("invalid_signature", 401)
    if event.get("event") != "charge.success":
        return
    tx = event.get("data") or {}
    reference = tx.get("reference")
    if not reference:
        raise OwnerError("deposit_reference_missing", 400)
    intent = _load_deposit_intent(session, "paystack", str(reference))
    if intent is None:
        raise OwnerError("deposit_not_found", 404)
    # Credit the user who started checkout. Webhook metadata is not an authority.
    _credit_deposit(session, intent, int(tx.get("amount") or 0), "paystack")


def korapay_webhook(session: Session, raw: bytes, signature: str | None, event: dict[str, Any]) -> None:
    from app.wallets.providers.base import ProviderEventType
    from app.wallets.providers.registry import get_provider_adapter

    adapter = get_provider_adapter("korapay")
    try:
        signature_ok = adapter.verify_webhook_signature(
            payload=event, raw_body=raw, headers={"x-korapay-signature": signature or ""}
        )
    except Exception as exc:
        raise OwnerError("invalid_signature", 401) from exc
    if not signature_ok:
        raise OwnerError("invalid_signature", 401)

    parsed = adapter.parse_webhook(event, headers={"x-korapay-signature": signature or ""})
    if parsed is None or parsed.is_payout or parsed.event_type != ProviderEventType.SETTLED:
        return
    if parsed.currency and parsed.currency.upper() != "NGN":
        raise OwnerError("unsupported_currency", 400)

    candidates = [ref for ref in (parsed.provider_reference, parsed.purchase_order_reference) if ref]
    if not candidates:
        raise OwnerError("deposit_reference_missing", 400)

    intent: OwnerDepositIntent | None = None
    for candidate_ref in candidates:
        intent = _load_deposit_intent(session, "korapay", str(candidate_ref))
        if intent is not None:
            break
    if intent is None:
        raise OwnerError("deposit_not_found", 404)

    if parsed.amount is None:
        raise OwnerError("deposit_amount_missing", 400)
    amount_kobo = int((Decimal(str(parsed.amount)) * Decimal(100)).to_integral_value())
    _credit_deposit(session, intent, amount_kobo, "korapay")


# ---------- capital moves ----------


def inject_capital(session: Session, user_id: str, club_id: str, amount, currency: str = "GTEX") -> LedgerEvent:
    require_state(session, club_id, user_id)
    gross_amount = ledger.D(amount)
    if gross_amount <= 0:
        raise OwnerError("amount_must_be_positive", 400)

    unit = ledger.FAN if str(currency or "GTEX").upper() in {"FAN", "FAN_COIN"} else ledger.GTEX
    user_acct = ledger.user_account(user_id)
    if unit == ledger.FAN:
        user_fan = ledger.balance(session, user_acct, ledger.FAN)
        if user_fan < gross_amount:
            raise OwnerError("insufficient_funds", 402, "Your wallet does not have enough Fan Coin for this transfer.")
        try:
            return ledger.record(
                session,
                event_type="owner_capital_injection",
                source=user_acct,
                destination=ledger.club_account(club_id),
                currency=ledger.FAN,
                gross=gross_amount,
                balance_class="earned",
                club_id=club_id,
                user_id=user_id,
                related_type="club",
                related_id=club_id,
                memo="Owner moved Fan Coin from the personal wallet into the club treasury",
            )
        except ledger.LedgerError as exc:
            raise OwnerError(str(exc), 402) from exc

    user_total = ledger.balance(session, user_acct, ledger.GTEX)
    if user_total < gross_amount:
        raise OwnerError("insufficient_funds", 402)

    # An explicit wallet top-up is purchase capital. Regens, legends, and
    # players at GSI 75 or above can only be signed with deposited coin.
    try:
        return ledger.record(
            session,
            event_type="owner_capital_injection",
            source=user_acct,
            destination=ledger.club_account(club_id),
            currency=ledger.GTEX,
            gross=gross_amount,
            balance_class="deposited",
            club_id=club_id,
            user_id=user_id,
            related_type="club",
            related_id=club_id,
            memo="Owner moved GTEX Coin from the personal wallet into the club treasury",
        )
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc


def distributable(session: Session, club_id: str) -> Decimal:
    acct = ledger.club_account(club_id)
    earned = session.scalar(
        select(func.coalesce(func.sum(LedgerEvent.net_amount), 0)).where(
            LedgerEvent.destination_account == acct,
            LedgerEvent.currency == ledger.GTEX,
            LedgerEvent.status == "completed",
            LedgerEvent.event_type.in_(
                ("gate_receipts", "competition_prize", "sponsor_revenue", "endorsement_revenue", "transfer_sale")
            ),
        )
    )
    paid = session.scalar(
        select(func.coalesce(func.sum(LedgerEvent.gross_amount), 0)).where(
            LedgerEvent.source_account == acct,
            LedgerEvent.event_type == "owner_distribution",
            LedgerEvent.status == "completed",
        )
    )
    cash = ledger.balance(session, acct, ledger.GTEX)
    return max(Decimal("0"), min(ledger.D(earned or 0) - ledger.D(paid or 0), cash))


def distribute_to_owner(session: Session, user_id: str, club_id: str, amount) -> LedgerEvent:
    require_state(session, club_id, user_id)
    amount = ledger.D(amount)
    limit = distributable(session, club_id)
    if amount > limit:
        raise OwnerError(
            "exceeds_distributable_earnings",
            409,
            f"Only earned club revenue can be distributed (max {limit}). Launch grants and capital injections stay in the club.",
        )
    return ledger.record(
        session,
        event_type="owner_distribution",
        source=ledger.club_account(club_id),
        destination=ledger.user_account(user_id),
        currency=ledger.GTEX,
        gross=amount,
        balance_class="earned",
        club_id=club_id,
        user_id=user_id,
        related_type="club",
        related_id=club_id,
        memo="Owner distribution from earned club revenue",
    )


def sister_capital(session: Session, user_id: str, from_club: str, to_club: str, amount) -> LedgerEvent:
    if from_club == to_club:
        raise OwnerError("same_club")
    require_state(session, from_club, user_id)
    require_state(session, to_club, user_id)
    amount = ledger.D(amount)
    cap = ledger.D(ledger.spendable_club_balance(session, from_club) * Decimal(SISTER_CAPITAL_CAP_BPS) / 10000)
    if amount > cap:
        raise OwnerError(
            "sister_capital_cap_exceeded", 409, f"Inter-club moves are capped at 25% of the source club's cash ({cap})."
        )
    return ledger.record(
        session,
        event_type="sister_club_capital",
        source=ledger.club_account(from_club),
        destination=ledger.club_account(to_club),
        currency=ledger.GTEX,
        gross=amount,
        club_id=to_club,
        user_id=user_id,
        related_type="club",
        related_id=from_club,
        memo="Disclosed related-party capital move",
    )


# ---------- related-party transfer ----------


def check_internal_transfer(session: Session, user_id: str, player_id: str, to_club: str, fee) -> dict[str, Any]:
    player = session.get(OwnerSquadPlayer, player_id)
    if player is None or player.status not in ("active", "listed"):
        raise OwnerError("player_not_found", 404)
    require_state(session, player.club_id, user_id)
    require_state(session, to_club, user_id)
    if player.club_id == to_club:
        raise OwnerError("same_club")
    fee = ledger.D(fee)
    value = Decimal(player.value_coin)
    low, high = ledger.D(value * FAIR_BAND[0]), ledger.D(value * FAIR_BAND[1])
    reciprocal = session.scalar(
        select(RelatedPartyTransfer).where(
            RelatedPartyTransfer.from_club_id == to_club,
            RelatedPartyTransfer.to_club_id == player.club_id,
            RelatedPartyTransfer.created_at >= now() - RECIPROCAL_COOLDOWN,
        )
    )
    recent = (
        session.scalar(
            select(func.count())
            .select_from(RelatedPartyTransfer)
            .where(
                RelatedPartyTransfer.owner_user_id == user_id,
                RelatedPartyTransfer.created_at >= now() - timedelta(days=30),
            )
        )
        or 0
    )
    rules = {
        "no_free_transfer": fee > 0,
        "within_fair_value_band": low <= fee <= high,
        "reciprocal_cooldown_clear": reciprocal is None,
    }
    return {
        "rules": rules,
        "allowed": all(rules.values()),
        "fair_value": str(value),
        "band": [str(low), str(high)],
        "recent_related_moves": int(recent),
        "shuffle_flag_risk": recent >= 2,
        "player": player,
        "fee": fee,
    }


def internal_transfer(session: Session, user_id: str, player_id: str, to_club: str, fee) -> dict[str, Any]:
    check = check_internal_transfer(session, user_id, player_id, to_club, fee)
    if not check["allowed"]:
        raise OwnerError("related_party_transfer_blocked", 409, {k: v for k, v in check.items() if k != "player"})
    player: OwnerSquadPlayer = check["player"]
    from_club = player.club_id
    try:
        ledger.record(
            session,
            event_type="related_party_transfer",
            source=ledger.club_account(to_club),
            destination=ledger.club_account(from_club),
            currency=ledger.GTEX,
            gross=check["fee"],
            fee_bps=ledger.TRANSFER_PLATFORM_FEE_BPS,
            club_id=from_club,
            user_id=user_id,
            related_type="player",
            related_id=player.id,
            memo=f"Related-party transfer: {player.name}",
        )
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    session.add(
        RelatedPartyTransfer(
            owner_user_id=user_id,
            from_club_id=from_club,
            to_club_id=to_club,
            player_name=player.name,
            player_ref=player.player_ref,
            fair_value=Decimal(check["fair_value"]),
            fee=check["fee"],
        )
    )
    seller_state = get_state(session, from_club)
    if seller_state is not None:
        from app.owner_console.service import _drop_from_filed_selection

        _drop_from_filed_selection(seller_state, str(player.id))
    player.club_id = to_club
    player.morale = max(0, player.morale - 5)
    notes = ["Disclosed in both clubs' history."]
    if check["shuffle_flag_risk"]:
        player.morale = max(0, player.morale - 15)
        raise_flag(
            session,
            user_id,
            from_club,
            "asset_shuffling",
            "medium",
            f"{check['recent_related_moves'] + 1} related-party moves in 30 days.",
            10,
            player.id,
        )
        notes.append("Repeated asset shuffling flagged; player morale -15.")
    session.flush()
    return {
        "player_id": player.id,
        "from_club_id": from_club,
        "to_club_id": to_club,
        "fee": str(check["fee"]),
        "notes": notes,
    }


# ---------- fan economy ----------


def buy_fan_coin(session: Session, user_id: str, gtex_amount) -> dict[str, Any]:
    gtex_amount = ledger.D(gtex_amount)
    try:
        ledger.record(
            session,
            event_type="fan_coin_purchase",
            source=ledger.user_account(user_id),
            destination=ledger.GIFT_CONVERSION_BRIDGE,
            currency=ledger.GTEX,
            gross=gtex_amount,
            user_id=user_id,
            memo="Converted to Fan Coin",
        )
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    ledger.record(
        session,
        event_type="fan_coin_purchase",
        source=ledger.PLATFORM_GRANTS,
        destination=ledger.user_account(user_id),
        currency=ledger.FAN,
        gross=gtex_amount * FAN_COIN_PER_GTEX,
        balance_class="non_withdrawable",
        user_id=user_id,
        memo="Fan Coin (non-withdrawable)",
    )
    fan_out = ledger.D(gtex_amount * FAN_COIN_PER_GTEX)
    return {
        "fan_coin": str(fan_out),
        "gtex_spent": str(gtex_amount),
        "fan_coin_per_gtex": str(FAN_COIN_PER_GTEX),
        "destination": "wallet",
    }


def convert_club_gtex_to_fan(session: Session, user_id: str, club_id: str, gtex_amount) -> dict[str, Any]:
    """Turn deposited or earned club GTEX into club Fan Coin.

    The welcome squad grant stays reserved for player signings. Fan Coin lands
    on the club and can pay a staff contract. It is not withdrawable.
    """
    require_state(session, club_id, user_id)
    gtex_amount = ledger.D(gtex_amount)
    if gtex_amount <= 0:
        raise OwnerError("invalid_amount", 400)
    funding = ledger.get_club_funding(session, club_id)
    pools = (
        ("deposited", ledger.D(funding["available_deposited"])),
        ("earned", ledger.D(funding["available_earned"])),
    )
    spendable = pools[0][1] + pools[1][1]
    if spendable < gtex_amount:
        raise OwnerError(
            "fan_conversion_needs_spendable_coin",
            402,
            "Only deposited and earned club coins convert to Fan Coin. The welcome squad grant stays for player signings.",
        )
    remaining = gtex_amount
    for balance_class, available in pools:
        if remaining <= 0:
            break
        portion = min(available, remaining)
        if portion <= 0:
            continue
        try:
            ledger.record(
                session,
                event_type="fan_coin_purchase",
                source=ledger.club_account(club_id),
                destination=ledger.GIFT_CONVERSION_BRIDGE,
                currency=ledger.GTEX,
                gross=portion,
                balance_class=balance_class,
                club_id=club_id,
                user_id=user_id,
                memo="Club GTEX Coin converted to Fan Coin",
            )
        except ledger.LedgerError as exc:
            raise OwnerError(str(exc), 402) from exc
        remaining -= portion
    if remaining > 0:
        raise OwnerError(
            "fan_conversion_needs_spendable_coin",
            402,
            "The club treasury could not convert that much GTEX Coin.",
        )
    fan_out = ledger.D(gtex_amount * FAN_COIN_PER_GTEX)
    ledger.record(
        session,
        event_type="fan_coin_purchase",
        source=ledger.PLATFORM_GRANTS,
        destination=ledger.club_account(club_id),
        currency=ledger.FAN,
        gross=fan_out,
        balance_class="non_withdrawable",
        club_id=club_id,
        user_id=user_id,
        memo="Fan Coin from club GTEX conversion (non-withdrawable)",
    )
    return {
        "fan_coin": str(fan_out),
        "gtex_spent": str(gtex_amount),
        "fan_coin_per_gtex": str(FAN_COIN_PER_GTEX),
        "destination": "club",
    }


def send_gift(
    session: Session,
    user,
    club_id: str,
    gift_code: str,
    match_id: str | None = None,
    app: Any = None,
) -> dict[str, Any]:
    gift = GIFTS.get(gift_code)
    if gift is None:
        raise OwnerError("unknown_gift")
    if get_state(session, club_id) is None:
        raise OwnerError("club_not_found", 404)
    try:
        event = ledger.record(
            session,
            event_type="gift",
            source=ledger.user_account(user.id),
            destination=ledger.club_account(club_id),
            currency=ledger.FAN,
            gross=gift["cost"],
            fee_bps=GIFT_PLATFORM_BPS,
            club_id=club_id,
            user_id=user.id,
            related_type="match" if match_id else "club",
            related_id=match_id or club_id,
            memo=f"{gift['name']} from {user.username}",
        )
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    state = get_state(session, club_id)
    state.fans += max(1, gift["cost"] // 10)

    animation_map = {
        "stadium_roar": ("fan_chant", "crowd_roar"),
        "captains_armband": ("legend_card_reveal", "tactics_board_ping"),
        "home_end_banner": ("club_banner_unfurl", "anthem_trumpet"),
        "golden_boot": ("world_best_award", "stadium_award_roar"),
        "floodlights": ("stadium_flare", "flare_burn"),
        "legendary_stadium": ("stadium_expansion_ceremony", "grand_stadium_echo"),
        "cheer": ("fan_chant", "crowd_cheer"),
        "flare": ("stadium_flare", "flare_burn"),
        "drum": ("stadium_drums", "drum_roll"),
        "banner": ("club_banner_unfurl", "anthem_trumpet"),
    }
    anim_key, snd_key = animation_map.get(gift_code, ("fan_chant", "crowd_cheer"))
    broadcast_data = {
        "match_id": match_id,
        "club_id": club_id,
        "gift_code": gift_code,
        "gift_name": gift["name"],
        "cost": gift["cost"],
        "sender": user.username,
        "sender_id": user.id,
        "animation_key": anim_key,
        "sound_key": snd_key,
    }

    try:
        from app.realtime.service import publish_realtime_domain_event

        publish_realtime_domain_event("match.gift", broadcast_data)
        if app is not None and getattr(app.state, "realtime", None):
            from app.core.events import DomainEvent

            app.state.realtime.handle_event(DomainEvent(name="match.gift", payload=broadcast_data))
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Failed to publish match.gift realtime event: %s", exc)

    if match_id:
        try:
            hub = None
            if app is not None:
                from app.live_matches.service import ensure_live_match_hub

                hub = ensure_live_match_hub(app)
            else:
                from app.live_matches.service import get_global_live_match_hub

                hub = get_global_live_match_hub()
            if hub is not None:
                hub.broadcast_match_gift(match_id, broadcast_data)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("Failed to broadcast gift to LiveMatchHub: %s", exc)

    return {
        "gift": gift,
        "sender": user.username,
        "ledger_event": ledger.serialize(event),
        "broadcast": broadcast_data,
    }


def supporter_leaderboard(session: Session, club_id: str) -> list[dict[str, Any]]:
    from app.models.user import User

    rows = session.execute(
        select(LedgerEvent.user_id, func.sum(LedgerEvent.gross_amount), func.count())
        .where(LedgerEvent.destination_account == ledger.club_account(club_id), LedgerEvent.event_type == "gift")
        .group_by(LedgerEvent.user_id)
        .order_by(func.sum(LedgerEvent.gross_amount).desc())
        .limit(10)
    ).all()
    out = []
    for user_id, total, count in rows:
        user = session.get(User, user_id)
        out.append(
            {
                "user_id": user_id,
                "username": user.username if user else "fan",
                "fan_coin_sent": str(ledger.D(total)),
                "gifts": int(count),
            }
        )
    return out


def _tier(units: int) -> dict[str, Any]:
    for threshold, name, benefits in SUPPORT_TIERS:
        if units >= threshold:
            return {"tier": name, "benefits": benefits}
    return {"tier": None, "benefits": []}


def buy_support_units(session: Session, user_id: str, club_id: str, units: int) -> dict[str, Any]:
    if units < 1 or units > 500:
        raise OwnerError("invalid_units")
    if get_state(session, club_id) is None:
        raise OwnerError("club_not_found", 404)
    try:
        ledger.record(
            session,
            event_type="support_units",
            source=ledger.user_account(user_id),
            destination=ledger.club_account(club_id),
            currency=ledger.GTEX,
            gross=units * SUPPORT_UNIT_PRICE,
            fee_bps=500,
            club_id=club_id,
            user_id=user_id,
            related_type="support_units",
            related_id=club_id,
            memo=f"{units} Club Support Units (supporter status, not an investment)",
        )
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    holding = session.scalar(
        select(SupportUnitHolding).where(SupportUnitHolding.user_id == user_id, SupportUnitHolding.club_id == club_id)
    )
    if holding is None:
        holding = SupportUnitHolding(user_id=user_id, club_id=club_id, units=0)
        session.add(holding)
    holding.units += units
    session.flush()
    return {"club_id": club_id, "units": holding.units, **_tier(holding.units)}


def support_holdings(session: Session, user_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(select(SupportUnitHolding).where(SupportUnitHolding.user_id == user_id)).all()
    out = []
    for h in rows:
        state = get_state(session, h.club_id)
        out.append(
            {
                "club_id": h.club_id,
                "club_name": state.club_name if state else h.club_id,
                "units": h.units,
                **_tier(h.units),
            }
        )
    return out


def world_clubs(session: Session) -> list[dict[str, Any]]:
    from sqlalchemy import func

    from app.models.club_profile import ClubLifecycleStatus, ClubProfile
    from app.models.club_trophy import ClubTrophy
    from app.models.user import User
    from app.owner_console.living_institution import division_name
    from app.owner_console.models import OwnerClubState, OwnerSquadPlayer

    states = session.scalars(select(OwnerClubState).order_by(OwnerClubState.prestige.desc()).limit(50)).all()
    state_by_id = {s.club_id: s for s in states}
    profiles = session.scalars(
        select(ClubProfile)
        .where(ClubProfile.lifecycle_status != ClubLifecycleStatus.ARCHIVED_GENERATED)
        .order_by(ClubProfile.created_at.asc())
        .limit(50)
    ).all()
    profile_by_id = {p.id: p for p in profiles}
    all_club_ids = [
        cid
        for cid in dict.fromkeys([*state_by_id.keys(), *profile_by_id.keys()])
        if cid not in profile_by_id
        or getattr(profile_by_id[cid].lifecycle_status, "value", profile_by_id[cid].lifecycle_status)
        != ClubLifecycleStatus.ARCHIVED_GENERATED.value
    ]
    if not all_club_ids:
        return []

    missing_profile_ids = [cid for cid in all_club_ids if cid not in profile_by_id]
    if missing_profile_ids:
        for p in session.scalars(select(ClubProfile).where(ClubProfile.id.in_(missing_profile_ids))).all():
            profile_by_id[p.id] = p

    owner_ids = list(
        {
            (state_by_id[cid].owner_user_id if cid in state_by_id else profile_by_id[cid].owner_user_id)
            for cid in all_club_ids
            if cid in state_by_id or cid in profile_by_id
        }
    )
    owners_by_id = (
        {u.id: u for u in session.scalars(select(User).where(User.id.in_(owner_ids))).all()} if owner_ids else {}
    )
    squad_counts = {
        str(cid): int(cnt)
        for cid, cnt in session.execute(
            select(OwnerSquadPlayer.club_id, func.count(OwnerSquadPlayer.id))
            .where(
                OwnerSquadPlayer.club_id.in_(all_club_ids),
                OwnerSquadPlayer.status.in_(("active", "listed")),
            )
            .group_by(OwnerSquadPlayer.club_id)
        ).all()
        if cid
    }
    trophy_counts = {
        str(cid): int(cnt)
        for cid, cnt in session.execute(
            select(ClubTrophy.club_id, func.count(ClubTrophy.id))
            .where(ClubTrophy.club_id.in_(all_club_ids))
            .group_by(ClubTrophy.club_id)
        ).all()
        if cid
    }
    owner_club_counts: dict[str, int] = {}
    for cid in all_club_ids:
        st = state_by_id.get(cid)
        pr = profile_by_id.get(cid)
        oid = (st.owner_user_id if st else None) or (pr.owner_user_id if pr else "")
        if oid:
            owner_club_counts[oid] = owner_club_counts.get(oid, 0) + 1

    results: list[dict[str, Any]] = []
    for cid in all_club_ids:
        st = state_by_id.get(cid)
        pr = profile_by_id.get(cid)
        if pr is not None and pr.visibility == "private":
            continue
        owner_id = (st.owner_user_id if st else None) or (pr.owner_user_id if pr else "")
        owner = owners_by_id.get(owner_id)
        owner_name = (
            getattr(owner, "display_name", None) or getattr(owner, "username", None) or "GTEX Club Owner"
            if owner is not None
            else "GTEX Club Owner"
        )
        fac_trophies = len((st.facilities_json or {}).get("_trophies") or []) if st else 0
        trophies = max(trophy_counts.get(cid, 0), fac_trophies)
        city_name = pr.city_name if pr else None
        country_code = pr.country_code if pr else None
        country_label = (
            f"{city_name}, {country_code}" if city_name and country_code else (country_code or city_name or "Global")
        )
        div_level = (st.division_level if st else None) or "foundation"
        results.append(
            {
                "club_id": cid,
                "slug": (pr.slug if pr and pr.slug else cid),
                "club_name": (st.club_name if st and st.club_name else None) or (pr.club_name if pr else "GTEX Club"),
                "short_name": pr.short_name if pr else None,
                "city_name": city_name,
                "country_code": country_code,
                "country": country_label,
                "crest_url": pr.crest_asset_ref if pr else None,
                "primary_color": (pr.primary_color if pr and pr.primary_color else None) or "#0F766E",
                "secondary_color": (pr.secondary_color if pr and pr.secondary_color else None) or "#F8FAFC",
                "fans": st.fans if st else 0,
                "prestige": st.prestige if st else 10,
                "trophies": trophies,
                "squad_count": squad_counts.get(cid, 0),
                "division_level": div_level,
                "division_name": division_name(div_level),
                "owner_user_id": owner_id,
                "owner_name": owner_name,
                "multi_club_group": owner_club_counts.get(owner_id, 0) > 1,
            }
        )
    results.sort(key=lambda item: (int(item.get("prestige") or 0), int(item.get("trophies") or 0)), reverse=True)
    return results
