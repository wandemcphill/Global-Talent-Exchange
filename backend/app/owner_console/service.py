from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.club_profile import ClubProfile
from app.models.user import PublicAccountType, User
from app.owner_console import engine, ledger
from app.owner_console.ai import inbox_body
from app.owner_console.models import (
    IntegrityFlag,
    OwnerClubState,
    OwnerCompetition,
    OwnerCompetitionEntry,
    OwnerInboxItem,
    OwnerSponsorDeal,
    OwnerSquadPlayer,
    RelatedPartyTransfer,
)

MAX_CLUBS = 3
LAUNCH_GRANT_GTEX = 100_000
LAUNCH_GRANT_FAN = 1_000
MIN_SQUAD = 11
MAX_SQUAD = 30
PLATFORM_SALE_FEE_BPS = 500
SPONSOR_PLATFORM_BPS = 3000


class OwnerError(ValueError):
    def __init__(self, code: str, status: int = 400, detail: Any = None):
        super().__init__(code)
        self.code = code
        self.status = status
        self.detail = detail


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------- ownership + state ----------


def _require_normal_user_account(session: Session, user_id: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise OwnerError("user_not_found", 404)
    if user.account_type != PublicAccountType.USER:
        raise OwnerError("club_owner_account_type_required", 403)
    return user


def owned_profiles(session: Session, user_id: str) -> list[ClubProfile]:
    _require_normal_user_account(session, user_id)
    return list(
        session.scalars(
            select(ClubProfile).where(ClubProfile.owner_user_id == user_id).order_by(ClubProfile.created_at.asc())
        ).all()
    )


def require_profile(session: Session, club_id: str, user_id: str) -> ClubProfile:
    _require_normal_user_account(session, user_id)
    profile = session.get(ClubProfile, club_id)
    if profile is None:
        raise OwnerError("club_not_found", 404)
    if profile.owner_user_id != user_id:
        raise OwnerError("not_club_owner", 403)
    return profile


def get_state(session: Session, club_id: str) -> OwnerClubState | None:
    return session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))


def require_state(session: Session, club_id: str, user_id: str) -> OwnerClubState:
    require_profile(session, club_id, user_id)
    state = get_state(session, club_id)
    if state is None:
        raise OwnerError("club_not_activated", 409)
    return state


def user_states(session: Session, user_id: str) -> list[OwnerClubState]:
    _require_normal_user_account(session, user_id)
    return list(
        session.scalars(
            select(OwnerClubState)
            .where(OwnerClubState.owner_user_id == user_id)
            .order_by(OwnerClubState.created_at.asc())
        ).all()
    )


def start_activation(session: Session, user_id: str, club_id: str) -> OwnerClubState:
    profile = require_profile(session, club_id, user_id)
    existing = get_state(session, club_id)
    if existing:
        return existing
    if len(user_states(session, user_id)) >= MAX_CLUBS:
        raise OwnerError("club_ownership_cap_reached", 409)
    state = OwnerClubState(
        club_id=club_id,
        owner_user_id=user_id,
        club_name=profile.club_name,
        stage="squad",
        manager_json={},
        facilities_json={kind: 1 for kind in engine.FACILITY_KINDS},
        value_history_json=[],
    )
    session.add(state)
    session.flush()
    ledger.record(
        session,
        event_type="launch_grant",
        source=ledger.PLATFORM_GRANTS,
        destination=ledger.club_account(club_id),
        currency=ledger.GTEX,
        gross=LAUNCH_GRANT_GTEX,
        balance_class="promotional",
        club_id=club_id,
        user_id=user_id,
        related_type="club",
        related_id=club_id,
        memo="GTEX launch grant for first squad (promotional, non-withdrawable)",
    )
    if len(user_states(session, user_id)) == 1:
        ledger.record(
            session,
            event_type="launch_grant",
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.user_account(user_id),
            currency=ledger.FAN,
            gross=LAUNCH_GRANT_FAN,
            balance_class="promotional",
            user_id=user_id,
            memo="Welcome Fan Coin (promotional, non-withdrawable)",
        )
    return state


def claim_starter_club(
    session: Session,
    user,
    *,
    city_name: str | None = None,
    country_code: str | None = None,
    continent_code: str | None = None,
) -> OwnerClubState:
    """Give this account a runnable club and today's first decisions.

    An existing owner club is left as it is. Otherwise the oldest owned club
    profile is activated, or a starter profile is created, then a squad, the
    staff coach, and the free launch league are filled in and the world ticks
    once.
    """
    _require_normal_user_account(session, user.id)
    existing = user_states(session, user.id)
    if existing:
        return existing[0]
    profiles = owned_profiles(session, user.id)
    if profiles:
        state = start_activation(session, user.id, profiles[0].id)
    else:
        state = start_activation(
            session,
            user.id,
            _create_starter_profile(
                session, user, city_name=city_name, country_code=country_code, continent_code=continent_code
            ).id,
        )
    _bootstrap_starter_club(session, user.id, state)
    return state


def _create_starter_profile(
    session: Session,
    user,
    *,
    city_name: str | None = None,
    country_code: str | None = None,
    continent_code: str | None = None,
):
    from app.access_control.service import AccessControlService
    from app.auth.service import AuthService
    from app.clubs.ownership_cap import ClubOwnershipCapError, assert_can_acquire_club
    from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
    from app.services.club_dynasty_service import ClubDynastyService
    from app.services.club_reputation_service import ClubReputationService
    from app.club_legacy.delegation import LegacyError
    from app.club_legacy.full.phase1 import resolve_location
    from app.services.club_trophy_service import ClubTrophyService

    try:
        assert_can_acquire_club(session, user.id)
    except ClubOwnershipCapError as exc:
        raise OwnerError(exc.reason, 409) from exc
    try:
        city, country, continent = resolve_location(
            city_name=city_name, country_code=country_code, continent_code=continent_code
        )
    except LegacyError as exc:
        raise OwnerError(exc.code, exc.status, exc.detail) from exc
    label = (getattr(user, "display_name", None) or getattr(user, "username", None) or "Owner").strip()
    club_name = f"{label} FC"[:120]
    club = ClubProfile(
        owner_user_id=user.id,
        club_name=club_name,
        short_name=(label[:4] or "OWN").upper(),
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug=AuthService()._generate_unique_club_slug(session, club_name),
        primary_color="#0F766E",
        secondary_color="#F8FAFC",
        accent_color="#EA580C",
        country_code=country,
        continent_code=continent,
        city_name=city,
        visibility="public",
    )
    session.add(club)
    session.flush()
    ClubReputationService(session).ensure_profile(club.id)
    ClubDynastyService(session).ensure_progress(club.id)
    ClubTrophyService(session).ensure_cabinet(club.id)
    AccessControlService(session).ensure_club_organization(club, owner_user_id=user.id)
    session.flush()
    return club


def _bootstrap_starter_club(session: Session, user_id: str, state: OwnerClubState) -> None:
    from app.owner_console import competitions as comps

    if state.stage == "squad":
        _sign_starter_squad(session, state)
    if state.stage == "manager":
        appoint_manager(session, user_id, state.club_id, None)
    comps.ensure_seed(session)
    league = session.scalar(
        select(OwnerCompetition).where(
            OwnerCompetition.name == "Naija Rising Stars League",
            OwnerCompetition.status == "open",
        )
    )
    already_in = session.scalar(select(OwnerCompetitionEntry).where(OwnerCompetitionEntry.club_id == state.club_id))
    if league is not None and already_in is None and state.stage != "squad":
        comps.enter_competition(session, user_id, league.id, state.club_id)
    if state.last_tick_at is None and state.stage in ("competition", "active"):
        tick_club(session, state)
    if state.stage == "competition":
        state.stage = "active"


def _sign_starter_squad(session: Session, state: OwnerClubState) -> None:
    current = squad(session, state.club_id)
    needed = max(0, MIN_SQUAD - len(current))
    if needed:
        regens = engine.generate_regens(state.club_id, state.world_day, 1, 12, needed)
        has_keeper = any(p.position.startswith("goal") for p in current) or any(
            regen["position"].startswith("goal") for regen in regens
        )
        if regens and not has_keeper:
            regens[0]["position"] = "goalkeeper"
        for regen in regens:
            _add_regen(session, state.club_id, regen)
    _advance_stage_after_squad(session, state)


def squad(session: Session, club_id: str, include_inactive: bool = False) -> list[OwnerSquadPlayer]:
    stmt = select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)
    if not include_inactive:
        stmt = stmt.where(OwnerSquadPlayer.status.in_(("active", "listed")))
    return list(session.scalars(stmt.order_by(OwnerSquadPlayer.rating.desc())).all())


def player_dict(p: OwnerSquadPlayer, session: Session | None = None) -> dict[str, Any]:
    from app.owner_console import storytelling

    return {
        "id": p.id,
        "player_ref": p.player_ref,
        "name": p.name,
        "portrait_url": storytelling.resolve_player_portrait_url(session, p.id, p.name),
        "position": p.position,
        "age": p.age,
        "rating": p.rating,
        "potential": p.potential,
        "value_coin": str(p.value_coin),
        "morale": p.morale,
        "minutes": p.minutes,
        "injured_days": p.injured_days,
        "is_regen": p.is_regen,
        "status": p.status,
        "personality": p.personality_json if p.is_regen else None,
        "growth_log": (p.growth_log_json or [])[-6:],
        "acquired_via": p.acquired_via,
    }


def squad_value(players: list[OwnerSquadPlayer]) -> Decimal:
    return sum((Decimal(p.value_coin) for p in players), Decimal("0"))


def club_value(session: Session, state: OwnerClubState) -> Decimal:
    facilities = sum(int(v) for v in (state.facilities_json or {}).values()) * 4000
    cash = ledger.balance(session, ledger.club_account(state.club_id), ledger.GTEX)
    return ledger.D(squad_value(squad(session, state.club_id)) + facilities + cash * Decimal("0.5") + state.fans * 2)


def snapshot_value(session: Session, state: OwnerClubState) -> None:
    history = list(state.value_history_json or [])
    history.append([state.world_day, str(club_value(session, state))])
    state.value_history_json = history[-20:]


def player_quotes(session: Session, players: list) -> dict[str, tuple[int, int]]:
    from app.players.read_models import PlayerSummaryReadModel

    ids = [p.id for p in players]
    credits = (
        dict(
            session.execute(
                select(PlayerSummaryReadModel.player_id, PlayerSummaryReadModel.current_value_credits).where(
                    PlayerSummaryReadModel.player_id.in_(ids)
                )
            ).all()
        )
        if ids
        else {}
    )
    return {p.id: engine.market_quote(p.market_value_eur, credits.get(p.id)) for p in players}


def sign_market_player(session: Session, user_id: str, club_id: str, player_id: str) -> OwnerSquadPlayer:
    from app.ingestion.models import Player

    state = require_state(session, club_id, user_id)
    current = squad(session, club_id)
    if len(current) >= MAX_SQUAD:
        raise OwnerError("squad_full")
    if any(p.player_ref == player_id for p in current):
        raise OwnerError("player_already_in_squad", 409)
    rival = session.scalar(
        select(OwnerSquadPlayer).where(
            OwnerSquadPlayer.player_ref == player_id,
            OwnerSquadPlayer.status.in_(("active", "listed")),
            OwnerSquadPlayer.club_id != club_id,
        )
    )
    if rival:
        raise OwnerError("player_owned_by_another_gtex_club", 409)
    player = session.get(Player, player_id)
    if player is None:
        raise OwnerError("player_not_found", 404)
    price, rating = player_quotes(session, [player])[player_id]
    try:
        ledger.record(
            session,
            event_type="transfer_purchase",
            source=ledger.club_account(club_id),
            destination=ledger.WORLD_MARKET,
            currency=ledger.GTEX,
            gross=price,
            club_id=club_id,
            user_id=user_id,
            related_type="player",
            related_id=player_id,
            memo=f"Signed {player.full_name}",
        )
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    age = 24
    if player.date_of_birth:
        age = max(16, now().year - player.date_of_birth.year)
    signed = OwnerSquadPlayer(
        club_id=club_id,
        player_ref=player_id,
        name=player.canonical_display_name or player.full_name,
        position=engine.normalize_position(player.normalized_position or player.position),
        age=age,
        rating=rating,
        potential=max(rating, int(player.potential or rating + 3)),
        value_coin=Decimal(price),
        morale=72,
        acquired_via="market",
    )
    session.add(signed)
    session.flush()
    _advance_stage_after_squad(session, state)
    return signed


def unsign_market_player(session: Session, user_id: str, club_id: str, player_id: str) -> dict[str, Any]:
    state = require_state(session, club_id, user_id)
    current = squad(session, club_id)
    target = next(
        (p for p in current if p.player_ref == player_id or p.id == player_id or str(p.id) == str(player_id)), None
    )
    if target is None:
        raise OwnerError("player_not_in_squad", 404)

    refund_amount = int(target.value_coin or 0)
    if refund_amount > 0:
        ledger.record(
            session,
            event_type="transfer_refund",
            source=ledger.WORLD_MARKET,
            destination=ledger.club_account(club_id),
            currency=ledger.GTEX,
            gross=refund_amount,
            club_id=club_id,
            user_id=user_id,
            related_type="player",
            related_id=target.player_ref or target.id,
            memo=f"Released {target.name} (refund)",
        )

    session.delete(target)
    session.flush()

    remaining = squad(session, club_id)
    has_keeper = any(p.position.startswith("goal") for p in remaining)
    if len(remaining) < MIN_SQUAD or not has_keeper:
        if state.stage == "manager":
            state.stage = "squad"

    return {
        "released_player_id": player_id,
        "refunded": refund_amount,
        "refund_amount": refund_amount,
        "squad_size": len(remaining),
        "stage": state.stage,
        "cash": str(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)),
    }


def autopick_squad(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    from app.ingestion.models import Player
    from app.players.read_models import PlayerSummaryReadModel

    state = require_state(session, club_id, user_id)
    current = squad(session, club_id)
    non_regens = [p for p in current if not p.is_regen]
    slots_needed = MIN_SQUAD - len(non_regens)
    if slots_needed <= 0:
        return {
            "signed": [],
            "signed_count": 0,
            "squad_size": len(current),
            "stage": state.stage,
            "cash": str(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)),
        }

    club_cash = int(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX))
    has_keeper = any(p.position.startswith("goal") for p in current)
    signed_refs = {p.player_ref for p in current if p.player_ref}

    query = (
        select(Player)
        .join(PlayerSummaryReadModel, Player.id == PlayerSummaryReadModel.player_id)
        .order_by(PlayerSummaryReadModel.current_value_credits.asc())
    )
    if signed_refs:
        query = query.where(Player.id.not_in(signed_refs))

    candidates = list(session.scalars(query.limit(300)).all())
    quotes_map = player_quotes(session, candidates)

    rival_refs = set(
        session.scalars(
            select(OwnerSquadPlayer.player_ref).where(
                OwnerSquadPlayer.player_ref.in_([c.id for c in candidates]),
                OwnerSquadPlayer.status.in_(("active", "listed")),
                OwnerSquadPlayer.club_id != club_id,
            )
        ).all()
    )

    eligible = [c for c in candidates if c.id not in rival_refs and quotes_map.get(c.id, (999999, 0))[0] > 0]

    selected_players = []
    remaining_budget = club_cash

    if not has_keeper:
        gk_candidate = next(
            (c for c in eligible if engine.normalize_position(c.normalized_position or c.position).startswith("goal")),
            None,
        )
        if gk_candidate:
            cost = quotes_map[gk_candidate.id][0]
            if cost <= remaining_budget:
                selected_players.append(gk_candidate)
                remaining_budget -= cost
                eligible = [c for c in eligible if c.id != gk_candidate.id]

    for c in eligible:
        if len(selected_players) >= slots_needed:
            break
        cost = quotes_map[c.id][0]
        if cost <= remaining_budget:
            selected_players.append(c)
            remaining_budget -= cost

    signed_results = []
    for player in selected_players:
        signed = sign_market_player(session, user_id, club_id, player.id)
        signed_results.append(player_dict(signed))

    final_squad = squad(session, club_id)
    return {
        "signed": signed_results,
        "signed_count": len(signed_results),
        "squad_size": len(final_squad),
        "stage": state.stage,
        "cash": str(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)),
    }


def _advance_stage_after_squad(session: Session, state: OwnerClubState) -> None:
    players = squad(session, state.club_id)
    if state.stage == "squad" and len(players) >= MIN_SQUAD and any(p.position.startswith("goal") for p in players):
        state.stage = "manager"
        regens = engine.generate_regens(state.club_id, state.world_day, 1, 10, 3)
        for regen in regens:
            _add_regen(session, state.club_id, regen)


def _add_regen(session: Session, club_id: str, regen: dict[str, Any]) -> OwnerSquadPlayer:
    player = OwnerSquadPlayer(
        club_id=club_id,
        name=regen["name"],
        position=regen["position"],
        age=regen["age"],
        rating=regen["rating"],
        potential=regen["potential"],
        value_coin=Decimal(engine.regen_value(regen["rating"], regen["potential"], regen["age"])),
        morale=75,
        is_regen=True,
        personality_json=regen["personality"],
        acquired_via="academy",
    )
    session.add(player)
    session.flush()
    return player


def appoint_manager(session: Session, user_id: str, club_id: str, snapshot: dict[str, Any] | None) -> OwnerClubState:
    state = require_state(session, club_id, user_id)
    if state.stage == "squad":
        raise OwnerError("sign_starting_squad_first", 409)
    profile = engine.manager_profile(snapshot or engine.DEFAULT_MANAGER)
    if (
        state.manager_json
        and not state.manager_json.get("is_default")
        and state.manager_json.get("manager_id") != profile["manager_id"]
    ):
        raise OwnerError("fire_current_manager_first", 409)
    state.manager_json = profile
    if state.stage == "manager":
        state.stage = "competition"
    _morale_shift(session, club_id, 3)
    return state


def fire_manager(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    state = require_state(session, club_id, user_id)
    current = state.manager_json or {}
    if not current or current.get("is_default"):
        raise OwnerError("no_appointed_manager")
    compensation = 2_000 + int(current.get("loyalty", 10)) * 100
    try:
        ledger.record(
            session,
            event_type="manager_compensation",
            source=ledger.club_account(club_id),
            destination=ledger.WORLD_CLUBS,
            currency=ledger.GTEX,
            gross=compensation,
            club_id=club_id,
            user_id=user_id,
            related_type="manager",
            related_id=current.get("manager_id"),
            memo=f"Severance for {current.get('name')}",
        )
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    state.manager_json = engine.manager_profile(engine.DEFAULT_MANAGER)
    _morale_shift(session, club_id, -6)
    return {
        "compensation": compensation,
        "why": "Dismissal triggers contract compensation and unsettles the dressing room (-6 morale).",
    }


def _morale_shift(session: Session, club_id: str, delta: int, player_id: str | None = None) -> None:
    for p in squad(session, club_id):
        if player_id is None or p.id == player_id:
            p.morale = int(engine.clamp(p.morale + delta, 0, 100))


def facility_cost(level: int) -> int:
    return int(5_000 * (level**1.6))


def upgrade_facility(session: Session, user_id: str, club_id: str, kind: str) -> dict[str, Any]:
    if kind not in engine.FACILITY_KINDS:
        raise OwnerError("unknown_facility")
    state = require_state(session, club_id, user_id)
    facilities = dict(state.facilities_json or {})
    level = int(facilities.get(kind, 1))
    if level >= 5:
        raise OwnerError("facility_max_level")
    cost = facility_cost(level)
    try:
        ledger.record(
            session,
            event_type="facility_spend",
            source=ledger.club_account(club_id),
            destination=ledger.WORLD_CLUBS,
            currency=ledger.GTEX,
            gross=cost,
            club_id=club_id,
            user_id=user_id,
            related_type="facility",
            related_id=kind,
            memo=f"{kind.title()} upgraded to level {level + 1}",
        )
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    facilities[kind] = level + 1
    state.facilities_json = facilities
    from app.owner_console import storytelling

    storytelling.record_verified_broadcast_event(
        session,
        event_type="facility_upgrade",
        club_id=club_id,
        owner_user_id=user_id,
        item_name=f"{kind.title()} Facility Level {level + 1}",
        item_image_url=storytelling.resolve_showroom_image_url(kind),
        verified_price_gtex=cost,
        idempotency_key=f"facility:{club_id}:{kind}:{level + 1}",
        payload_json={"facility_kind": kind, "facility_level": level + 1},
    )
    manager = dict(state.manager_json or {})
    if manager:
        manager["mood"] = int(engine.clamp(manager.get("mood", 70) + 6, 0, 100))
        state.manager_json = manager
    effects = {
        "training": "Faster growth for every player, especially regens with high environment sensitivity.",
        "academy": "Bigger and higher-potential academy intakes.",
        "medical": "Shorter injuries and a small matchday strength boost.",
        "stadium": "Higher gate receipts and fan growth.",
        "commercial": "Better sponsor offers and endorsement value.",
    }
    return {"kind": kind, "level": level + 1, "cost": cost, "effect": effects[kind]}


def academy_intake(session: Session, user_id: str, club_id: str) -> list[OwnerSquadPlayer]:
    state = require_state(session, club_id, user_id)
    level = int((state.facilities_json or {}).get("academy", 1))
    cost = 1_500 * level
    try:
        ledger.record(
            session,
            event_type="academy_intake",
            source=ledger.club_account(club_id),
            destination=ledger.WORLD_CLUBS,
            currency=ledger.GTEX,
            gross=cost,
            club_id=club_id,
            user_id=user_id,
            related_type="academy",
            related_id=str(state.world_day),
            memo="Academy scouting intake",
        )
    except ledger.LedgerError as exc:
        raise OwnerError(str(exc), 402) from exc
    youth = int((state.manager_json or {}).get("youth_development", 10))
    state.world_day += 1
    return [
        _add_regen(session, club_id, r)
        for r in engine.generate_regens(club_id, state.world_day, level, youth, 1 + level // 2)
    ]


# ---------- integrity ----------


def integrity_score(session: Session, user_id: str) -> int:
    impact = (
        session.scalar(
            select(func.coalesce(func.sum(IntegrityFlag.score_impact), 0)).where(
                IntegrityFlag.user_id == user_id, IntegrityFlag.status.in_(("open", "actioned"))
            )
        )
        or 0
    )
    return int(engine.clamp(100 - int(impact), 0, 100))


def open_high_flags(session: Session, user_id: str) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(IntegrityFlag)
            .where(IntegrityFlag.user_id == user_id, IntegrityFlag.status == "open", IntegrityFlag.severity == "high")
        )
        or 0
    )


def raise_flag(
    session: Session,
    user_id: str,
    club_id: str | None,
    flag_type: str,
    severity: str,
    detail: str,
    impact: int,
    related: str | None = None,
) -> IntegrityFlag:
    flag = IntegrityFlag(
        user_id=user_id,
        club_id=club_id,
        flag_type=flag_type,
        severity=severity,
        detail=detail,
        score_impact=impact,
        related_object_id=related,
    )
    session.add(flag)
    session.flush()
    return flag


def disclosures(session: Session, club_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(RelatedPartyTransfer)
        .where((RelatedPartyTransfer.from_club_id == club_id) | (RelatedPartyTransfer.to_club_id == club_id))
        .order_by(RelatedPartyTransfer.created_at.desc())
    ).all()
    return [
        {
            "id": r.id,
            "from_club_id": r.from_club_id,
            "to_club_id": r.to_club_id,
            "player_name": r.player_name,
            "fair_value": str(r.fair_value),
            "fee": str(r.fee),
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


def group_label(session: Session, user_id: str) -> dict[str, Any] | None:
    states = user_states(session, user_id)
    if len(states) < 2:
        return None
    return {
        "label": f"Multi-club ownership group ({len(states)} clubs)",
        "club_ids": [s.club_id for s in states],
        "club_names": [s.club_name for s in states],
    }


# ---------- world tick + inbox ----------


def _open_item_exists(session: Session, club_id: str, kind: str, subject: str | None = None) -> bool:
    stmt = select(OwnerInboxItem).where(
        OwnerInboxItem.club_id == club_id, OwnerInboxItem.kind == kind, OwnerInboxItem.status == "open"
    )
    items = session.scalars(stmt).all()
    if subject is None:
        return bool(items)
    return any((i.payload_json or {}).get("subject") == subject for i in items)


def _item(
    user_id: str,
    club_id: str,
    kind: str,
    *,
    sender: str,
    title: str,
    what: str,
    why: str,
    actions: list[dict[str, str]],
    payload: dict[str, Any],
    priority: str = "normal",
    prompt: str | None = None,
) -> tuple[OwnerInboxItem, str | None]:

    cat_map = {
        "manager_meeting": "staff_recommendations",
        "manager_request": "staff_recommendations",
        "facility_request": "staff_recommendations",
        "player_unrest": "player_issues",
        "regen_breakthrough": "player_issues",
        "scouting_report": "scouting_reports",
        "contract_negotiation": "negotiations",
        "transfer_bid": "negotiations",
        "competition_invite": "scheduling",
        "match_schedule": "scheduling",
        "sponsor_opportunity": "requests",
        "regen_endorsement": "requests",
    }
    resolved_category = cat_map.get(kind, "requests")
    item = OwnerInboxItem(
        user_id=user_id,
        club_id=club_id,
        save_context_id=f"club:{club_id}" if club_id else None,
        category=resolved_category,
        kind=kind,
        sender=sender,
        title=title,
        what=what,
        why=why,
        actions_json=actions,
        payload_json=payload,
        priority=priority,
        is_decision=bool(actions),
    )
    return item, prompt


def tick_club(session: Session, state: OwnerClubState, use_ai: bool = True) -> dict[str, Any]:
    state.world_day += 1
    state.last_tick_at = now()
    rng = engine.seeded("tick", state.club_id, state.world_day)
    manager = state.manager_json or engine.manager_profile(engine.DEFAULT_MANAGER)
    facilities = state.facilities_json or {}
    players = squad(session, state.club_id)
    entries = (
        session.scalar(
            select(func.count())
            .select_from(OwnerCompetitionEntry)
            .where(OwnerCompetitionEntry.club_id == state.club_id)
        )
        or 0
    )
    ctx = {
        "training": int(facilities.get("training", 1)),
        "manager_youth": int(manager.get("youth_development", 10)),
        "competition_quality": min(1.0, 0.3 + entries * 0.2),
        "prestige": state.prestige,
    }
    pending: list[tuple[OwnerInboxItem, str | None]] = []
    growth_report = []
    for p in players:
        if p.injured_days > 0:
            p.injured_days = max(0, p.injured_days - (1 + int(facilities.get("medical", 1)) // 2))
        if not p.is_regen:
            continue
        pdata = player_dict(p)
        pdata["personality"] = dict(p.personality_json)
        result = engine.regen_growth(pdata, ctx)
        p.personality_json = pdata["personality"]
        if result["points"]:
            p.rating += result["points"]
            p.value_coin = Decimal(engine.regen_value(p.rating, p.potential, p.age))
        log = list(p.growth_log_json or [])
        log.append(
            {
                "day": state.world_day,
                "gain": result["points"],
                "rating": p.rating,
                "explanation": result["explanation"],
                "drivers": result["drivers"],
            }
        )
        p.growth_log_json = log[-12:]
        growth_report.append({"player": p.name, **result})
        traits = p.personality_json
        if result["points"] >= 2 or (result["points"] and p.rating in (60, 65, 70, 75, 80)):
            if not _open_item_exists(session, state.club_id, "regen_breakthrough", p.id):
                pending.append(
                    _item(
                        state.owner_user_id,
                        state.club_id,
                        "regen_breakthrough",
                        sender=manager["name"],
                        title=f"Breakthrough: {p.name} jumps to {p.rating}",
                        what=f"{p.name} ({p.age}, {p.position}) gained {result['points']} rating points this week.",
                        why=result["explanation"],
                        actions=[
                            {
                                "key": "new_contract",
                                "label": "Offer improved academy contract (1,000)",
                                "style": "primary",
                            },
                            {"key": "acknowledge", "label": "Acknowledge", "style": "ghost"},
                        ],
                        payload={"subject": p.id, "player_id": p.id},
                        priority="high",
                        prompt=f"Sender: manager {manager['name']} (temperament {manager.get('temperament')}, media style {manager.get('media_style')}). Tell the owner that academy regen {p.name}, age {p.age}, just jumped to rating {p.rating} (potential {p.potential}). Main driver: {result['top_driver']}.",
                    )
                )
        if traits.get("transfer_pressure", 0) >= 60 and not _open_item_exists(
            session, state.club_id, "player_unrest", p.id
        ):
            pending.append(
                _item(
                    state.owner_user_id,
                    state.club_id,
                    "player_unrest",
                    sender=f"{p.name}'s agent",
                    title=f"{p.name} is unsettled",
                    what=f"{p.name} wants clarity on his future. Transfer pressure is {traits['transfer_pressure']}/100.",
                    why=f"Ambition {traits['ambition']}/20 with only {p.minutes} minutes played; loyalty {traits['loyalty']}/20; club prestige {state.prestige}.",
                    actions=[
                        {"key": "promise_minutes", "label": "Promise first-team minutes", "style": "primary"},
                        {"key": "transfer_list", "label": "Transfer-list him", "style": "secondary"},
                        {"key": "ignore", "label": "Ignore", "style": "ghost"},
                    ],
                    payload={"subject": p.id, "player_id": p.id},
                    priority="high",
                    prompt=f"Sender: agent of young player {p.name} (ambition {traits['ambition']}/20, loyalty {traits['loyalty']}/20). He has played {p.minutes} minutes and wants assurances or a move. Firm but professional.",
                )
            )
    for p in players:
        if not p.is_regen and p.morale < 45 and not _open_item_exists(session, state.club_id, "player_unrest", p.id):
            pending.append(
                _item(
                    state.owner_user_id,
                    state.club_id,
                    "player_unrest",
                    sender=p.name,
                    title=f"Morale issue: {p.name}",
                    what=f"{p.name}'s morale has dropped to {p.morale}.",
                    why="Recent results, playing time and board decisions have hit his confidence.",
                    actions=[
                        {"key": "promise_minutes", "label": "Promise minutes", "style": "primary"},
                        {"key": "ignore", "label": "Ignore", "style": "ghost"},
                    ],
                    payload={"subject": p.id, "player_id": p.id},
                    priority="normal",
                    prompt=None,
                )
            )
            break
    weakest = min(engine.FACILITY_KINDS[:3], key=lambda k: int(facilities.get(k, 1)))
    if (
        int(facilities.get(weakest, 1)) <= 2
        and manager.get("temperament") in ("fiery", "demanding", "volatile")
        and not _open_item_exists(session, state.club_id, "facility_request")
        and rng.random() < 0.7
    ):
        cost = facility_cost(int(facilities.get(weakest, 1)))
        pending.append(
            _item(
                state.owner_user_id,
                state.club_id,
                "facility_request",
                sender=manager["name"],
                title=f"Manager demands a {weakest} upgrade",
                what=f"{manager['name']} wants the {weakest} facility raised to level {int(facilities.get(weakest, 1)) + 1} ({cost:,} GTEX Coin).",
                why=f"Temperament: {manager.get('temperament')}. Current {weakest} level {facilities.get(weakest, 1)} is limiting player growth.",
                actions=[
                    {"key": "approve", "label": f"Approve spend ({cost:,})", "style": "primary"},
                    {"key": "reject", "label": "Reject", "style": "ghost"},
                ],
                payload={"subject": weakest, "facility": weakest, "cost": cost},
                priority="high",
                prompt=f"Sender: manager {manager['name']} (temperament {manager.get('temperament')}, ambition {manager.get('ambition')}/20). Demand the owner approves upgrading the {weakest} facility to level {int(facilities.get(weakest, 1)) + 1} for {cost} GTEX Coin.",
            )
        )
    positions = [p.position for p in players]
    thin = min(engine.ROLE_REQUESTS, key=lambda pos: sum(1 for x in positions if x.startswith(pos[:4])))
    if (
        not _open_item_exists(session, state.club_id, "manager_request")
        and (len(players) < 18 or manager.get("ambition", 10) >= 13)
        and rng.random() < 0.6
    ):
        budget = 4_000 + manager.get("ambition", 10) * 300
        pending.append(
            _item(
                state.owner_user_id,
                state.club_id,
                "manager_request",
                sender=manager["name"],
                title=f"Manager requests {engine.ROLE_REQUESTS[thin]}",
                what=f"{manager['name']} asks for a transfer budget of {budget:,} GTEX Coin to sign {engine.ROLE_REQUESTS[thin]}.",
                why=f"Squad depth at {thin}: {sum(1 for x in positions if x.startswith(thin[:4]))} players. Transfer preference: {manager.get('transfer_preference')}.",
                actions=[
                    {"key": "approve", "label": "Approve budget & open market", "style": "primary"},
                    {"key": "reject", "label": "Reject", "style": "ghost"},
                ],
                payload={"subject": thin, "position": thin, "budget": budget},
                priority="normal",
                prompt=f"Sender: manager {manager['name']} (transfer preference {manager.get('transfer_preference')}, temperament {manager.get('temperament')}). Ask the owner for {budget} GTEX Coin budget to sign {engine.ROLE_REQUESTS[thin]}.",
            )
        )
    sellable = [p for p in players if Decimal(p.value_coin) >= 1500]
    if sellable and not _open_item_exists(session, state.club_id, "transfer_bid") and rng.random() < 0.45:
        target = rng.choice(sellable[:5])
        bidder = rng.choice(engine.AI_CLUBS)
        bid = int(Decimal(target.value_coin) * Decimal(str(round(rng.uniform(0.9, 1.45), 2))))
        pending.append(
            _item(
                state.owner_user_id,
                state.club_id,
                "transfer_bid",
                sender=f"{bidder} sporting director",
                title=f"{bidder} bid {bid:,} for {target.name}",
                what=f"{bidder} offer {bid:,} GTEX Coin for {target.name} (valued {int(target.value_coin):,}).",
                why=f"{target.name} rated {target.rating} has caught their scouts' attention. Platform fee on sales: 5%.",
                actions=[
                    {"key": "accept", "label": "Accept bid", "style": "primary"},
                    {"key": "reject", "label": "Reject", "style": "ghost"},
                ],
                payload={"subject": target.id, "player_id": target.id, "bid": bid, "bidder": bidder},
                priority="normal",
                prompt=f"Sender: sporting director of {bidder}. Formally offer {bid} GTEX Coin for player {target.name}. Polite, a little persuasive.",
            )
        )
    deals = session.scalars(
        select(OwnerSponsorDeal).where(OwnerSponsorDeal.club_id == state.club_id, OwnerSponsorDeal.status == "active")
    ).all()
    used_slots = {d.slot for d in deals if not d.player_id}
    free_slots = [s for s in engine.SPONSOR_SLOTS if s not in used_slots]
    if free_slots and not _open_item_exists(session, state.club_id, "sponsor_opportunity") and rng.random() < 0.5:
        sponsor, slot = rng.choice(engine.SPONSORS), free_slots[0]
        gross = 300 + int(facilities.get("commercial", 1)) * 150 + state.fans // 40
        pending.append(
            _item(
                state.owner_user_id,
                state.club_id,
                "sponsor_opportunity",
                sender=f"{sponsor} partnerships",
                title=f"{sponsor}: {slot} deal",
                what=f"{sponsor} offer {gross:,} GTEX Coin per match for 10 matches ({slot}).",
                why=f"Club receives 70% ({int(gross * 0.7):,}); platform keeps 30%. Value driven by commercial level {facilities.get('commercial', 1)} and {state.fans:,} fans.",
                actions=[
                    {"key": "accept", "label": "Sign sponsor", "style": "primary"},
                    {"key": "reject", "label": "Decline", "style": "ghost"},
                ],
                payload={"subject": slot, "sponsor": sponsor, "slot": slot, "gross": gross},
                priority="normal",
                prompt=f"Sender: partnerships lead at {sponsor}, a Nigerian brand. Pitch a {slot} sponsorship worth {gross} GTEX Coin per match for 10 matches.",
            )
        )
    for p in players:
        if (
            p.is_regen
            and p.personality_json.get("marketability", 0) >= 15
            and p.rating >= 55
            and not _open_item_exists(session, state.club_id, "regen_endorsement", p.id)
        ):
            already = session.scalar(
                select(OwnerSponsorDeal).where(OwnerSponsorDeal.player_id == p.id, OwnerSponsorDeal.status == "active")
            )
            if already is None and rng.random() < 0.5:
                sponsor = rng.choice(engine.SPONSORS)
                gross = 150 + p.personality_json["marketability"] * 10
                pending.append(
                    _item(
                        state.owner_user_id,
                        state.club_id,
                        "regen_endorsement",
                        sender=f"{sponsor} partnerships",
                        title=f"Endorsement offer for {p.name}",
                        what=f"{sponsor} want {p.name} as a face of their campaign: {gross:,} per match for 10 matches.",
                        why=f"Marketability {p.personality_json['marketability']}/20. Split: 70% club / 30% platform.",
                        actions=[
                            {"key": "accept", "label": "Approve endorsement", "style": "primary"},
                            {"key": "reject", "label": "Decline", "style": "ghost"},
                        ],
                        payload={"subject": p.id, "player_id": p.id, "sponsor": sponsor, "gross": gross},
                        priority="normal",
                        prompt=None,
                    )
                )
                break
    open_comp = session.scalar(
        select(OwnerCompetition)
        .where(OwnerCompetition.status == "open", OwnerCompetition.host_type == "gtex")
        .order_by(OwnerCompetition.created_at.asc())
    )
    if (
        open_comp
        and not session.scalar(
            select(OwnerCompetitionEntry).where(
                OwnerCompetitionEntry.competition_id == open_comp.id, OwnerCompetitionEntry.club_id == state.club_id
            )
        )
        and not _open_item_exists(session, state.club_id, "competition_invite", open_comp.id)
    ):
        pending.append(
            _item(
                state.owner_user_id,
                state.club_id,
                "competition_invite",
                sender="GTEX Competitions",
                title=f"Invitation: {open_comp.name}",
                what=f"{open_comp.name} has open slots. Entry {int(open_comp.entry_fee):,} GTEX Coin.",
                why="Competition football raises prestige, fan engagement and regen growth (competition quality driver).",
                actions=[
                    {"key": "enter", "label": "Enter competition", "style": "primary"},
                    {"key": "decline", "label": "Not now", "style": "ghost"},
                ],
                payload={"subject": open_comp.id, "competition_id": open_comp.id},
                priority="normal",
                prompt=None,
            )
        )
    if manager.get("mood", 70) < 40 and not _open_item_exists(session, state.club_id, "manager_meeting"):
        pending.append(
            _item(
                state.owner_user_id,
                state.club_id,
                "manager_meeting",
                sender=manager["name"],
                title="Manager requests a board meeting",
                what=f"{manager['name']}'s mood is {manager.get('mood')}/100. He wants to discuss the club's direction.",
                why="Recent rejected requests and results have strained the relationship.",
                actions=[
                    {"key": "back_manager", "label": "Publicly back the manager", "style": "primary"},
                    {"key": "ignore", "label": "Decline meeting", "style": "ghost"},
                ],
                payload={"subject": "meeting"},
                priority="high",
                prompt=f"Sender: manager {manager['name']} (temperament {manager.get('temperament')}, loyalty {manager.get('loyalty')}/20), mood {manager.get('mood')}/100. Request a meeting with the owner about board support.",
            )
        )
    items = [p[0] for p in pending]
    for item in items:
        item.body = inbox_body(item.sender, item.what, item.why)
        item.ai_generated = False
    del use_ai
    for item in items:
        session.add(item)
    snapshot_value(session, state)
    session.flush()
    return {"world_day": state.world_day, "new_items": len(items), "growth": growth_report}


def resolve_item(session: Session, user_id: str, item_id: str, action: str) -> OwnerInboxItem:
    item = session.get(OwnerInboxItem, item_id)
    if item is None or item.user_id != user_id:
        raise OwnerError("inbox_item_not_found", 404)
    if item.status != "open":
        raise OwnerError("inbox_item_already_resolved", 409)
    valid = {a["key"] for a in item.actions_json or []}
    if valid and action not in valid:
        raise OwnerError("invalid_action")
    state = require_state(session, item.club_id, user_id) if item.club_id else None
    payload = item.payload_json or {}
    manager = dict(state.manager_json or {}) if state else {}
    outcome = "Noted."

    def mood(delta: int) -> None:
        if manager:
            manager["mood"] = int(engine.clamp(manager.get("mood", 70) + delta, 0, 100))

    player = session.get(OwnerSquadPlayer, payload["player_id"]) if payload.get("player_id") else None
    kind = item.kind
    if kind == "facility_request":
        if action == "approve":
            result = upgrade_facility(session, user_id, item.club_id, payload["facility"])
            manager = dict(state.manager_json or {})
            mood(4)
            outcome = f"{payload['facility'].title()} upgraded to level {result['level']}. {result['effect']} Manager mood up."
        else:
            mood(-10)
            outcome = "Request rejected. The manager is frustrated (mood -10) and growth stays limited by the current facility."
    elif kind == "manager_request":
        if action == "approve":
            mood(8)
            outcome = f"Budget of {payload['budget']:,} approved. The market is filtered to {payload['position']}s. Manager mood +8."
        else:
            mood(-8)
            outcome = "Budget rejected. The manager feels unsupported (mood -8)."
    elif kind == "transfer_bid" and player:
        if action == "accept":
            bid = payload["bid"]
            ledger.record(
                session,
                event_type="transfer_sale",
                source=ledger.WORLD_CLUBS,
                destination=ledger.club_account(item.club_id),
                currency=ledger.GTEX,
                gross=bid,
                fee_bps=PLATFORM_SALE_FEE_BPS,
                club_id=item.club_id,
                user_id=user_id,
                related_type="player",
                related_id=player.id,
                memo=f"Sold {player.name} to {payload['bidder']}",
            )
            player.status = "sold"
            pref = manager.get("transfer_preference")
            mood(-6 if pref in ("proven-veterans", "system-fits") else 2)
            outcome = f"{player.name} sold for {bid:,} (5% platform fee). Funds added to club cash."
        else:
            if player.is_regen and player.personality_json.get("ambition", 10) >= 14:
                player.morale = max(0, player.morale - 8)
                outcome = f"Bid rejected. {player.name} is ambitious and disappointed (morale -8)."
            else:
                outcome = "Bid rejected. The player stays."
    elif kind == "player_unrest" and player:
        if action == "promise_minutes":
            player.morale = min(100, player.morale + 15)
            if player.is_regen:
                traits = dict(player.personality_json)
                traits["transfer_pressure"] = max(0, traits.get("transfer_pressure", 0) - 25)
                traits["promised_minutes"] = True
                player.personality_json = traits
            mood(-3 if manager.get("discipline_style") == "strict" else 0)
            outcome = f"Minutes promised. {player.name} morale +15. The manager must now honour it in selection."
        elif action == "transfer_list":
            player.status = "listed"
            outcome = f"{player.name} is transfer-listed. Expect bids in the inbox."
        else:
            _morale_shift(session, item.club_id, -2)
            player.morale = max(0, player.morale - 10)
            outcome = "Ignored. Player morale -10, squad morale -2."
    elif kind == "regen_breakthrough" and player:
        if action == "new_contract":
            ledger.record(
                session,
                event_type="contract_bonus",
                source=ledger.club_account(item.club_id),
                destination=ledger.WORLD_CLUBS,
                currency=ledger.GTEX,
                gross=1000,
                club_id=item.club_id,
                user_id=user_id,
                related_type="player",
                related_id=player.id,
                memo=f"Improved academy contract for {player.name}",
            )
            traits = dict(player.personality_json)
            traits["loyalty"] = min(20, traits.get("loyalty", 10) + 2)
            traits["transfer_pressure"] = max(0, traits.get("transfer_pressure", 0) - 15)
            player.personality_json = traits
            player.morale = min(100, player.morale + 10)
            outcome = f"{player.name} signs an improved deal: loyalty +2, morale +10, transfer pressure -15."
        else:
            outcome = "Acknowledged."
    elif kind in ("sponsor_opportunity", "regen_endorsement"):
        if action == "accept":
            session.add(
                OwnerSponsorDeal(
                    club_id=item.club_id,
                    sponsor_name=payload["sponsor"],
                    slot=payload.get("slot") or f"Endorsement: {player.name if player else ''}",
                    per_match_gross=Decimal(payload["gross"]),
                    player_id=payload.get("player_id") if kind == "regen_endorsement" else None,
                )
            )
            outcome = f"{payload['sponsor']} deal signed. 70% of {payload['gross']:,} per match goes to club cash after each match."
        else:
            outcome = "Declined."
    elif kind == "competition_invite":
        if action == "enter":
            from app.owner_console.competitions import enter_competition

            enter_competition(session, user_id, payload["competition_id"], item.club_id)
            outcome = "Entered. Your fixtures appear on the Competition rail."
        else:
            outcome = "Invitation declined."
    elif kind == "manager_meeting":
        if action == "back_manager":
            mood(15)
            outcome = "You publicly backed the manager. Mood +15."
        else:
            mood(-5)
            outcome = "Meeting declined. Mood -5. Risk of resignation if it keeps falling."
    if state and manager:
        state.manager_json = manager
    item.status = "resolved"
    item.resolution = action
    item.outcome_text = outcome
    item.resolved_at = now()
    session.flush()
    return item


def mark_inbox_read(session: Session, user_id: str, item_id: str, is_read: bool = True) -> OwnerInboxItem:
    item = session.get(OwnerInboxItem, item_id)
    if not item or item.user_id != user_id:
        raise OwnerError("item_not_found", 404, "Inbox item not found.")
    item.is_read = is_read
    item.read_at = datetime.now(timezone.utc) if is_read else None
    session.flush()
    return item


def archive_inbox_item(session: Session, user_id: str, item_id: str, archive: bool = True) -> OwnerInboxItem:
    item = session.get(OwnerInboxItem, item_id)
    if not item or item.user_id != user_id:
        raise OwnerError("item_not_found", 404, "Inbox item not found.")
    item.archived_at = datetime.now(timezone.utc) if archive else None
    if archive and item.status == "open":
        item.status = "archived"
    elif not archive and item.status == "archived":
        item.status = "open"
    session.flush()
    return item


def inbox_dict(item: OwnerInboxItem) -> dict[str, Any]:
    from app.owner_console.alerts import respond_by

    due = respond_by(item) if item.status == "open" else None
    return {
        "respond_by": due.isoformat() if due else None,
        "id": item.id,
        "club_id": item.club_id,
        "save_context_id": item.save_context_id or (f"club:{item.club_id}" if item.club_id else None),
        "category": item.category or "requests",
        "kind": item.kind,
        "priority": item.priority,
        "sender": item.sender,
        "title": item.title,
        "what": item.what,
        "why": item.why,
        "body": item.body,
        "ai_generated": item.ai_generated,
        "actions": item.actions_json,
        "payload": item.payload_json,
        "is_decision": item.is_decision,
        "is_read": bool(item.is_read),
        "read_at": item.read_at.isoformat() if item.read_at else None,
        "archived_at": item.archived_at.isoformat() if item.archived_at else None,
        "deadline_at": item.deadline_at.isoformat() if item.deadline_at else (due.isoformat() if due else None),
        "status": item.status,
        "resolution": item.resolution,
        "outcome": item.outcome_text,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def club_health(session: Session, state: OwnerClubState) -> dict[str, Any]:
    players = squad(session, state.club_id)
    regens = [p for p in players if p.is_regen]
    morale = int(sum(p.morale for p in players) / len(players)) if players else 0
    econ = ledger.club_economy(session, state.club_id)
    return {
        "club_id": state.club_id,
        "club_name": state.club_name,
        "cash": econ["cash_gtex"],
        "squad_size": len(players),
        "squad_depth": "thin" if len(players) < 16 else "healthy" if len(players) < 26 else "deep",
        "morale": morale,
        "injuries": sum(1 for p in players if p.injured_days > 0),
        "academy_players": len(regens),
        "academy_output": sum(1 for p in regens if p.rating >= 60),
        "fans": state.fans,
        "fan_engagement": int(engine.clamp(state.fans / 60 + state.prestige / 2, 0, 100)),
        "prestige": state.prestige,
    }


def club_card(session: Session, state: OwnerClubState) -> dict[str, Any]:
    profile = session.get(ClubProfile, state.club_id)
    history = state.value_history_json or []
    value = club_value(session, state)
    prev = Decimal(history[-2][1]) if len(history) >= 2 else value
    entry = session.scalar(
        select(OwnerCompetitionEntry)
        .join(OwnerCompetition, OwnerCompetition.id == OwnerCompetitionEntry.competition_id)
        .where(OwnerCompetitionEntry.club_id == state.club_id, OwnerCompetition.status.in_(("open", "running")))
        .order_by(OwnerCompetitionEntry.created_at.desc())
    )
    comp = session.get(OwnerCompetition, entry.competition_id) if entry else None
    manager = state.manager_json or {}
    return {
        "club_id": state.club_id,
        "club_name": state.club_name,
        "short_name": profile.short_name if profile else None,
        "primary_color": profile.primary_color if profile else "#10B981",
        "secondary_color": profile.secondary_color if profile else "#0F172A",
        "city": profile.city_name if profile else None,
        "public_profile_slug": profile.slug if profile and profile.visibility == "public" else None,
        "country_code": profile.country_code if profile else None,
        "continent_code": profile.continent_code if profile else None,
        "stage": state.stage,
        "status": "active" if state.stage == "active" else "activating",
        "competition": {"id": comp.id, "name": comp.name, "status": comp.status} if comp else None,
        "value": str(value),
        "value_trend": str(value - prev),
        "value_history": history,
        "manager": (
            {"name": manager.get("name"), "mood": manager.get("mood"), "temperament": manager.get("temperament")}
            if manager
            else None
        ),
        "world_day": state.world_day,
        "mentality": state.mentality,
    }


def club_detail(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    from app.owner_console import storytelling

    state = require_state(session, club_id, user_id)
    deals = session.scalars(
        select(OwnerSponsorDeal).where(OwnerSponsorDeal.club_id == club_id).order_by(OwnerSponsorDeal.created_at.desc())
    ).all()
    facilities = state.facilities_json or {}
    return {
        **club_card(session, state),
        "manager_profile": state.manager_json,
        "facilities": {
            k: {
                "level": int(facilities.get(k, 1)),
                "next_cost": facility_cost(int(facilities.get(k, 1))) if int(facilities.get(k, 1)) < 5 else None,
            }
            for k in engine.FACILITY_KINDS
        },
        "squad": [player_dict(p, session) for p in squad(session, club_id)],
        "health": club_health(session, state),
        "economy": ledger.club_economy(session, club_id),
        "sponsors": [
            {
                "id": d.id,
                "sponsor": d.sponsor_name,
                "slot": d.slot,
                "per_match_gross": str(d.per_match_gross),
                "club_share": str(ledger.D(d.per_match_gross * Decimal("0.7"))),
                "matches_remaining": d.matches_remaining,
                "status": d.status,
                "player_id": d.player_id,
            }
            for d in deals
        ],
        "disclosures": disclosures(session, club_id),
        "ownership_group": group_label(session, user_id),
        "showroom": storytelling.get_club_showroom(session, user_id, club_id),
    }


def maybe_auto_tick(session: Session, user_id: str) -> None:
    for state in user_states(session, user_id):
        last = aware(state.last_tick_at)
        if state.stage in ("competition", "active") and (last is None or now() - last > timedelta(hours=6)):
            tick_club(session, state, use_ai=False)


def get_owner_newsroom(*args, **kwargs):
    from app.owner_console import storytelling

    return storytelling.list_newsroom_articles(*args, **kwargs)
