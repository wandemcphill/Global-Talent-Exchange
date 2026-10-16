from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Token:
    name: str = "GTEX Coin"
    symbol: str = "GTEX"
    total_supply: int = 1_000_000_000
    usd_per_coin: Decimal = Decimal("0.05")

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["usd_per_coin"] = str(self.usd_per_coin)
        return payload

    def coins_to_usd(self, coins: int) -> Decimal:
        return (Decimal(max(coins, 0)) * self.usd_per_coin).quantize(Decimal("0.01"))

    def usd_to_coins(self, usd_value: Decimal | str | float) -> int:
        amount = Decimal(str(usd_value))
        if amount <= 0:
            return 0
        return int((amount / self.usd_per_coin).to_integral_value())
