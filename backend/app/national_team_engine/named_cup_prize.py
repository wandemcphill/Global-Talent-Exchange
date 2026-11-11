"""Put a GTEX prize into one named cup and keep that coin aside for it."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.national_team import NationalTeamCompetition
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.national_team_engine.competition_profiles import default_reward_structure_for, infer_competition_family
from app.wallets.service import LedgerPosting, WalletService

PRIZE_QUANTUM = Decimal("0.0001")


class NamedCupPrizeError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def cup_prize_account_code(competition_id: str) -> str:
    return f"platform:coin:cup_prize:{competition_id}"


def _money(value: Decimal | int | float | str) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(PRIZE_QUANTUM)
    except Exception as exc:
        raise NamedCupPrizeError("Prize coin must be a number.") from exc
    if amount < 0:
        raise NamedCupPrizeError("Prize coin cannot be negative.")
    return amount


def _places(competition: NationalTeamCompetition) -> tuple[Decimal, Decimal, Decimal]:
    metadata = dict(competition.metadata_json or {})
    structure = metadata.get("reward_structure") if isinstance(metadata.get("reward_structure"), dict) else {}
    places = structure.get("place_prizes") if isinstance(structure.get("place_prizes"), dict) else {}
    if not places:
        family = infer_competition_family(key=competition.key, title=competition.title, metadata_json=metadata)
        places = default_reward_structure_for(family, competition.age_band or "senior").get("place_prizes") or {}
    return (
        _money(places.get("first", "0")),
        _money(places.get("second", "0")),
        _money(places.get("third", "0")),
    )


def cup_prize_view(session: Session, competition: NationalTeamCompetition, wallet: WalletService) -> dict[str, str]:
    first, second, third = _places(competition)
    metadata = dict(competition.metadata_json or {})
    account = wallet.ensure_named_system_account(
        session,
        code=cup_prize_account_code(competition.id),
        label=f"Prize held for {competition.title}",
        unit=LedgerUnit.COIN,
        allow_negative=False,
    )
    held = wallet.get_balance(session, account)
    return {
        "id": competition.id,
        "title": competition.title,
        "season_label": competition.season_label,
        "first": str(first),
        "second": str(second),
        "third": str(third),
        "funded_coin": str(_money(metadata.get("gtex_funded_place_prize_coin", held))),
        "held_coin": str(_money(held)),
    }


def list_named_cups(session: Session, wallet: WalletService | None = None) -> list[dict[str, str]]:
    wallet = wallet or WalletService()
    rows = list(session.scalars(select(NationalTeamCompetition).order_by(NationalTeamCompetition.title.asc())).all())
    return [cup_prize_view(session, row, wallet) for row in rows[:200]]


def set_named_cup_prize(
    session: Session,
    *,
    competition_id: str,
    actor: User,
    first: Decimal | int | float | str,
    second: Decimal | int | float | str,
    third: Decimal | int | float | str,
    wallet: WalletService | None = None,
) -> dict[str, Any]:
    """Save 1st, 2nd and 3rd for one cup and move the difference into that cup's prize pot."""
    wallet = wallet or WalletService()
    competition = session.get(NationalTeamCompetition, competition_id)
    if competition is None:
        raise NamedCupPrizeError("That cup was not found.")
    first_amount = _money(first)
    second_amount = _money(second)
    third_amount = _money(third)
    total = _money(first_amount + second_amount + third_amount)

    metadata = dict(competition.metadata_json or {})
    already = _money(metadata.get("gtex_funded_place_prize_coin", "0"))
    family = infer_competition_family(key=competition.key, title=competition.title, metadata_json=metadata)
    structure = dict(
        metadata.get("reward_structure") or default_reward_structure_for(family, competition.age_band or "senior")
    )
    structure["place_prizes"] = {
        "first": str(first_amount),
        "second": str(second_amount),
        "third": str(third_amount),
    }
    if family == "world_cup" or str(structure.get("reward_mode") or "") == "match_and_stage":
        stage = dict(structure.get("stage_progression_coin") or {})
        stage["champion"] = str(first_amount)
        stage["runner_up"] = str(second_amount)
        structure["stage_progression_coin"] = stage
    metadata["reward_structure"] = structure
    metadata["gtex_named_prize_set"] = True

    cup_account = wallet.ensure_named_system_account(
        session,
        code=cup_prize_account_code(competition.id),
        label=f"Prize held for {competition.title}",
        unit=LedgerUnit.COIN,
        allow_negative=False,
    )
    platform = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    delta = _money(total - already)
    if delta > 0:
        wallet.append_transaction(
            session,
            postings=[
                LedgerPosting(
                    account=platform,
                    amount=-delta,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    transaction_type=LedgerTransactionType.ADJUSTMENT,
                ),
                LedgerPosting(
                    account=cup_account,
                    amount=delta,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    transaction_type=LedgerTransactionType.ADJUSTMENT,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference=f"named-cup-prize:{competition.id}",
            description=f"Prize set aside for {competition.title}",
            actor=actor,
            metadata={"competition_id": competition.id, "prize_total": str(total)},
        )
        already = _money(already + delta)
    elif delta < 0:
        held = wallet.get_balance(session, cup_account)
        give_back = _money(min(abs(delta), held))
        if give_back > 0:
            wallet.append_transaction(
                session,
                postings=[
                    LedgerPosting(
                        account=cup_account,
                        amount=-give_back,
                        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                        transaction_type=LedgerTransactionType.ADJUSTMENT,
                    ),
                    LedgerPosting(
                        account=platform,
                        amount=give_back,
                        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                        transaction_type=LedgerTransactionType.ADJUSTMENT,
                    ),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                reference=f"named-cup-prize-return:{competition.id}",
                description=f"Prize reduced for {competition.title}",
                actor=actor,
            )
            already = _money(already - give_back)
    metadata["gtex_funded_place_prize_coin"] = str(already)
    competition.metadata_json = metadata
    session.flush()
    view = cup_prize_view(session, competition, wallet)
    view["moved_coin"] = str(delta)
    return view
