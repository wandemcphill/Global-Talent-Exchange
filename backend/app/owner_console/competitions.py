from __future__ import annotations

import logging
import secrets
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.owner_console import engine, ledger
from app.owner_console.models import (
    OwnerClubState,
    OwnerCompetition,
    OwnerCompetitionEntry,
    OwnerMatch,
    OwnerSponsorDeal,
)
from app.owner_console.engine import club_strength

logger = logging.getLogger(__name__)


from app.owner_console.service import (
    OwnerError,
    get_state,
    now,
    open_high_flags,
    player_dict,
    raise_flag,
    require_state,
    squad,
)

SEED = (
    {
        "name": "GTEX Lagos Launch Cup",
        "format": "league",
        "tier": "Launch",
        "entry_fee": 2000,
        "sponsored_pool": 20000,
        "max_clubs": 6,
        "description": "The flagship launch league. Six clubs, double prestige, platform-funded prize pool.",
    },
    {
        "name": "Naija Rising Stars League",
        "format": "league",
        "tier": "Development",
        "entry_fee": 0,
        "sponsored_pool": 5000,
        "max_clubs": 6,
        "description": "Free entry. Built for new owners and academy minutes.",
    },
    {
        "name": "Weekend Knockout Shield",
        "format": "knockout",
        "tier": "Cup",
        "entry_fee": 5000,
        "sponsored_pool": 15000,
        "max_clubs": 8,
        "description": "Eight-club single-elimination cup. Same-owner clubs are auto-routed apart.",
    },
)
PRIZE_SPLIT = (Decimal("0.5"), Decimal("0.3"), Decimal("0.2"))


def comp_account(competition_id: str) -> str:
    return f"competition:{competition_id}"


def ensure_seed(session: Session) -> None:
    for spec in SEED:
        open_exists = session.scalar(
            select(OwnerCompetition).where(
                OwnerCompetition.name == spec["name"], OwnerCompetition.status.in_(("open", "running"))
            )
        )
        if open_exists:
            continue
        comp = OwnerCompetition(
            host_type="gtex", prize_sensitive=spec["entry_fee"] > 0, **{k: v for k, v in spec.items()}
        )
        session.add(comp)
        session.flush()
        ledger.record(
            session,
            event_type="competition_pool_funding",
            source=ledger.PLATFORM_SPONSORS,
            destination=comp_account(comp.id),
            currency=ledger.GTEX,
            gross=spec["sponsored_pool"],
            related_type="competition",
            related_id=comp.id,
            memo=f"Platform-funded pool for {comp.name}",
        )
    session.flush()


def entries(session: Session, competition_id: str) -> list[OwnerCompetitionEntry]:
    return list(
        session.scalars(
            select(OwnerCompetitionEntry)
            .where(OwnerCompetitionEntry.competition_id == competition_id)
            .order_by(OwnerCompetitionEntry.created_at.asc())
        ).all()
    )


def comp_dict(session: Session, comp: OwnerCompetition, user_id: str | None = None) -> dict[str, Any]:
    rows = entries(session, comp.id)
    mine = [e.club_id for e in rows if user_id and e.owner_user_id == user_id]
    return {
        "id": comp.id,
        "name": comp.name,
        "host_type": comp.host_type,
        "format": comp.format,
        "tier": comp.tier,
        "entry_fee": str(comp.entry_fee),
        "prize_pool": str(ledger.balance(session, comp_account(comp.id), ledger.GTEX)),
        "platform_fee_bps": comp.platform_fee_bps,
        "max_clubs": comp.max_clubs,
        "entrants": len(rows),
        "allow_same_owner": comp.allow_same_owner,
        "prize_sensitive": comp.prize_sensitive,
        "status": comp.status,
        "current_round": comp.current_round,
        "total_rounds": comp.total_rounds,
        "description": comp.description,
        "invite_code": comp.invite_code if user_id and comp.host_user_id == user_id else None,
        "is_host": bool(user_id and comp.host_user_id == user_id),
        "my_club_ids": mine,
    }


def standings(session: Session, comp: OwnerCompetition) -> list[dict[str, Any]]:
    rows = entries(session, comp.id)
    rows.sort(key=lambda e: (e.final_position or 99, -e.points, -(e.goals_for - e.goals_against), -e.goals_for))
    return [
        {
            "club_id": e.club_id,
            "club_name": e.club_name,
            "is_ai": e.is_ai,
            "owner_user_id": e.owner_user_id,
            "played": e.played,
            "won": e.won,
            "drawn": e.drawn,
            "lost": e.lost,
            "gf": e.goals_for,
            "ga": e.goals_against,
            "points": e.points,
            "eliminated": e.eliminated,
            "final_position": e.final_position,
        }
        for e in rows
    ]


def match_dict(m: OwnerMatch, full: bool = False) -> dict[str, Any]:
    data = {
        "id": m.id,
        "competition_id": m.competition_id,
        "round": m.round_number,
        "home_club_id": m.home_club_id,
        "away_club_id": m.away_club_id,
        "home_name": m.home_name,
        "away_name": m.away_name,
        "status": m.status,
        "home_goals": m.home_goals,
        "away_goals": m.away_goals,
        "played_at": m.played_at.isoformat() if m.played_at else None,
    }
    if full:
        data["events"] = m.events_json
        data["narrative"] = m.narrative_json
    return data


def detail(session: Session, competition_id: str, user_id: str) -> dict[str, Any]:
    comp = session.get(OwnerCompetition, competition_id)
    if comp is None:
        raise OwnerError("competition_not_found", 404)
    matches = session.scalars(
        select(OwnerMatch).where(OwnerMatch.competition_id == comp.id).order_by(OwnerMatch.round_number.asc())
    ).all()
    return {
        **comp_dict(session, comp, user_id),
        "standings": standings(session, comp),
        "fixtures": [match_dict(m) for m in matches],
    }


def enter_competition(session: Session, user_id: str, competition_id: str, club_id: str) -> OwnerCompetitionEntry:
    state = require_state(session, club_id, user_id)
    if state.stage == "squad":
        raise OwnerError("sign_starting_squad_first", 409)
    comp = session.get(OwnerCompetition, competition_id)
    if comp is None:
        raise OwnerError("competition_not_found", 404)
    if comp.status != "open":
        raise OwnerError("competition_closed", 409)
    rows = entries(session, comp.id)
    if any(e.club_id == club_id for e in rows):
        raise OwnerError("already_entered", 409)
    if len(rows) >= comp.max_clubs:
        raise OwnerError("competition_full", 409)
    if not comp.allow_same_owner and any(e.owner_user_id == user_id for e in rows):
        raise OwnerError(
            "same_owner_bracket_blocked",
            409,
            "Clubs under common ownership cannot enter the same prize-sensitive bracket unless the format is explicitly labelled to allow it.",
        )
    if comp.entry_fee > 0:
        try:
            ledger.record(
                session,
                event_type="competition_entry_fee",
                source=ledger.club_account(club_id),
                destination=comp_account(comp.id),
                currency=ledger.GTEX,
                gross=comp.entry_fee,
                fee_bps=comp.platform_fee_bps,
                club_id=club_id,
                user_id=user_id,
                related_type="competition",
                related_id=comp.id,
                memo=f"Entry: {comp.name}",
            )
        except ledger.LedgerError as exc:
            raise OwnerError(str(exc), 402) from exc
    strength = club_strength(
        [player_dict(p) for p in squad(session, club_id)], state.manager_json or {}, state.facilities_json or {}
    )
    entry = OwnerCompetitionEntry(
        competition_id=comp.id,
        club_id=club_id,
        club_name=state.club_name,
        owner_user_id=user_id,
        strength=int(strength["strength"]),
    )
    session.add(entry)
    from app.owner_console.models import OwnerInboxItem

    for invite in session.scalars(
        select(OwnerInboxItem).where(
            OwnerInboxItem.club_id == club_id,
            OwnerInboxItem.kind == "competition_invite",
            OwnerInboxItem.status == "open",
        )
    ).all():
        if (invite.payload_json or {}).get("competition_id") == comp.id:
            invite.status, invite.resolution, invite.outcome_text, invite.resolved_at = (
                "resolved",
                "enter",
                "Entered.",
                now(),
            )
    if state.stage == "competition":
        state.stage = "active"
    session.flush()
    return entry


def host_competition(session: Session, user_id: str, payload: dict[str, Any]) -> OwnerCompetition:
    comp = OwnerCompetition(
        name=payload["name"],
        host_type="user",
        host_user_id=user_id,
        format=payload.get("format", "league"),
        tier="Friends",
        entry_fee=Decimal(str(payload.get("entry_fee", 0))),
        max_clubs=int(payload.get("max_clubs", 4)),
        allow_same_owner=bool(payload.get("allow_same_owner", False)),
        prize_sensitive=Decimal(str(payload.get("entry_fee", 0))) > 0,
        platform_fee_bps=1000,
        invite_code=secrets.token_hex(3).upper(),
        description=payload.get("description")
        or ("Same-owner clubs allowed (labelled)." if payload.get("allow_same_owner") else "One club per owner."),
    )
    session.add(comp)
    session.flush()
    return comp


def join_by_code(session: Session, user_id: str, code: str, club_id: str) -> OwnerCompetitionEntry:
    comp = session.scalar(select(OwnerCompetition).where(OwnerCompetition.invite_code == code.strip().upper()))
    if comp is None:
        raise OwnerError("invite_code_not_found", 404)
    return enter_competition(session, user_id, comp.id, club_id)


def _round_robin(ids: list[str]) -> list[list[tuple[str, str]]]:
    teams = list(ids) + (["BYE"] if len(ids) % 2 else [])
    rounds = []
    for r in range(len(teams) - 1):
        pairs = []
        for i in range(len(teams) // 2):
            a, b = teams[i], teams[-1 - i]
            if "BYE" not in (a, b):
                pairs.append((a, b) if r % 2 == 0 else (b, a))
        rounds.append(pairs)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    return rounds


def _knockout_pairs(rows: list[OwnerCompetitionEntry]) -> list[tuple[str, str]]:
    pool = list(rows)
    pairs = []
    while len(pool) >= 2:
        a = pool.pop(0)
        idx = next((i for i, b in enumerate(pool) if not (a.owner_user_id and a.owner_user_id == b.owner_user_id)), 0)
        b = pool.pop(idx)
        pairs.append((a.club_id, b.club_id))
    return pairs


def _start(session: Session, comp: OwnerCompetition) -> None:
    rows = entries(session, comp.id)
    rng = engine.seeded("fill", comp.id)
    names = [n for n in engine.AI_CLUBS if n not in {e.club_name for e in rows}]
    rng.shuffle(names)
    target = comp.max_clubs if comp.format == "league" else 8 if len(rows) > 4 else 4
    avg = int(sum(e.strength for e in rows) / len(rows)) if rows else 60
    while len(rows) < target:
        name = names.pop()
        entry = OwnerCompetitionEntry(
            competition_id=comp.id,
            club_id=f"ai:{name.lower().replace(' ', '-')}",
            club_name=name,
            is_ai=True,
            strength=avg + rng.randint(-7, 5),
        )
        session.add(entry)
        rows.append(entry)
    session.flush()
    by_id = {e.club_id: e for e in rows}
    if comp.format == "league":
        schedule = _round_robin([e.club_id for e in rows])
        for rnd, pairs in enumerate(schedule, start=1):
            for h, a in pairs:
                session.add(
                    OwnerMatch(
                        competition_id=comp.id,
                        round_number=rnd,
                        home_club_id=h,
                        away_club_id=a,
                        home_name=by_id[h].club_name,
                        away_name=by_id[a].club_name,
                    )
                )
        comp.total_rounds = len(schedule)
    else:
        for h, a in _knockout_pairs(rows):
            session.add(
                OwnerMatch(
                    competition_id=comp.id,
                    round_number=1,
                    home_club_id=h,
                    away_club_id=a,
                    home_name=by_id[h].club_name,
                    away_name=by_id[a].club_name,
                )
            )
        comp.total_rounds = {8: 3, 4: 2}.get(len(rows), 3)
    comp.status = "running"
    comp.current_round = 1
    session.flush()


def _side(session: Session, entry: OwnerCompetitionEntry, mentality: str | None, lineup_mode: str) -> dict[str, Any]:
    if entry.is_ai:
        return {
            "name": entry.club_name,
            "strength": float(entry.strength),
            "mentality": "balanced",
            "scorers": [],
            "manager": None,
            "state": None,
            "xi": [],
        }
    state = get_state(session, entry.club_id)
    players = [player_dict(p) for p in squad(session, entry.club_id)]
    strength = club_strength(players, state.manager_json or {}, state.facilities_json or {})
    value = strength["strength"] - (6 if lineup_mode == "rotate" else 0)
    xi = [p for p in players if p["id"] in strength["xi"]]
    scorers = [p["name"] for p in xi if p["position"].startswith(("forw", "midf", "att"))] or [p["name"] for p in xi]
    return {
        "name": entry.club_name,
        "strength": value,
        "mentality": mentality or state.mentality,
        "scorers": scorers,
        "manager": state.manager_json,
        "state": state,
        "xi": strength["xi"],
        "avg_morale": strength["avg_morale"],
    }


def _apply_result(entry: OwnerCompetitionEntry, gf: int, ga: int) -> None:
    entry.played += 1
    entry.goals_for += gf
    entry.goals_against += ga
    if gf > ga:
        entry.won += 1
        entry.points += 3
    elif gf == ga:
        entry.drawn += 1
        entry.points += 1
    else:
        entry.lost += 1


def _post_match_club(
    session: Session, side: dict[str, Any], is_home: bool, gf: int, ga: int, match: OwnerMatch
) -> list[str]:
    state: OwnerClubState = side["state"]
    notes = []
    result = 1 if gf > ga else 0 if gf == ga else -1
    for p in squad(session, state.club_id):
        if p.id in side["xi"]:
            p.minutes += 90
            p.morale = int(engine.clamp(p.morale + result * 4 + 1, 0, 100))
        else:
            ambition = (p.personality_json or {}).get("ambition", 10) if p.is_regen else 10
            p.morale = int(engine.clamp(p.morale - (2 if ambition >= 14 else 0) + result, 0, 100))
    state.fans = max(200, state.fans + result * 60 + gf * 15)
    state.prestige = int(engine.clamp(state.prestige + result, 0, 100))
    manager = dict(state.manager_json or {})
    if manager:
        manager["mood"] = int(engine.clamp(manager.get("mood", 70) + result * 5, 0, 100))
        state.manager_json = manager
    if is_home:
        gate = int(state.fans * 0.4 * int((state.facilities_json or {}).get("stadium", 1)))
        ledger.record(
            session,
            event_type="gate_receipts",
            source=ledger.WORLD_CLUBS,
            destination=ledger.club_account(state.club_id),
            currency=ledger.GTEX,
            gross=max(gate, 50),
            club_id=state.club_id,
            user_id=state.owner_user_id,
            related_type="match",
            related_id=match.id,
            memo=f"Gate receipts vs {match.away_name}",
        )
        notes.append(f"Gate receipts {max(gate, 50):,}")
    for deal in session.scalars(
        select(OwnerSponsorDeal).where(OwnerSponsorDeal.club_id == state.club_id, OwnerSponsorDeal.status == "active")
    ).all():
        ledger.record(
            session,
            event_type="endorsement_revenue" if deal.player_id else "sponsor_revenue",
            source=ledger.PLATFORM_SPONSORS,
            destination=ledger.club_account(state.club_id),
            currency=ledger.GTEX,
            gross=deal.per_match_gross,
            fee_bps=3000,
            club_id=state.club_id,
            user_id=state.owner_user_id,
            related_type="sponsor_deal",
            related_id=deal.id,
            memo=f"{deal.sponsor_name} ({deal.slot}) 70/30 split",
        )
        deal.matches_remaining -= 1
        if deal.matches_remaining <= 0:
            deal.status = "completed"
    return notes


def play_next(
    session: Session, user_id: str, competition_id: str, club_id: str, mentality: str, lineup_mode: str
) -> dict[str, Any]:
    state = require_state(session, club_id, user_id)
    comp = session.get(OwnerCompetition, competition_id)
    if comp is None:
        raise OwnerError("competition_not_found", 404)
    if mentality not in engine.MENTALITY:
        raise OwnerError("invalid_mentality")
    by_id = {e.club_id: e for e in entries(session, comp.id)}
    if club_id not in by_id:
        raise OwnerError("club_not_entered", 409)
    if comp.status == "open":
        _start(session, comp)
        by_id = {e.club_id: e for e in entries(session, comp.id)}
    if comp.status != "running":
        raise OwnerError("competition_finished", 409)
    round_matches = list(
        session.scalars(
            select(OwnerMatch).where(
                OwnerMatch.competition_id == comp.id,
                OwnerMatch.round_number == comp.current_round,
                OwnerMatch.status == "scheduled",
            )
        ).all()
    )
    my_match = next((m for m in round_matches if club_id in (m.home_club_id, m.away_club_id)), None)
    if my_match is None:
        raise OwnerError("no_fixture_this_round", 409, "Your club is not in this round (eliminated or bye).")
    if lineup_mode == "rotate" and comp.prize_sensitive:
        opponent_id = my_match.away_club_id if my_match.home_club_id == club_id else my_match.home_club_id
        opponent = by_id.get(opponent_id)
        if opponent and opponent.owner_user_id == user_id:
            raise_flag(
                session,
                user_id,
                club_id,
                "sister_club_lineup_weakening",
                "high",
                f"Rotated lineup against sister club {opponent.club_name} in prize-sensitive {comp.name}.",
                25,
                my_match.id,
            )
        else:
            recent = (state.manager_json or {}).get("rotations", 0) + 1
            manager = dict(state.manager_json or {})
            manager["rotations"] = recent
            state.manager_json = manager
            if recent >= 3:
                raise_flag(
                    session,
                    user_id,
                    club_id,
                    "repeated_lineup_weakening",
                    "medium",
                    f"Rotated lineup {recent} times in prize-sensitive competitions.",
                    10,
                    my_match.id,
                )
    played_mine = None
    for m in round_matches:
        home_e, away_e = by_id[m.home_club_id], by_id[m.away_club_id]
        home = _side(
            session,
            home_e,
            mentality if m.home_club_id == club_id else None,
            lineup_mode if m.home_club_id == club_id else "strongest",
        )
        away = _side(
            session,
            away_e,
            mentality if m.away_club_id == club_id else None,
            lineup_mode if m.away_club_id == club_id else "strongest",
        )
        sim = engine.simulate_match(m.id, home, away)
        hg, ag = sim["home_goals"], sim["away_goals"]
        if comp.format == "knockout" and hg == ag:
            rng = engine.seeded("pens", m.id)
            home_wins = rng.random() < home["strength"] / (home["strength"] + away["strength"])
            sim["events"].append(
                {
                    "minute": 120,
                    "type": "penalties",
                    "team": "home" if home_wins else "away",
                    "text": f"{home['name'] if home_wins else away['name']} win on penalties!",
                }
            )
            sim["penalty_winner"] = "home" if home_wins else "away"
        m.home_goals, m.away_goals, m.status, m.played_at = hg, ag, "played", now()
        m.events_json = sim["events"]
        _apply_result(home_e, hg, ag)
        _apply_result(away_e, ag, hg)
        narrative: dict[str, Any] = {
            "momentum": sim["momentum"],
            "expected_goals": sim["lambda"],
            "mentality": {"home": home["mentality"], "away": away["mentality"]},
        }
        for side_key, side, entry_obj, gf, ga in (("home", home, home_e, hg, ag), ("away", away, away_e, ag, hg)):
            if side["state"] is not None:
                notes = _post_match_club(session, side, side_key == "home", gf, ga, m)
                expl = engine.explain_match(
                    sim,
                    side_key,
                    home,
                    away,
                    {
                        "avg_morale": side.get("avg_morale", 60),
                        "training": int((side["state"].facilities_json or {}).get("training", 1)),
                    },
                )
                expl["manager_reaction"] = engine.manager_reaction(side["manager"] or {}, expl["result"])
                expl["revenue_notes"] = notes
                narrative[f"{side_key}_owner_view"] = expl
        if comp.format == "knockout":
            winner_home = hg > ag or (hg == ag and sim.get("penalty_winner") == "home")
            (away_e if winner_home else home_e).eliminated = True
        m.narrative_json = narrative
        from app.owner_console import storytelling

        if home.get("state") and away.get("state"):
            try:
                storytelling.record_match_news_article(session, m, home["state"], away["state"])
            except Exception as err:
                logger.warning("failed to record match news article: %s", err)
        if m.id == my_match.id:
            played_mine = m
    session.flush()
    _advance(session, comp)
    return {"match": match_dict(played_mine, full=True), "competition": comp_dict(session, comp, user_id)}


def _advance(session: Session, comp: OwnerCompetition) -> None:
    remaining = session.scalars(
        select(OwnerMatch).where(
            OwnerMatch.competition_id == comp.id,
            OwnerMatch.round_number == comp.current_round,
            OwnerMatch.status == "scheduled",
        )
    ).all()
    if remaining:
        return
    if comp.format == "league":
        if comp.current_round >= comp.total_rounds:
            _finalize(session, comp)
        else:
            comp.current_round += 1
        return
    alive = [e for e in entries(session, comp.id) if not e.eliminated]
    if len(alive) <= 1:
        _finalize(session, comp)
        return
    comp.current_round += 1
    by_id = {e.club_id: e for e in alive}
    for h, a in _knockout_pairs(alive):
        session.add(
            OwnerMatch(
                competition_id=comp.id,
                round_number=comp.current_round,
                home_club_id=h,
                away_club_id=a,
                home_name=by_id[h].club_name,
                away_name=by_id[a].club_name,
            )
        )
    session.flush()


def _finalize(session: Session, comp: OwnerCompetition) -> None:
    rows = entries(session, comp.id)
    if comp.format == "league":
        rows.sort(key=lambda e: (-e.points, -(e.goals_for - e.goals_against), -e.goals_for))
    else:
        rows.sort(key=lambda e: (e.eliminated, -e.won, -(e.goals_for - e.goals_against)))
    for pos, e in enumerate(rows, start=1):
        e.final_position = pos
    pot = ledger.balance(session, comp_account(comp.id), ledger.GTEX)
    for share, e in zip(PRIZE_SPLIT, rows[:3]):
        amount = ledger.D(pot * share)
        if amount <= 0:
            continue
        if e.is_ai:
            ledger.record(
                session,
                event_type="competition_unclaimed_prize",
                source=comp_account(comp.id),
                destination=ledger.PLATFORM_SPONSORS,
                currency=ledger.GTEX,
                gross=amount,
                related_type="competition",
                related_id=comp.id,
                memo=f"AI club {e.club_name} prize returned to pool",
                check_funds=False,
            )
            continue
        held = open_high_flags(session, e.owner_user_id) > 0
        ledger.record(
            session,
            event_type="competition_prize",
            source=comp_account(comp.id),
            destination=ledger.club_account(e.club_id),
            currency=ledger.GTEX,
            gross=amount,
            status="held" if held else "completed",
            club_id=e.club_id,
            user_id=e.owner_user_id,
            related_type="competition",
            related_id=comp.id,
            memo=f"{comp.name}: position {e.final_position}" + (" (held pending integrity review)" if held else ""),
            check_funds=False,
        )
        state = get_state(session, e.club_id)
        if state:
            state.prestige = int(engine.clamp(state.prestige + (4 - e.final_position) * 3, 0, 100))
    comp.status = "finished"
    session.flush()
    ensure_seed(session)


def forfeit(session: Session, user_id: str, match_id: str, club_id: str) -> dict[str, Any]:
    require_state(session, club_id, user_id)
    m = session.get(OwnerMatch, match_id)
    if m is None or club_id not in (m.home_club_id, m.away_club_id) or m.status != "scheduled":
        raise OwnerError("match_not_forfeitable", 409)
    comp = session.get(OwnerCompetition, m.competition_id)
    by_id = {e.club_id: e for e in entries(session, comp.id)}
    opp = by_id[m.away_club_id if m.home_club_id == club_id else m.home_club_id]
    mine = by_id[club_id]
    sister = opp.owner_user_id == user_id
    raise_flag(
        session,
        user_id,
        club_id,
        "sister_club_forfeit" if sister else "forfeit",
        "high" if sister else "medium",
        f"Forfeited {m.home_name} vs {m.away_name} in {comp.name}." + (" Opponent is a sister club." if sister else ""),
        30 if sister else 8,
        m.id,
    )
    is_home = m.home_club_id == club_id
    m.home_goals, m.away_goals = (0, 3) if is_home else (3, 0)
    m.status, m.played_at = "forfeited", now()
    m.events_json = [
        {
            "minute": 0,
            "type": "forfeit",
            "team": None,
            "text": f"{mine.club_name} forfeited. Awarded 3-0 to {opp.club_name}.",
        }
    ]
    _apply_result(mine, 0, 3)
    _apply_result(opp, 3, 0)
    mine.points -= 3
    if comp.format == "knockout":
        mine.eliminated = True
    session.flush()
    _advance(session, comp)
    return {
        "penalty": "0-3 loss, -3 points, integrity flag" + (" (high: sister club)" if sister else ""),
        "payouts_held": sister,
    }
