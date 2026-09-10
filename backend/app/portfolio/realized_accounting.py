from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.player_token_market import PlayerShareEvent, PlayerShareHolding
from app.models.user import User

AMOUNT_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class RealizedPLRow:
    event_id: str
    player_id: str
    occurred_at: datetime
    quantity: Decimal
    execution_price: Decimal
    gross_proceeds: Decimal
    fee: Decimal
    cost_basis: Decimal
    realized_pl: Decimal
    transaction_id: str
    idempotency_reference: str | None


@dataclass(frozen=True, slots=True)
class RealizedPLSummary:
    total: Decimal
    available: bool
    rows: list[RealizedPLRow]
    unavailable_reason: str | None = None


def _amount(value: Decimal | int | str | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(AMOUNT_QUANTUM)


def _unavailable(reason: str) -> RealizedPLSummary:
    return RealizedPLSummary(
        total=Decimal("0.0000"),
        available=False,
        rows=[],
        unavailable_reason=reason,
    )


def calculate_user_realized_pl(session: Session, user: User) -> RealizedPLSummary:
    events = list(
        session.scalars(
            select(PlayerShareEvent)
            .where(PlayerShareEvent.user_id == user.id)
            .where(PlayerShareEvent.event_type.in_(("buy", "sell")))
            .order_by(PlayerShareEvent.created_at.asc(), PlayerShareEvent.id.asc())
        ).all()
    )

    if not events:
        has_owned_position = session.scalar(
            select(PlayerShareHolding.id)
            .where(PlayerShareHolding.user_id == user.id, PlayerShareHolding.share_count > 0)
            .limit(1)
        )
        if has_owned_position is not None:
            return _unavailable(
                "Realized P/L is not calculated because this position has no complete trade-event history."
            )
        return RealizedPLSummary(total=Decimal("0.0000"), available=True, rows=[])

    state: dict[str, dict[str, Decimal]] = {}
    rows: list[RealizedPLRow] = []

    for event in events:
        meta = event.metadata_json or {}
        transaction_id = str(meta.get("transaction_id") or "").strip()
        if not transaction_id:
            return _unavailable(
                "Historical player-share events do not contain settlement metadata for this account."
            )

        try:
            quantity = _amount(abs(event.share_delta))
            execution_price = _amount(event.price_per_share_coin)
            gross_amount = _amount(event.gross_amount_coin)
            fee = _amount(meta.get("fee_amount_coin"))
        except (ArithmeticError, ValueError, TypeError):
            return _unavailable("A player-share settlement contains incomplete accounting data.")

        if quantity <= Decimal("0.0000") or execution_price < Decimal("0.0000"):
            return _unavailable("A player-share settlement contains invalid quantity or price data.")

        player_state = state.setdefault(
            event.player_id,
            {"quantity": Decimal("0.0000"), "cost_basis": Decimal("0.0000")},
        )

        if event.event_type == "buy":
            total_paid = _amount(gross_amount + fee)
            player_state["quantity"] = _amount(player_state["quantity"] + quantity)
            player_state["cost_basis"] = _amount(player_state["cost_basis"] + total_paid)
            continue

        if player_state["quantity"] < quantity or player_state["quantity"] <= Decimal("0.0000"):
            return _unavailable("A player-share sale has no complete preceding cost basis.")

        average_cost = _amount(player_state["cost_basis"] / player_state["quantity"])
        cost_basis = _amount(average_cost * quantity)
        net_proceeds = _amount(gross_amount - fee)
        realized = _amount(net_proceeds - cost_basis)
        player_state["quantity"] = _amount(player_state["quantity"] - quantity)
        player_state["cost_basis"] = _amount(player_state["cost_basis"] - cost_basis)
        if player_state["quantity"] == Decimal("0.0000"):
            player_state["cost_basis"] = Decimal("0.0000")

        rows.append(
            RealizedPLRow(
                event_id=str(event.id),
                player_id=event.player_id,
                occurred_at=event.created_at,
                quantity=quantity,
                execution_price=execution_price,
                gross_proceeds=gross_amount,
                fee=fee,
                cost_basis=cost_basis,
                realized_pl=realized,
                transaction_id=transaction_id,
                idempotency_reference=(
                    str(meta.get("idempotency_reference")) if meta.get("idempotency_reference") else None
                ),
            )
        )

    total = _amount(sum((row.realized_pl for row in rows), Decimal("0.0000")))
    return RealizedPLSummary(total=total, available=True, rows=rows)


__all__ = ["RealizedPLRow", "RealizedPLSummary", "calculate_user_realized_pl"]
