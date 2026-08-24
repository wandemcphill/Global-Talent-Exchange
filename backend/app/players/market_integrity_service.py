from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.player_token_market import PlayerShareHolding, PlayerShareMarket
from app.models.wallet import LedgerAccount, LedgerAccountKind, LedgerUnit
from app.wallets.service import WalletService


ZERO = Decimal("0.0000")


@dataclass(frozen=True, slots=True)
class MarketIntegrityIssue:
    code: str
    severity: str
    player_id: str
    market_id: str
    detail: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MarketIntegrityReport:
    markets_scanned: int
    active_markets: int
    healthy_markets: int
    issue_count: int
    issues: tuple[MarketIntegrityIssue, ...]

    @property
    def healthy(self) -> bool:
        return self.issue_count == 0


class PlayerShareMarketIntegrityService:
    """Read-only reconciliation service for the player-share economy."""

    def __init__(self, session: Session, *, wallet_service: WalletService | None = None) -> None:
        self.session = session
        self.wallet_service = wallet_service or WalletService()

    @staticmethod
    def _liquidity_account_code(player_id: str) -> str:
        return f"platform:player_share:{player_id}:liquidity"

    def _liquidity_balance(self, player_id: str) -> Decimal:
        account = self.session.scalar(
            select(LedgerAccount).where(
                LedgerAccount.code == self._liquidity_account_code(player_id),
                LedgerAccount.unit == LedgerUnit.COIN,
                LedgerAccount.kind == LedgerAccountKind.SYSTEM,
            )
        )
        if account is None:
            return ZERO
        return self.wallet_service.get_balance(self.session, account)

    def inspect_market(self, market: PlayerShareMarket) -> list[MarketIntegrityIssue]:
        issues: list[MarketIntegrityIssue] = []
        player = market.player or self.session.get(Player, market.player_id)
        metadata = dict(market.metadata_json or {})
        circulating = int(market.circulating_shares or 0)
        total = int(market.total_shares or 0)
        price = Decimal(str(market.share_price_coin or ZERO))
        liquidity = self._liquidity_balance(market.player_id)

        def add(code: str, severity: str, detail: str, **extra: Any) -> None:
            issues.append(
                MarketIntegrityIssue(
                    code=code,
                    severity=severity,
                    player_id=market.player_id,
                    market_id=market.id,
                    detail=detail,
                    metadata=extra,
                )
            )

        if total <= 0:
            add("invalid_total_supply", "critical", "Market total share supply must be positive.")
        if circulating < 0:
            add("negative_circulation", "critical", "Market circulation cannot be negative.")
        if circulating > total:
            add(
                "circulation_exceeds_supply",
                "critical",
                "Circulating shares exceed total supply.",
                circulating=circulating,
                total=total,
            )
        if price < ZERO:
            add("negative_share_price", "critical", "Share price cannot be negative.")
        if market.status == "active" and price <= ZERO:
            add("active_zero_price", "critical", "An active market must have a positive share price.")
        if liquidity < ZERO:
            add("negative_liquidity", "critical", "Market liquidity ledger balance is negative.")

        if market.status == "active" and (
            metadata.get("market_issued") is not True or metadata.get("auto_initialized") is True
        ):
            add(
                "missing_issuance_provenance",
                "high",
                "Active market is not proven to have been explicitly issued.",
                market_issued=metadata.get("market_issued"),
                auto_initialized=metadata.get("auto_initialized"),
            )

        if player is None:
            add("player_missing", "critical", "Market references a missing player.")
        elif not bool(player.is_tradable) and market.status == "active":
            add(
                "ineligible_active_market",
                "high",
                "Active market belongs to a player who is no longer tradable.",
            )

        holding_sum = int(
            self.session.scalar(
                select(func.coalesce(func.sum(PlayerShareHolding.share_count), 0)).where(
                    PlayerShareHolding.player_id == market.player_id,
                    PlayerShareHolding.share_count > 0,
                )
            )
            or 0
        )
        if holding_sum != circulating:
            add(
                "holding_circulation_mismatch",
                "critical",
                "Positive holdings do not reconcile to market circulation.",
                holding_shares=holding_sum,
                circulating_shares=circulating,
            )

        metadata_liquidity = metadata.get("liquidity_coin")
        if metadata_liquidity is not None:
            try:
                projected = Decimal(str(metadata_liquidity))
            except (TypeError, ValueError):
                add("invalid_liquidity_metadata", "high", "Market liquidity metadata is not numeric.")
            else:
                if projected.quantize(Decimal("0.0001")) != liquidity.quantize(Decimal("0.0001")):
                    add(
                        "liquidity_metadata_drift",
                        "high",
                        "Stored liquidity metadata does not match the authoritative ledger balance.",
                        metadata_liquidity=str(projected),
                        ledger_liquidity=str(liquidity),
                    )

        return issues

    def audit(self, *, limit: int = 5000) -> MarketIntegrityReport:
        if limit <= 0:
            raise ValueError("limit must be positive")
        markets = list(
            self.session.scalars(
                select(PlayerShareMarket).order_by(PlayerShareMarket.id.asc()).limit(limit)
            ).all()
        )
        issues: list[MarketIntegrityIssue] = []
        active = 0
        healthy = 0
        for market in markets:
            if market.status == "active":
                active += 1
            market_issues = self.inspect_market(market)
            issues.extend(market_issues)
            if not market_issues:
                healthy += 1
        return MarketIntegrityReport(
            markets_scanned=len(markets),
            active_markets=active,
            healthy_markets=healthy,
            issue_count=len(issues),
            issues=tuple(issues),
        )


__all__ = ["MarketIntegrityIssue", "MarketIntegrityReport", "PlayerShareMarketIntegrityService"]
