"""Phase 8: cases, appeals, reviewable related-party trades, stakes, and distributions."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_legacy.delegation import LegacyError, require_owner
from app.club_legacy.ledger import post_club_legacy_transfer
from app.club_legacy.models import (
    ClubLegacyAsset,
    ClubLegacyCase,
    ClubLegacyCatalogueItem,
    ClubLegacyDistribution,
    ClubLegacyDistributionLine,
    ClubLegacyStake,
    ClubLegacyTradeReview,
)
from app.models.club_profile import ClubProfile
from app.models.user import User
from app.owner_console import ledger

STAKE_CAP = Decimal("100")


def _q(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def open_case(session: Session, *, club_id: str, rule_code: str, allegation: str, evidence: str) -> ClubLegacyCase:
    if rule_code == "luxury_possession":
        raise LegacyError("not_misconduct", 409, "Expensive possessions alone are not a disciplinary case.")
    if not allegation.strip() or not evidence.strip():
        raise LegacyError("case_details_required")
    case = ClubLegacyCase(
        club_id=club_id,
        rule_code=rule_code,
        allegation=allegation,
        evidence=evidence,
        status="open",
    )
    session.add(case)
    session.flush()
    return case


def rule_case(session: Session, *, case_id: str, sanction: str, reason: str) -> ClubLegacyCase:
    case = session.get(ClubLegacyCase, case_id)
    if case is None:
        raise LegacyError("case_not_found", 404)
    if not sanction.strip() or not reason.strip():
        raise LegacyError("ruling_required")
    case.status = "ruled"
    case.sanction = sanction
    case.reason = reason
    session.flush()
    return case


def appeal_case(session: Session, *, case_id: str, outcome: str) -> ClubLegacyCase:
    case = session.get(ClubLegacyCase, case_id)
    if case is None or case.status != "ruled":
        raise LegacyError("appeal_unavailable", 409)
    if not outcome.strip():
        raise LegacyError("appeal_outcome_required")
    case.status = "appealed"
    case.appeal_outcome = outcome
    session.flush()
    return case


def case_dict(case: ClubLegacyCase) -> dict:
    return {
        "id": case.id,
        "club_id": case.club_id,
        "rule_code": case.rule_code,
        "allegation": case.allegation,
        "evidence": case.evidence,
        "status": case.status,
        "sanction": case.sanction,
        "reason": case.reason,
        "appeal_outcome": case.appeal_outcome,
    }


def log_trade_review(
    session: Session,
    *,
    listing_id: str | None,
    from_club_id: str | None,
    to_club_id: str | None,
    kind: str,
    note: str,
) -> ClubLegacyTradeReview:
    if kind not in {"related_party", "sister_club"}:
        raise LegacyError("unknown_trade_kind")
    review = ClubLegacyTradeReview(
        listing_id=listing_id,
        from_club_id=from_club_id,
        to_club_id=to_club_id,
        kind=kind,
        status="reviewable",
        note=note,
    )
    session.add(review)
    session.flush()
    return review


def list_trade_reviews(session: Session, club_id: str) -> list[ClubLegacyTradeReview]:
    return list(
        session.scalars(
            select(ClubLegacyTradeReview)
            .where((ClubLegacyTradeReview.from_club_id == club_id) | (ClubLegacyTradeReview.to_club_id == club_id))
            .order_by(ClubLegacyTradeReview.id.asc())
        ).all()
    )


def trade_review_dict(review: ClubLegacyTradeReview) -> dict:
    return {
        "id": review.id,
        "listing_id": review.listing_id,
        "from_club_id": review.from_club_id,
        "to_club_id": review.to_club_id,
        "kind": review.kind,
        "status": review.status,
        "note": review.note,
    }


def set_stake(
    session: Session,
    *,
    club_id: str,
    holder_user_id: str,
    percentage,
    voting_rights=None,
) -> ClubLegacyStake:
    stake = session.scalar(
        select(ClubLegacyStake).where(
            ClubLegacyStake.club_id == club_id, ClubLegacyStake.holder_user_id == holder_user_id
        )
    )
    percent = _q(percentage)
    if percent <= 0 or percent > STAKE_CAP:
        raise LegacyError("invalid_percentage")
    votes = percent if voting_rights is None else _q(voting_rights)
    if votes < 0 or votes > STAKE_CAP:
        raise LegacyError("invalid_voting_rights")
    others = session.scalars(select(ClubLegacyStake).where(ClubLegacyStake.club_id == club_id)).all()
    total = (
        sum((Decimal(row.percentage) for row in others if row.holder_user_id != holder_user_id), Decimal("0")) + percent
    )
    if total > STAKE_CAP:
        raise LegacyError("stake_total", 409, f"Stakes would total {total}, above 100.")
    vote_total = (
        sum((Decimal(row.voting_rights) for row in others if row.holder_user_id != holder_user_id), Decimal("0"))
        + votes
    )
    if vote_total > STAKE_CAP:
        raise LegacyError("voting_total", 409, f"Voting rights would total {vote_total}, above 100.")
    if stake is None:
        stake = ClubLegacyStake(
            club_id=club_id, holder_user_id=holder_user_id, percentage=percent, voting_rights=votes
        )
        session.add(stake)
    else:
        stake.percentage = percent
        stake.voting_rights = votes
    session.flush()
    return stake


def _valuation(session: Session, club_id: str) -> Decimal:
    from app.club_legacy.operations import club_valuation

    return club_valuation(session, club_id)


def economic_interest(session: Session, *, club_id: str, holder_user_id: str) -> Decimal:
    stake = session.scalar(
        select(ClubLegacyStake).where(
            ClubLegacyStake.club_id == club_id, ClubLegacyStake.holder_user_id == holder_user_id
        )
    )
    if stake is None:
        return Decimal("0.00")
    return _q(_valuation(session, club_id) * Decimal(stake.percentage) / Decimal("100"))


def _allocate(amount: Decimal, stakes: list[ClubLegacyStake]) -> list[Decimal]:
    total_pct = sum((Decimal(row.percentage) for row in stakes), Decimal("0"))
    if total_pct <= 0:
        raise LegacyError("no_stakes", 409)
    shares = [_q(amount * Decimal(row.percentage) / total_pct) for row in stakes]
    drift = _q(amount - sum(shares, Decimal("0")))
    if drift != 0 and shares:
        index = max(range(len(stakes)), key=lambda item: (Decimal(stakes[item].percentage), stakes[item].holder_user_id))
        shares[index] = _q(shares[index] + drift)
    if _q(sum(shares, Decimal("0"))) != _q(amount):
        raise LegacyError("allocation_mismatch", 500)
    return shares


def distribute(
    session: Session, *, club_id: str, user_id: str, amount, idempotency_key: str
) -> ClubLegacyDistribution:
    require_owner(session, club_id, user_id)
    existing = session.scalar(
        select(ClubLegacyDistribution).where(ClubLegacyDistribution.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing
    gross = _q(amount)
    if gross <= 0:
        raise LegacyError("amount_must_be_positive")
    stakes = list(
        session.scalars(
            select(ClubLegacyStake).where(ClubLegacyStake.club_id == club_id).order_by(ClubLegacyStake.holder_user_id.asc())
        ).all()
    )
    if not stakes:
        raise LegacyError("no_stakes", 409)
    for stake in stakes:
        if session.get(User, stake.holder_user_id) is None:
            raise LegacyError("holder_not_found", 404)
    shares = _allocate(gross, stakes)
    distribution = ClubLegacyDistribution(
        club_id=club_id, amount=gross, idempotency_key=idempotency_key, status="paid"
    )
    session.add(distribution)
    session.flush()
    source = ledger.wallet_account(session, ledger.club_account(club_id), ledger.GTEX)
    for stake, share in zip(stakes, shares, strict=True):
        if share <= 0:
            continue
        line_key = f"distribution:{idempotency_key}:{stake.holder_user_id}"
        session.add(
            ClubLegacyDistributionLine(
                distribution_id=distribution.id,
                holder_user_id=stake.holder_user_id,
                percentage=stake.percentage,
                amount=share,
                idempotency_key=line_key,
            )
        )
        destination = ledger.wallet_account(session, ledger.user_account(stake.holder_user_id), ledger.GTEX)
        post_club_legacy_transfer(
            session,
            idempotency_key=line_key,
            source=source,
            destination=destination,
            amount=share,
            description=f"Stake distribution {stake.percentage}%",
        )
    session.flush()
    return distribution


def distribution_lines(session: Session, distribution_id: str) -> list[ClubLegacyDistributionLine]:
    return list(
        session.scalars(
            select(ClubLegacyDistributionLine)
            .where(ClubLegacyDistributionLine.distribution_id == distribution_id)
            .order_by(ClubLegacyDistributionLine.holder_user_id.asc())
        ).all()
    )


def distribution_dict(session: Session, distribution: ClubLegacyDistribution) -> dict:
    lines = distribution_lines(session, distribution.id)
    return {
        "id": distribution.id,
        "club_id": distribution.club_id,
        "amount": str(distribution.amount),
        "idempotency_key": distribution.idempotency_key,
        "status": distribution.status,
        "lines": [
            {
                "holder_user_id": line.holder_user_id,
                "percentage": str(line.percentage),
                "amount": str(line.amount),
            }
            for line in lines
        ],
        "paid": str(_q(sum((Decimal(line.amount) for line in lines), Decimal("0")))),
    }


def owner_net_worth(session: Session, user_id: str) -> dict:
    personal_cash = ledger.balance(session, ledger.user_account(user_id), ledger.GTEX)
    personal_assets = Decimal("0")
    for asset in session.scalars(
        select(ClubLegacyAsset).where(
            ClubLegacyAsset.owner_class == "owner",
            ClubLegacyAsset.owner_ref == user_id,
            ClubLegacyAsset.status == "owned",
        )
    ).all():
        item = session.get(ClubLegacyCatalogueItem, asset.catalogue_id)
        if item is not None:
            personal_assets += Decimal(item.price)
    owned_club_ids = [
        profile.id
        for profile in session.scalars(select(ClubProfile).where(ClubProfile.owner_user_id == user_id)).all()
    ]
    club_assets = Decimal("0")
    if owned_club_ids:
        for asset in session.scalars(
            select(ClubLegacyAsset).where(
                ClubLegacyAsset.owner_class == "club",
                ClubLegacyAsset.status == "owned",
                ClubLegacyAsset.club_id.in_(owned_club_ids),
            )
        ).all():
            item = session.get(ClubLegacyCatalogueItem, asset.catalogue_id)
            if item is not None:
                club_assets += Decimal(item.price)
    equity = Decimal("0")
    minority = Decimal("0")
    for stake in session.scalars(select(ClubLegacyStake).where(ClubLegacyStake.holder_user_id == user_id)).all():
        interest = _q(_valuation(session, stake.club_id) * Decimal(stake.percentage) / Decimal("100"))
        equity += interest
        if Decimal(stake.percentage) < Decimal("50"):
            minority += interest
    personal_assets = _q(personal_assets)
    club_assets = _q(club_assets)
    equity = _q(equity)
    minority = _q(minority)
    return {
        "personal_cash": str(_q(personal_cash)),
        "personal_assets": str(personal_assets),
        "club_assets": str(club_assets),
        "minority_stakes": str(minority),
        "equity": str(equity),
        "net_worth": str(_q(personal_cash + personal_assets + equity)),
    }
