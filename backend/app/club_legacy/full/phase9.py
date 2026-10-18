"""Phase 9: multi-season simulation, subsystem metrics, and catalogue reads."""

from __future__ import annotations

from decimal import Decimal
import random
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.club_legacy.delegation import LegacyError
from app.club_legacy.models import (
    ClubLegacyAsset,
    ClubLegacyCase,
    ClubLegacyCatalogueItem,
    ClubLegacyExecutive,
    ClubLegacyPreseasonInvite,
    ClubLegacyPreseasonSettlement,
    ClubLegacySeasonRun,
    ClubLegacyShowroomFailure,
    ClubLegacyYouthProspect,
)
from app.club_legacy.ratings import development_score, financial_strength, prestige_score
from app.models.club_profile import ClubProfile
from app.owner_console import ledger
from app.owner_console.models import OwnerClubState

TIERS = ("small", "established", "elite")
HIGH_POTENTIAL = 85
REVENUE_BANDS = {
    "small": (80_000, 160_000),
    "established": (700_000, 1_400_000),
    "elite": (4_000_000, 9_000_000),
}
REPUTATION_START = {"small": 24, "established": 58, "elite": 86}
YOUTH_NAMES = ("Ada", "Ife", "Chidi", "Ngozi", "Tunde", "Amina", "Kwame", "Zola", "Sena", "Bola")


def _q(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def _club_id(club) -> str:
    if isinstance(club, str):
        return club
    ident = getattr(club, "id", None)
    if ident is None:
        raise LegacyError("club_not_found", 404)
    return str(ident)


def _step_reputation(tier: str, value: int, rng: random.Random) -> int:
    if tier == "small":
        return min(70, value + 3 + rng.randint(0, 2))
    if tier == "established":
        return min(84, max(40, value + rng.randint(-1, 2)))
    return min(99, max(80, value + rng.randint(-1, 1)))


def _revenue(tier: str, rng: random.Random) -> Decimal:
    low, high = REVENUE_BANDS[tier]
    return Decimal(low + rng.randint(0, high - low))


def _youth(tier: str, rng: random.Random, season_index: int) -> list[dict]:
    count = 3 + rng.randint(0, 4)
    base = rng.randint(48, 70)
    prospects = []
    for index in range(count):
        swing = rng.randint(4, 18) * (1 if index % 2 == 0 else -1)
        potential = max(40, min(84, base + swing))
        prospects.append(potential)
    if rng.randrange(5) == 0:
        prospects.append(rng.randint(HIGH_POTENTIAL, 94))
    rows = []
    for index, potential in enumerate(prospects):
        rows.append(
            {
                "season": season_index,
                "name": f"{rng.choice(YOUTH_NAMES)} {rng.choice(YOUTH_NAMES)}",
                "potential": potential,
                "high_potential": potential >= HIGH_POTENTIAL,
                "tier": tier,
            }
        )
    return rows


def simulate_seasons(session: Session, club, seasons: int, tier: str, *, seed: int = 0) -> dict:
    """Run several seasons. Revenue bands stay apart. Youth intake is a draw, not a guarantee."""
    club_id = _club_id(club)
    if session.get(ClubProfile, club_id) is None:
        raise LegacyError("club_not_found", 404)
    if tier not in TIERS:
        raise LegacyError("unknown_tier")
    if int(seasons) < 1:
        raise LegacyError("invalid_seasons")
    rng = random.Random(f"{club_id}:{tier}:{int(seasons)}:{int(seed)}")
    reputation = REPUTATION_START[tier]
    season_rows = []
    youth_rows = []
    sanction_total = 0
    revenue_total = Decimal("0")
    for index in range(1, int(seasons) + 1):
        reputation = _step_reputation(tier, reputation, rng)
        revenue = _revenue(tier, rng)
        revenue_total += revenue
        intake = _youth(tier, rng, index)
        youth_rows.extend(intake)
        sanctions = 1 if tier != "small" and rng.randrange(4) == 0 else 0
        sanction_total += sanctions
        season_rows.append(
            {
                "season": index,
                "reputation": reputation,
                "revenue": str(_q(revenue)),
                "youth_intake": intake,
                "sanction_count": sanctions,
            }
        )
    payload = {
        "club_id": club_id,
        "tier": tier,
        "seed": int(seed),
        "seasons_run": int(seasons),
        "reputation_start": REPUTATION_START[tier],
        "reputation": reputation,
        "revenue": str(_q(revenue_total)),
        "youth_intake": youth_rows,
        "sanction_count": sanction_total,
        "seasons": season_rows,
    }
    run = ClubLegacySeasonRun(
        club_id=club_id,
        tier=tier,
        seasons=int(seasons),
        seed=int(seed),
        reputation=reputation,
        revenue=_q(revenue_total),
        sanction_count=sanction_total,
        results_json=payload,
    )
    session.add(run)
    session.flush()
    for prospect in youth_rows:
        session.add(
            ClubLegacyYouthProspect(
                run_id=run.id,
                club_id=club_id,
                season_index=prospect["season"],
                name=prospect["name"],
                potential=prospect["potential"],
                high_potential=bool(prospect["high_potential"]),
            )
        )
    session.flush()
    payload["run_id"] = run.id
    run.results_json = payload
    session.flush()
    return payload


def simulate_season(session: Session, club_id: str) -> dict:
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    development = development_score(state.facilities_json if state else {})
    cash = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
    jets = (
        session.scalar(
            select(func.count())
            .select_from(ClubLegacyAsset)
            .join(ClubLegacyCatalogueItem, ClubLegacyCatalogueItem.id == ClubLegacyAsset.catalogue_id)
            .where(ClubLegacyAsset.club_id == club_id, ClubLegacyCatalogueItem.category == "jet")
        )
        or 0
    )
    return {
        "club_id": club_id,
        "development": development,
        "financial_strength": financial_strength(cash),
        "prestige": prestige_score(session, club_id),
        "jets": int(jets),
        "can_progress_without_jets": int(jets) == 0 and development >= 20,
    }


def record_showroom_failure(session: Session, *, club_id: str, reason: str) -> ClubLegacyShowroomFailure:
    failure = ClubLegacyShowroomFailure(club_id=club_id, reason=reason)
    session.add(failure)
    session.flush()
    return failure


def supply_snapshot(session: Session) -> dict[str, dict]:
    rows = {}
    for item in session.scalars(select(ClubLegacyCatalogueItem).order_by(ClubLegacyCatalogueItem.sku.asc())).all():
        remaining = None if item.supply_cap is None else int(item.supply_cap) - int(item.minted_count)
        rows[item.sku] = {
            "supply_cap": item.supply_cap,
            "minted_count": int(item.minted_count),
            "remaining": remaining,
        }
    return rows


def load_catalogue(session: Session, rounds: int = 40) -> dict:
    from app.club_legacy.operations import seed_catalogue

    seed_catalogue(session)
    before = supply_snapshot(session)
    started = time.perf_counter()
    for _ in range(rounds):
        session.scalars(select(ClubLegacyCatalogueItem)).all()
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    after = supply_snapshot(session)
    return {
        "rounds": rounds,
        "elapsed_ms": elapsed_ms,
        "within_budget": elapsed_ms < 1000,
        "supply_unchanged": before == after,
        "supply": after,
    }


def _count(session: Session, model, *where) -> int:
    statement = select(func.count()).select_from(model)
    if where:
        statement = statement.where(*where)
    return int(session.scalar(statement) or 0)


def metrics(session: Session) -> dict:
    from app.club_legacy.operations import seed_catalogue

    seed_catalogue(session)
    invitation_count = _count(session, ClubLegacyPreseasonInvite)
    acceptance = _count(session, ClubLegacyPreseasonInvite, ClubLegacyPreseasonInvite.status == "accepted")
    platform = session.scalar(select(func.coalesce(func.sum(ClubLegacyPreseasonSettlement.platform_amount), 0)))
    host = session.scalar(select(func.coalesce(func.sum(ClubLegacyPreseasonSettlement.host_amount), 0)))
    participant = session.scalar(select(func.coalesce(func.sum(ClubLegacyPreseasonSettlement.participant_amount), 0)))
    platform_q = _q(platform or 0)
    host_q = _q(host or 0)
    participant_q = _q(participant or 0)
    return {
        "executives": _count(session, ClubLegacyExecutive),
        "assets": _count(session, ClubLegacyAsset),
        "invites": invitation_count,
        "invitation_count": invitation_count,
        "acceptance": acceptance,
        "settlements": _count(session, ClubLegacyPreseasonSettlement),
        "settlement_totals": {
            "platform": str(platform_q),
            "host": str(host_q),
            "participant": str(participant_q),
            "combined": str(_q(platform_q + host_q + participant_q)),
        },
        "supply_remaining": supply_snapshot(session),
        "cases": _count(session, ClubLegacyCase),
        "open_cases": _count(session, ClubLegacyCase, ClubLegacyCase.status == "open"),
        "showroom_failure_count": _count(session, ClubLegacyShowroomFailure),
        "rollback": "Disable the club_legacy feature flag. Legacy routes then return 404.",
    }
