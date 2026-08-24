from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.event_backbone import defer_event_publish_until_commit
from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.economy.governor_service import EconomyGovernorService
from app.ingestion.models import Player
from app.market.player_eligibility_policy import is_preseeded_national_regen, is_share_market_eligible
from app.models.admin_rules import AdminRewardRule
from app.models.base import generate_uuid
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.player_token_market import PlayerShareEvent, PlayerShareHolding, PlayerShareMarket
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.players.token_market_defaults import MIN_SHARE_PRICE_COIN, resolve_player_share_market_config
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
MAX_PRICE_IMPACT_PCT = Decimal("0.0500")
MIN_PRICE_IMPACT_PCT = Decimal("0.0050")
PRICE_IMPACT_MULTIPLIER = Decimal("2.5000")
VALID_PLAYER_SHARE_MARKET_STATUSES = frozenset({"active", "paused", "closed"})


class PlayerTokenMarketError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


class PlayerTokenMarketService:
    def __init__(
        self,
        session: Session,
        *,
        wallet_service: WalletService | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.session = session
        self.wallet_service = wallet_service or WalletService(event_publisher=event_publisher)
        self.event_publisher = event_publisher or getattr(
            self.wallet_service, "event_publisher", InMemoryEventPublisher()
        )

    def _active_trading_fee_bps(self) -> int:
        rule = self.session.scalar(
            select(AdminRewardRule).where(AdminRewardRule.active.is_(True)).order_by(AdminRewardRule.updated_at.desc())
        )
        return int(rule.trading_fee_bps if rule is not None else 2000)

    def _trading_fee(self, gross_amount: Decimal) -> Decimal:
        fee_bps = self._active_trading_fee_bps()
        if fee_bps <= 0:
            return Decimal("0.0000")
        return self._amount((gross_amount * Decimal(fee_bps)) / Decimal("10000"))

    def issue_market(
        self,
        *,
        actor: User,
        player_id: str,
        total_shares: int = 1000,
        share_price_coin: Decimal,
        liquidity_coin: Decimal | None = None,
        status: str = "active",
    ) -> PlayerShareMarket:
        return self._upsert_market(
            player_id=player_id,
            actor=actor,
            total_shares=total_shares,
            share_price_coin=share_price_coin,
            liquidity_coin=liquidity_coin,
            status=status,
            require_admin=True,
            record_event=True,
            auto_initialized=False,
        )

    def ensure_market(
        self,
        *,
        player_id: str,
        total_shares: int | None = None,
        share_price_coin: Decimal | int | float | str | None = None,
        liquidity_coin: Decimal | int | float | str | None = None,
        status: str | None = "active",
    ) -> PlayerShareMarket:
        market = self.session.scalar(
            select(PlayerShareMarket)
            .options(
                selectinload(PlayerShareMarket.player).selectinload(Player.current_club),
                selectinload(PlayerShareMarket.player).selectinload(Player.country),
            )
            .where(PlayerShareMarket.player_id == player_id)
        )
        if market is None:
            return self._upsert_market(
                player_id=player_id,
                actor=None,
                total_shares=total_shares,
                share_price_coin=share_price_coin,
                liquidity_coin=liquidity_coin,
                status=status,
                require_admin=False,
                record_event=False,
                auto_initialized=True,
            )
        return self._synchronize_market_defaults(
            market,
            total_shares=total_shares,
            share_price_coin=share_price_coin,
            liquidity_coin=liquidity_coin,
            status=status,
        )

    def get_market(self, *, player_id: str) -> PlayerShareMarket:
        return self.ensure_market(player_id=player_id)

    def get_market_view(self, *, player_id: str) -> dict[str, Any]:
        return self._serialize_market_view(self.get_market(player_id=player_id))

    def list_markets(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
    ) -> dict[str, Any]:
        normalized_search = (search or "").strip()
        filters = [
            Player.is_tradable.is_(True),
            PlayerShareMarket.status == "active",
        ]
        if normalized_search:
            search_pattern = f"%{normalized_search}%"
            filters.append(
                or_(
                    Player.full_name.ilike(search_pattern),
                    Player.canonical_display_name.ilike(search_pattern),
                )
            )

        total = int(
            self.session.scalar(
                select(func.count(PlayerShareMarket.id))
                .join(Player, Player.id == PlayerShareMarket.player_id)
                .where(*filters)
            )
            or 0
        )
        statement = (
            select(PlayerShareMarket)
            .join(Player, Player.id == PlayerShareMarket.player_id)
            .options(
                selectinload(PlayerShareMarket.player).selectinload(Player.current_club),
                selectinload(PlayerShareMarket.player).selectinload(Player.country),
            )
            .where(*filters)
            .order_by(PlayerShareMarket.updated_at.desc(), Player.full_name.asc())
            .offset(offset)
            .limit(limit)
        )
        markets = list(self.session.scalars(statement).all())
        items = [self._serialize_market_list_item(self._synchronize_market_defaults(market)) for market in markets]
        return {
            "items": items,
            "limit": limit,
            "offset": offset,
            "total": total,
        }

    def list_events(self, *, player_id: str, limit: int = 50) -> list[PlayerShareEvent]:
        self.ensure_market(player_id=player_id)
        return list(
            self.session.scalars(
                select(PlayerShareEvent)
                .where(PlayerShareEvent.player_id == player_id)
                .order_by(PlayerShareEvent.created_at.desc(), PlayerShareEvent.id.desc())
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
        market = self.ensure_market(player_id=player_id)
        market = self.session.scalar(
            select(PlayerShareMarket)
            .where(PlayerShareMarket.id == market.id)
            .with_for_update()
        )
        if market is None:
            raise PlayerTokenMarketError("Player share market was not found.", reason="market_not_found")
        self._assert_share_market_eligible(market.player)
        if market.status != "active":
            raise PlayerTokenMarketError("Player share market is not active.", reason="market_inactive")
        if share_count <= 0:
            raise PlayerTokenMarketError("Share count must be greater than zero.", reason="share_count_invalid")

        available = int(market.total_shares or 0) - int(market.circulating_shares or 0)
        if share_count > available:
            raise PlayerTokenMarketError("Requested shares exceed current supply.", reason="share_supply_insufficient")

        executed_price = self._amount(market.share_price_coin)
        gross_amount = self._amount(executed_price * Decimal(share_count))
        fee_amount = self._trading_fee(gross_amount)
        total_buyer_debit = self._amount(gross_amount + fee_amount)
        buyer_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        market_liquidity_account = self._ensure_player_share_liquidity_account(player_id)
        trade_fee_account = self.wallet_service.ensure_trade_fee_account(self.session, LedgerUnit.COIN)
        try:
            postings = [
                LedgerPosting(
                    account=buyer_account,
                    amount=-total_buyer_debit,
                    source_tag=LedgerSourceTag.PLAYER_SHARE_PURCHASE,
                    transaction_type=LedgerTransactionType.TRADE_BUY,
                ),
                LedgerPosting(
                    account=market_liquidity_account,
                    amount=gross_amount,
                    source_tag=LedgerSourceTag.PLAYER_SHARE_PURCHASE,
                    transaction_type=LedgerTransactionType.TRADE_BUY,
                ),
            ]
            if fee_amount > Decimal("0.0000"):
                postings.append(
                    LedgerPosting(
                        account=trade_fee_account,
                        amount=fee_amount,
                        source_tag=LedgerSourceTag.PLAYER_SHARE_PURCHASE,
                        transaction_type=LedgerTransactionType.TRADE_BUY,
                    )
                )
            entries = self.wallet_service.append_transaction(
                self.session,
                postings=postings,
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
        total_cost = (previous_cost * Decimal(previous_shares)) + total_buyer_debit
        holding.share_count = new_share_count
        holding.average_cost_coin = self._amount(total_cost / Decimal(new_share_count))
        holding.metadata_json = {
            **(holding.metadata_json or {}),
            "last_transaction_id": entries[0].transaction_id,
            "last_trade_side": "buy",
            "last_trade_price_coin": str(executed_price),
        }

        market.circulating_shares = int(market.circulating_shares or 0) + int(share_count)
        previous_price = executed_price
        market.share_price_coin = self._price_after_trade(market=market, direction="buy", share_count=share_count)
        liquidity_balance = self._sync_market_liquidity_balance(market)
        self._record_event(
            player_id=player_id,
            user_id=actor.id,
            actor_user_id=actor.id,
            event_type="buy",
            share_delta=int(share_count),
            price_per_share_coin=executed_price,
            gross_amount_coin=gross_amount,
            metadata_json={
                "market_id": market.id,
                "transaction_id": entries[0].transaction_id,
                "fee_amount_coin": str(fee_amount),
                "net_amount_coin": str(total_buyer_debit),
                "circulating_shares": int(market.circulating_shares or 0),
                "total_shares": int(market.total_shares or 0),
                "previous_share_price_coin": str(previous_price),
                "updated_share_price_coin": str(self._amount(market.share_price_coin)),
                "liquidity_coin": str(liquidity_balance),
            },
        )
        self._stage_market_trade_event(
            market=market,
            actor=actor,
            event_type="buy",
            transaction_id=entries[0].transaction_id,
            share_delta=share_count,
            executed_price=executed_price,
            previous_price=previous_price,
            gross_amount=gross_amount,
        )
        self.session.flush()
        return {
            "market": self._serialize_market_view(market),
            "holding": holding,
            "transaction_id": entries[0].transaction_id,
            "gross_amount_coin": gross_amount,
            "fee_amount_coin": fee_amount,
            "net_amount_coin": total_buyer_debit,
        }

    def sell_shares(self, *, actor: User, player_id: str, share_count: int) -> dict[str, Any]:
        market = self.ensure_market(player_id=player_id)
        market = self.session.scalar(select(PlayerShareMarket).options(selectinload(PlayerShareMarket.player)).where(PlayerShareMarket.id == market.id).with_for_update())
        if market is None:
            raise PlayerTokenMarketError("Player share market was not found.", reason="market_not_found")
        self._assert_share_market_eligible(market.player)
        if market.status != "active":
            raise PlayerTokenMarketError("Player share market is not active.", reason="market_inactive")
        if share_count <= 0:
            raise PlayerTokenMarketError("Share count must be greater than zero.", reason="share_count_invalid")

        holding = self.session.scalar(
            select(PlayerShareHolding)
            .where(
                PlayerShareHolding.user_id == actor.id,
                PlayerShareHolding.player_id == player_id,
            )
            .with_for_update()
        )
        if holding is None or int(holding.share_count or 0) <= 0:
            raise PlayerTokenMarketError("No player share holding was found.", reason="holding_not_found")
        if int(holding.share_count or 0) < int(share_count):
            raise PlayerTokenMarketError("Requested shares exceed current ownership.", reason="shares_not_owned")

        executed_price = self._amount(market.share_price_coin)
        gross_amount = self._amount(executed_price * Decimal(share_count))
        fee_amount = self._trading_fee(gross_amount)
        net_seller_credit = self._amount(gross_amount - fee_amount)
        market_liquidity_account = self._ensure_player_share_liquidity_account(player_id)
        current_liquidity = self.wallet_service.get_balance(self.session, market_liquidity_account)
        if current_liquidity < gross_amount:
            raise PlayerTokenMarketError(
                "Market liquidity is too low to settle this sale right now.",
                reason="market_liquidity_insufficient",
            )

        seller_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        trade_fee_account = self.wallet_service.ensure_trade_fee_account(self.session, LedgerUnit.COIN)
        postings = [
            LedgerPosting(
                account=seller_account,
                amount=net_seller_credit,
                source_tag=LedgerSourceTag.PLAYER_SHARE_SALE,
                transaction_type=LedgerTransactionType.TRADE_SELL,
            ),
            LedgerPosting(
                account=market_liquidity_account,
                amount=-gross_amount,
                source_tag=LedgerSourceTag.PLAYER_SHARE_SALE,
                transaction_type=LedgerTransactionType.TRADE_SELL,
            ),
        ]
        if fee_amount > Decimal("0.0000"):
            postings.append(
                LedgerPosting(
                    account=trade_fee_account,
                    amount=fee_amount,
                    source_tag=LedgerSourceTag.PLAYER_SHARE_SALE,
                    transaction_type=LedgerTransactionType.TRADE_SELL,
                )
            )
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.TRADE_SETTLEMENT,
            source_tag=LedgerSourceTag.PLAYER_SHARE_SALE,
            reference=f"player-share-sell:{player_id}:{generate_uuid()}",
            description=f"Sold {share_count} player shares for {player_id}",
            actor=actor,
        )

        remaining_shares = int(holding.share_count or 0) - int(share_count)
        holding.share_count = remaining_shares
        if remaining_shares <= 0:
            holding.average_cost_coin = Decimal("0.0000")
        holding.metadata_json = {
            **(holding.metadata_json or {}),
            "last_transaction_id": entries[0].transaction_id,
            "last_trade_side": "sell",
            "last_trade_price_coin": str(executed_price),
        }

        market.circulating_shares = max(0, int(market.circulating_shares or 0) - int(share_count))
        previous_price = executed_price
        market.share_price_coin = self._price_after_trade(market=market, direction="sell", share_count=share_count)
        liquidity_balance = self._sync_market_liquidity_balance(market)
        self._record_event(
            player_id=player_id,
            user_id=actor.id,
            actor_user_id=actor.id,
            event_type="sell",
            share_delta=-int(share_count),
            price_per_share_coin=executed_price,
            gross_amount_coin=gross_amount,
            metadata_json={
                "market_id": market.id,
                "transaction_id": entries[0].transaction_id,
                "fee_amount_coin": str(fee_amount),
                "net_amount_coin": str(net_seller_credit),
                "circulating_shares": int(market.circulating_shares or 0),
                "total_shares": int(market.total_shares or 0),
                "previous_share_price_coin": str(previous_price),
                "updated_share_price_coin": str(self._amount(market.share_price_coin)),
                "liquidity_coin": str(liquidity_balance),
            },
        )
        self._stage_market_trade_event(
            market=market,
            actor=actor,
            event_type="sell",
            transaction_id=entries[0].transaction_id,
            share_delta=-share_count,
            executed_price=executed_price,
            previous_price=previous_price,
            gross_amount=gross_amount,
        )
        self.session.flush()
        return {
            "market": self._serialize_market_view(market),
            "holding": holding,
            "transaction_id": entries[0].transaction_id,
            "gross_amount_coin": gross_amount,
            "fee_amount_coin": fee_amount,
            "net_amount_coin": net_seller_credit,
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
            raise PlayerTokenMarketError(
                "Performance multiplier must be greater than zero.", reason="multiplier_invalid"
            )

        reference_price = self._amount(market.share_price_coin)
        proposed_price = self._amount(reference_price * normalized_multiplier)
        market.share_price_coin = EconomyGovernorService(self.session).clamp_price_change(
            reference_price=reference_price,
            proposed_price=proposed_price,
        )
        self._sync_market_liquidity_balance(market)
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
            raise PlayerTokenMarketError(
                "No shareholders are available for dividend distribution.", reason="no_shareholders"
            )

        total_shares = sum(int(item.share_count or 0) for item in holdings)
        if total_shares <= 0:
            raise PlayerTokenMarketError(
                "No circulating shares are available for dividend distribution.", reason="no_circulation"
            )

        source_account = self._ensure_player_share_liquidity_account(player_id)
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

        try:
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
        except InsufficientBalanceError as exc:
            raise PlayerTokenMarketError(
                "Market liquidity is too low to distribute this dividend right now.",
                reason="market_liquidity_insufficient",
            ) from exc

        market.revenue_distributed_coin = self._amount(Decimal(market.revenue_distributed_coin) + normalized_gross)
        liquidity_balance = self._sync_market_liquidity_balance(market)
        for holding, payout in payouts:
            self._record_event(
                player_id=player_id,
                user_id=holding.user_id,
                actor_user_id=actor.id,
                event_type="dividend",
                share_delta=0,
                price_per_share_coin=self._amount(market.share_price_coin),
                gross_amount_coin=payout,
                metadata_json={
                    "transaction_id": entries[0].transaction_id,
                    "note": note,
                    "liquidity_coin": str(liquidity_balance),
                },
            )
        self.session.flush()
        return {
            "market": self._serialize_market_view(market),
            "transaction_id": entries[0].transaction_id,
            "gross_amount_coin": normalized_gross,
        }

    def _upsert_market(
        self,
        *,
        player_id: str,
        actor: User | None,
        total_shares: int | None,
        share_price_coin: Decimal | int | float | str | None,
        liquidity_coin: Decimal | int | float | str | None,
        status: str | None,
        require_admin: bool,
        record_event: bool,
        auto_initialized: bool,
    ) -> PlayerShareMarket:
        if require_admin and actor is not None:
            self._require_admin(actor)

        player = self._get_player(player_id)
        if not is_share_market_eligible(player):
            raise PlayerTokenMarketError("Player is not eligible for a share market.", reason="market_ineligible")
        if total_shares is not None and int(total_shares) <= 0:
            raise PlayerTokenMarketError("Total shares must be greater than zero.", reason="total_shares_invalid")
        if share_price_coin is not None and self._amount(share_price_coin) <= Decimal("0.0000"):
            raise PlayerTokenMarketError("Share price must be greater than zero.", reason="share_price_invalid")
        if liquidity_coin is not None and self._amount(liquidity_coin) < Decimal("0.0000"):
            raise PlayerTokenMarketError("Liquidity must be zero or greater.", reason="liquidity_invalid")

        config = resolve_player_share_market_config(
            player,
            total_shares=total_shares,
            share_price_coin=share_price_coin,
            liquidity_coin=liquidity_coin,
            status=status,
        )
        normalized_status = self._normalize_market_status(config.status)

        market = self.session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id))
        if market is None:
            market = PlayerShareMarket(player_id=player.id)
            self.session.add(market)
        elif int(market.circulating_shares or 0) > int(config.total_shares):
            raise PlayerTokenMarketError(
                "Total shares cannot be lower than currently circulating shares.",
                reason="total_shares_below_circulation",
            )

        market.total_shares = int(config.total_shares)
        market.share_price_coin = self._amount(config.share_price_coin)
        market.status = normalized_status
        market.metadata_json = {
            **(market.metadata_json or {}),
            "player_name": player.canonical_display_name or player.full_name,
            "is_real_player": bool(player.is_real_player),
            "real_player_tier": player.real_player_tier,
            "market_issued": True,
            "auto_initialized": bool(auto_initialized),
            **({"issued_by_user_id": actor.id} if actor is not None else {}),
        }
        self.session.flush()

        liquidity_balance = self._ensure_liquidity_target(
            market,
            target_liquidity_coin=config.liquidity_coin,
            actor=actor,
        )
        self._update_market_metadata(
            market,
            liquidity_balance=liquidity_balance,
            initial_liquidity_coin=config.liquidity_coin,
            auto_initialized=auto_initialized,
        )

        if record_event:
            self._record_event(
                player_id=player.id,
                actor_user_id=actor.id if actor is not None else None,
                event_type="issue",
                share_delta=0,
                price_per_share_coin=self._amount(market.share_price_coin),
                gross_amount_coin=Decimal("0.0000"),
                metadata_json={
                    "market_id": market.id,
                    "total_shares": int(market.total_shares or 0),
                    "status": market.status,
                    "is_real_player": bool(player.is_real_player),
                    "liquidity_coin": str(liquidity_balance),
                },
            )
        self.session.flush()
        return market

    def _assert_share_market_eligible(self, player: Player | None) -> None:
        if not is_share_market_eligible(player):
            raise PlayerTokenMarketError("Player is not eligible for a share market.", reason="market_ineligible")

    def _synchronize_market_defaults(
        self,
        market: PlayerShareMarket,
        *,
        total_shares: int | None = None,
        share_price_coin: Decimal | int | float | str | None = None,
        liquidity_coin: Decimal | int | float | str | None = None,
        status: str | None = None,
    ) -> PlayerShareMarket:
        player = market.player or self._get_player(market.player_id)
        metadata = dict(market.metadata_json or {})
        config = resolve_player_share_market_config(
            player,
            total_shares=total_shares or int(market.total_shares or 0) or None,
            share_price_coin=share_price_coin or market.share_price_coin,
            liquidity_coin=liquidity_coin or metadata.get("initial_liquidity_coin") or metadata.get("liquidity_coin"),
            status=status or market.status,
        )

        if int(market.total_shares or 0) <= 0:
            market.total_shares = int(config.total_shares)
        if self._amount(market.share_price_coin) <= Decimal("0.0000"):
            market.share_price_coin = config.share_price_coin
        if not market.status:
            market.status = self._normalize_market_status(config.status)

        liquidity_balance = self._ensure_liquidity_target(
            market,
            target_liquidity_coin=config.liquidity_coin,
            actor=None,
        )
        self._update_market_metadata(
            market,
            liquidity_balance=liquidity_balance,
            initial_liquidity_coin=config.liquidity_coin,
            auto_initialized=bool(metadata.get("auto_initialized", True)),
        )
        self.session.flush()
        return market

    def _ensure_liquidity_target(
        self,
        market: PlayerShareMarket,
        *,
        target_liquidity_coin: Decimal | int | float | str | None,
        actor: User | None,
    ) -> Decimal:
        target_balance = self._amount(target_liquidity_coin)
        liquidity_account = self._ensure_player_share_liquidity_account(market.player_id)
        current_balance = self.wallet_service.get_balance(self.session, liquidity_account)
        if current_balance >= target_balance:
            return self._amount(current_balance)

        top_up_amount = self._amount(target_balance - current_balance)
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.COIN)
        self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=liquidity_account,
                    amount=top_up_amount,
                    source_tag=LedgerSourceTag.MARKET_TOPUP,
                    transaction_type=LedgerTransactionType.ADJUSTMENT,
                ),
                LedgerPosting(
                    account=platform_account,
                    amount=-top_up_amount,
                    source_tag=LedgerSourceTag.MARKET_TOPUP,
                    transaction_type=LedgerTransactionType.ADJUSTMENT,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.MARKET_TOPUP,
            reference=f"player-share-market-topup:{market.player_id}:{generate_uuid()}",
            description=f"Seeded liquidity for player share market {market.player_id}",
            actor=actor,
        )
        return self._amount(self.wallet_service.get_balance(self.session, liquidity_account))

    def _sync_market_liquidity_balance(self, market: PlayerShareMarket) -> Decimal:
        liquidity_balance = self.wallet_service.get_balance(
            self.session,
            self._ensure_player_share_liquidity_account(market.player_id),
        )
        self._update_market_metadata(market, liquidity_balance=self._amount(liquidity_balance))
        return self._amount(liquidity_balance)

    def _update_market_metadata(
        self,
        market: PlayerShareMarket,
        *,
        liquidity_balance: Decimal,
        initial_liquidity_coin: Decimal | int | float | str | None = None,
        auto_initialized: bool | None = None,
    ) -> None:
        player = market.player or self._get_player(market.player_id)
        metadata = dict(market.metadata_json or {})
        metadata.update(
            {
                "player_name": player.canonical_display_name or player.full_name,
                "is_real_player": bool(player.is_real_player),
                "real_player_tier": player.real_player_tier,
                "market_issued": True,
                "liquidity_coin": str(self._amount(liquidity_balance)),
                "liquidity_account_code": self._player_share_liquidity_account_code(market.player_id),
            }
        )
        if initial_liquidity_coin is not None:
            metadata["initial_liquidity_coin"] = str(self._amount(initial_liquidity_coin))
        elif "initial_liquidity_coin" not in metadata:
            metadata["initial_liquidity_coin"] = str(self._amount(liquidity_balance))
        if auto_initialized is not None:
            metadata["auto_initialized"] = bool(auto_initialized)
        market.metadata_json = metadata

    def _serialize_market_view(self, market: PlayerShareMarket) -> dict[str, Any]:
        self._sync_market_liquidity_balance(market)
        return {
            "id": market.id,
            "player_id": market.player_id,
            "total_shares": int(market.total_shares or 0),
            "circulating_shares": int(market.circulating_shares or 0),
            "share_price_coin": self._amount(market.share_price_coin),
            "liquidity_coin": self._amount((market.metadata_json or {}).get("liquidity_coin")),
            "status": market.status,
            "market_issued": True,
            "revenue_distributed_coin": self._amount(market.revenue_distributed_coin),
            "metadata_json": dict(market.metadata_json or {}),
            "created_at": market.created_at,
            "updated_at": market.updated_at,
        }

    def _serialize_market_list_item(self, market: PlayerShareMarket) -> dict[str, Any]:
        player = market.player or self._get_player(market.player_id)
        if player.current_club is not None:
            current_club_name = player.current_club.name
        else:
            current_club_name = player.real_world_club_name
        return {
            "player_id": player.id,
            "player_name": player.canonical_display_name or player.full_name,
            "position": player.normalized_position or player.position,
            "nationality": player.country.name if player.country is not None else None,
            "current_club_name": current_club_name,
            "age": self._player_age(player),
            "share_price_coin": self._amount(market.share_price_coin),
            "liquidity_coin": self._amount((market.metadata_json or {}).get("liquidity_coin")),
            "total_shares": int(market.total_shares or 0),
            "circulating_shares": int(market.circulating_shares or 0),
            "status": market.status,
            "market_issued": True,
            "metadata_json": dict(market.metadata_json or {}),
            "created_at": market.created_at,
            "updated_at": market.updated_at,
        }

    def _price_after_trade(
        self,
        *,
        market: PlayerShareMarket,
        direction: str,
        share_count: int,
    ) -> Decimal:
        reference_price = self._amount(market.share_price_coin)
        total_shares = max(int(market.total_shares or 0), 1)
        trade_pressure = Decimal(share_count) / Decimal(total_shares)
        impact_pct = max(
            MIN_PRICE_IMPACT_PCT,
            min(MAX_PRICE_IMPACT_PCT, self._amount(trade_pressure * PRICE_IMPACT_MULTIPLIER)),
        )
        if direction == "sell":
            proposed_price = self._amount(reference_price * (Decimal("1.0000") - impact_pct))
        else:
            proposed_price = self._amount(reference_price * (Decimal("1.0000") + impact_pct))
        proposed_price = max(proposed_price, MIN_SHARE_PRICE_COIN)
        return self._amount(
            EconomyGovernorService(self.session).clamp_price_change(
                reference_price=reference_price,
                proposed_price=proposed_price,
            )
        )

    def _ensure_player_share_liquidity_account(self, player_id: str):
        return self.wallet_service.ensure_named_system_account(
            self.session,
            code=self._player_share_liquidity_account_code(player_id),
            label=f"Player share liquidity {player_id}",
            unit=LedgerUnit.COIN,
            allow_negative=False,
        )

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

    def _stage_market_trade_event(
        self,
        *,
        market: PlayerShareMarket,
        actor: User,
        event_type: str,
        transaction_id: str | None,
        share_delta: int,
        executed_price: Decimal,
        previous_price: Decimal,
        gross_amount: Decimal,
    ) -> None:
        event = DomainEvent(
            name="market.trade.executed",
            payload={
                "market_id": market.id,
                "player_id": market.player_id,
                "user_id": actor.id,
                "side": event_type,
                "share_delta": share_delta,
                "shares": abs(int(share_delta)),
                "price": str(self._amount(executed_price)),
                "previous_price": str(self._amount(previous_price)),
                "updated_share_price_coin": str(self._amount(market.share_price_coin)),
                "circulating_shares": int(market.circulating_shares or 0),
                "total_shares": int(market.total_shares or 0),
                "transaction_id": transaction_id,
                "gross_amount": str(self._amount(gross_amount)),
            },
            aggregate_id=market.id,
            aggregate_type="player_share_market",
            producer="player_token_market",
            partition_key=market.player_id,
        )
        defer_event_publish_until_commit(
            self.session,
            publisher=self.event_publisher,
            event=event,
        )

    def _require_admin(self, actor: User) -> None:
        if actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise PlayerTokenMarketError("Admin access is required.", reason="admin_required")

    def _get_player(self, player_id: str) -> Player:
        statement = (
            select(Player)
            .options(selectinload(Player.current_club), selectinload(Player.country))
            .where(Player.id == player_id)
        )
        player = self.session.scalar(statement)
        if player is not None:
            if not is_share_market_eligible(player):
                raise PlayerTokenMarketError(
                    "Player is not eligible for the share market.",
                    reason="share_market_ineligible",
                )
            return player
        seed = self.session.get(NationalRegenSeed, player_id)
        if seed is not None and is_preseeded_national_regen(seed):
            raise PlayerTokenMarketError(
                "Preseeded national regens are national-pool-only and cannot be issued to the share market.",
                reason="preseeded_national_regen_share_market_ineligible",
            )
        raise PlayerTokenMarketError("Player was not found.", reason="player_not_found")

    def _normalize_market_status(self, status: str | None) -> str:
        normalized_status = str(status or "active").strip().lower() or "active"
        if normalized_status not in VALID_PLAYER_SHARE_MARKET_STATUSES:
            raise PlayerTokenMarketError(
                "Player share market status must be active, paused, or closed.",
                reason="market_status_invalid",
            )
        return normalized_status

    @staticmethod
    def _player_share_liquidity_account_code(player_id: str) -> str:
        return f"platform:player_share:{player_id}:liquidity"

    @staticmethod
    def _player_age(player: Player) -> int | None:
        if player.date_of_birth is None:
            return None
        today = player.last_synced_at.date() if player.last_synced_at is not None else date.today()
        age = today.year - player.date_of_birth.year
        before_birthday = (today.month, today.day) < (player.date_of_birth.month, player.date_of_birth.day)
        return age - 1 if before_birthday else age

    @staticmethod
    def _amount(value: Decimal | str | int | float | None) -> Decimal:
        return Decimal(str(value or "0.0000")).quantize(AMOUNT_QUANTUM)


__all__ = ["PlayerTokenMarketError", "PlayerTokenMarketService"]
