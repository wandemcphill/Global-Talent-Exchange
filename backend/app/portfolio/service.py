from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.ingestion.models import MarketSignal
from backend.app.models.user import User
from backend.app.models.wallet import LedgerAccount, LedgerEntry, LedgerEntryReason
from backend.app.players.read_models import PlayerSummaryReadModel
from backend.app.value_engine.read_models import PlayerValueSnapshotRecord
from backend.app.wallets.service import WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
PRICE_SIGNAL_TYPES = (
    "current_credits",
    "credits",
    "market_mid_price_credits",
    "mid_price_credits",
    "snapshot_mid_price_credits",
    "index_price_credits",
    "last_trade_price_credits",
    "last_sale_price_credits",
    "recent_trade_price_credits",
)


class PortfolioValuationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SettledExecution:
    execution_id: str
    player_id: str
    side: str
    quantity: Decimal
    price: Decimal
    gross_amount: Decimal
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class PortfolioHolding:
    player_id: str
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pl: Decimal
    unrealized_pl_percent: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    total_market_value: Decimal
    cash_balance: Decimal
    total_equity: Decimal
    unrealized_pl_total: Decimal
    realized_pl_total: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    holdings: list[PortfolioHolding]
    summary: PortfolioSummary


@dataclass(slots=True)
class PortfolioService:
    wallet_service: WalletService = field(default_factory=WalletService)

    def build_for_user(self, session: Session, user: User) -> PortfolioSnapshot:
        executions = self._load_settled_executions(session, user)
        position_state: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {
                "quantity": Decimal("0.0000"),
                "cost_basis": Decimal("0.0000"),
                "realized_pl": Decimal("0.0000"),
            }
        )

        for execution in executions:
            state = position_state[execution.player_id]
            if execution.side == "buy":
                state["quantity"] = self._normalize_amount(state["quantity"] + execution.quantity)
                state["cost_basis"] = self._normalize_amount(state["cost_basis"] + execution.gross_amount)
                continue

            if state["quantity"] < execution.quantity:
                raise PortfolioValuationError(
                    f"Settled sell quantity exceeds owned position for player {execution.player_id}."
                )

            average_cost = (
                self._normalize_amount(state["cost_basis"] / state["quantity"])
                if state["quantity"] > Decimal("0.0000")
                else Decimal("0.0000")
            )
            cost_reduction = self._normalize_amount(average_cost * execution.quantity)
            state["quantity"] = self._normalize_amount(state["quantity"] - execution.quantity)
            state["cost_basis"] = self._normalize_amount(state["cost_basis"] - cost_reduction)
            state["realized_pl"] = self._normalize_amount(
                state["realized_pl"] + execution.gross_amount - cost_reduction
            )
            if state["quantity"] == Decimal("0.0000"):
                state["cost_basis"] = Decimal("0.0000")

        holdings: list[PortfolioHolding] = []
        realized_pl_total = Decimal("0.0000")
        unrealized_pl_total = Decimal("0.0000")
        total_market_value = Decimal("0.0000")

        for player_id, state in sorted(position_state.items(), key=lambda item: item[0]):
            realized_pl_total = self._normalize_amount(realized_pl_total + state["realized_pl"])
            if state["quantity"] <= Decimal("0.0000"):
                continue

            average_cost = self._normalize_amount(state["cost_basis"] / state["quantity"])
            current_price = self._resolve_current_price(session, player_id)
            market_value = self._normalize_amount(state["quantity"] * current_price)
            unrealized_pl = self._normalize_amount(market_value - state["cost_basis"])
            unrealized_pl_percent = Decimal("0.0000")
            if state["cost_basis"] > Decimal("0.0000"):
                unrealized_pl_percent = self._normalize_amount((unrealized_pl / state["cost_basis"]) * Decimal("100"))

            total_market_value = self._normalize_amount(total_market_value + market_value)
            unrealized_pl_total = self._normalize_amount(unrealized_pl_total + unrealized_pl)
            holdings.append(
                PortfolioHolding(
                    player_id=player_id,
                    quantity=state["quantity"],
                    average_cost=average_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pl=unrealized_pl,
                    unrealized_pl_percent=unrealized_pl_percent,
                )
            )

        holdings.sort(key=lambda item: (-item.market_value, item.player_id))
        wallet_summary = self.wallet_service.get_wallet_summary(session, user)
        return PortfolioSnapshot(
            holdings=holdings,
            summary=PortfolioSummary(
                total_market_value=total_market_value,
                cash_balance=wallet_summary.available_balance,
                total_equity=self._normalize_amount(wallet_summary.total_balance + total_market_value),
                unrealized_pl_total=unrealized_pl_total,
                realized_pl_total=realized_pl_total,
            ),
        )

    def build_holdings(self, session: Session, user: User) -> list[PortfolioHolding]:
        return self.build_for_user(session, user).holdings

    def build_summary(self, session: Session, user: User) -> PortfolioSummary:
        return self.build_for_user(session, user).summary

    def _load_settled_executions(self, session: Session, user: User) -> list[SettledExecution]:
        rows = session.execute(
            select(LedgerEntry, LedgerAccount)
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerEntry.reason == LedgerEntryReason.TRADE_SETTLEMENT,
                LedgerEntry.external_reference.is_not(None),
                or_(
                    LedgerAccount.code.like(f"position:{user.id}:%"),
                    LedgerAccount.code.like(f"user:{user.id}:credit%"),
                ),
            )
            .order_by(LedgerEntry.created_at.asc(), LedgerEntry.id.asc())
        ).all()

        entries_by_execution: dict[str, list[tuple[LedgerEntry, LedgerAccount]]] = defaultdict(list)
        for entry, account in rows:
            if entry.external_reference is None:
                continue
            entries_by_execution[entry.external_reference].append((entry, account))

        executions: list[SettledExecution] = []
        for execution_id, execution_rows in entries_by_execution.items():
            asset_entry: LedgerEntry | None = None
            asset_account: LedgerAccount | None = None
            cash_entry: LedgerEntry | None = None
            for entry, account in execution_rows:
                if account.code.startswith("position:"):
                    asset_entry = entry
                    asset_account = account
                elif account.code.startswith(f"user:{user.id}:credit"):
                    cash_entry = entry

            if asset_entry is None or asset_account is None or cash_entry is None:
                continue

            quantity = self._normalize_amount(abs(asset_entry.amount))
            if quantity == Decimal("0.0000"):
                continue

            gross_amount = self._normalize_amount(abs(cash_entry.amount))
            executions.append(
                SettledExecution(
                    execution_id=execution_id,
                    player_id=self._player_id_from_position_code(asset_account.code),
                    side="buy" if asset_entry.amount > Decimal("0.0000") else "sell",
                    quantity=quantity,
                    price=self._normalize_amount(gross_amount / quantity),
                    gross_amount=gross_amount,
                    occurred_at=asset_entry.created_at,
                )
            )

        executions.sort(key=lambda item: (item.occurred_at, item.execution_id))
        return executions

    def _resolve_current_price(self, session: Session, player_id: str) -> Decimal:
        summary = session.get(PlayerSummaryReadModel, player_id)
        if summary is not None and summary.current_value_credits > 0:
            return self._normalize_amount(summary.current_value_credits)

        snapshot = session.scalar(
            select(PlayerValueSnapshotRecord)
            .where(PlayerValueSnapshotRecord.player_id == player_id)
            .order_by(PlayerValueSnapshotRecord.as_of.desc(), PlayerValueSnapshotRecord.created_at.desc())
            .limit(1)
        )
        if snapshot is not None and snapshot.target_credits > 0:
            return self._normalize_amount(snapshot.target_credits)

        signal = session.scalar(
            select(MarketSignal)
            .where(
                MarketSignal.player_id == player_id,
                MarketSignal.signal_type.in_(PRICE_SIGNAL_TYPES),
            )
            .order_by(MarketSignal.as_of.desc(), MarketSignal.created_at.desc(), MarketSignal.id.desc())
            .limit(1)
        )
        if signal is not None and signal.score > 0:
            return self._normalize_amount(signal.score)

        return Decimal("0.0000")

    @staticmethod
    def _player_id_from_position_code(code: str) -> str:
        _, _, player_id, _ = code.split(":", 3)
        return player_id

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)
