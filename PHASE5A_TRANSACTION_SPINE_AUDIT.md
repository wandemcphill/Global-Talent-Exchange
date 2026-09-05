# PHASE 5A — Transaction Spine Audit

**CURRENT MAIN:** `origin/main`
**CURRENT HEAD:** `b6aa43ec`
**BRANCH:** `phase5/market-economy-transaction-integrity`
**RESULT:** **STOP FOR ARCHITECTURAL DECISION** — no production code changed.

---

## Summary

The Phase 5 opening question is:

> Can a user discover a footballer, understand the opportunity, acquire ownership,
> see the resulting economic state, and later make another decision?

Today the answer is **no**, and the reason is not UI. GTEX contains **two complete,
live, mutually invisible player-ownership systems**. Production supply was issued
into one of them; the app trades and reports ownership out of the other; the only
working acquisition path is unreachable from the Flutter client.

This is an explicit STOP condition from the Phase 5 brief on two counts:
*two competing canonical trading systems exist*, and *existing price/value
ownership is contradictory*. Choosing which system is canonical is an economic
model decision, not an implementation detail, so no fix was attempted.

---

## The two systems

### System A — share markets (`PlayerShareMarket` / `PlayerShareHolding`)

| | |
|---|---|
| Ownership record | `player_share_holdings` (`share_count`, `average_cost_coin`) |
| Price record | `player_share_markets.share_price_coin` (Numeric 18,4, coin) |
| Canonical service | `backend/app/players/token_service.py::PlayerTokenMarketService` (production subclass) over `backend/app/players/legacy_token_service.py` (implementation) |
| Fail-closed boundary | `backend/app/players/trade_boundary.py::PlayerShareTradeBoundary` |
| Execution model | Instant fill against the market at `share_price_coin`, then deterministic price impact |
| Liquidity | Real: a per-player `market_liquidity` ledger account; sells are refused when it is too thin |
| HTTP surface | `POST /market/buy`, `POST /market/sell`, `POST /players/{id}/shares/buy`, `POST /players/{id}/shares/sell` |
| Issuance | `backend/app/ingestion/share_market_issuance.py` + `scripts/issue_player_share_markets*.py`, `scripts/backfill_real_league_share_markets.py`, `scripts/bulk_issue_regen_markets.py` |
| **Production state** | **~26,000 issued, active markets** (all real-league and regen supply) |
| **Flutter callers** | **none** |

### System B — order book (`exchange_orders` / position ledger accounts)

| | |
|---|---|
| Ownership record | `LedgerAccount` rows coded `position:{user_id}:{player_id}` |
| Price record | none — price is the taker's own limit price |
| Canonical service | `backend/app/orders/service.py::OrderService` + `backend/app/matching/service.py::MatchingService` |
| Execution model | Limit order book, maker/taker matching, `TradeExecution` rows |
| Liquidity | Only other users' resting orders. No market maker |
| HTTP surface | `POST /orders`, `GET /orders/book/{player_id}`, `POST /orders/{id}/cancel`, admin buyback |
| Issuance | none in production. Position units are credited only by `_settle_execution`, admin god-mode, `demo_bootstrap`, and the simulation harness |
| **Production state** | **zero position units — the book cannot bootstrap** |
| **Flutter callers** | `GteOrderTicketSheet` → `placeOrder` → `POST /orders`. **This is the app's only player trading UI.** |

`GET /portfolio` (`backend/app/portfolio/service.py`) is built **exclusively** from
System B's `position:` ledger accounts. It never reads `PlayerShareHolding`.

---

## Proven user journey on `b6aa43ec`

Regression suite: `backend/tests/players/test_phase5_transaction_spine_audit.py`
(3 strict-xfail defects, 2 passing guards).

**Path 1 — the working buy, invisible.**

```
POST /players/{id}/shares/market   -> 200  market issued, 1000 shares @ 0.5000 coin
POST /market/buy {share_count: 10} -> 201  gross 5.0000, fee 1.0000, net 6.0000
  DB: player_share_holdings.share_count = 10, average_cost_coin = 0.6000
GET  /portfolio                    -> 200  {"holdings": []}
GET  /portfolio/summary            -> 200  total_market_value 0.0000, cash 494.0000
```

The coin is gone. The asset does not exist as far as every ownership consumer is
concerned.

**Path 2 — the app's actual buy, unfillable.**

```
POST /orders {side: buy, quantity: 5, max_price: 0.5} -> 201
  status "open", filled_quantity 0.0000, execution_count 0,
  reserved_amount 2.5000, hold_transaction_id set
GET  /orders/book/{id} -> 200  {"bids":[...], "asks": []}
```

1000 shares are issued and active, and the book the app trades on shows no ask.
The user's coin is reserved indefinitely against an order that cannot fill.

**Path 3 — the two stores disagree.**

```
POST /market/buy {share_count: 10} -> 201   (user now owns 10 shares)
POST /orders {side: sell, quantity: 5} -> 400
  "Sell quantity 5.0000 exceeds owned quantity for player ..."
```

---

## Findings

### P0

**P0-1 — Ownership acquired through the canonical Market buy path is invisible to the Portfolio.**
`POST /market/buy` writes `PlayerShareHolding`; `GET /portfolio`,
`GET /portfolio/summary`, `GtexOwnershipBook.fromPortfolio`, and the order
ticket's "Owned quantity" chip all read `position:` ledger accounts. A successful
purchase debits the wallet and produces no visible position anywhere in the
product.
`backend/app/portfolio/service.py:176` (`_load_settled_executions`), `backend/app/market/router.py:425`

**P0-2 — Two unreconciled ownership stores; the venue the app trades on has no supply.**
Production issuance credits `PlayerShareMarket.circulating_shares`. Only a
settled `TradeExecution` can credit `position:` units. There is no bridge and no
market maker, so no user can ever hold position units, therefore no user can ever
post an ask, therefore no buy order can ever fill. The Flutter client's only
player trading path (`lib/widgets/gte_order_ticket_sheet.dart:261` → `POST /orders`)
targets this system.
`backend/app/orders/service.py:382`, `backend/app/wallets/service.py:1926`

**P0-3 — The order ticket reserves coin using a credit-denominated valuation.**
`GteOrderTicketSheet` pre-fills its limit price from
`snapshot.ticker.bestAsk ?? snapshot.ticker.referencePrice`. The book is always
empty, so it is always `referencePrice`, which
`MarketPlayerQueryService._reference_price` resolves from
`authoritative_reference_credits(...)` — the value-engine **credits** valuation
(or an EUR-derived fallback). The order is placed in `LedgerUnit.COIN` and
`reserved_amount = quantity × max_price` debits the **coin** wallet at that
number, next to a chip labelled "Available GTEX Coin". Coin and credit are
distinct ledger units that `append_transaction` balances separately. This is
`PRICE != VALUE` violated at the point where money moves.
`frontend/lib/widgets/gte_order_ticket_sheet.dart:296`, `backend/app/market/service.py:2274`, `backend/app/orders/service.py:87`

### P1

**P1-1 — `/market/buy` and `/market/sell` silently discard `idempotency_key`.**
`PlayerSharePurchaseRequest` and `PlayerShareSaleRequest` carry an
`idempotency_key` field and a `model_post_init` hook that seeds the contextvar.
`PlayerShareTradeRequest` — the schema used by both `/market` trade endpoints —
carries neither. Pydantic drops the unknown field without a 422, so the client
believes it sent a key. Proven: two identical POSTs with the same key produced
two transactions and 20 shares, while the same key on
`/players/{id}/shares/buy` correctly replayed (one transaction, 10 shares).
A client retry after a timeout executes a second real trade.
`backend/app/players/token_schemas.py:94`

**P1-2 — The Market read model exposes no tradable price at all.**
`MarketPlayerListItemView` publishes `current_value_credits`, `market_value_eur`,
`movement_pct`, `trend_score`, `global_scouting_index` — and never
`share_price_coin`. The Market can answer "what is this player worth" but not
"what does ownership cost", which is Phase 5 question 3.
`backend/app/market/schemas.py:195`

**P1-3 — "Movement" is valuation movement presented as market movement.**
`MarketPlayerQueryService._movement_pct` returns
`summary.movement_pct` / `latest_snapshot.movement_pct` — value-engine snapshot
movement. The movers rail renders it as `dayChangePercent` with up/down market
colouring. No tradable-price movement signal is exposed anywhere.
`backend/app/market/service.py:2187`, `frontend/lib/features/player_market_redesign/widgets/gtex_market_movers_rail.dart:202`

**P1-4 — Portfolio P/L mixes units.**
`PortfolioService._resolve_current_price` returns
`PlayerSummaryReadModel.current_value_credits` /
`PlayerValueSnapshotRecord.target_credits` / a `MarketSignal` score, while
`average_cost` is derived from coin ledger entries. `unrealized_pl` subtracts one
from the other. Currently masked by P0-1 (the portfolio is always empty), but it
becomes wrong the moment ownership is bridged.
`backend/app/portfolio/service.py:257`

### P2

**P2-1 — `SettlementService` is a third, orphaned settlement implementation.**
`backend/app/settlement/service.py` implements single-sided settlement
(reserve → settle → credit position units) in parallel with
`OrderService._settle_execution`. It has zero callers outside its own module.

**P2-2 — `/market/buy` and `/market/sell` do not roll back on domain errors.**
`raise_player_share_market_http_exception` is called without a preceding
`session.rollback()`, unlike the `CreatorTradeRequest` branch three lines above,
which does roll back. The `get_session` teardown discards the transaction, so
this is currently latent rather than exploitable — but it is an inconsistency in
a money path.
`backend/app/market/router.py:460,510`, `backend/app/players/router.py:319,346`

**P2-3 — `PlayerShareTradeBoundary` is bypassed by every production caller.**
Both `/market` and `/players` routers construct `PlayerTokenMarketService`
directly. The service's own `_require_trade_market` happens to reproduce the
boundary's fail-closed check, so behaviour is correct — but the class named as
the trade boundary is only exercised by tests.

**P2-4 — Idempotency is carried on a module-level monkeypatch and a contextvar.**
`token_service.py` mutates `legacy_token_service.generate_uuid` at import time to
smuggle a deterministic ledger reference, and the request key travels from a
Pydantic `model_post_init` through a `ContextVar`. It works, and it is proven to
work, but it is invisible at the call site and fragile under refactor.

### P3

**P3-1** — `Order` status vocabulary (`open` / `partially_filled` / `filled` /
`cancelled` / `rejected`) has no `pending` or `reversed`; the UI correctly
reports the server status verbatim ("Order open for …"), so no state is invented.
This is a pass, recorded for the Workstream 16 trace.

**P3-2** — `PlayerShareMarket.liquidity_coin` is a genuine ledger-backed balance;
`MarketPlayerMarketProfileView.liquidity_band` is a value-engine band. Two
different things share the word "liquidity" across the contract.

---

## Ownership boundary verification (Workstream 2)

| Concern | Status |
|---|---|
| Matchday writes `share_price_coin` | **CLEAN** — no writer outside trading/issuance/governed reprice |
| Narrative writes `share_price_coin` | **CLEAN** |
| Portfolio computes its own player value | **VIOLATED** — P1-4, and it is the only value source it has |
| Market manufactures value from rating | **CLEAN** — `_require_reference_price` raises rather than inventing a price for real players |

Complete writer classification of `share_price_coin`:

- **CANONICAL (trade):** `legacy_token_service.py:332,463` (`_price_after_trade`)
- **CANONICAL (governed):** `legacy_token_service.py:523` (`EconomyGovernorService.clamp_price_change`)
- **ISSUANCE:** `legacy_token_service.py:78,108,118,676,693,778,786`, `ingestion/share_market_issuance.py:106`, `players/router.py:287`, `token_market_defaults.py:57`
- **ADMIN/OPS SCRIPTS:** `scripts/issue_player_share_markets*.py`, `scripts/backfill_real_league_share_markets.py`, `scripts/bulk_issue_regen_markets.py`, `scripts/reprice_appreciation.py`
- **SEPARATE DOMAIN:** `club_ownership/service.py:136`, `services/creator_share_market_service.py` (club and creator markets, distinct tables)

The Phase 4I ownership model holds. The break is not in price authorship — it is
in ownership representation.

---

## Atomicity / idempotency / concurrency (Workstreams 5–7)

Assessed against System A, the only path that actually moves player ownership.

**Atomicity — sound.** One `Session`, one `session.commit()` at the router. Wallet
debit, holding upsert, `circulating_shares`, price impact, liquidity sync,
`PlayerShareEvent`, and the domain event are all in the same transaction.
`append_transaction` enforces per-unit balanced postings, a
`ck_ledger_entries_amount_non_zero` check constraint, and a negative-balance
guard against row-locked `LedgerBalanceProjection` rows. No partial-failure
window found.

**Idempotency — sound where wired, absent where used.** `transactions.idempotency_key`
is `unique`. `_replay_idempotent_trade` returns the original result and raises
`trade_idempotency_conflict` if the same key is reused for a different economic
intent. Proven working on `/players/{id}/shares/buy`. Not reachable from
`/market/buy` (P1-1). Server-authoritative, no client-only mechanism.

**Concurrency — sound in design, unverifiable in this test environment.** Every
trade takes `SELECT ... FOR UPDATE` on the `PlayerShareMarket` row before doing
anything, and sells additionally lock the `PlayerShareHolding` row. Concurrent
buy×buy, sell×sell, and buy×sell on the same player serialise on the market row;
the unique `idempotency_key` is the backstop. **Caveat:** `with_for_update()` is a
no-op on SQLite, which is what the entire test suite runs on, so no automated
test in this repository can actually demonstrate the lock. Production is
Postgres, where it holds. This is a verification gap, not a known defect.

**Order book (System B):** `place_order` → reserve → match → settle is atomic
within the request. `ensure_execution_not_settled` guards double settlement.
There is **no** idempotency key on `POST /orders` — a retry after a timeout
creates a second order and a second fund reservation. Lower severity only
because the order cannot fill.

---

## Scorecard

| Lane | Status | Note |
|---|---|---|
| TRADING ATOMICITY | **GREEN** | Single transaction boundary, balanced ledger, no partial-failure window found |
| IDEMPOTENCY | **RED** | Mechanism is correct and proven, but the Market trade endpoints silently drop the key |
| CONCURRENCY | **AMBER** | Row locks + unique key are correct by construction; unprovable on SQLite |
| LEDGER INTEGRITY | **GREEN** | Unique idempotency key, non-zero check constraint, per-unit balance, locked projections |
| ORDER INTEGRITY | **AMBER** | State machine and transitions are sound; the book has no supply and no idempotency |
| PORTFOLIO INTEGRITY | **RED** | Reports from a store nothing writes; mixes coin cost against credit valuation |
| PRICE/VALUE SEPARATION | **RED** | Reservation priced in credits, debited in coin; no tradable price in the Market contract |
| MARKET CONTRACT | **RED** | Cannot answer "what does ownership cost" or "what can I buy" |
| DATA HONESTY | **AMBER** | No fabricated timestamps or fake ownership; but valuation movement is labelled market movement |
| RESPONSIVE MARKET | **NOT ASSESSED** | Deferred — gated behind the transaction decision per the brief |
| ACCESSIBILITY | **NOT ASSESSED** | Deferred — same |
| TEST HEALTH | **GREEN** | New suite: 2 passed, 3 strict-xfail. Affected suites unchanged |

**FINAL RECOMMENDATION: STOP FOR ARCHITECTURAL DECISION.**

---

## The decision required

Which system is canonical for player ownership? Everything downstream follows
from this and none of it is safe to guess.

**Option 1 — System A is canonical (recommended).**
Retire the order book for player shares. Point the Flutter order ticket at
`/market/buy` and `/market/sell`, rebuild `PortfolioService` on
`PlayerShareHolding`, publish `share_price_coin` in the Market contract, add
`idempotency_key` to `PlayerShareTradeRequest`.

*Why:* it is the only system with production supply (~26k active markets), real
ledger-backed liquidity, working idempotency, and a price that responds to
trading. It fills instantly, which is what a mobile product needs.
*Cost:* the order book, matching engine, position-account layer, admin buyback,
and `SettlementService` become dead code. Admin buyback's KYC-gated fiat exit
path would need re-homing onto System A.

**Option 2 — System B is canonical.**
Build a market-maker that issues position units from `PlayerShareMarket` supply,
migrate the ~26k markets into position accounts, keep the book.

*Why:* real price discovery, a real bid/ask, and the admin buyback exit already
exists here.
*Cost:* materially larger. Needs a market maker, a supply migration, an
idempotency mechanism on `POST /orders`, and it inherits the coin/credit unit
break in P0-3. And an order book with thin real user liquidity is a poor first
experience.

**Option 3 — Both, with an explicit bridge.**
Not recommended without a written invariant that `PlayerShareHolding.share_count`
equals the `position:` unit balance at all times, enforced in one place.

Until this is chosen, Phase 5's Market work should not start: every actionability
field (price, ownership, liquidity, P/L, next action) resolves differently under
each option.

---

## What was NOT done, and why

- No production code changed. The brief's STOP conditions were met on two counts.
- No Market UI work (Workstreams 8–11, 13–16, 19–20). All of it depends on which
  ownership contract is canonical.
- No legacy deletion. The brief says classify, do not delete.
- No golden regeneration. None were touched.

## Next Phase-5 dependency

Architect selects Option 1, 2, or 3. Then the first implementation PR is
"bridge or retire", with the three strict-xfail tests in
`backend/tests/players/test_phase5_transaction_spine_audit.py` as its acceptance
criteria — when they XPASS, the markers come off.
