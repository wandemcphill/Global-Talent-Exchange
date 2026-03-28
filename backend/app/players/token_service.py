from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.economy.governor_service import EconomyGovernorService
from app.ingestion.models import Player
from app.models.base import generate_uuid
from app.models.player_token_market import PlayerShareEvent, PlayerShareHolding, PlayerShareMarket
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")


class PlayerTokenMarketError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


class PlayerTokenMarketService:
    def __init__(self, session: Session, *, wallet_service: WalletService | None = None) -> None:
        self.session = session
        self.wallet_service = wallet_service or WalletService()

    def issue_market(
        self,
        *,
        actor: User,
        player_id: str,
        total_shares: int = 1000,
        share_price_coin: Decimal,
        status: str = "active",
    ) -> PlayerShareMarket:
        self._require_admin(actor)
        player = self._get_player(player_id)
        if total_shares <= 0:
            raise PlayerTokenMarketError("Total shares must be greater than zero.", reason="total_shares_invalid")
        normalized_price = self._amount(share_price_coin)
        if normalized_price <= Decimal("0.0000"):
            raise PlayerTokenMarketError("Share price must be greater than zero.", reason="share_price_invalid")
        market = self.session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id))
        if market is None:
            market = PlayerShareMarket(player_id=player.id)
            self.session.add(market)
        elif int(market.circulating_shares or 0) > int(total_shares):
            raise PlayerTokenMarketError(
                "Total shares cannot be lower than currently circulating shares.",
                reason="total_shares_below_circulation",
            )
        market.total_shares = int(total_shares)
        market.share_price_coin = normalized_price
        market.status = status.strip().lower() or "active"
        market.metadata_json = {
            **(market.metadata_json or {}),
            "player_name": player.canonical_display_name or player.full_name,
            "issued_by_user_id": actor.id,
        }
        self._record_event(
            player_id=player.id,
            actor_user_id=actor.id,
            event_type="issue",
            share_delta=0,
            price_per_share_coin=normalized_price,
            gross_amount_coin=Decimal("0.0000"),
            metadata_json={"total_shares": int(total_shares), "status": market.status},
        )
        self.session.flush()
        return market

    def get_market(self, *, player_id: str) -> PlayerShareMarket:
        market = self.session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player_id))
        if market is None:
            raise PlayerTokenMarketError("Player share market was not found.", reason="market_not_found")
        return market

    def list_events(self, *, player_id: str, limit: int = 50) -> list[PlayerShareEvent]:
        return list(
            self.session.scalars(
                select(PlayerShareEvent)
                .where(PlayerShareEvent.player_id == player_id)
                .order_by(PlayerShareEvent.created_at.desc())
                .limit(limit)
            ).all()
        )

    def list_holdings(self, *, user_id: str, limit: int = 50) -> list[PlayerShareHolding]:
        return list(
            self.session.scalars(
                select(PlayerShareHolding)
                .where(PlayerShareHolding.user_id == user_id, PlayerShareHolding.share_count > 0)
                .order_by(PlayerShareHolding.updated_at.desc())
                .limit(limit)
            ).all()
        )

    def get_holding(self, *, user_id: str, player_id: str) -> PlayerShareHolding | None:
        return self.session.scalar(
            select(PlayerShareHolding).where(
                PlayerShareHolding.user_id == user_id,
                PlayerShareHolding.player_id == player_id,
            )
        )

    def buy_shares(self, *, actor: User, player_id: str, share_count: int) -> dict[str, Any]:
        market = self.get_market(player_id=player_id)
        if market.status != "active":
            raise PlayerTokenMarketError("Player share market is not active.", reason="market_inactive")
        if share_count <= 0:
            raise PlayerTokenMarketError("Share count must be greater than zero.", reason="share_count_invalid")
        available = int(market.total_shares or 0) - int(market.circulating_shares or 0)
        if share_count > available:
            raise PlayerTokenMarketError("Requested shares exceed current supply.", reason="share_supply_insufficient")

        gross_amount = self._amount(Decimal(market.share_price_coin) * Decimal(share_count))
        buyer_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        market_liquidity_account = self.wallet_service.ensure_market_liquidity_account(self.session, LedgerUnit.COIN)
        try:
            entries = self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=buyer_account,
                        amount=-gross_amount,
                        source_tag=LedgerSourceTag.PLAYER_SHARE_PURCHASE,
                        transaction_type=LedgerTransactionType.TRADE_BUY,
                    ),
                    LedgerPosting(
                        account=market_liquidity_account,
                        amount=gross_amount,
                        source_tag=LedgerSourceTag.PLAYER_SHARE_PURCHASE,
                        transaction_type=LedgerTransactionType.TRADE_BUY,
                    ),
                ],
                reason=LedgerEntryReason.TRADE_SETTLEMENT,
                source_tag=LedgerSourceTag.PLAYER_SHARE_PURCHASE,
                reference=f"player-share-buy:{player_id}:{generate_uuid()}",
                description=f"Purchased {share_count} player shares for {player_id}",
                actor=actor,
            )
        except InsufficientBalanceError as exc:
            raise PlayerTokenMarketError(str(exc), reason="insufficient_balance") from exc

        holding = self.get_holding(user_id=actor.id, player_id=player_id)
        if holding is None:
            holding = PlayerShareHolding(user_id=actor.id, player_id=player_id)
            self.session.add(holding)
            previous_shares = 0
            previous_cost = Decimal("0.0000")
        else:
            previous_shares = int(holding.share_count or 0)
            previous_cost = self._amount(holding.average_cost_coin)
        new_share_count = previous_shares + int(share_count)
        total_cost = (previous_cost * Decimal(previous_shares)) + gross_amount
        holding.share_count = new_share_count
        holding.average_cost_coin = self._amount(total_cost / Decimal(new_share_count))
        holding.metadata_json = {
            **(holding.metadata_json or {}),
            "last_transaction_id": entries[0].transaction_id,
        }
        market.circulating_shares = int(market.circulating_shares or 0) + int(share_count)
        self._record_event(
            player_id=player_id,
            user_id=actor.id,
            actor_user_id=actor.id,
            event_type="buy",
            share_delta=int(share_count),
            price_per_share_coin=self._amount(market.share_price_coin),
            gross_amount_coin=gross_amount,
            metadata_json={"transaction_id": entries[0].transaction_id},
        )
        self.session.flush()
        return {
            "market": market,
            "holding": holding,
            "transaction_id": entries[0].transaction_id,
            "gross_amount_coin": gross_amount,
        }

    def apply_performance_adjustment(
        self,
        *,
        actor: User,
        player_id: str,
        multiplier: Decimal,
        reason: str | None = None,
    ) -> PlayerShareMarket:
        self._require_admin(actor)
        market = self.get_market(player_id=player_id)
        normalized_multiplier = self._amount(multiplier)
        if normalized_multiplier <= Decimal("0.0000"):
            raise PlayerTokenMarketError("Performance multiplier must be greater than zero.", reason="multiplier_invalid")
        reference_price = self._amount(market.share_price_coin)
        proposed_price = self._amount(reference_price * normalized_multiplier)
        market.share_price_coin = EconomyGovernorService(self.session).clamp_price_change(
            reference_price=reference_price,
            proposed_price=proposed_price,
        )
        self._record_event(
            player_id=player_id,
            actor_user_id=actor.id,
            event_type="performance",
            share_delta=0,
            price_per_share_coin=self._amount(market.share_price_coin),
            gross_amount_coin=Decimal("0.0000"),
            metadata_json={"multiplier": str(normalized_multiplier), "reason": reason},
        )
        self.session.flush()
        return market

    def distribute_dividend(
        self,
        *,
        actor: User,
        player_id: str,
        gross_amount_coin: Decimal,
        note: str | None = None,
    ) -> dict[str, Any]:
        self._require_admin(actor)
        market = self.get_market(player_id=player_id)
        normalized_gross = self._amount(gross_amount_coin)
        if normalized_gross <= Decimal("0.0000"):
            raise PlayerTokenMarketError("Dividend amount must be positive.", reason="dividend_invalid")
        holdings = list(
            self.session.scalars(
                select(PlayerShareHolding)
                .where(PlayerShareHolding.player_id == player_id, PlayerShareHolding.share_count > 0)
                .order_by(PlayerShareHolding.share_count.desc(), PlayerShareHolding.updated_at.asc())
            ).all()
        )
        if not holdings:
            raise PlayerTokenMarketError("No shareholders are available for dividend distribution.", reason="no_shareholders")
        total_shares = sum(int(item.share_count or 0) for item in holdings)
        if total_shares <= 0:
            raise PlayerTokenMarketError("No circulating shares are available for dividend distribution.", reason="no_circulation")

        source_account = self.wallet_service.ensure_market_liquidity_account(self.session, LedgerUnit.COIN)
        payouts: list[tuple[PlayerShareHolding, Decimal]] = []
        allocated = Decimal("0.0000")
        for index, holding in enumerate(holdings):
            if index == len(holdings) - 1:
                payout = self._amount(normalized_gross - allocated)
            else:
                payout = self._amount(normalized_gross * Decimal(int(holding.share_count)) / Decimal(total_shares))
                allocated += payout
            payouts.append((holding, payout))

        postings = [
            LedgerPosting(
                account=source_account,
                amount=-normalized_gross,
                source_tag=LedgerSourceTag.PLAYER_SHARE_DIVIDEND,
                transaction_type=LedgerTransactionType.ADJUSTMENT,
            )
        ]
        for holding, payout in payouts:
            user = holding.user
            if user is None:
                continue
            account = self.wallet_service.get_user_account(self.session, user, LedgerUnit.COIN)
            postings.append(
                LedgerPosting(
                    account=account,
                    amount=payout,
                    source_tag=LedgerSourceTag.PLAYER_SHARE_DIVIDEND,
                    transaction_type=LedgerTransactionType.ADJUSTMENT,
                )
            )
            holding.dividends_earned_coin = self._amount(Decimal(holding.dividends_earned_coin) + payout)

        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.PLAYER_SHARE_DIVIDEND,
            reference=f"player-share-dividend:{player_id}:{generate_uuid()}",
            description=f"Dividend distribution for player shares {player_id}",
            actor=actor,
            metadata={"note": note},
        )
        market.revenue_distributed_coin = self._amount(Decimal(market.revenue_distributed_coin) + normalized_gross)
        for holding, payout in payouts:
            self._record_event(
                player_id=player_id,
                user_id=holding.user_id,
                actor_user_id=actor.id,
                event_type="dividend",
                share_delta=0,
                price_per_share_coin=self._amount(market.share_price_coin),
                gross_amount_coin=payout,
                metadata_json={"transaction_id": entries[0].transaction_id, "note": note},
            )
        self.session.flush()
        return {
            "market": market,
            "transaction_id": entries[0].transaction_id,
            "gross_amount_coin": normalized_gross,
        }

    def _record_event(
        self,
        *,
        player_id: str,
        event_type: str,
        share_delta: int,
        price_per_share_coin: Decimal,
        gross_amount_coin: Decimal,
        metadata_json: dict[str, Any] | None = None,
        user_id: str | None = None,
        actor_user_id: str | None = None,
    ) -> None:
        self.session.add(
            PlayerShareEvent(
                player_id=player_id,
                user_id=user_id,
                actor_user_id=actor_user_id,
                event_type=event_type,
                share_delta=share_delta,
                price_per_share_coin=self._amount(price_per_share_coin),
                gross_amount_coin=self._amount(gross_amount_coin),
                metadata_json=metadata_json or {},
            )
        )

    def _require_admin(self, actor: User) -> None:
        if actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise PlayerTokenMarketError("Admin access is required.", reason="admin_required")

    def _get_player(self, player_id: str) -> Player:
        player = self.session.get(Player, player_id)
        if player is None:
            raise PlayerTokenMarketError("Player was not found.", reason="player_not_found")
        return player

    @staticmethod
    def _amount(value: Decimal | str | int | float | None) -> Decimal:
        return Decimal(str(value or "0.0000")).quantize(AMOUNT_QUANTUM)


__all__ = ["PlayerTokenMarketError", "PlayerTokenMarketService"]
