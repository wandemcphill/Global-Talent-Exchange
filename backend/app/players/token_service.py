from __future__ import annotations

import logging
from contextvars import ContextVar
from decimal import Decimal
from hashlib import sha256
from typing import Callable, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.player_token_market import PlayerShareEvent, PlayerShareHolding, PlayerShareMarket
from app.models.user import User
from app.models.wallet import (
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransaction,
    LedgerTransactionType,
    LedgerUnit,
)
from app.wallets.service import LedgerPosting
from app.players import legacy_token_service as _legacy
from app.players.trade_context import consume_player_share_idempotency_key

PlayerTokenMarketError = _legacy.PlayerTokenMarketError
logger = logging.getLogger(__name__)

_trade_reference: ContextVar[str | None] = ContextVar("player_share_trade_reference", default=None)
_trade_market_override: ContextVar[PlayerShareMarket | None] = ContextVar(
    "player_share_trade_market_override", default=None
)
_original_generate_uuid = _legacy.generate_uuid


def _ledger_reference_token() -> str:
    reference = _trade_reference.get()
    if reference:
        if len(reference) > 60:
            return sha256(reference.encode("utf-8")).hexdigest()[:32]
        return reference
    return _original_generate_uuid()


_legacy.generate_uuid = _ledger_reference_token


class PlayerTokenMarketService(_legacy.PlayerTokenMarketService):
    """Production-facing player-share service with strict trade and supply boundaries."""

    @staticmethod
    def _trade_reference(*, market_id: str, actor_id: str, side: str, circulating_shares: int, share_count: int) -> str:
        return (
            f"market:{market_id}:actor:{actor_id}:side:{side}:"
            f"before:{int(circulating_shares)}:shares:{int(share_count)}"
        )

    @staticmethod
    def _idempotency_reference(*, actor_id: str, key: str) -> str:
        digest = sha256(f"{actor_id}|{key}".encode("utf-8")).hexdigest()
        return f"trade-idempotency:{digest}"

    def _require_trade_market(self, player_id: str) -> PlayerShareMarket:
        market = self.session.scalar(
            select(PlayerShareMarket)
            .options(selectinload(PlayerShareMarket.player))
            .where(PlayerShareMarket.player_id == player_id)
            .with_for_update()
        )
        if market is None:
            raise PlayerTokenMarketError("Player share market has not been issued.", reason="market_not_found")
        return market

    def _bind_trade_idempotency(
        self,
        *,
        transaction_id: str,
        reference: str,
        actor: User,
        player_id: str,
        side: str,
        share_count: int,
    ) -> None:
        transaction = self.session.get(LedgerTransaction, transaction_id)
        if transaction is None:
            raise PlayerTokenMarketError(
                "Player-share trade ledger transaction was not found.", reason="trade_integrity_error"
            )
        transaction.idempotency_key = reference
        transaction.metadata_json = {
            **(transaction.metadata_json or {}),
            "player_share_trade": {
                "actor_user_id": actor.id,
                "player_id": player_id,
                "side": side,
                "share_count": int(share_count),
                "idempotency_reference": reference,
            },
        }
        self.session.flush()

    def _replay_idempotent_trade(
        self,
        *,
        reference: str,
        actor: User,
        player_id: str,
        side: str,
        share_count: int,
    ) -> dict[str, Any] | None:
        transaction = self.session.scalar(
            select(LedgerTransaction)
            .where(LedgerTransaction.idempotency_key == reference)
            .order_by(LedgerTransaction.created_at.desc())
        )
        if transaction is None:
            return None

        trade_meta = (transaction.metadata_json or {}).get("player_share_trade")
        if isinstance(trade_meta, dict) and (
            str(trade_meta.get("actor_user_id") or "") != actor.id
            or str(trade_meta.get("player_id") or "") != player_id
            or str(trade_meta.get("side") or "") != side
            or int(trade_meta.get("share_count") or 0) != int(share_count)
        ):
            raise PlayerTokenMarketError(
                "Idempotency key was already used for a different player-share trade.",
                reason="trade_idempotency_conflict",
            )

        entries = list(
            self.session.scalars(select(LedgerEntry).where(LedgerEntry.transaction_id == transaction.id)).all()
        )
        if not entries:
            raise PlayerTokenMarketError(
                "Existing player-share trade has no ledger entries.", reason="trade_integrity_error"
            )

        fee_amount = next((abs(entry.amount) for entry in entries if "trade_fee_revenue" in str(entry.account.code)), 0)
        fee_amount = self._amount(fee_amount)
        if side == "buy":
            gross_entry = next(
                (entry for entry in entries if entry.amount > 0 and "trade_fee_revenue" not in str(entry.account.code)),
                None,
            )
            debit_entry = next((entry for entry in entries if entry.amount < 0), None)
            if gross_entry is None or debit_entry is None:
                raise PlayerTokenMarketError(
                    "Existing player-share purchase has incomplete ledger postings.", reason="trade_integrity_error"
                )
            gross_amount = self._amount(gross_entry.amount)
            total_debit = self._amount(abs(debit_entry.amount))
        else:
            gross_entry = next((entry for entry in entries if entry.amount < 0), None)
            credit_entry = next(
                (entry for entry in entries if entry.amount > 0 and "trade_fee_revenue" not in str(entry.account.code)),
                None,
            )
            if gross_entry is None or credit_entry is None:
                raise PlayerTokenMarketError(
                    "Existing player-share sale has incomplete ledger postings.", reason="trade_integrity_error"
                )
            gross_amount = self._amount(abs(gross_entry.amount))
            total_debit = self._amount(credit_entry.amount + fee_amount)

        market = self.get_market(player_id=player_id)
        holding = self.get_holding(user_id=actor.id, player_id=player_id)
        if holding is None:
            raise PlayerTokenMarketError(
                "Existing player-share trade has no holding projection.", reason="trade_integrity_error"
            )
        return {
            "market": self._serialize_market_view(market),
            "holding": holding,
            "transaction_id": transaction.id,
            "gross_amount_coin": gross_amount,
            "fee_amount_coin": fee_amount,
            "net_amount_coin": total_debit,
        }

    def issue_market(
        self,
        *,
        actor: User,
        player_id: str,
        total_shares: int = 1000,
        share_price_coin,
        liquidity_coin=None,
        status: str = "active",
    ) -> PlayerShareMarket:
        player = self._get_player(player_id)
        source_provider = str(getattr(player, "source_provider", "") or "").strip().lower()
        tier = str(getattr(player, "real_player_tier", "") or "").strip().lower()
        is_one_of_one = (
            getattr(player, "is_real_player", True) is False
            or bool(getattr(player, "legendary_profile_id", None))
            or source_provider in {"gtex_legend", "gtex_legend_prime"}
            or tier in {"legend", "legendary", "icon", "immortal", "world_class", "hero"}
        )
        if is_one_of_one:
            total_shares = 1
            liquidity_coin = 0
        elif total_shares > 600:
            total_shares = 600
        if total_shares < 1:
            raise PlayerTokenMarketError(
                "Player availability must be at least one unit.", reason="player_supply_invalid"
            )
        return super().issue_market(
            actor=actor,
            player_id=player_id,
            total_shares=total_shares,
            share_price_coin=share_price_coin,
            liquidity_coin=liquidity_coin,
            status=status,
        )

    def ensure_market(self, *, player_id: str, **kwargs: Any):
        override = _trade_market_override.get()
        if override is not None and override.player_id == player_id:
            return override
        return super().ensure_market(player_id=player_id, **kwargs)

    def _run_trade_with_boundary(
        self,
        *,
        actor: User,
        player_id: str,
        share_count: int,
        side: str,
        idempotency_key: str | None,
        operation: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        resolved_idempotency_key = idempotency_key or consume_player_share_idempotency_key()
        market = self._require_trade_market(player_id)
        if resolved_idempotency_key:
            reference = self._idempotency_reference(actor_id=actor.id, key=resolved_idempotency_key.strip())
        else:
            reference = self._trade_reference(
                market_id=market.id,
                actor_id=actor.id,
                side=side,
                circulating_shares=int(market.circulating_shares or 0),
                share_count=share_count,
            )

        reference_token = _trade_reference.set(reference)
        market_token = _trade_market_override.set(market)
        try:
            if resolved_idempotency_key:
                replay = self._replay_idempotent_trade(
                    reference=reference,
                    actor=actor,
                    player_id=player_id,
                    side=side,
                    share_count=share_count,
                )
                if replay is not None:
                    return replay
            result = operation()
            if resolved_idempotency_key:
                self._bind_trade_idempotency(
                    transaction_id=str(result["transaction_id"]),
                    reference=reference,
                    actor=actor,
                    player_id=player_id,
                    side=side,
                    share_count=share_count,
                )
            return result
        finally:
            _trade_market_override.reset(market_token)
            _trade_reference.reset(reference_token)

    def _primary_available_shares(self, market: PlayerShareMarket) -> int:
        if market.released_shares is None:
            return int(market.total_shares or 0) - int(market.circulating_shares or 0)
        return int(market.released_shares) - int(market.circulating_shares or 0)

    def buy_shares(
        self,
        *,
        actor: User,
        player_id: str,
        share_count: int,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if share_count != 1:
            raise PlayerTokenMarketError(
                "A player is acquired as one complete unit. Quantity must be exactly one.",
                reason="acquisition_quantity_must_be_one",
            )

        def acquire_one_unit() -> dict[str, Any]:
            # The boundary has already locked the player market and replayed a
            # previous request with the same idempotency key before this
            # operation runs. That ordering preserves safe retries after a
            # successful purchase whose response was lost.
            market = _trade_market_override.get()
            if market is None:
                market = self._require_trade_market(player_id)
            self._assert_share_market_eligible(market.player)
            if market.status != "active":
                raise PlayerTokenMarketError("Player acquisition is not available.", reason="market_inactive")

            existing_holding = self.get_holding(user_id=actor.id, player_id=player_id)
            if existing_holding is not None and int(existing_holding.share_count or 0) > 0:
                raise PlayerTokenMarketError(
                    "This account already owns this player. Only one unit is permitted per account.",
                    reason="player_already_owned",
                )
            if self._primary_available_shares(market) < 1:
                raise PlayerTokenMarketError(
                    "This player has no unallocated units remaining.", reason="player_supply_exhausted"
                )
            purchased = super(PlayerTokenMarketService, self).buy_shares(
                actor=actor, player_id=player_id, share_count=1
            )
            try:
                from app.owner_console.service import register_acquired_shares

                with self.session.begin_nested():
                    register_acquired_shares(self.session, actor.id)
            except Exception:
                logger.exception("squad registration after acquisition failed")
            return purchased

        return self._run_trade_with_boundary(
            actor=actor,
            player_id=player_id,
            share_count=share_count,
            side="buy",
            idempotency_key=idempotency_key,
            operation=acquire_one_unit,
        )

    def sell_shares(
        self,
        *,
        actor: User,
        player_id: str,
        share_count: int,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        def reject_resale() -> dict[str, Any]:
            raise PlayerTokenMarketError(
                "Player acquisitions are not listed for resale or secondary trading.",
                reason="player_acquisition_non_transferable",
            )

        return self._run_trade_with_boundary(
            actor=actor,
            player_id=player_id,
            share_count=share_count,
            side="sell",
            idempotency_key=idempotency_key,
            operation=reject_resale,
        )

    def distribute_dividend(
        self,
        *,
        actor: User,
        player_id: str,
        gross_amount_coin,
        note: str | None = None,
    ) -> dict[str, Any]:
        del actor, player_id, gross_amount_coin, note
        raise PlayerTokenMarketError(
            "Player acquisitions do not create dividend, yield or investment entitlements.",
            reason="player_acquisition_non_investment",
        )

    def release_shares(
        self,
        *,
        actor: User,
        player_id: str,
        release_count: int,
    ) -> PlayerShareMarket:
        self._require_admin(actor)
        if release_count <= 0:
            raise PlayerTokenMarketError("Release count must be greater than zero.", reason="release_invalid")

        market = self.session.scalar(
            select(PlayerShareMarket)
            .options(selectinload(PlayerShareMarket.player))
            .where(PlayerShareMarket.player_id == player_id)
            .with_for_update()
        )
        if market is None:
            raise PlayerTokenMarketError("Player share market was not found.", reason="market_not_found")
        if market.released_shares is None:
            raise PlayerTokenMarketError(
                "Released supply is unknown for this legacy market and must be reconciled before more supply is released.",
                reason="released_supply_unknown",
            )

        released_before = int(market.released_shares)
        released_after = released_before + int(release_count)
        if released_after > int(market.total_shares or 0):
            raise PlayerTokenMarketError(
                "Released supply cannot exceed lifetime total supply.", reason="released_supply_exceeds_total"
            )

        market.released_shares = released_after
        self._record_event(
            player_id=player_id,
            actor_user_id=actor.id,
            event_type="release",
            share_delta=0,
            price_per_share_coin=self._amount(market.share_price_coin),
            gross_amount_coin=self._amount(0),
            metadata_json={
                "market_id": market.id,
                "released_before": released_before,
                "released_after": released_after,
                "release_count": int(release_count),
                "total_shares": int(market.total_shares or 0),
                "circulating_shares": int(market.circulating_shares or 0),
            },
        )
        self.session.flush()
        return market

    def release_account_acquisitions(self, *, user_id: str) -> dict[str, Any]:
        """Return one account's acquired units to the market and refund what it paid.

        Circulating supply falls by the released count. Released supply and
        lifetime total supply stay where they are, so a 1-of-1 legend is not minted again.
        """
        user = self.session.get(User, user_id)
        if user is None:
            raise PlayerTokenMarketError("User was not found.", reason="user_not_found")

        holdings = list(
            self.session.scalars(
                select(PlayerShareHolding)
                .where(
                    PlayerShareHolding.user_id == user_id,
                    PlayerShareHolding.share_count > 0,
                )
                .with_for_update()
            ).all()
        )
        releases: list[dict[str, Any]] = []
        refund_total = Decimal("0.0000")
        shares_released = 0
        for holding in holdings:
            release = self._release_holding(user=user, holding=holding)
            releases.append(release)
            refund_total = self._amount(refund_total + Decimal(release["refund_coin"]))
            shares_released += int(release["shares"])
        self.session.flush()
        return {
            "user_id": user_id,
            "holdings_released": len(releases),
            "shares_released": shares_released,
            "refund_total": str(refund_total),
            "releases": releases,
        }

    def release_player_acquisition(self, *, user_id: str, player_id: str) -> dict[str, Any]:
        """Return one acquired unit to the market and refund what this account paid."""
        user = self.session.get(User, user_id)
        if user is None:
            raise PlayerTokenMarketError("User was not found.", reason="user_not_found")
        holding = self.session.scalar(
            select(PlayerShareHolding)
            .where(
                PlayerShareHolding.user_id == user_id,
                PlayerShareHolding.player_id == player_id,
                PlayerShareHolding.share_count > 0,
            )
            .with_for_update()
        )
        if holding is None:
            return {"player_id": player_id, "shares": 0, "refund_coin": "0.0000", "released": False}
        release = self._release_holding(user=user, holding=holding)
        self.session.flush()
        return {**release, "released": True}

    def _release_holding(self, *, user: User, holding: PlayerShareHolding) -> dict[str, Any]:
        share_count = int(holding.share_count or 0)
        market = self.session.scalar(
            select(PlayerShareMarket).where(PlayerShareMarket.player_id == holding.player_id).with_for_update()
        )
        if market is None:
            raise PlayerTokenMarketError(
                "Player share market was not found.",
                reason="market_not_found",
            )
        circulating_before = int(market.circulating_shares or 0)
        if circulating_before < share_count:
            raise PlayerTokenMarketError(
                "Circulating supply is lower than this holding.",
                reason="holding_circulation_mismatch",
            )
        released_before = market.released_shares
        total_before = market.total_shares
        available_before = self._primary_available_shares(market)
        gross, fee = self._acquisition_settlement(holding)
        refund = self._amount(gross + fee)
        transaction_id = self._refund_acquisition(
            user=user,
            player_id=holding.player_id,
            gross=gross,
            fee=fee,
        )
        holding.share_count = 0
        holding.average_cost_coin = Decimal("0.0000")
        holding.metadata_json = {
            **(holding.metadata_json or {}),
            "last_transaction_id": transaction_id,
            "last_trade_side": "reset_release",
        }
        market.circulating_shares = circulating_before - share_count
        if market.released_shares != released_before or market.total_shares != total_before:
            raise PlayerTokenMarketError(
                "Releasing an acquisition must not mint supply.",
                reason="release_minted_supply",
            )
        available_after = self._primary_available_shares(market)
        if available_after != available_before + share_count:
            raise PlayerTokenMarketError(
                "Released units did not return to the market.",
                reason="release_availability_mismatch",
            )
        self._record_event(
            player_id=holding.player_id,
            user_id=user.id,
            actor_user_id=user.id,
            event_type="reset_release",
            share_delta=-share_count,
            price_per_share_coin=self._amount(market.share_price_coin),
            gross_amount_coin=gross,
            metadata_json={
                "market_id": market.id,
                "transaction_id": transaction_id,
                "fee_amount_coin": str(fee),
                "refund_coin": str(refund),
                "circulating_before": circulating_before,
                "circulating_shares": int(market.circulating_shares or 0),
                "released_shares": released_before,
                "total_shares": int(total_before or 0),
            },
        )
        return {
            "player_id": holding.player_id,
            "shares": share_count,
            "circulating_before": circulating_before,
            "circulating_after": int(market.circulating_shares or 0),
            "available_before": available_before,
            "available_after": available_after,
            "refund_coin": str(refund),
            "released_shares": released_before,
            "total_shares": total_before,
        }

    def _acquisition_settlement(self, holding: PlayerShareHolding) -> tuple[Decimal, Decimal]:
        share_count = int(holding.share_count or 0)
        events = list(
            self.session.scalars(
                select(PlayerShareEvent).where(
                    PlayerShareEvent.user_id == holding.user_id,
                    PlayerShareEvent.player_id == holding.player_id,
                    PlayerShareEvent.event_type == "buy",
                    PlayerShareEvent.share_delta > 0,
                )
            ).all()
        )
        gross = Decimal("0.0000")
        fee = Decimal("0.0000")
        shares_seen = 0
        for event in events:
            gross = self._amount(gross + self._amount(event.gross_amount_coin))
            fee = self._amount(fee + self._amount((event.metadata_json or {}).get("fee_amount_coin")))
            shares_seen += int(event.share_delta or 0)
        if shares_seen == share_count and gross > 0:
            return gross, fee
        paid = self._amount(self._amount(holding.average_cost_coin) * Decimal(share_count))
        return paid, Decimal("0.0000")

    def _refund_acquisition(
        self,
        *,
        user: User,
        player_id: str,
        gross: Decimal,
        fee: Decimal,
    ) -> str | None:
        refund = self._amount(gross + fee)
        if refund <= 0:
            return None
        user_account = self.wallet_service.get_user_account(self.session, user, LedgerUnit.COIN)
        liquidity = self._ensure_player_share_liquidity_account(player_id)
        liquidity_balance = self.wallet_service.get_balance(self.session, liquidity)
        liquidity_debit = self._amount(min(liquidity_balance, gross))
        fee_debit = Decimal("0.0000")
        fee_account = None
        if fee > 0:
            fee_account = self.wallet_service.ensure_trade_fee_account(self.session, LedgerUnit.COIN)
            fee_balance = self.wallet_service.get_balance(self.session, fee_account)
            fee_debit = self._amount(min(fee_balance, fee))
        shortfall = self._amount(refund - liquidity_debit - fee_debit)
        postings = [
            LedgerPosting(
                account=user_account,
                amount=refund,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                transaction_type=LedgerTransactionType.ADJUSTMENT,
            )
        ]
        if liquidity_debit > 0:
            postings.append(
                LedgerPosting(
                    account=liquidity,
                    amount=-liquidity_debit,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    transaction_type=LedgerTransactionType.ADJUSTMENT,
                )
            )
        if fee_account is not None and fee_debit > 0:
            postings.append(
                LedgerPosting(
                    account=fee_account,
                    amount=-fee_debit,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    transaction_type=LedgerTransactionType.ADJUSTMENT,
                )
            )
        if shortfall > 0:
            platform = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.COIN)
            postings.append(
                LedgerPosting(
                    account=platform,
                    amount=-shortfall,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    transaction_type=LedgerTransactionType.ADJUSTMENT,
                )
            )
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference=f"player-share-reset-release:{player_id}:{user.id}",
            description=f"Released acquired player {player_id} back to the market",
            actor=user,
        )
        return entries[0].transaction_id

    def _serialize_market_view(self, market: PlayerShareMarket) -> dict[str, Any]:
        payload = super()._serialize_market_view(market)
        payload["released_shares"] = market.released_shares
        return payload

    def _serialize_market_list_item(self, market: PlayerShareMarket) -> dict[str, Any]:
        payload = super()._serialize_market_list_item(market)
        payload["released_shares"] = market.released_shares
        return payload


__all__ = ["PlayerTokenMarketError", "PlayerTokenMarketService"]
