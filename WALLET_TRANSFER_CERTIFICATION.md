# WALLET + TRANSFER MARKET CERTIFICATION (N33)

Date: 2026-06-12
Branch: `feature/original-visual-runtime` @ `5ca8db2d`
Verdict: **PASS — money lanes certified green**

## Evidence

### Shard 1 — money core: `pytest tests/wallets tests/treasury tests/settlement tests/trader`
**100 passed, 0 failed** in 813.11s (log: `.runtime/n33_money.log`)

| Lane | Test files | What it proves |
|---|---|---|
| Funding | `wallets/test_payment_gateway_service.py`, `test_wallet_rail_service.py` | KoraPay/manual rails: payment-event creation, verification, top-up quoting |
| Ledger safety | `wallets/test_wallet_service.py` (23 tests) | Balanced-posting enforcement, unbalanced rollback, idempotency-key reuse across atomic calls, negative-balance rejection |
| Reservation lifecycle | `wallets/test_wallet_service.py`, `trader/test_trader_service.py` | reserve → release → settle for cash and position units; escrow accounting |
| Withdrawal | `treasury/test_withdrawal_reviews.py`, payout tests in `test_wallet_service.py` | Payout hold (total incl. fee), withdrawal review workflow, risk gating |
| Settlement | `settlement/test_settlement_service.py` | Trade execution reserve/settle via RiskControlService |
| Trader matching | `trader/test_trader_service.py` (17 tests, incl. new cross-counterparty test) | Order crossing, partial fills, price-improvement refund, 50bps fee capture, escrow→liquidity→seller flow, book release on cancel |
| HTTP contracts | `wallets/test_wallet_http.py`, `test_wallet_router.py`, `trader/test_trader_router_contract.py` | Route-level wallet/trader contracts |
| Event backbone | `wallets/test_wallet_event_backbone.py` | Commit-deferred wallet event publishing |

### Shard 2 — transfer market: `pytest tests/realtime tests/players/test_transfer_market.py tests/market/test_market_service.py`
**77 passed, 0 failed** in 416.93s (log: `.runtime/n35_realtime_transfer.log`)

- `players/test_transfer_market.py`: bid reservation parity, bid withdrawal release, checkout/settlement handoff.
- `market/test_market_service.py`: market read-model/service truth.
- `realtime/test_wallet_websocket_gateway.py`: wallet realtime payloads.

## Key invariants verified
1. Every ledger transaction nets to zero per unit (`UnbalancedTransactionError` enforced + rollback test green).
2. No spend without balance: `InsufficientBalanceError` on projected negative unless `allow_negative`.
3. Idempotency keys dedupe retried transactions.
4. Reservations are double-entry (available→escrow), not flags; release and settle paths both proven.
5. Withdrawal holds include fee; fee constant now config-driven (`gtex_withdrawal_fee_bps`).
6. Trader matching settles atomically per fill: buyer escrow debit, seller net credit, fee to trade-fee account, units escrow→buyer.

## Residual risks (not blockers)
- Suite runtime (~13.5m for 100 tests) is too slow for per-commit CI; covered by release-gate shard selection.
- P2P offer settlement remains manual-rail (by design, treasury-reviewed) — no automated escrow on the P2P lane.
- Trader matching engine is new this cycle (2026-06-12); recommend a staging soak with concurrent order placement before launch (locking is `with_for_update`, untested under real concurrency).
