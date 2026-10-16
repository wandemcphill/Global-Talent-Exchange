from __future__ import annotations

from decimal import Decimal

from services.economy import RewardEngine, Token, Wallet, cash_out_wallet, quote_cash_out


def test_reward_engine_applies_clip_rewards_to_wallet() -> None:
    wallet = Wallet(user_id="user_1")
    quote = RewardEngine().apply(wallet, "viral_clip", metadata={"viral_score": 94})

    assert quote.coins == 62
    assert wallet.coins == 62
    assert wallet.entries[-1].event == "viral_clip"


def test_cash_out_quote_and_wallet_update() -> None:
    wallet = Wallet(user_id="user_2", coins=500)
    token = Token()
    preview = quote_cash_out(token=token, coins=100)
    payout = cash_out_wallet(wallet, token=token, coins=200)

    assert preview.eligible is False
    assert payout.gross_usd == Decimal("10.00")
    assert payout.fee_usd == Decimal("1.00")
    assert payout.net_usd == Decimal("9.00")
    assert wallet.coins == 300
    assert wallet.usd_balance == Decimal("9.00")
