from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class WalletEntry:
    event: str
    coins_delta: int
    usd_delta: Decimal
    note: str = ""

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["usd_delta"] = str(self.usd_delta)
        return payload


@dataclass(slots=True)
class Wallet:
    user_id: str
    coins: int = 0
    usd_balance: Decimal = Decimal("0.00")
    entries: list[WalletEntry] = field(default_factory=list)

    def credit_coins(self, amount: int, *, event: str, note: str = "") -> int:
        if amount < 0:
            raise ValueError("Coin credit amount must be non-negative.")
        self.coins += amount
        self.entries.append(WalletEntry(event=event, coins_delta=amount, usd_delta=Decimal("0.00"), note=note))
        return self.coins

    def debit_coins(self, amount: int, *, event: str, note: str = "") -> int:
        if amount < 0:
            raise ValueError("Coin debit amount must be non-negative.")
        if amount > self.coins:
            raise ValueError("Insufficient coin balance.")
        self.coins -= amount
        self.entries.append(WalletEntry(event=event, coins_delta=-amount, usd_delta=Decimal("0.00"), note=note))
        return self.coins

    def credit_usd(self, amount: Decimal | str | float, *, event: str, note: str = "") -> Decimal:
        value = Decimal(str(amount)).quantize(Decimal("0.01"))
        if value < 0:
            raise ValueError("USD credit amount must be non-negative.")
        self.usd_balance = (self.usd_balance + value).quantize(Decimal("0.01"))
        self.entries.append(WalletEntry(event=event, coins_delta=0, usd_delta=value, note=note))
        return self.usd_balance

    def snapshot(self) -> dict[str, object]:
        return {
            "user_id": self.user_id,
            "coins": self.coins,
            "usd_balance": f"{self.usd_balance:.2f}",
            "entries": [entry.as_dict() for entry in self.entries],
        }
