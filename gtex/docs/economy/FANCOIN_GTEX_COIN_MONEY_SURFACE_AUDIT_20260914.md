# FanCoin / GTEX Coin Money-Surface Audit

Branch hardening pass: `hardening/fancoin-gtex-money-surface-20260914`

## Canonical monetary rules

- `CREDIT` is FanCoin and is non-withdrawable.
- `COIN` is GTEX Coin and is withdrawable.
- FanCoin → GTEX Coin conversion is only permitted through the canonical gift conversion bridge.
- GTEX Coin is not generically transferable as a gift between users.
- Coin Trader P2P movement uses escrow and canonical ledger postings.
- Competition escrows are currency-specific: participant-funded competitions use FanCoin; host-funded Coin-prize competitions use GTEX Coin.

## Audited flows

| Flow | Canonical accounting | Status |
| --- | --- | --- |
| FanCoin purchase | verified payment → `CREDIT` wallet ledger | CLOSED |
| Coin funding / deposit | verified payment or treasury deposit → `COIN` wallet ledger | CLOSED |
| Admin → Coin Trader liquidity issue | platform Coin liquidity pool → trader Coin wallet | HARDENED |
| Admin → Coin Trader liquidity redeem | trader Coin wallet → platform Coin liquidity pool | CLOSED |
| User buys Coin from trader | trader Coin → escrow → user Coin | CLOSED |
| User sells Coin to trader | user Coin → escrow → trader Coin | CLOSED |
| User withdrawal | user Coin → withdrawal escrow → clearing | CLOSED |
| User → user gift | sender FanCoin → conversion → recipient GTEX Coin | CLOSED |
| User-hosted FanCoin competition | participant FanCoin → competition escrow → FanCoin rewards | CLOSED |
| Host-funded Coin competition | host Coin → Coin escrow → winners + platform fee | CLOSED |
| GTEX-hosted competition | admin/platform funding → competition settlement | CLOSED |

## Coin Trader liquidity hardening

Historically, the platform liquidity-pool system account could be created with
`allow_negative=True`. That meant an authorized liquidity-desk admin could issue
Coin to a trader even when the platform liquidity pool had insufficient balance.

Migration `20260914_0122_coin_trader_liquidity_backing` now makes the Coin and
FanCoin liquidity-pool accounts non-negative and creates them eagerly when they
do not exist. The canonical ledger's existing balance-projection locking then
blocks any issue transfer that would drive the pool below zero.

This is intentionally a ledger-level control rather than a UI-only check.

## Regression coverage added

- Admin liquidity issue cannot overdraw the Coin liquidity pool.
- Admin liquidity issue is replay-safe and idempotency keys cannot be rebound to a different transfer.
- User buys Coin from an approved trader through escrow and the settlement moves exactly the intended Coin balance once.

Existing money-surface suites also cover the canonical FanCoin → GTEX Coin gift
bridge, gift idempotency, withdrawal restrictions, and hosted competition funding/
settlement paths.

## Important boundary

This hardening does not introduce a generic user-to-user Coin transfer. GTEX Coin
remains intentionally non-giftable; the supported user-to-user economic paths are
explicit products such as Coin Trader escrow, competition rewards, and FanCoin gifts.
