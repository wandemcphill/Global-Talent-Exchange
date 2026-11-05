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
    data = {
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
    if comp.host_type == "gtex":
        mapping = _active_owner_competition_mapping(session, comp.id)
        data["execution_model"] = "canonical"
        data["canonical_lifecycle_status"] = "active" if mapping is not None else "unmapped"
        data["history_read_only"] = mapping is None
        data["standings_source"] = "canonical" if mapping is not None else "legacy_historical"
        if mapping is not None:
            from decimal import Decimal

            from app.common.enums.competition_status import CompetitionStatus
            from app.models.competition import UserCompetition
            from app.models.competition_match import CompetitionMatch
            from app.models.competition_participant import CompetitionParticipant
            from app.models.competition_reward_pool import CompetitionRewardPool

            canonical = session.get(UserCompetition, mapping.canonical_competition_id)
            if canonical is None:
                data["canonical_lifecycle_status"] = "missing"
                data["canonical_status"] = "missing"
            else:
                canonical_status = str(canonical.status)
                data["canonical_competition_id"] = canonical.id
                data["canonical_status"] = canonical_status
                data["canonical_currency"] = canonical.currency
                data["canonical_format"] = canonical.format

                # Translate lifecycle state only for the existing owner-console UI
                # contract; all displayed result/standings data remains canonical.
                if canonical_status in {
                    CompetitionStatus.DRAFT.value,
                    CompetitionStatus.OPEN.value,
                    CompetitionStatus.OPEN_FOR_JOIN.value,
                    CompetitionStatus.PUBLISHED.value,
                    CompetitionStatus.SEEDED.value,
                    CompetitionStatus.FILLED.value,
                    CompetitionStatus.LOCKED.value,
                }:
                    data["status"] = "open"
                elif canonical_status in {CompetitionStatus.LIVE.value, CompetitionStatus.IN_PROGRESS.value}:
                    data["status"] = "running"
                elif canonical_status in {
                    CompetitionStatus.COMPLETED.value,
                    CompetitionStatus.SETTLED.value,
                    CompetitionStatus.CANCELLED.value,
                    CompetitionStatus.REFUNDED.value,
                    CompetitionStatus.DISPUTED.value,
                }:
                    data["status"] = "finished"

                canonical_participants = list(
                    session.scalars(
                        select(CompetitionParticipant).where(CompetitionParticipant.competition_id == canonical.id)
                    ).all()
                )
                canonical_club_ids = {participant.club_id for participant in canonical_participants}
                data["entrants"] = len(canonical_participants)
                data["my_club_ids"] = [
                    entry.club_id
                    for entry in rows
                    if user_id and entry.owner_user_id == user_id and entry.club_id in canonical_club_ids
                ]
                canonical_matches = list(
                    session.scalars(
                        select(CompetitionMatch).where(CompetitionMatch.competition_id == canonical.id)
                    ).all()
                )
                current_rounds = [
                    match.round_number for match in canonical_matches if match.status in {"scheduled", "in_progress"}
                ]
                data["current_round"] = (
                    min(current_rounds)
                    if current_rounds
                    else max((match.round_number for match in canonical_matches), default=0)
                )
                data["total_rounds"] = max((match.round_number for match in canonical_matches), default=0)
                data["entry_fee"] = str(Decimal(canonical.entry_fee_minor) / Decimal("10000"))
                pools = list(
                    session.scalars(
                        select(CompetitionRewardPool).where(CompetitionRewardPool.competition_id == canonical.id)
                    ).all()
                )
                prize_minor = (
                    sum(max(int(pool.amount_minor or 0), 0) for pool in pools)
                    if pools
                    else max(int(canonical.net_prize_pool_minor or 0), 0)
                )
                data["prize_pool"] = str(Decimal(prize_minor) / Decimal("10000"))
    else:
        data["execution_model"] = "user_hosted_legacy"
        data["canonical_lifecycle_status"] = "not_applicable"
    return data


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
    narrative = dict(m.narrative_json or {})
    persisted_tv = narrative.get("tv_revenue")
    if persisted_tv is None:
        persisted_tv = narrative.get("tv_revenue_gtex")
    if persisted_tv is None:
        persisted_tv = narrative.get("home_tv_revenue_gtex")
    if persisted_tv is None:
        persisted_tv = narrative.get("away_tv_revenue_gtex")
    tv_revenue_val = int(persisted_tv) if persisted_tv is not None else None
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
        "attendance": narrative.get("attendance"),
        "stadium_capacity": narrative.get("stadium_capacity"),
        "capacity_utilization_pct": narrative.get("capacity_utilization_pct"),
        "gate_receipts_gtex": narrative.get("gate_receipts_gtex"),
        "tv_revenue": tv_revenue_val,
        "tv_revenue_gtex": tv_revenue_val,
        "played_at": m.played_at.isoformat() if m.played_at else None,
    }
    if full:
        data["events"] = m.events_json
        data["narrative"] = m.narrative_json
    return data


def _active_owner_competition_mapping(session: Session, legacy_competition_id: str):
    from app.models.owner_competition_lifecycle_mapping import OwnerCompetitionLifecycleMapping

    return session.scalar(
        select(OwnerCompetitionLifecycleMapping).where(
            OwnerCompetitionLifecycleMapping.legacy_competition_id == legacy_competition_id,
            OwnerCompetitionLifecycleMapping.mapping_status == "active",
        )
    )


def _canonical_club_name(session: Session, club_id: str, legacy_match: OwnerMatch | None) -> str:
    if legacy_match is not None:
        if club_id == legacy_match.home_club_id:
            return legacy_match.home_name
        if club_id == legacy_match.away_club_id:
            return legacy_match.away_name
    from app.models.club_profile import ClubProfile

    club = session.get(ClubProfile, club_id)
    return club.club_name if club is not None else club_id


def _canonical_match_dict(
    session: Session,
    canonical_match,
    *,
    legacy_match: OwnerMatch | None = None,
    full: bool = False,
) -> dict[str, Any]:
    from app.common.enums.match_status import MatchStatus

    completed = canonical_match.status == MatchStatus.COMPLETED.value or canonical_match.completed_at is not None
    legacy_competition_id = legacy_match.competition_id if legacy_match is not None else None
    data = {
        "id": legacy_match.id if legacy_match is not None else canonical_match.id,
        "legacy_match_id": legacy_match.id if legacy_match is not None else None,
        "canonical_match_id": canonical_match.id,
        "competition_id": legacy_competition_id or canonical_match.competition_id,
        "canonical_competition_id": canonical_match.competition_id,
        "round": canonical_match.round_number,
        "home_club_id": canonical_match.home_club_id,
        "away_club_id": canonical_match.away_club_id,
        "home_name": _canonical_club_name(session, canonical_match.home_club_id, legacy_match),
        "away_name": _canonical_club_name(session, canonical_match.away_club_id, legacy_match),
        "status": canonical_match.status,
        "home_goals": canonical_match.home_score if completed else None,
        "away_goals": canonical_match.away_score if completed else None,
        "played_at": canonical_match.completed_at.isoformat() if canonical_match.completed_at else None,
        "execution_model": "canonical",
    }
    if full:
        from app.models.competition_match_event import CompetitionMatchEvent

        event_rows = session.scalars(
            select(CompetitionMatchEvent)
            .where(CompetitionMatchEvent.match_id == canonical_match.id)
            .order_by(CompetitionMatchEvent.minute.asc().nulls_last(), CompetitionMatchEvent.created_at.asc())
        ).all()
        data["events"] = [
            {
                "minute": event.minute,
                "type": event.event_type,
                "team": event.club_id,
                "player_id": event.player_id,
                "text": (event.metadata_json or {}).get("commentary", ""),
                "metadata": event.metadata_json,
            }
            for event in event_rows
        ]
        metadata = dict(canonical_match.metadata_json or {})
        data["narrative"] = metadata.get("match_viewer") or metadata.get("replay_payload") or {}
    return data


def mapped_match_dict(session: Session, legacy_match: OwnerMatch, *, full: bool = False) -> dict[str, Any]:
    from app.services.owner_competition_lifecycle_mapping_service import (
        OwnerCompetitionLifecycleMappingService,
    )

    canonical_match = OwnerCompetitionLifecycleMappingService(session).canonical_match_for_legacy_match(legacy_match.id)
    if canonical_match is None:
        data = match_dict(legacy_match, full=full)
        legacy_competition = session.get(OwnerCompetition, legacy_match.competition_id)
        if legacy_competition is not None and legacy_competition.host_type == "gtex":
            data.update(
                execution_model="legacy_historical",
                canonical_lifecycle_status="unmapped",
                history_read_only=True,
            )
        return data
    return _canonical_match_dict(session, canonical_match, legacy_match=legacy_match, full=full)


def canonical_match_detail(session: Session, canonical_match_id: str, *, full: bool = False):
    from app.models.competition_match import CompetitionMatch
    from app.models.owner_competition_lifecycle_mapping import (
        OwnerCompetitionLifecycleMapping,
        OwnerMatchLifecycleMapping,
    )

    canonical_match = session.get(CompetitionMatch, canonical_match_id)
    if canonical_match is None:
        return None
    competition_mapping = session.scalar(
        select(OwnerCompetitionLifecycleMapping).where(
            OwnerCompetitionLifecycleMapping.canonical_competition_id == canonical_match.competition_id,
            OwnerCompetitionLifecycleMapping.mapping_status == "active",
        )
    )
    if competition_mapping is None:
        return None
    match_mapping = session.scalar(
        select(OwnerMatchLifecycleMapping).where(
            OwnerMatchLifecycleMapping.canonical_match_id == canonical_match.id,
            OwnerMatchLifecycleMapping.competition_mapping_id == competition_mapping.id,
            OwnerMatchLifecycleMapping.mapping_status == "active",
        )
    )
    legacy_match = session.get(OwnerMatch, match_mapping.legacy_match_id) if match_mapping is not None else None
    return _canonical_match_dict(session, canonical_match, legacy_match=legacy_match, full=full)


def _canonical_competition_standings(session: Session, legacy_competition_id: str, canonical_competition_id: str):
    from app.models.competition_rule_set import CompetitionRuleSet
    from app.services.competition_match_service import CompetitionMatchService

    rule_set = session.scalar(
        select(CompetitionRuleSet).where(CompetitionRuleSet.competition_id == canonical_competition_id)
    )
    if rule_set is None:
        # An active mapping must never make legacy standings look authoritative.
        return []

    legacy_entries = {entry.club_id: entry for entry in entries(session, legacy_competition_id)}
    participants = CompetitionMatchService(session).standings(
        competition_id=canonical_competition_id,
        rule_set=rule_set,
    )
    rows = []
    for position, participant in enumerate(participants, start=1):
        legacy_entry = legacy_entries.get(participant.club_id)
        rows.append(
            {
                "club_id": participant.club_id,
                "club_name": (
                    legacy_entry.club_name
                    if legacy_entry is not None
                    else _canonical_club_name(session, participant.club_id, None)
                ),
                "is_ai": bool(legacy_entry.is_ai) if legacy_entry is not None else False,
                "owner_user_id": legacy_entry.owner_user_id if legacy_entry is not None else None,
                "played": participant.played,
                "won": participant.wins,
                "drawn": participant.draws,
                "lost": participant.losses,
                "gf": participant.goals_for,
                "ga": participant.goals_against,
                "points": participant.points,
                "eliminated": bool(legacy_entry.eliminated) if legacy_entry is not None else False,
                "final_position": position,
            }
        )
    return rows


def detail(session: Session, competition_id: str, user_id: str) -> dict[str, Any]:
    comp = session.get(OwnerCompetition, competition_id)
    if comp is None:
        raise OwnerError("competition_not_found", 404)
    matches = session.scalars(
        select(OwnerMatch).where(OwnerMatch.competition_id == comp.id).order_by(OwnerMatch.round_number.asc())
    ).all()
    mapping = _active_owner_competition_mapping(session, comp.id) if comp.host_type == "gtex" else None
    if mapping is None:
        return {
            **comp_dict(session, comp, user_id),
            "standings": standings(session, comp),
            "fixtures": [mapped_match_dict(session, match) for match in matches],
        }

    from app.models.competition import UserCompetition
    from app.models.competition_match import CompetitionMatch
    from app.models.owner_competition_lifecycle_mapping import OwnerMatchLifecycleMapping

    canonical_competition = session.get(UserCompetition, mapping.canonical_competition_id)
    if canonical_competition is None:
        raise OwnerError(
            "canonical_competition_not_found",
            409,
            "The global competition mapping references a missing canonical competition.",
        )
    legacy_matches_by_canonical_id = {
        link.canonical_match_id: session.get(OwnerMatch, link.legacy_match_id)
        for link in session.scalars(
            select(OwnerMatchLifecycleMapping).where(
                OwnerMatchLifecycleMapping.competition_mapping_id == mapping.id,
                OwnerMatchLifecycleMapping.mapping_status == "active",
            )
        ).all()
    }
    canonical_matches = session.scalars(
        select(CompetitionMatch)
        .where(CompetitionMatch.competition_id == canonical_competition.id)
        .order_by(CompetitionMatch.round_number.asc(), CompetitionMatch.scheduled_at.asc().nulls_last())
    ).all()
    return {
        **comp_dict(session, comp, user_id),
        "canonical_competition_id": canonical_competition.id,
        "canonical_status": canonical_competition.status,
        "canonical_lifecycle_status": "active",
        "standings": _canonical_competition_standings(session, comp.id, canonical_competition.id),
        "fixtures": [
            _canonical_match_dict(
                session,
                canonical_match,
                legacy_match=legacy_matches_by_canonical_id.get(canonical_match.id),
            )
            for canonical_match in canonical_matches
        ],
    }


def enter_competition(session: Session, user_id: str, competition_id: str, club_id: str) -> OwnerCompetitionEntry:
    state = require_state(session, club_id, user_id)
    if getattr(state, "stage", None) == "squad":
        raise OwnerError("sign_starting_squad_first", 409)
    from app.owner_console import service as owner_service

    formation = owner_service.get_club_formation_status(session, club_id)
    if not formation["is_formed"]:
        raise OwnerError(
            "minimum_squad_size_not_met",
            409,
            f"Club requires at least {owner_service.MIN_SQUAD} registered players with goalkeeper coverage (currently {formation['total_registered']}).",
        )
    comp = session.get(OwnerCompetition, competition_id)
    if comp is None:
        raise OwnerError("competition_not_found", 404)
    if comp.host_type == "gtex":
        raise OwnerError(
            "canonical_competition_mapping_required",
            409,
            "Global GTEX entry must be processed by the canonical competition system; the legacy owner-console entry and fee path is disabled.",
        )
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

    try:
        ledger.record(
            session,
            event_type="competition_entry_grant",
            source=ledger.COMPETITION_PRIZE_POOL,
            destination=ledger.club_account(club_id),
            currency=ledger.GTEX,
            gross=500,
            club_id=club_id,
            user_id=user_id,
            related_type="competition",
            related_id=comp.id,
            memo=f"Participation grant for entering {comp.name}",
        )
    except Exception as exc:
        logger.warning("competition_entry_grant failed: %s", exc)

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


def _side(
    session: Session,
    entry: OwnerCompetitionEntry,
    mentality: str | None,
    lineup_mode: str,
    *,
    is_home: bool | None = None,
) -> dict[str, Any]:
    if entry.is_ai:
        return {
            "name": entry.club_name,
            "strength": float(entry.strength),
            "mentality": "balanced",
            "scorers": [],
            "manager": None,
            "state": None,
            "xi": [],
            "campus_effects": {},
        }
    from app.owner_console import prestige_campus_comms

    state = get_state(session, entry.club_id)
    campus_effects = (
        prestige_campus_comms.compute_authoritative_campus_effects(session, state, reconcile=True)
        if state is not None
        else {}
    )
    players = [player_dict(p) for p in squad(session, entry.club_id)]
    strength = club_strength(
        players,
        (state.manager_json if state else None) or {},
        (state.facilities_json if state else None) or {},
        campus_effects=campus_effects,
    )
    venue_bonus = 0.0
    if is_home is True:
        venue_bonus = float(campus_effects.get("home_advantage_bonus", 0)) * 0.25
    elif is_home is False:
        venue_bonus = float(campus_effects.get("away_travel_readiness_pct", 0)) * 0.10
    value = round(strength["strength"] + venue_bonus - (6 if lineup_mode == "rotate" else 0), 2)
    xi = [p for p in players if p["id"] in strength["xi"]]
    scorers = [p["name"] for p in xi if p["position"].startswith(("forw", "midf", "att"))] or [p["name"] for p in xi]
    return {
        "name": entry.club_name,
        "strength": value,
        "mentality": mentality or (state.mentality if state else "balanced"),
        "scorers": scorers,
        "manager": state.manager_json if state else None,
        "state": state,
        "xi": strength["xi"],
        "avg_morale": strength["avg_morale"],
        "avg_fitness": strength.get("avg_fitness", 95.0),
        "campus_effects": campus_effects,
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
    from sqlalchemy.orm.attributes import flag_modified
    from app.owner_console import prestige_campus_comms

    state: OwnerClubState = side["state"]
    side_key = "home" if is_home else "away"
    existing_narrative = dict(match.narrative_json or {})
    if match.id and existing_narrative.get(f"{side_key}_settled_club_id") == state.club_id:
        return list(existing_narrative.get(f"{side_key}_settlement_notes") or [])

    campus_effects = side.get("campus_effects") or prestige_campus_comms.compute_authoritative_campus_effects(
        session, state, reconcile=True
    )
    notes = []
    result = 1 if gf > ga else 0 if gf == ga else -1

    stamina_ret_pct = int(campus_effects.get("stamina_retention_pct", 0))
    away_travel_pct = int(campus_effects.get("away_travel_readiness_pct", 0))
    injury_red_pct = int(campus_effects.get("injury_reduction_pct", 0))
    facs_dict = dict(state.facilities_json or {})
    med_level = int(facs_dict.get("medical", 1) or 1)
    med_director = dict((facs_dict.get("_executive_staff") or {}).get("medical_director") or {})
    med_expertise = int(med_director.get("medical_expertise", 10))
    base_fatigue = 14 + (0 if is_home else max(0, 3 - away_travel_pct // 8))
    effective_fatigue = max(4, int(round(base_fatigue * (1.0 - min(0.55, stamina_ret_pct / 100.0)))))

    injury_assessments: list[dict[str, Any]] = []
    match_injuries: list[dict[str, Any]] = []
    for p in squad(session, state.club_id):
        pers = dict(p.personality_json or {})
        cur_fitness = int(pers.get("fitness", 95))
        pre_existing_injured_days = int(p.injured_days or 0)
        if p.id in side["xi"] and pre_existing_injured_days <= 0:
            p.minutes += 90
            p.morale = int(engine.clamp(p.morale + result * 4 + 1, 0, 100))
            new_fitness = int(engine.clamp(cur_fitness - effective_fatigue, 25, 100))
            pers["fitness"] = new_fitness
            inj_eval = engine.evaluate_player_injury_risk(
                club_id=state.club_id,
                player_id=p.id,
                context_key=f"match:{match.id}",
                fitness=new_fitness,
                minutes_load=90,
                mentality=str(side.get("mentality") or state.mentality or "balanced"),
                medical_level=med_level,
                med_director_expertise=med_expertise,
                campus_injury_reduction_pct=injury_red_pct,
            )
            pers["last_injury_risk"] = inj_eval["effective_risk"]
            pers["unmitigated_injury_risk"] = inj_eval["unmitigated_risk"]
            pers["last_injury_match_id"] = match.id
            injury_assessments.append(
                {
                    "player_id": p.id,
                    "player_name": p.name,
                    "post_match_fitness": new_fitness,
                    "unmitigated_risk": inj_eval["unmitigated_risk"],
                    "effective_risk": inj_eval["effective_risk"],
                    "injury_reduction_pct": inj_eval["injury_reduction_pct"],
                    "injured": inj_eval["injured"],
                    "injured_days": inj_eval["injured_days"],
                }
            )
            if inj_eval["injured"]:
                p.injured_days = inj_eval["injured_days"]
                if inj_eval.get("injury_type"):
                    pers["last_injury_type"] = inj_eval["injury_type"]
                match_injuries.append(
                    {
                        "player_id": p.id,
                        "player_name": p.name,
                        "injured_days": p.injured_days,
                        "injury_type": pers.get("last_injury_type"),
                        "effective_risk": inj_eval["effective_risk"],
                    }
                )
                notes.append(f"Injury: {p.name} ({p.injured_days}d)")
        elif pre_existing_injured_days > 0:
            # Preserve existing injury state without overwriting or re-rolling
            p.injured_days = pre_existing_injured_days
        else:
            ambition = pers.get("ambition", 10) if p.is_regen else 10
            p.morale = int(engine.clamp(p.morale - (2 if ambition >= 14 else 0) + result, 0, 100))
            pers["fitness"] = int(engine.clamp(cur_fitness + 4, 25, 100))
        p.personality_json = pers
        flag_modified(p, "personality_json")

    state.fans = max(200, state.fans + result * 60 + gf * 15)
    state.prestige = int(engine.clamp(state.prestige + result, 0, 100))
    manager = dict(state.manager_json or {})
    if manager:
        manager["mood"] = int(engine.clamp(manager.get("mood", 70) + result * 5, 0, 100))
        state.manager_json = manager
    if is_home:
        stadium_level = int((state.facilities_json or {}).get("stadium", 1))
        matchday_rev_pct = int(campus_effects.get("matchday_revenue_bonus_pct", 15))
        vip_hospitality_gtex = int(campus_effects.get("vip_hospitality_flat_gtex", 0))
        att_info = engine.calculate_match_attendance(
            fans=state.fans,
            prestige=state.prestige,
            stadium_level=stadium_level,
            campus_effects=campus_effects,
            gf=gf,
            ga=ga,
        )
        attendance = att_info["attendance"]
        stadium_capacity = att_info["stadium_capacity"]
        gate = att_info["gate_receipts_gtex"]
        match_narrative = dict(match.narrative_json or {})
        match_narrative.update(
            {
                "attendance": attendance,
                "stadium_capacity": stadium_capacity,
                "raw_attendance_demand": att_info["raw_demand"],
                "capacity_utilization_pct": att_info["capacity_utilization_pct"],
                "sold_out": att_info["sold_out"],
                "gate_receipts_gtex": gate,
            }
        )
        match.narrative_json = match_narrative
        flag_modified(match, "narrative_json")
        ledger.record(
            session,
            event_type="gate_receipts",
            source=ledger.WORLD_CLUBS,
            destination=ledger.club_account(state.club_id),
            currency=ledger.GTEX,
            gross=gate,
            club_id=state.club_id,
            user_id=state.owner_user_id,
            related_type="match",
            related_id=match.id,
            memo=f"Gate receipts vs {match.away_name} (att {attendance:,}/{stadium_capacity:,}, +{matchday_rev_pct}% rev, VIP {vip_hospitality_gtex} GTX)",
        )
        notes.append(f"Attendance {attendance:,}/{stadium_capacity:,}")
        notes.append(f"Gate receipts {gate:,}")
    sponsor_bonus_pct = int(campus_effects.get("sponsor_revenue_bonus_pct", 0))
    for deal in session.scalars(
        select(OwnerSponsorDeal).where(OwnerSponsorDeal.club_id == state.club_id, OwnerSponsorDeal.status == "active")
    ).all():
        effective_deal_gross = Decimal(
            str(max(1, int(round(float(deal.per_match_gross) * (1.0 + sponsor_bonus_pct / 200.0)))))
        )
        ledger.record(
            session,
            event_type="endorsement_revenue" if deal.player_id else "sponsor_revenue",
            source=ledger.PLATFORM_SPONSORS,
            destination=ledger.club_account(state.club_id),
            currency=ledger.GTEX,
            gross=effective_deal_gross,
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

    # TV Broadcast Revenue
    broadcast_bonus_pct = int(campus_effects.get("broadcast_revenue_bonus_pct", 0))
    tv_rev = int(round((250 + state.prestige * 8) * (1.0 + broadcast_bonus_pct / 100.0)))
    try:
        ledger.record(
            session,
            event_type="tv_broadcast_revenue",
            source=ledger.TV_BROADCAST_POOL,
            destination=ledger.club_account(state.club_id),
            currency=ledger.GTEX,
            gross=tv_rev,
            club_id=state.club_id,
            user_id=state.owner_user_id,
            related_type="match",
            related_id=match.id,
            memo=f"TV broadcast distribution vs {match.away_name if is_home else match.home_name}",
        )
        notes.append(f"TV revenue {tv_rev:,}")
        match_narrative = dict(match.narrative_json or {})
        match_narrative[f"{side_key}_tv_revenue_gtex"] = tv_rev
        if is_home or "tv_revenue" not in match_narrative:
            match_narrative["tv_revenue"] = tv_rev
            match_narrative["tv_revenue_gtex"] = tv_rev
        match.narrative_json = match_narrative
        flag_modified(match, "narrative_json")
    except Exception as exc:
        logger.warning("tv_broadcast_revenue recording failed: %s", exc)

    # Settle pledged pre-match win bonus if victorious
    if result > 0:
        facs = dict(state.facilities_json or {})
        pledged_bonus = int(facs.get("_pledged_win_bonus_gtex", 0))
        if pledged_bonus > 0:
            facs["_pledged_win_bonus_gtex"] = 0
            state.facilities_json = facs
            try:
                ledger.record(
                    session,
                    event_type="owner_win_bonus_payout",
                    source=ledger.club_account(state.club_id),
                    destination=ledger.WORLD_CLUBS,
                    currency=ledger.GTEX,
                    gross=pledged_bonus,
                    club_id=state.club_id,
                    user_id=state.owner_user_id,
                    related_type="match",
                    related_id=match.id,
                    memo="Pledged win bonus paid for victory",
                )
                for p in squad(session, state.club_id):
                    p.morale = int(engine.clamp(p.morale + 4, 0, 100))
                notes.append(f"Pledged win bonus paid {pledged_bonus:,}")
            except Exception as exc:
                logger.warning("pledged_win_bonus payout failed: %s", exc)
        sponsor_win_clause = int((state.facilities_json or {}).get("_sponsor_win_bonus_clause_gtex", 0))
        if sponsor_win_clause > 0:
            try:
                ledger.record(
                    session,
                    event_type="sponsor_win_bonus",
                    source=ledger.PLATFORM_SPONSORS,
                    destination=ledger.club_account(state.club_id),
                    currency=ledger.GTEX,
                    gross=sponsor_win_clause,
                    club_id=state.club_id,
                    user_id=state.owner_user_id,
                    related_type="match",
                    related_id=match.id,
                    memo=f"Sponsor victory bonus clause ({(state.facilities_json or {}).get('_active_sponsor_name', 'Partner')})",
                )
                notes.append(f"Sponsor win bonus {sponsor_win_clause:,}")
            except Exception as exc:
                logger.warning("sponsor_win_bonus payout failed: %s", exc)

    final_narrative = dict(match.narrative_json or {})
    final_narrative[f"{side_key}_injury_assessments"] = injury_assessments
    final_narrative[f"{side_key}_injuries"] = match_injuries
    final_narrative[f"{side_key}_settled_club_id"] = state.club_id
    final_narrative[f"{side_key}_settlement_notes"] = list(notes)
    match.narrative_json = final_narrative
    flag_modified(match, "narrative_json")

    return notes


def ensure_owner_console_execution_allowed(comp: OwnerCompetition) -> None:
    """Keep global GTEX fixtures on the canonical CompetitionMatch execution rail."""
    if comp.host_type == "gtex":
        raise OwnerError(
            "global_competition_uses_canonical_lifecycle",
            409,
            "Global GTEX fixtures must be executed by the canonical CompetitionMatch lifecycle. "
            "The owner-console simulator is retained for historical reads and user-hosted tournaments "
            "until the explicit fixture mapping is available.",
        )


def _save_global_competition_tactics(
    session: Session,
    user_id: str,
    comp: OwnerCompetition,
    club_id: str,
    mentality: str,
    lineup_mode: str,
) -> dict[str, Any]:
    if mentality not in engine.MENTALITY:
        raise OwnerError("invalid_mentality")
    if comp.status != "running":
        raise OwnerError(
            "canonical_fixture_mapping_required",
            409,
            "Global GTEX competitions must be reconciled to scheduled canonical fixtures before tactics can be submitted.",
        )
    by_id = {entry.club_id: entry for entry in entries(session, comp.id)}
    if club_id not in by_id:
        raise OwnerError("club_not_entered", 409)

    round_matches = list(
        session.scalars(
            select(OwnerMatch).where(
                OwnerMatch.competition_id == comp.id,
                OwnerMatch.round_number == comp.current_round,
                OwnerMatch.status == "scheduled",
            )
        ).all()
    )
    my_match = next(
        (match for match in round_matches if club_id in (match.home_club_id, match.away_club_id)),
        None,
    )
    if my_match is None:
        raise OwnerError(
            "no_fixture_this_round",
            409,
            "Your club has no scheduled fixture in the current round.",
        )

    from app.services.owner_competition_lifecycle_mapping_service import (
        OwnerCompetitionLifecycleMappingError,
        OwnerCompetitionLifecycleMappingService,
    )

    try:
        canonical_match = OwnerCompetitionLifecycleMappingService(session).save_pre_match_tactics(
            legacy_match_id=my_match.id,
            club_id=club_id,
            user_id=user_id,
            mentality=mentality,
            lineup_mode=lineup_mode,
        )
    except OwnerCompetitionLifecycleMappingError as exc:
        raise OwnerError(exc.code, 409, exc.detail) from exc

    return {
        "execution": "canonical_fixture",
        "tactics_saved": True,
        "match": {
            "id": my_match.id,
            "legacy_match_id": my_match.id,
            "canonical_match_id": canonical_match.id,
            "competition_id": comp.id,
            "canonical_competition_id": canonical_match.competition_id,
            "round": canonical_match.round_number,
            "home_club_id": canonical_match.home_club_id,
            "away_club_id": canonical_match.away_club_id,
            "status": canonical_match.status,
            "home_goals": canonical_match.home_score,
            "away_goals": canonical_match.away_score,
            "played_at": None,
            "tactics": {
                "mentality": mentality,
                "lineup_mode": lineup_mode,
                "club_id": club_id,
            },
        },
        "competition": comp_dict(session, comp, user_id),
    }


def play_next(
    session: Session, user_id: str, competition_id: str, club_id: str, mentality: str, lineup_mode: str
) -> dict[str, Any]:
    state = require_state(session, club_id, user_id)
    comp = session.get(OwnerCompetition, competition_id)
    if comp is None:
        raise OwnerError("competition_not_found", 404)
    if comp.host_type == "gtex":
        return _save_global_competition_tactics(session, user_id, comp, club_id, mentality, lineup_mode)
    ensure_owner_console_execution_allowed(comp)
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
            is_home=True,
        )
        away = _side(
            session,
            away_e,
            mentality if m.away_club_id == club_id else None,
            lineup_mode if m.away_club_id == club_id else "strongest",
            is_home=False,
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
        if home["state"] is None:
            ai_att = engine.calculate_match_attendance(
                fans=int(home["strength"] * 40),
                prestige=int(home["strength"] * 0.7),
                stadium_level=1,
                campus_effects={},
                gf=hg,
                ga=ag,
            )
            narrative.update(
                {
                    "attendance": ai_att["attendance"],
                    "stadium_capacity": ai_att["stadium_capacity"],
                    "raw_attendance_demand": ai_att["raw_demand"],
                    "capacity_utilization_pct": ai_att["capacity_utilization_pct"],
                    "sold_out": ai_att["sold_out"],
                    "gate_receipts_gtex": ai_att["gate_receipts_gtex"],
                }
            )
        for side_key, side, entry_obj, gf, ga in (("home", home, home_e, hg, ag), ("away", away, away_e, ag, hg)):
            if side["state"] is not None:
                notes = _post_match_club(session, side, side_key == "home", gf, ga, m)
                narrative.update(dict(m.narrative_json or {}))
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
                expl["attendance"] = narrative.get("attendance")
                expl["stadium_capacity"] = narrative.get("stadium_capacity")
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
    if comp is not None and comp.host_type == "gtex":
        raise OwnerError(
            "global_competition_uses_canonical_lifecycle",
            409,
            "Global GTEX fixtures cannot be forfeited on the legacy owner-console rail.",
        )
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
