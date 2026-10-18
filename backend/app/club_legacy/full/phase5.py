"""Phase 5 pre-season: windows, offers, tournaments, blocks, and GM policy.

Platform, host, and participant shares are read from the active
``club_legacy_revenue_rules`` row and must sum to 100 percent. When that row
stores a stage map, settlement uses the map for the club's development stage.
The documented default map reproduces the original television split:

* foundation clubs keep 30 percent, growing 40, established 50, elite 60, legacy 70
* the host receives 40 percent of the clubs' share and participants receive the rest
* the platform keeps the remainder

Reputation, audience, and money are separate settlement fields. Settlement does
not write an official league standing. A repeated fixture inside the same window
adds no further reputation. Paying a settlement twice does not post the ledger again.

The GM may accept a pre-season invite only when the club's preseason_response
policy is automatic and the appearance fee is within that policy's cap
(``max_amount``). ``owner_only`` leaves the decision with the owner.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.club_legacy.delegation import PRESEASON_RESPONSE, LegacyError, policy_for, require_owner
from app.club_legacy.full.support import money, remember_refusal
from app.club_legacy.ledger import post_club_legacy_transfer
from app.club_legacy.models import (
    ClubLegacyExecutive,
    ClubLegacyManagerCommitment,
    ClubLegacyPreseasonEvent,
    ClubLegacyPreseasonInvite,
    ClubLegacyPreseasonOffer,
    ClubLegacyPreseasonSettlement,
    ClubLegacyPreseasonWindow,
    ClubLegacyRevenueRule,
    ClubLegacyTournament,
    ClubLegacyTournamentParticipant,
    ClubLegacyTournamentSettlement,
)
from app.club_legacy.ratings import development_score
from app.models.club_profile import ClubProfile
from app.owner_console import ledger
from app.owner_console.models import OwnerClubState

HOST_CUT_OF_CLUB_POOL = Decimal("0.40")
TV_SHARES = {
    "foundation": Decimal("0.30"),
    "growing": Decimal("0.40"),
    "established": Decimal("0.50"),
    "elite": Decimal("0.60"),
    "legacy": Decimal("0.70"),
}
SHARE_QUANTUM = Decimal("0.000001")


def development_stage_name(score: int) -> str:
    if score < 20:
        return "foundation"
    if score < 40:
        return "growing"
    if score < 60:
        return "established"
    if score < 80:
        return "elite"
    return "legacy"


def _stage_share(stage: str) -> dict[str, str]:
    club_rate = TV_SHARES[stage]
    platform = Decimal("1") - club_rate
    host = (club_rate * HOST_CUT_OF_CLUB_POOL).quantize(SHARE_QUANTUM)
    participant = (club_rate - host).quantize(SHARE_QUANTUM)
    platform = platform.quantize(SHARE_QUANTUM)
    return {"platform": str(platform), "host": str(host), "participant": str(participant)}


def default_stage_shares() -> dict[str, dict[str, str]]:
    return {stage: _stage_share(stage) for stage in TV_SHARES}


def ensure_revenue_rule(session: Session) -> ClubLegacyRevenueRule:
    rule = session.scalar(
        select(ClubLegacyRevenueRule).where(ClubLegacyRevenueRule.active.is_(True)).order_by(ClubLegacyRevenueRule.version.desc())
    )
    if rule is not None:
        _assert_rule_sums(rule, stage=None)
        return rule
    foundation = _stage_share("foundation")
    rule = ClubLegacyRevenueRule(
        version=1,
        active=True,
        platform_share=Decimal(foundation["platform"]),
        host_share=Decimal(foundation["host"]),
        participant_share=Decimal(foundation["participant"]),
        stage_shares_json=default_stage_shares(),
        note="Documented default television split by development stage.",
    )
    session.add(rule)
    session.flush()
    return rule


def set_revenue_rule(
    session: Session, *, platform_share, host_share, participant_share, note: str = "admin rule"
) -> ClubLegacyRevenueRule:
    platform = Decimal(platform_share).quantize(SHARE_QUANTUM)
    host = Decimal(host_share).quantize(SHARE_QUANTUM)
    participant = Decimal(participant_share).quantize(SHARE_QUANTUM)
    if platform + host + participant != Decimal("1.000000"):
        raise LegacyError("allocation_mismatch", 409, "Platform, host, and participant shares must sum to 100 percent.")
    for row in session.scalars(select(ClubLegacyRevenueRule).where(ClubLegacyRevenueRule.active.is_(True))).all():
        row.active = False
    version = int(session.scalar(select(func.max(ClubLegacyRevenueRule.version))) or 0) + 1
    rule = ClubLegacyRevenueRule(
        version=version,
        active=True,
        platform_share=platform,
        host_share=host,
        participant_share=participant,
        stage_shares_json={},
        note=note,
    )
    session.add(rule)
    session.flush()
    return rule


def _assert_rule_sums(rule: ClubLegacyRevenueRule, stage: str | None) -> tuple[Decimal, Decimal, Decimal]:
    staged = (rule.stage_shares_json or {}).get(stage) if stage else None
    if staged:
        platform = Decimal(staged["platform"])
        host = Decimal(staged["host"])
        participant = Decimal(staged["participant"])
    else:
        platform = Decimal(rule.platform_share)
        host = Decimal(rule.host_share)
        participant = Decimal(rule.participant_share)
    if (platform + host + participant).quantize(SHARE_QUANTUM) != Decimal("1.000000"):
        raise LegacyError("allocation_mismatch", 500, "The active revenue rule does not sum to 100 percent.")
    return platform, host, participant


def _split_pool(pool: Decimal, platform_rate: Decimal, host_rate: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    platform = money(pool * platform_rate)
    host = money(pool * host_rate)
    participant = money(pool - platform - host)
    if platform + host + participant != pool:
        raise LegacyError("allocation_mismatch", 500)
    return platform, host, participant


def reject_related_clubs(session: Session, from_club_id: str, to_club_id: str, *, actor_user_id: str | None) -> None:
    home = session.get(ClubProfile, from_club_id)
    away = session.get(ClubProfile, to_club_id)
    if home is not None and away is not None and home.owner_user_id == away.owner_user_id:
        remember_refusal(
            session,
            club_id=from_club_id,
            actor_user_id=actor_user_id,
            action="related_club_refused",
            detail={"from_club_id": from_club_id, "to_club_id": to_club_id, "reason": "related_club_blocked"},
        )
        raise LegacyError("related_club_blocked", 409, "Clubs with the same owner cannot arrange this friendly.")


def reject_blocked_calendar(session: Session, match_on: str) -> None:
    from app.models.admin_rules import AdminCalendarRule

    rules = session.scalars(select(AdminCalendarRule).where(AdminCalendarRule.active.is_(True))).all()
    for rule in rules:
        for block in (rule.config_json or {}).get("blocked_ranges", []):
            if str(block.get("start")) <= match_on <= str(block.get("end")):
                raise LegacyError("calendar_blocked", 409, "The competition calendar blocks that date.")


def reject_manager_clash(session: Session, from_club_id: str, to_club_id: str, match_on: str) -> None:
    from app.owner_console.models import OwnerMatch

    committed = session.scalar(
        select(ClubLegacyManagerCommitment).where(
            ClubLegacyManagerCommitment.match_on == match_on,
            ClubLegacyManagerCommitment.club_id.in_([from_club_id, to_club_id]),
        )
    )
    if committed is not None:
        raise LegacyError("manager_unavailable", 409, "The football manager already has a match that day.")
    scheduled = session.scalars(
        select(OwnerMatch).where(
            OwnerMatch.status == "scheduled",
            or_(
                OwnerMatch.home_club_id.in_([from_club_id, to_club_id]),
                OwnerMatch.away_club_id.in_([from_club_id, to_club_id]),
            ),
        )
    ).all()
    for match in scheduled:
        played = match.played_at.date().isoformat() if match.played_at else None
        if played == match_on:
            raise LegacyError("manager_unavailable", 409, "The football manager already has a match that day.")


def open_window(session: Session, *, name: str, starts_on: str, ends_on: str) -> ClubLegacyPreseasonWindow:
    window = ClubLegacyPreseasonWindow(name=name, starts_on=starts_on, ends_on=ends_on, status="open")
    session.add(window)
    session.flush()
    return window


def _require_open_date(session: Session, window: ClubLegacyPreseasonWindow | None, match_on: str) -> None:
    if window is None or window.status != "open" or not (window.starts_on <= match_on <= window.ends_on):
        raise LegacyError("outside_window", 409, "That date is outside the pre-season window.")


def _record_event(
    session: Session,
    invite: ClubLegacyPreseasonInvite,
    *,
    status: str,
    actor_user_id: str | None,
    detail: dict | None = None,
) -> ClubLegacyPreseasonEvent:
    sequence = int(
        session.scalar(
            select(func.count()).select_from(ClubLegacyPreseasonEvent).where(ClubLegacyPreseasonEvent.invite_id == invite.id)
        )
        or 0
    ) + 1
    event = ClubLegacyPreseasonEvent(
        invite_id=invite.id,
        sequence=sequence,
        status=status,
        appearance_fee=invite.appearance_fee,
        match_on=invite.match_on,
        actor_user_id=actor_user_id,
        detail_json=detail or {},
    )
    session.add(event)
    return event


def _add_offer(session: Session, invite: ClubLegacyPreseasonInvite, *, status: str) -> ClubLegacyPreseasonOffer:
    sequence = int(
        session.scalar(
            select(func.count()).select_from(ClubLegacyPreseasonOffer).where(ClubLegacyPreseasonOffer.invite_id == invite.id)
        )
        or 0
    ) + 1
    offer = ClubLegacyPreseasonOffer(
        invite_id=invite.id,
        sequence=sequence,
        appearance_fee=invite.appearance_fee,
        match_on=invite.match_on,
        status=status,
    )
    session.add(offer)
    return offer


def invite_preseason(
    session: Session, *, window_id: str, from_club_id: str, to_club_id: str, match_on: str, appearance_fee, user_id: str
) -> ClubLegacyPreseasonInvite:
    require_owner(session, from_club_id, user_id)
    reject_related_clubs(session, from_club_id, to_club_id, actor_user_id=user_id)
    reject_blocked_calendar(session, match_on)
    reject_manager_clash(session, from_club_id, to_club_id, match_on)
    window = session.get(ClubLegacyPreseasonWindow, window_id)
    _require_open_date(session, window, match_on)
    conflict = session.scalar(
        select(ClubLegacyPreseasonInvite).where(
            ClubLegacyPreseasonInvite.match_on == match_on,
            ClubLegacyPreseasonInvite.status == "accepted",
            or_(
                ClubLegacyPreseasonInvite.from_club_id.in_([from_club_id, to_club_id]),
                ClubLegacyPreseasonInvite.to_club_id.in_([from_club_id, to_club_id]),
            ),
        )
    )
    if conflict is not None:
        raise LegacyError("date_conflict", 409, "One of the clubs already has a pre-season match that day.")
    invite = ClubLegacyPreseasonInvite(
        window_id=window_id,
        from_club_id=from_club_id,
        to_club_id=to_club_id,
        match_on=match_on,
        appearance_fee=money(appearance_fee),
        status="pending",
    )
    session.add(invite)
    session.flush()
    _add_offer(session, invite, status="open")
    _record_event(session, invite, status="pending", actor_user_id=user_id, detail={"kind": "invite"})
    session.flush()
    return invite


def _assert_gm(session: Session, club_id: str, amount: Decimal) -> None:
    policy = policy_for(session, club_id, PRESEASON_RESPONSE)
    if policy is None or policy.mode == "owner_only":
        raise LegacyError("manual_only", 409, "The owner still handles this task.")
    if policy.mode != "automatic":
        raise LegacyError("manual_only", 409, "The GM can accept only when pre-season is automatic.")
    gm = session.scalar(
        select(ClubLegacyExecutive).where(
            ClubLegacyExecutive.club_id == club_id,
            ClubLegacyExecutive.role == "gm",
            ClubLegacyExecutive.status == "hired",
        )
    )
    if gm is None:
        raise LegacyError("gm_unavailable", 409, "The club has no GM who can answer this invite.")
    if policy.max_amount is not None and amount > Decimal(policy.max_amount):
        raise LegacyError("over_threshold", 409, f"Appearance fee {amount} is outside the GM cap of {policy.max_amount}.")


def respond_preseason(
    session: Session,
    *,
    invite_id: str,
    user_id: str,
    decision: str,
    as_staff: bool = False,
    appearance_fee=None,
    match_on: str | None = None,
) -> ClubLegacyPreseasonInvite:
    invite = session.get(ClubLegacyPreseasonInvite, invite_id)
    if invite is None or invite.status not in {"pending", "countered"}:
        raise LegacyError("invite_not_open", 409)
    if decision == "counter":
        _counter(session, invite, user_id=user_id, appearance_fee=appearance_fee, match_on=match_on, as_staff=as_staff)
        return invite
    if decision not in {"reject", "accept"}:
        raise LegacyError("unknown_decision")
    if as_staff:
        _assert_gm(session, invite.to_club_id, Decimal(invite.appearance_fee))
    elif invite.status == "countered":
        require_owner(session, invite.from_club_id, user_id)
    else:
        require_owner(session, invite.to_club_id, user_id)
    if decision == "reject":
        invite.status = "rejected"
        _close_open_offers(session, invite, "rejected")
        _record_event(session, invite, status="rejected", actor_user_id=user_id)
    else:
        invite.status = "accepted"
        _close_open_offers(session, invite, "accepted")
        _record_event(session, invite, status="accepted", actor_user_id=user_id)
        _commit_manager(session, invite.from_club_id, invite.match_on, invite.id)
        _commit_manager(session, invite.to_club_id, invite.match_on, invite.id)
    session.flush()
    return invite


def _counter(
    session: Session,
    invite: ClubLegacyPreseasonInvite,
    *,
    user_id: str,
    appearance_fee,
    match_on: str | None,
    as_staff: bool,
) -> None:
    if appearance_fee is None or not match_on:
        raise LegacyError("counter_incomplete", 409, "A counter changes both the fee and the date.")
    if as_staff:
        _assert_gm(session, invite.to_club_id, Decimal(appearance_fee))
    else:
        require_owner(session, invite.to_club_id, user_id)
    previous_fee = str(invite.appearance_fee)
    previous_date = invite.match_on
    reject_blocked_calendar(session, match_on)
    reject_manager_clash(session, invite.from_club_id, invite.to_club_id, match_on)
    window = session.get(ClubLegacyPreseasonWindow, invite.window_id)
    _require_open_date(session, window, match_on)
    _close_open_offers(session, invite, "superseded")
    invite.appearance_fee = money(appearance_fee)
    invite.match_on = match_on
    invite.status = "countered"
    _add_offer(session, invite, status="open")
    _record_event(
        session,
        invite,
        status="countered",
        actor_user_id=user_id,
        detail={"previous_fee": previous_fee, "previous_match_on": previous_date},
    )
    session.flush()


def _close_open_offers(session: Session, invite: ClubLegacyPreseasonInvite, status: str) -> None:
    offers = session.scalars(
        select(ClubLegacyPreseasonOffer).where(
            ClubLegacyPreseasonOffer.invite_id == invite.id,
            ClubLegacyPreseasonOffer.status == "open",
        )
    ).all()
    for offer in offers:
        offer.status = status


def _commit_manager(session: Session, club_id: str, match_on: str, source_id: str) -> None:
    existing = session.scalar(
        select(ClubLegacyManagerCommitment).where(
            ClubLegacyManagerCommitment.club_id == club_id,
            ClubLegacyManagerCommitment.match_on == match_on,
        )
    )
    if existing is not None:
        return
    session.add(
        ClubLegacyManagerCommitment(club_id=club_id, match_on=match_on, source="preseason_invite", source_id=source_id)
    )


def _gift_split(session: Session, invite: ClubLegacyPreseasonInvite, gift_pool) -> tuple[Decimal, Decimal]:
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == invite.to_club_id))
    stage = development_stage_name(development_score(state.facilities_json if state else {}))
    gift = money(gift_pool)
    club_rate = TV_SHARES[stage]
    gift_club = money(gift * Decimal("0.40")) if stage == "foundation" else money(gift * club_rate)
    gift_platform = money(gift - gift_club)
    if gift_platform + gift_club != gift:
        raise LegacyError("allocation_mismatch", 500)
    return gift_platform, gift_club


def _same_pair_count(session: Session, invite: ClubLegacyPreseasonInvite) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(ClubLegacyPreseasonSettlement)
            .join(ClubLegacyPreseasonInvite, ClubLegacyPreseasonInvite.id == ClubLegacyPreseasonSettlement.invite_id)
            .where(
                ClubLegacyPreseasonInvite.window_id == invite.window_id,
                or_(
                    (ClubLegacyPreseasonInvite.from_club_id == invite.from_club_id)
                    & (ClubLegacyPreseasonInvite.to_club_id == invite.to_club_id),
                    (ClubLegacyPreseasonInvite.from_club_id == invite.to_club_id)
                    & (ClubLegacyPreseasonInvite.to_club_id == invite.from_club_id),
                ),
            )
        )
        or 0
    )


def settle_preseason(session: Session, *, invite_id: str, tv_pool, gift_pool=0) -> ClubLegacyPreseasonSettlement:
    existing = session.scalar(
        select(ClubLegacyPreseasonSettlement).where(ClubLegacyPreseasonSettlement.invite_id == invite_id)
    )
    if existing is not None:
        return existing
    invite = session.get(ClubLegacyPreseasonInvite, invite_id)
    if invite is None or invite.status != "accepted":
        raise LegacyError("invite_not_accepted", 409)
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == invite.to_club_id))
    stage = development_stage_name(development_score(state.facilities_json if state else {}))
    rule = ensure_revenue_rule(session)
    platform_rate, host_rate, _participant_rate = _assert_rule_sums(rule, stage)
    pool = money(tv_pool)
    platform, host, participants = _split_pool(pool, platform_rate, host_rate)
    gift_platform, gift_club = _gift_split(session, invite, gift_pool)
    reputation = 0 if _same_pair_count(session, invite) else 10
    settlement = ClubLegacyPreseasonSettlement(
        invite_id=invite.id,
        idempotency_key=f"preseason:{invite.id}",
        platform_amount=platform,
        host_amount=host,
        participant_amount=participants,
        reputation_delta=reputation,
        audience=100,
        gift_platform_amount=gift_platform,
        gift_club_amount=gift_club,
        rule_version=rule.version,
    )
    session.add(settlement)
    session.flush()
    _pay_share(
        session,
        source_name=ledger.PLATFORM_SPONSORS,
        destination_club_id=invite.from_club_id,
        amount=host,
        idempotency_key=f"preseason:{invite.id}:host",
        description="Pre-season host share",
    )
    _pay_share(
        session,
        source_name=ledger.PLATFORM_SPONSORS,
        destination_club_id=invite.to_club_id,
        amount=participants,
        idempotency_key=f"preseason:{invite.id}:participant",
        description="Pre-season participant share",
    )
    session.flush()
    return settlement


def _pay_share(session: Session, *, source_name: str, destination_club_id: str, amount: Decimal, idempotency_key: str, description: str) -> None:
    if amount <= 0:
        return
    source = ledger.wallet_account(session, source_name, ledger.GTEX)
    destination = ledger.wallet_account(session, ledger.club_account(destination_club_id), ledger.GTEX)
    post_club_legacy_transfer(
        session,
        idempotency_key=idempotency_key,
        source=source,
        destination=destination,
        amount=amount,
        description=description,
    )


def host_tournament(
    session: Session,
    *,
    window_id: str,
    host_club_id: str,
    name: str,
    match_on: str,
    user_id: str,
    participant_club_ids: list[str],
) -> ClubLegacyTournament:
    require_owner(session, host_club_id, user_id)
    if not participant_club_ids:
        raise LegacyError("participants_required", 409)
    window = session.get(ClubLegacyPreseasonWindow, window_id)
    _require_open_date(session, window, match_on)
    reject_blocked_calendar(session, match_on)
    for club_id in participant_club_ids:
        reject_related_clubs(session, host_club_id, club_id, actor_user_id=user_id)
        reject_manager_clash(session, host_club_id, club_id, match_on)
    tournament = ClubLegacyTournament(
        window_id=window_id, host_club_id=host_club_id, name=name, match_on=match_on, status="open"
    )
    session.add(tournament)
    session.flush()
    for club_id in participant_club_ids:
        session.add(ClubLegacyTournamentParticipant(tournament_id=tournament.id, club_id=club_id))
    session.flush()
    return tournament


def add_tournament_participant(
    session: Session, *, tournament_id: str, club_id: str, user_id: str
) -> ClubLegacyTournamentParticipant:
    tournament = session.get(ClubLegacyTournament, tournament_id)
    if tournament is None or tournament.status != "open":
        raise LegacyError("tournament_closed", 409)
    require_owner(session, tournament.host_club_id, user_id)
    reject_related_clubs(session, tournament.host_club_id, club_id, actor_user_id=user_id)
    reject_blocked_calendar(session, tournament.match_on)
    reject_manager_clash(session, tournament.host_club_id, club_id, tournament.match_on)
    window = session.get(ClubLegacyPreseasonWindow, tournament.window_id)
    _require_open_date(session, window, tournament.match_on)
    row = ClubLegacyTournamentParticipant(tournament_id=tournament.id, club_id=club_id)
    session.add(row)
    session.flush()
    return row


def settle_tournament(session: Session, *, tournament_id: str, tv_pool) -> ClubLegacyTournamentSettlement:
    existing = session.scalar(
        select(ClubLegacyTournamentSettlement).where(ClubLegacyTournamentSettlement.tournament_id == tournament_id)
    )
    if existing is not None:
        return existing
    tournament = session.get(ClubLegacyTournament, tournament_id)
    if tournament is None or tournament.status != "open":
        raise LegacyError("tournament_closed", 409)
    participants = session.scalars(
        select(ClubLegacyTournamentParticipant).where(ClubLegacyTournamentParticipant.tournament_id == tournament.id)
    ).all()
    if not participants:
        raise LegacyError("participants_required", 409)
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == tournament.host_club_id))
    stage = development_stage_name(development_score(state.facilities_json if state else {}))
    rule = ensure_revenue_rule(session)
    platform_rate, host_rate, _participant_rate = _assert_rule_sums(rule, stage)
    pool = money(tv_pool)
    platform, host, participant_pool = _split_pool(pool, platform_rate, host_rate)
    settlement = ClubLegacyTournamentSettlement(
        tournament_id=tournament.id,
        idempotency_key=f"tournament:{tournament.id}",
        rule_version=rule.version,
        platform_amount=platform,
        host_amount=host,
        participant_amount=participant_pool,
        audience=len(participants) * 100,
        reputation_delta=10,
    )
    session.add(settlement)
    tournament.status = "settled"
    session.flush()
    _pay_share(
        session,
        source_name=ledger.PLATFORM_SPONSORS,
        destination_club_id=tournament.host_club_id,
        amount=host,
        idempotency_key=f"tournament:{tournament.id}:host",
        description="Pre-season tournament host share",
    )
    remaining = participant_pool
    count = len(participants)
    for index, participant in enumerate(participants):
        if index == count - 1:
            share = remaining
        else:
            share = money(participant_pool / Decimal(count))
            remaining = money(remaining - share)
        _pay_share(
            session,
            source_name=ledger.PLATFORM_SPONSORS,
            destination_club_id=participant.club_id,
            amount=share,
            idempotency_key=f"tournament:{tournament.id}:participant:{participant.club_id}",
            description="Pre-season tournament participant share",
        )
    session.flush()
    return settlement


def invite_dict(invite: ClubLegacyPreseasonInvite) -> dict:
    return {
        "id": invite.id,
        "window_id": invite.window_id,
        "from_club_id": invite.from_club_id,
        "to_club_id": invite.to_club_id,
        "match_on": invite.match_on,
        "appearance_fee": str(invite.appearance_fee),
        "status": invite.status,
    }


def settlement_dict(row: ClubLegacyPreseasonSettlement) -> dict:
    return {
        "id": row.id,
        "invite_id": row.invite_id,
        "rule_version": row.rule_version,
        "platform_amount": str(row.platform_amount),
        "host_amount": str(row.host_amount),
        "participant_amount": str(row.participant_amount),
        "money": str(row.platform_amount + row.host_amount + row.participant_amount),
        "reputation_delta": row.reputation_delta,
        "audience": row.audience,
    }


def tournament_dict(row: ClubLegacyTournament, participants: list[str]) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "host_club_id": row.host_club_id,
        "match_on": row.match_on,
        "status": row.status,
        "participants": participants,
    }
