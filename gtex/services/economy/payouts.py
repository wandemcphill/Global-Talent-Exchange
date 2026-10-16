from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal

from services.economy.token import Token
from services.economy.wallet import Wallet


@dataclass(frozen=True, slots=True)
class PayoutPolicy:
    minimum_cash_out_coins: int = 200
    fee_percent: Decimal = Decimal("0.10")


@dataclass(frozen=True, slots=True)
class PayoutQuote:
    requested_coins: int
    gross_usd: Decimal
    fee_usd: Decimal
    net_usd: Decimal
    eligible: bool

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["gross_usd"] = str(self.gross_usd)
        payload["fee_usd"] = str(self.fee_usd)
        payload["net_usd"] = str(self.net_usd)
        return payload


def quote_cash_out(
    *,
    token: Token,
    coins: int,
    policy: PayoutPolicy | None = None,
) -> PayoutQuote:
    resolved_policy = policy or PayoutPolicy()
    requested = max(coins, 0)
    gross = token.coins_to_usd(requested)
    fee = (gross * resolved_policy.fee_percent).quantize(Decimal("0.01"))
    net = (gross - fee).quantize(Decimal("0.01"))
    return PayoutQuote(
        requested_coins=requested,
        gross_usd=gross,
        fee_usd=fee,
        net_usd=net,
        eligible=requested >= resolved_policy.minimum_cash_out_coins,
    )


def cash_out_wallet(
    wallet: Wallet,
    *,
    token: Token | None = None,
    coins: int,
    policy: PayoutPolicy | None = None,
) -> PayoutQuote:
    resolved_token = token or Token()
    quote = quote_cash_out(token=resolved_token, coins=coins, policy=policy)
    if not quote.eligible:
        raise ValueError("Requested amount does not meet the minimum cash-out threshold.")
    wallet.debit_coins(coins, event="cash_out", note="Coin cash-out")
    wallet.credit_usd(quote.net_usd, event="cash_out", note="Cash-out proceeds")
    return quote
