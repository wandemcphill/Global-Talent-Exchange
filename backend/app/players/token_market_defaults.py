from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ingestion.models import Player

AMOUNT_QUANTUM = Decimal("0.0001")
DEFAULT_TOTAL_SHARES = 1000
DEFAULT_LIQUIDITY_MINIMUM = Decimal("25.0000")
DEFAULT_REFERENCE_MARKET_VALUE_EUR = 10_000_000.0
MIN_SHARE_PRICE_COIN = Decimal("0.0500")
MAX_DEFAULT_LIQUIDITY_SHARES = 250
MIN_DEFAULT_LIQUIDITY_SHARES = 50

POSITION_REFERENCE_VALUES_EUR: dict[str, float] = {
    "goalkeeper": 7_500_000.0,
    "defender": 11_000_000.0,
    "midfielder": 16_500_000.0,
    "forward": 20_000_000.0,
    "striker": 20_000_000.0,
    "winger": 18_000_000.0,
    "attacker": 20_000_000.0,
}


@dataclass(frozen=True, slots=True)
class ResolvedPlayerShareMarketConfig:
    total_shares: int
    share_price_coin: Decimal
    liquidity_coin: Decimal
    status: str


def resolve_player_share_market_config(
    player: Player,
    *,
    total_shares: int | None = None,
    share_price_coin: Decimal | int | float | str | None = None,
    liquidity_coin: Decimal | int | float | str | None = None,
    status: str | None = "active",
) -> ResolvedPlayerShareMarketConfig:
    normalized_total_shares = int(total_shares or DEFAULT_TOTAL_SHARES)
    normalized_share_price = _resolve_share_price_coin(
        player, explicit_value=share_price_coin, total_shares=normalized_total_shares
    )
    normalized_liquidity = _resolve_liquidity_coin(
        normalized_total_shares,
        normalized_share_price,
        explicit_value=liquidity_coin,
    )
    normalized_status = str(status or "active").strip().lower() or "active"
    return ResolvedPlayerShareMarketConfig(
        total_shares=normalized_total_shares,
        share_price_coin=normalized_share_price,
        liquidity_coin=normalized_liquidity,
        status=normalized_status,
    )


def _resolve_share_price_coin(
    player: Player,
    *,
    explicit_value: Decimal | int | float | str | None,
    total_shares: int = DEFAULT_TOTAL_SHARES,
) -> Decimal:
    if explicit_value is not None:
        return _amount(explicit_value)

    # Prefer the banded player value (same model as the display value, so appreciation
    # and admin re-rates move the tradeable price), converted credits -> Coin so the
    # full share float equals the player's banded value. Fall back to the EUR reference
    # for players without stored ratings.
    from datetime import UTC, datetime

    from app.value_engine.banded_pricing import (
        SOFIFA_SNAPSHOT_DATE,
        banded_credits_from_dna,
        share_price_coin_from_credits,
    )

    as_of = datetime.now(UTC).date()
    created_at = getattr(player, "created_at", None)
    anchor = (
        created_at.date()
        if getattr(player, "source_provider", None) == "gtex_regen" and created_at is not None
        else SOFIFA_SNAPSHOT_DATE
    )
    value_credits = banded_credits_from_dna(
        player.dna_profile, dob=player.date_of_birth, ingest_date=anchor, as_of=as_of
    )
    if value_credits is None:
        value_credits = _credits_from_real_world_value(_reference_market_value_eur(player))
    # share_price_coin_from_credits already floors at a tiny min so the full float
    # tracks the player's banded value; do not re-apply the higher legacy floor
    # (it would over-price cheap players).
    coin_price = share_price_coin_from_credits(value_credits, total_shares)
    return _amount(coin_price)


def _resolve_liquidity_coin(
    total_shares: int,
    share_price_coin: Decimal,
    *,
    explicit_value: Decimal | int | float | str | None,
) -> Decimal:
    if explicit_value is not None:
        return _amount(explicit_value)

    liquidity_share_count = min(
        max(int(total_shares * 0.10), MIN_DEFAULT_LIQUIDITY_SHARES),
        MAX_DEFAULT_LIQUIDITY_SHARES,
    )
    derived_liquidity = share_price_coin * Decimal(liquidity_share_count)
    return max(_amount(derived_liquidity), DEFAULT_LIQUIDITY_MINIMUM)


def _reference_market_value_eur(player: Player) -> float:
    for candidate in (player.current_market_reference_value, player.market_value_eur):
        if candidate is not None and float(candidate) > 0:
            return float(candidate)

    position_key = _normalized_position_key(player)
    if position_key is not None and position_key in POSITION_REFERENCE_VALUES_EUR:
        return POSITION_REFERENCE_VALUES_EUR[position_key]

    return DEFAULT_REFERENCE_MARKET_VALUE_EUR


def _normalized_position_key(player: Player) -> str | None:
    for raw_value in (player.normalized_position, player.position):
        if raw_value is None:
            continue
        candidate = str(raw_value).strip().lower()
        if not candidate:
            continue
        if candidate in POSITION_REFERENCE_VALUES_EUR:
            return candidate
        if "keeper" in candidate:
            return "goalkeeper"
        if "def" in candidate:
            return "defender"
        if "mid" in candidate:
            return "midfielder"
        if any(token in candidate for token in ("striker", "forward", "wing", "attack")):
            return "forward"
    return None


def _amount(value: Decimal | int | float | str | None) -> Decimal:
    return Decimal(str(value or "0.0000")).quantize(AMOUNT_QUANTUM)


def _credits_from_real_world_value(real_world_value_eur: float) -> float:
    from app.value_engine.scoring import credits_from_real_world_value

    return credits_from_real_world_value(real_world_value_eur)


__all__ = [
    "DEFAULT_TOTAL_SHARES",
    "ResolvedPlayerShareMarketConfig",
    "resolve_player_share_market_config",
]
