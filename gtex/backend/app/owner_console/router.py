from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.owner_console import competitions as comps
from app.owner_console import ledger, money, service
from app.owner_console.models import IntegrityFlag, LedgerEvent, OwnerCompetition, OwnerCompetitionEntry, OwnerInboxItem, OwnerMatch, OwnerWithdrawal
from app.owner_console.service import OwnerError

router = APIRouter(prefix="/owner", tags=["owner-console"])


def _run(session: Session, fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
        session.commit()
        return result
    except OwnerError as exc:
        session.rollback()
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "detail": exc.detail}) from exc


class ManagerSnapshot(BaseModel):
    manager_id: str
    display_name: str
    rarity: str | None = None
    mentality: str | None = None
    tactics: list[str] = []
    traits: list[str] = []
    philosophy_summary: str | None = None


class AppointRequest(BaseModel):
    manager: ManagerSnapshot | None = None


class SignRequest(BaseModel):
    player_id: str


class DecideRequest(BaseModel):
    action: str


class EnterRequest(BaseModel):
    club_id: str


class PlayRequest(BaseModel):
    club_id: str
    mentality: Literal["defensive", "balanced", "attacking"] = "balanced"
    lineup_mode: Literal["strongest", "rotate"] = "strongest"


class HostRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    format: Literal["league", "knockout"] = "league"
    entry_fee: int = Field(ge=0, le=100000, default=0)
    max_clubs: int = Field(ge=2, le=8, default=4)
    allow_same_owner: bool = False
    description: str | None = None


class JoinCodeRequest(BaseModel):
    code: str
    club_id: str


class AmountRequest(BaseModel):
    amount: float = Field(gt=0)


class ClubAmountRequest(BaseModel):
    club_id: str
    amount: float = Field(gt=0)


class SisterCapitalRequest(BaseModel):
    from_club_id: str
    to_club_id: str
    amount: float = Field(gt=0)


class InternalTransferRequest(BaseModel):
    player_id: str
    to_club_id: str
    fee: float = Field(ge=0)


class WithdrawalRequest(BaseModel):
    amount_coin: float = Field(gt=0)
    bank_name: str = Field(min_length=2, max_length=120)
    account_number: str = Field(min_length=10, max_length=10, pattern=r"^\d{10}$")
    account_name: str = Field(min_length=2, max_length=160)


class DepositInitRequest(BaseModel):
    amount_ngn: int = Field(ge=100)
    callback_url: str


class GiftRequest(BaseModel):
    club_id: str
    gift_code: str
    match_id: str | None = None


class SupportRequest(BaseModel):
    club_id: str
    units: int = Field(ge=1, le=500)


class ReviewRequest(BaseModel):
    decision: Literal["approve", "reject", "hold"]
    note: str | None = None


class MentalityRequest(BaseModel):
    mentality: Literal["defensive", "balanced", "attacking"]


# ---------- onboarding + clubs ----------

@router.get("/onboarding")
def onboarding(user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    profiles = service.owned_profiles(session, user.id)
    out = []
    for p in profiles:
        state = service.get_state(session, p.id)
        out.append({"club_id": p.id, "club_name": p.club_name, "stage": state.stage if state else "not_started", "squad_size": len(service.squad(session, p.id)) if state else 0, "cash": str(ledger.balance(session, ledger.club_account(p.id), ledger.GTEX)) if state else "0"})
    return {"clubs": out, "max_clubs": service.MAX_CLUBS, "min_squad": service.MIN_SQUAD, "launch_grant": service.LAUNCH_GRANT_GTEX}


@router.post("/clubs/{club_id}/activate")
def activate(club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    state = _run(session, service.start_activation, session, user.id, club_id)
    return {"club_id": state.club_id, "stage": state.stage}


@router.post("/clubs/{club_id}/sign")
def sign(club_id: str, body: SignRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    player = _run(session, service.sign_market_player, session, user.id, club_id, body.player_id)
    state = service.get_state(session, club_id)
    return {"player": service.player_dict(player), "stage": state.stage, "squad_size": len(service.squad(session, club_id)), "cash": str(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX))}


@router.get("/market/quote")
def quote(player_ids: str, session: Session = Depends(get_session), user=Depends(get_current_user)) -> dict[str, Any]:
    from app.ingestion.models import Player

    ids = [pid for pid in player_ids.split(",")[:100] if pid]
    players = list(session.scalars(select(Player).where(Player.id.in_(ids))).all()) if ids else []
    quotes = service.player_quotes(session, players)
    return {"quotes": {pid: {"price": price, "rating": rating} for pid, (price, rating) in quotes.items()}}


@router.post("/clubs/{club_id}/manager")
def appoint(club_id: str, body: AppointRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    state = _run(session, service.appoint_manager, session, user.id, club_id, body.manager.model_dump() if body.manager else None)
    return {"manager": state.manager_json, "stage": state.stage}


@router.post("/clubs/{club_id}/manager/fire")
def fire(club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, service.fire_manager, session, user.id, club_id)


@router.post("/clubs/{club_id}/finish-onboarding")
def finish_onboarding(club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    def go():
        state = service.require_state(session, club_id, user.id)
        if state.stage == "competition":
            state.stage = "active"
        return {"stage": state.stage}

    return _run(session, go)


@router.get("/clubs/{club_id}")
def club(club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, service.club_detail, session, user.id, club_id)


@router.put("/clubs/{club_id}/mentality")
def set_mentality(club_id: str, body: MentalityRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    def go():
        state = service.require_state(session, club_id, user.id)
        state.mentality = body.mentality
        return {"mentality": state.mentality}

    return _run(session, go)


@router.post("/clubs/{club_id}/facilities/{kind}/upgrade")
def upgrade(club_id: str, kind: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, service.upgrade_facility, session, user.id, club_id, kind)


@router.post("/clubs/{club_id}/academy/intake")
def intake(club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    players = _run(session, service.academy_intake, session, user.id, club_id)
    return {"regens": [service.player_dict(p) for p in players]}


@router.post("/clubs/{club_id}/advance")
def advance(club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    def go():
        state = service.require_state(session, club_id, user.id)
        return service.tick_club(session, state)

    return _run(session, go)


@router.get("/clubs/{club_id}/supporters")
def supporters(club_id: str, session: Session = Depends(get_session), user=Depends(get_current_user)) -> dict[str, Any]:
    return {"leaderboard": money.supporter_leaderboard(session, club_id)}


@router.get("/world/clubs")
def world(session: Session = Depends(get_session), user=Depends(get_current_user)) -> dict[str, Any]:
    return {"clubs": money.world_clubs(session)}


# ---------- control center + inbox ----------

@router.get("/control-center")
def control_center(user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    def go():
        comps.ensure_seed(session)
        service.maybe_auto_tick(session, user.id)
        states = service.user_states(session, user.id)
        club_ids = [s.club_id for s in states]
        items = session.scalars(select(OwnerInboxItem).where(OwnerInboxItem.user_id == user.id, OwnerInboxItem.status == "open").order_by(OwnerInboxItem.created_at.desc())).all()
        entries = session.scalars(select(OwnerCompetitionEntry).where(OwnerCompetitionEntry.club_id.in_(club_ids))).all() if club_ids else []
        comp_ids = list({e.competition_id for e in entries})
        upcoming, recent = [], []
        if comp_ids:
            for m in session.scalars(select(OwnerMatch).where(OwnerMatch.competition_id.in_(comp_ids)).order_by(OwnerMatch.round_number.asc())).all():
                if m.home_club_id in club_ids or m.away_club_id in club_ids:
                    (upcoming if m.status == "scheduled" else recent).append(comps.match_dict(m))
        my_comp_rows = session.scalars(select(OwnerCompetition).where(OwnerCompetition.id.in_(comp_ids))).all() if comp_ids else []
        my_comps = [comps.comp_dict(session, c, user.id) for c in my_comp_rows]
        board = [{"competition": comp, "standings": comps.standings(session, row)} for comp, row in zip(my_comps, my_comp_rows)]
        open_comps = [comps.comp_dict(session, c, user.id) for c in session.scalars(select(OwnerCompetition).where(OwnerCompetition.status == "open", OwnerCompetition.host_type == "gtex")).all()]
        economy_by_club = {s.club_id: ledger.club_economy(session, s.club_id) for s in states}
        totals: dict[str, float] = {}
        for econ in economy_by_club.values():
            for k, v in econ["earnings_sources"].items():
                totals[k] = totals.get(k, 0.0) + float(v)
        return {
            "user": {"id": user.id, "username": user.username, "display_name": getattr(user, "display_name", None), "role": str(getattr(user.role, "value", user.role))},
            "clubs": [service.club_card(session, s) for s in states],
            "max_clubs": service.MAX_CLUBS,
            "ownership_group": service.group_label(session, user.id),
            "inbox": [service.inbox_dict(i) for i in items[:8]],
            "inbox_open_count": len(items),
            "decisions": [service.inbox_dict(i) for i in items if i.is_decision][:6],
            "health": [service.club_health(session, s) for s in states],
            "board": board,
            "fixtures": {"upcoming": upcoming[:6], "recent": list(reversed(recent))[:6], "my_competitions": my_comps, "open_competitions": open_comps, "hosted": [c for c in my_comps if c["host_type"] == "user"]},
            "economy": {
                "wallet": ledger.wallet_classes(session, user.id),
                "club_cash_total": str(sum(float(e["cash_gtex"]) for e in economy_by_club.values())),
                "earnings_sources": totals,
                "pending_payouts": str(sum(float(e["pending_payouts"]) for e in economy_by_club.values())),
                "gifts_received_fan_coin": str(sum(float(e["gifts_fan_coin"]) for e in economy_by_club.values())),
            },
            "integrity": {"score": service.integrity_score(session, user.id), "open_high_flags": service.open_high_flags(session, user.id)},
        }

    return _run(session, go)


@router.get("/inbox")
def inbox(status: str = "open", user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    stmt = select(OwnerInboxItem).where(OwnerInboxItem.user_id == user.id)
    if status != "all":
        stmt = stmt.where(OwnerInboxItem.status == status)
    items = session.scalars(stmt.order_by(OwnerInboxItem.created_at.desc()).limit(100)).all()
    return {"items": [service.inbox_dict(i) for i in items]}


@router.post("/inbox/{item_id}/decide")
def decide(item_id: str, body: DecideRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    item = _run(session, service.resolve_item, session, user.id, item_id, body.action)
    return service.inbox_dict(item)


# ---------- competitions ----------

@router.get("/competitions")
def competitions_list(user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    def go():
        comps.ensure_seed(session)
        rows = session.scalars(select(OwnerCompetition).order_by(OwnerCompetition.created_at.desc()).limit(60)).all()
        visible = [c for c in rows if c.host_type == "gtex" or c.host_user_id == user.id or user.id in {e.owner_user_id for e in comps.entries(session, c.id)}]
        return {"competitions": [comps.comp_dict(session, c, user.id) for c in visible]}

    return _run(session, go)


@router.post("/competitions")
def host(body: HostRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    comp = _run(session, comps.host_competition, session, user.id, body.model_dump())
    return comps.comp_dict(session, comp, user.id)


@router.post("/competitions/join-by-code")
def join_code(body: JoinCodeRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    entry = _run(session, comps.join_by_code, session, user.id, body.code, body.club_id)
    return {"competition_id": entry.competition_id, "club_id": entry.club_id}


@router.get("/competitions/{competition_id}")
def competition(competition_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, comps.detail, session, competition_id, user.id)


@router.post("/competitions/{competition_id}/enter")
def enter(competition_id: str, body: EnterRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    entry = _run(session, comps.enter_competition, session, user.id, competition_id, body.club_id)
    return {"competition_id": entry.competition_id, "club_id": entry.club_id}


@router.post("/competitions/{competition_id}/play-next")
def play(competition_id: str, body: PlayRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, comps.play_next, session, user.id, competition_id, body.club_id, body.mentality, body.lineup_mode)


@router.get("/matches/{match_id}")
def match(match_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    m = session.get(OwnerMatch, match_id)
    if m is None:
        raise HTTPException(404, detail={"code": "match_not_found"})
    return comps.match_dict(m, full=True)


@router.post("/matches/{match_id}/forfeit")
def forfeit(match_id: str, body: EnterRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, comps.forfeit, session, user.id, match_id, body.club_id)


# ---------- finance ----------

@router.get("/finance")
def finance(user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    states = service.user_states(session, user.id)
    events = ledger.events_for(session, user_id=user.id, club_ids=[s.club_id for s in states], limit=150)
    return {
        "wallet": ledger.wallet_classes(session, user.id),
        "clubs": [{"club_id": s.club_id, "club_name": s.club_name, **ledger.club_economy(session, s.club_id), "distributable": str(money.distributable(session, s.club_id))} for s in states],
        "ledger": [ledger.serialize(e) for e in events],
        "withdrawals": [money.withdrawal_dict(w) for w in ledger.pending_withdrawals(session, user.id)],
        "support_units": money.support_holdings(session, user.id),
        "gift_catalog": money.GIFTS,
        "support_unit_price": money.SUPPORT_UNIT_PRICE,
        "fan_coin_per_gtex": money.FAN_COIN_PER_GTEX,
        "paystack_configured": bool(money.paystack_secret()),
        "paystack_mode": "live" if (money.paystack_secret() or "").startswith("sk_live_") else "test",
        "treasury_rates": {k: str(v) for k, v in money.treasury_rates(session).items()},
        "withdrawal_processor_mode": "manual_bank_transfer",
    }


@router.get("/withdrawals/eligibility")
def eligibility(amount: float = 1, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, money.withdrawal_eligibility, session, user, ledger.D(amount))


@router.post("/withdrawals")
def withdraw(body: WithdrawalRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    w = _run(session, money.request_withdrawal, session, user, body.model_dump())
    return money.withdrawal_dict(w)


@router.post("/deposits/init")
def deposit_init(body: DepositInitRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, money.paystack_init, session, user, body.amount_ngn, body.callback_url)


@router.get("/deposits/verify/{reference}")
def deposit_verify(reference: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, money.paystack_verify, session, user, reference)


@router.post("/deposits/webhook")
async def deposit_webhook(request: Request, session: Session = Depends(get_session)) -> JSONResponse:
    raw = await request.body()
    payload = await request.json()
    _run(session, money.paystack_webhook, session, raw, request.headers.get("x-paystack-signature"), payload)
    return JSONResponse({"status": "ok"})


@router.post("/capital/inject")
def inject(body: ClubAmountRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return ledger.serialize(_run(session, money.inject_capital, session, user.id, body.club_id, body.amount))


@router.post("/capital/distribute")
def distribute(body: ClubAmountRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return ledger.serialize(_run(session, money.distribute_to_owner, session, user.id, body.club_id, body.amount))


@router.post("/capital/sister-transfer")
def sister(body: SisterCapitalRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return ledger.serialize(_run(session, money.sister_capital, session, user.id, body.from_club_id, body.to_club_id, body.amount))


@router.post("/transfers/internal/check")
def internal_check(body: InternalTransferRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    result = _run(session, money.check_internal_transfer, session, user.id, body.player_id, body.to_club_id, body.fee)
    result.pop("player", None)
    result["fee"] = str(result["fee"])
    return result


@router.post("/transfers/internal")
def internal(body: InternalTransferRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, money.internal_transfer, session, user.id, body.player_id, body.to_club_id, body.fee)


@router.post("/fan-coin/buy")
def fan_coin(body: AmountRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, money.buy_fan_coin, session, user.id, body.amount)


@router.post("/gifts/send")
def gift(body: GiftRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, money.send_gift, session, user, body.club_id, body.gift_code, body.match_id)


@router.post("/support-units/buy")
def support(body: SupportRequest, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    return _run(session, money.buy_support_units, session, user.id, body.club_id, body.units)


@router.get("/integrity")
def integrity(user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    flags = session.scalars(select(IntegrityFlag).where(IntegrityFlag.user_id == user.id).order_by(IntegrityFlag.created_at.desc())).all()
    return {"score": service.integrity_score(session, user.id), "flags": [_flag(f) for f in flags]}


def _flag(f: IntegrityFlag) -> dict[str, Any]:
    return {"id": f.id, "user_id": f.user_id, "club_id": f.club_id, "flag_type": f.flag_type, "severity": f.severity, "detail": f.detail, "score_impact": f.score_impact, "status": f.status, "related_object_id": f.related_object_id, "created_at": f.created_at.isoformat()}


# ---------- admin review ----------

@router.get("/admin/review-queue")
def review_queue(admin=Depends(get_current_admin), session: Session = Depends(get_session)) -> dict[str, Any]:
    withdrawals = session.scalars(select(OwnerWithdrawal).where(OwnerWithdrawal.status.in_(("pending_review", "held"))).order_by(OwnerWithdrawal.created_at.asc())).all()
    flags = session.scalars(select(IntegrityFlag).where(IntegrityFlag.status == "open").order_by(IntegrityFlag.created_at.desc())).all()
    held = session.scalars(select(LedgerEvent).where(LedgerEvent.status == "held", LedgerEvent.event_type != "withdrawal")).all()
    return {"withdrawals": [money.withdrawal_dict(w) for w in withdrawals], "flags": [_flag(f) for f in flags], "held_payouts": [ledger.serialize(e) for e in held]}


@router.post("/admin/withdrawals/{withdrawal_id}/review")
def review(withdrawal_id: str, body: ReviewRequest, admin=Depends(get_current_admin), session: Session = Depends(get_session)) -> dict[str, Any]:
    return money.withdrawal_dict(_run(session, money.review_withdrawal, session, admin, withdrawal_id, body.decision, body.note))


@router.post("/admin/flags/{flag_id}/{decision}")
def flag_decision(flag_id: str, decision: Literal["clear", "action"], admin=Depends(get_current_admin), session: Session = Depends(get_session)) -> dict[str, Any]:
    def go():
        flag = session.get(IntegrityFlag, flag_id)
        if flag is None:
            raise OwnerError("flag_not_found", 404)
        flag.status = "cleared" if decision == "clear" else "actioned"
        return _flag(flag)

    return _run(session, go)


@router.post("/admin/payouts/{event_id}/release")
def release(event_id: str, admin=Depends(get_current_admin), session: Session = Depends(get_session)) -> dict[str, Any]:
    return ledger.serialize(_run(session, money.release_payout, session, event_id))
