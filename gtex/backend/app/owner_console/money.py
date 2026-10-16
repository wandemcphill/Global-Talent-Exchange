from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.club_profile import ClubProfile
from app.owner_console import engine, ledger
from app.value_engine.banded_pricing import NAIRA_PER_COIN
from app.wallets.service import COIN_TO_CREDIT_RATE
from app.owner_console.models import LedgerEvent, OwnerSquadPlayer, OwnerWithdrawal, RelatedPartyTransfer, SupportUnitHolding
from app.owner_console.service import OwnerError, get_state, integrity_score, now, open_high_flags, raise_flag, require_state, user_states

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
    (50, "Founders' Circle", ["Vote on club kit & anthem polls", "Supporter-only competitions", "Name on the Founders' Wall"]),
    (10, "Patron", ["Supporter-only competitions", "Patron badge on club page"]),
    (1, "Supporter", ["Supporter badge", "Club supporter leaderboard"]),
)
FAN_COIN_PER_GTEX = COIN_TO_CREDIT_RATE
NGN_PER_GTEX_COIN = Decimal(str(NAIRA_PER_COIN))
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
    club_countries = {(c.country_code or "").upper() for c in session.scalars(select(ClubProfile).where(ClubProfile.owner_user_id == user.id)).all()}
    score = integrity_score(session, user.id)
    kyc = str(getattr(user.kyc_status, "value", user.kyc_status))
    checks = {
        "country_supported": bool(club_countries & countries),
        "withdrawable_balance": Decimal(classes["withdrawable"]) >= amount,
        "kyc_ok": amount <= kyc_threshold or kyc == "verified",
        "integrity_ok": score >= min_score,
        "no_open_high_flags": open_high_flags(session, user.id) == 0,
    }
    return {"checks": checks, "eligible": all(checks.values()), "integrity_score": score, "kyc_status": kyc, "kyc_threshold": str(kyc_threshold), "withdrawable": classes["withdrawable"], "supported_countries": sorted(countries)}


def request_withdrawal(session: Session, user, payload: dict[str, Any]) -> OwnerWithdrawal:
    amount = ledger.D(payload["amount_coin"])
    if amount <= 0:
        raise OwnerError("amount_must_be_positive")
    result = withdrawal_eligibility(session, user, amount)
    if not result["eligible"]:
        raise OwnerError("withdrawal_not_eligible", 403, result)
    rate = NGN_PER_GTEX_COIN
    account_age_days = (now() - (user.created_at if user.created_at.tzinfo else user.created_at.replace(tzinfo=now().tzinfo))).days
    risk = {"new_account": account_age_days < 7, "large_amount": amount > Decimal(result["kyc_threshold"])}
    withdrawal = OwnerWithdrawal(user_id=user.id, amount_coin=amount, amount_ngn=ledger.D(amount * rate), bank_name=payload["bank_name"], account_number=payload["account_number"], account_name=payload["account_name"], checks_json={**result, "risk": risk})
    session.add(withdrawal)
    session.flush()
    event = ledger.record(session, event_type="withdrawal", source=ledger.user_account(user.id), destination=ledger.BANK_OUT, currency=ledger.GTEX, gross=amount, status="pending_review", user_id=user.id, related_type="withdrawal", related_id=withdrawal.id, memo=f"Withdrawal to {payload['bank_name']} ****{payload['account_number'][-4:]}", check_funds=False)
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
    w.status, event.status = mapping[decision]
    w.review_note, w.reviewed_by, w.reviewed_at = note, admin.id, now()
    session.flush()
    return w


def withdrawal_dict(w: OwnerWithdrawal) -> dict[str, Any]:
    return {"id": w.id, "user_id": w.user_id, "amount_coin": str(w.amount_coin), "amount_ngn": str(w.amount_ngn), "bank_name": w.bank_name, "account_last4": w.account_number[-4:], "account_name": w.account_name, "status": w.status, "checks": w.checks_json, "review_note": w.review_note, "created_at": w.created_at.isoformat(), "reviewed_at": w.reviewed_at.isoformat() if w.reviewed_at else None}


def release_payout(session: Session, ledger_event_id: str) -> LedgerEvent:
    event = session.get(LedgerEvent, ledger_event_id)
    if event is None or event.status != "held" or event.event_type == "withdrawal":
        raise OwnerError("payout_not_held", 409)
    event.status = "completed"
    session.flush()
    return event


# ---------- Paystack deposits ----------

def paystack_init(session: Session, user, amount_ngn: int, callback_url: str) -> dict[str, Any]:
    secret = _secret()
    if amount_ngn < NGN_PER_GTEX_COIN:
        raise OwnerError("minimum_deposit_100_ngn")
    reference = f"gtex_{uuid.uuid4().hex[:18]}"
    response = httpx.post("https://api.paystack.co/transaction/initialize", headers={"Authorization": f"Bearer {secret}"}, json={"email": user.email, "amount": amount_ngn * 100, "currency": "NGN", "reference": reference, "callback_url": callback_url, "metadata": {"user_id": user.id, "product": "gtex_coin"}}, timeout=20)
    data = response.json()
    if not data.get("status"):
        raise OwnerError("paystack_init_failed", 502, data.get("message"))
    return {"authorization_url": data["data"]["authorization_url"], "reference": reference}


def _credit_deposit(session: Session, user_id: str, reference: str, amount_kobo: int) -> LedgerEvent:
    existing = session.scalar(select(LedgerEvent).where(LedgerEvent.related_object_type == "paystack", LedgerEvent.related_object_id == reference))
    if existing:
        return existing
    ngn = Decimal(amount_kobo) / 100
    coins = ledger.D(ngn / NGN_PER_GTEX_COIN)
    return ledger.record(session, event_type="deposit", source=ledger.PAYSTACK, destination=ledger.user_account(user_id), currency=ledger.GTEX, gross=coins, balance_class="deposited", user_id=user_id, related_type="paystack", related_id=reference, memo=f"Paystack deposit NGN {ngn:,.2f}")


def paystack_verify(session: Session, user, reference: str) -> dict[str, Any]:
    secret = _secret()
    data = httpx.get(f"https://api.paystack.co/transaction/verify/{reference}", headers={"Authorization": f"Bearer {secret}"}, timeout=20).json()
    tx = data.get("data") or {}
    if not data.get("status") or tx.get("status") != "success":
        return {"status": "failed", "message": data.get("message")}
    if (tx.get("metadata") or {}).get("user_id") != user.id:
        raise OwnerError("deposit_owner_mismatch", 403)
    event = _credit_deposit(session, user.id, reference, int(tx["amount"]))
    return {"status": "success", "ledger_event": ledger.serialize(event)}


def paystack_webhook(session: Session, raw: bytes, signature: str | None, event: dict[str, Any]) -> None:
    secret = _secret()
    computed = hmac.new(secret.encode(), raw, hashlib.sha512).hexdigest()
    if not signature or not hmac.compare_digest(computed, signature):
        raise OwnerError("invalid_signature", 401)
    if event.get("event") == "charge.success":
        tx = event.get("data") or {}
        user_id = (tx.get("metadata") or {}).get("user_id")
        if user_id:
            _credit_deposit(session, user_id, tx["reference"], int(tx["amount"]))


# ---------- capital moves ----------

def inject_capital(session: Session, user_id: str, club_id: str, amount) -> LedgerEvent:
    require_state(session, club_id, user_id)
    try:
        return ledger.record(session, event_type="owner_capital_injection", source=ledger.user_account(user_id), destination=ledger.club_account(club_id), currency=ledger.GTEX, gross=amount, club_id=club_id, user_id=user_id, related_type="club", related_id=club_id, memo="Approved owner capital action")
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc


def distributable(session: Session, club_id: str) -> Decimal:
    acct = ledger.club_account(club_id)
    earned = session.scalar(select(func.coalesce(func.sum(LedgerEvent.net_amount), 0)).where(LedgerEvent.destination_account == acct, LedgerEvent.currency == ledger.GTEX, LedgerEvent.status == "completed", LedgerEvent.event_type.in_(("gate_receipts", "competition_prize", "sponsor_revenue", "endorsement_revenue", "transfer_sale"))))
    paid = session.scalar(select(func.coalesce(func.sum(LedgerEvent.gross_amount), 0)).where(LedgerEvent.source_account == acct, LedgerEvent.event_type == "owner_distribution", LedgerEvent.status == "completed"))
    cash = ledger.balance(session, acct, ledger.GTEX)
    return max(Decimal("0"), min(ledger.D(earned or 0) - ledger.D(paid or 0), cash))


def distribute_to_owner(session: Session, user_id: str, club_id: str, amount) -> LedgerEvent:
    require_state(session, club_id, user_id)
    amount = ledger.D(amount)
    limit = distributable(session, club_id)
    if amount > limit:
        raise OwnerError("exceeds_distributable_earnings", 409, f"Only earned club revenue can be distributed (max {limit}). Launch grants and capital injections stay in the club.")
    return ledger.record(session, event_type="owner_distribution", source=ledger.club_account(club_id), destination=ledger.user_account(user_id), currency=ledger.GTEX, gross=amount, balance_class="earned", club_id=club_id, user_id=user_id, related_type="club", related_id=club_id, memo="Owner distribution from earned club revenue")


def sister_capital(session: Session, user_id: str, from_club: str, to_club: str, amount) -> LedgerEvent:
    if from_club == to_club:
        raise OwnerError("same_club")
    require_state(session, from_club, user_id)
    require_state(session, to_club, user_id)
    amount = ledger.D(amount)
    cap = ledger.D(ledger.balance(session, ledger.club_account(from_club), ledger.GTEX) * Decimal(SISTER_CAPITAL_CAP_BPS) / 10000)
    if amount > cap:
        raise OwnerError("sister_capital_cap_exceeded", 409, f"Inter-club moves are capped at 25% of the source club's cash ({cap}).")
    return ledger.record(session, event_type="sister_club_capital", source=ledger.club_account(from_club), destination=ledger.club_account(to_club), currency=ledger.GTEX, gross=amount, club_id=to_club, user_id=user_id, related_type="club", related_id=from_club, memo="Disclosed related-party capital move")


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
    reciprocal = session.scalar(select(RelatedPartyTransfer).where(RelatedPartyTransfer.from_club_id == to_club, RelatedPartyTransfer.to_club_id == player.club_id, RelatedPartyTransfer.created_at >= now() - RECIPROCAL_COOLDOWN))
    recent = session.scalar(select(func.count()).select_from(RelatedPartyTransfer).where(RelatedPartyTransfer.owner_user_id == user_id, RelatedPartyTransfer.created_at >= now() - timedelta(days=30))) or 0
    rules = {
        "no_free_transfer": fee > 0,
        "within_fair_value_band": low <= fee <= high,
        "reciprocal_cooldown_clear": reciprocal is None,
    }
    return {"rules": rules, "allowed": all(rules.values()), "fair_value": str(value), "band": [str(low), str(high)], "recent_related_moves": int(recent), "shuffle_flag_risk": recent >= 2, "player": player, "fee": fee}


def internal_transfer(session: Session, user_id: str, player_id: str, to_club: str, fee) -> dict[str, Any]:
    check = check_internal_transfer(session, user_id, player_id, to_club, fee)
    if not check["allowed"]:
        raise OwnerError("related_party_transfer_blocked", 409, {k: v for k, v in check.items() if k != "player"})
    player: OwnerSquadPlayer = check["player"]
    from_club = player.club_id
    try:
        ledger.record(session, event_type="related_party_transfer", source=ledger.club_account(to_club), destination=ledger.club_account(from_club), currency=ledger.GTEX, gross=check["fee"], fee_bps=200, club_id=from_club, user_id=user_id, related_type="player", related_id=player.id, memo=f"Related-party transfer: {player.name}")
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    session.add(RelatedPartyTransfer(owner_user_id=user_id, from_club_id=from_club, to_club_id=to_club, player_name=player.name, player_ref=player.player_ref, fair_value=Decimal(check["fair_value"]), fee=check["fee"]))
    player.club_id = to_club
    player.morale = max(0, player.morale - 5)
    notes = ["Disclosed in both clubs' history."]
    if check["shuffle_flag_risk"]:
        player.morale = max(0, player.morale - 15)
        raise_flag(session, user_id, from_club, "asset_shuffling", "medium", f"{check['recent_related_moves'] + 1} related-party moves in 30 days.", 10, player.id)
        notes.append("Repeated asset shuffling flagged; player morale -15.")
    session.flush()
    return {"player_id": player.id, "from_club_id": from_club, "to_club_id": to_club, "fee": str(check["fee"]), "notes": notes}


# ---------- fan economy ----------

def buy_fan_coin(session: Session, user_id: str, gtex_amount) -> dict[str, Any]:
    gtex_amount = ledger.D(gtex_amount)
    try:
        ledger.record(session, event_type="fan_coin_purchase", source=ledger.user_account(user_id), destination=ledger.PLATFORM_FEES, currency=ledger.GTEX, gross=gtex_amount, user_id=user_id, memo="Converted to Fan Coin")
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    ledger.record(session, event_type="fan_coin_purchase", source=ledger.PLATFORM_GRANTS, destination=ledger.user_account(user_id), currency=ledger.FAN, gross=gtex_amount * FAN_COIN_PER_GTEX, balance_class="non_withdrawable", user_id=user_id, memo="Fan Coin (non-withdrawable)")
    return {"fan_coin": str(gtex_amount * FAN_COIN_PER_GTEX)}


def send_gift(session: Session, user, club_id: str, gift_code: str, match_id: str | None) -> dict[str, Any]:
    gift = GIFTS.get(gift_code)
    if gift is None:
        raise OwnerError("unknown_gift")
    if get_state(session, club_id) is None:
        raise OwnerError("club_not_found", 404)
    try:
        event = ledger.record(session, event_type="gift", source=ledger.user_account(user.id), destination=ledger.club_account(club_id), currency=ledger.FAN, gross=gift["cost"], fee_bps=GIFT_PLATFORM_BPS, club_id=club_id, user_id=user.id, related_type="match" if match_id else "club", related_id=match_id or club_id, memo=f"{gift['name']} from {user.username}")
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    state = get_state(session, club_id)
    state.fans += max(1, gift["cost"] // 10)
    return {"gift": gift, "sender": user.username, "ledger_event": ledger.serialize(event)}


def supporter_leaderboard(session: Session, club_id: str) -> list[dict[str, Any]]:
    from app.models.user import User

    rows = session.execute(select(LedgerEvent.user_id, func.sum(LedgerEvent.gross_amount), func.count()).where(LedgerEvent.destination_account == ledger.club_account(club_id), LedgerEvent.event_type == "gift").group_by(LedgerEvent.user_id).order_by(func.sum(LedgerEvent.gross_amount).desc()).limit(10)).all()
    out = []
    for user_id, total, count in rows:
        user = session.get(User, user_id)
        out.append({"user_id": user_id, "username": user.username if user else "fan", "fan_coin_sent": str(ledger.D(total)), "gifts": int(count)})
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
        ledger.record(session, event_type="support_units", source=ledger.user_account(user_id), destination=ledger.club_account(club_id), currency=ledger.GTEX, gross=units * SUPPORT_UNIT_PRICE, fee_bps=500, club_id=club_id, user_id=user_id, related_type="support_units", related_id=club_id, memo=f"{units} Club Support Units (supporter status, not an investment)")
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    holding = session.scalar(select(SupportUnitHolding).where(SupportUnitHolding.user_id == user_id, SupportUnitHolding.club_id == club_id))
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
        out.append({"club_id": h.club_id, "club_name": state.club_name if state else h.club_id, "units": h.units, **_tier(h.units)})
    return out


def world_clubs(session: Session) -> list[dict[str, Any]]:
    from app.owner_console.models import OwnerClubState

    states = session.scalars(select(OwnerClubState).where(OwnerClubState.stage.in_(("competition", "active"))).order_by(OwnerClubState.prestige.desc()).limit(50)).all()
    counts: dict[str, int] = {}
    for s in states:
        counts[s.owner_user_id] = counts.get(s.owner_user_id, 0) + 1
    return [{"club_id": s.club_id, "club_name": s.club_name, "fans": s.fans, "prestige": s.prestige, "owner_user_id": s.owner_user_id, "multi_club_group": len(user_states(session, s.owner_user_id)) > 1} for s in states]
