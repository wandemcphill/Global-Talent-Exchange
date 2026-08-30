from __future__ import annotations

from contextvars import ContextVar
from hashlib import sha256
from typing import Callable, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.player_token_market import PlayerShareMarket
from app.models.user import User
from app.models.wallet import LedgerEntry, LedgerTransaction
from app.players import legacy_token_service as _legacy
from app.players.trade_context import consume_player_share_idempotency_key

PlayerTokenMarketError = _legacy.PlayerTokenMarketError

_trade_reference: ContextVar[str | None] = ContextVar("player_share_trade_reference", default=None)
_trade_market_override: ContextVar[PlayerShareMarket | None] = ContextVar(
    "player_share_trade_market_override", default=None
)
_original_generate_uuid = _legacy.generate_uuid


def _ledger_reference_token() -> str:
    reference = _trade_reference.get()
    if reference:
        return reference
    return _original_generate_uuid()


_legacy.generate_uuid = _ledger_reference_token


class PlayerTokenMarketService(_legacy.PlayerTokenMarketService):
    """Production-facing player-share service with a strict trade boundary."""

    @staticmethod
    def _trade_reference(*, market_id: str, actor_id: str, side: str, circulating_shares: int, share_count: int) -> str:
        return (
            f"market:{market_id}:actor:{actor_id}:side:{side}:"
            f"before:{int(circulating_shares)}:shares:{int(share_count)}"
        )

    @staticmethod
    def _idempotency_reference(*, actor_id: str, key: str) -> str:
        # Scoped to (actor, key) only - NOT player/side/share_count - so that reusing
        # the same key for a different trade lands on the same lookup bucket and is
        # caught as a conflict by _replay_idempotent_trade's metadata check below,
        # rather than silently executing as an unrelated trade.
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

        entries = list(self.session.scalars(select(LedgerEntry).where(LedgerEntry.transaction_id == transaction.id)).all())
        if not entries:
            raise PlayerTokenMarketError("Existing player-share trade has no ledger entries.", reason="trade_integrity_error")

        fee_amount = next((abs(entry.amount) for entry in entries if "trade_fee_revenue" in str(entry.account.code)), 0)
        fee_amount = self._amount(fee_amount)
        if side == "buy":
            gross_entry = next(
                (entry for entry in entries if entry.amount > 0 and "trade_fee_revenue" not in str(entry.account.code)),
                None,
            )
            debit_entry = next((entry for entry in entries if entry.amount < 0), None)
            if gross_entry is None or debit_entry is None:
                raise PlayerTokenMarketError("Existing player-share purchase has incomplete ledger postings.", reason="trade_integrity_error")
            gross_amount = self._amount(gross_entry.amount)
            total_debit = self._amount(abs(debit_entry.amount))
        else:
            gross_entry = next((entry for entry in entries if entry.amount < 0), None)
            credit_entry = next(
                (entry for entry in entries if entry.amount > 0 and "trade_fee_revenue" not in str(entry.account.code)),
                None,
            )
            if gross_entry is None or credit_entry is None:
                raise PlayerTokenMarketError("Existing player-share sale has incomplete ledger postings.", reason="trade_integrity_error")
            gross_amount = self._amount(abs(gross_entry.amount))
            total_debit = self._amount(credit_entry.amount + fee_amount)

        market = self.get_market(player_id=player_id)
        holding = self.get_holding(user_id=actor.id, player_id=player_id)
        if holding is None:
            raise PlayerTokenMarketError("Existing player-share trade has no holding projection.", reason="trade_integrity_error")
        return {
            "market": self._serialize_market_view(market),
            "holding": holding,
            "transaction_id": transaction.id,
            "gross_amount_coin": gross_amount,
            "fee_amount_coin": fee_amount,
            "net_amount_coin": total_debit,
        }

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
            reference = self._idempotency_reference(
                actor_id=actor.id,
                key=resolved_idempotency_key.strip(),
            )
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

    def buy_shares(
        self,
        *,
        actor: User,
        player_id: str,
        share_count: int,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return self._run_trade_with_boundary(
            actor=actor,
            player_id=player_id,
            share_count=share_count,
            side="buy",
            idempotency_key=idempotency_key,
            operation=lambda: super(PlayerTokenMarketService, self).buy_shares(
                actor=actor, player_id=player_id, share_count=share_count
            ),
        )

    def sell_shares(
        self,
        *,
        actor: User,
        player_id: str,
        share_count: int,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return self._run_trade_with_boundary(
            actor=actor,
            player_id=player_id,
            share_count=share_count,
            side="sell",
            idempotency_key=idempotency_key,
            operation=lambda: super(PlayerTokenMarketService, self).sell_shares(
                actor=actor, player_id=player_id, share_count=share_count
            ),
        )


__all__ = ["PlayerTokenMarketError", "PlayerTokenMarketService"]
