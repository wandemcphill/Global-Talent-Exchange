# Phase 5H — Retire Admin Buyback

## Decision

GTEX will **not buy player shares from users**. The platform is a marketplace operator, not the buyer of last resort.

The canonical player-share economy is System A (`PlayerShareMarket`, `PlayerShareHolding`, `PlayerTokenMarketService`). Users may buy and sell through the canonical market. GTEX does not promise an admin-funded exit when market liquidity is unavailable.

## What this retires

- Admin buyback is removed from the product surface.
- `/orders/{order_id}/admin-buyback-preview` is no longer exposed.
- `/orders/{order_id}/admin-buyback` is no longer exposed.
- The portfolio/order detail UI no longer presents an admin fallback sale.
- Synthetic System B orders are prohibited for any future exit flow.

## What remains

Legacy System B order and buyback implementation may remain in the repository temporarily for historical inspection, simulation fixtures, or controlled migration work. It is **not a supported player-share exit path** and must not be reintroduced into product routes.

Admin remains a market governor, not a counterparty. Admin controls may still:

- suspend or halt a market;
- retire or disable a player listing;
- investigate abuse or corrupted state;
- correct integrity issues through an explicitly audited repair process.

Those controls do not purchase, assume, or liquidate a user's player shares.

## Exit and liquidity contract

GTEX must not describe a player-share position as instantly liquid or imply that the platform will always provide a buyer. Product copy should distinguish:

- **tradable:** the market currently accepts a sell action;
- **filled:** a sell actually matched or settled;
- **liquidity unavailable:** there is no guaranteed immediate counterparty.

A future liquidity improvement may add better discovery, matching, market-making, or external counterparties. Such work must use System A and must not resurrect the retired System B venue.

## Accounting boundary

Removing admin buyback removes the need for an admin-liquidity funding account, payout band, P2P-priority timer, or admin buyback ledger settlement. These concepts are not part of the canonical player-share contract.

Phase 5G realized P/L continues to account only for canonical player-share events. No special admin-buyer accounting branch is required for the launch economy.

## Acceptance criteria

1. No supported backend route can execute an admin buyback.
2. No supported frontend surface offers an admin buyback or "quick exit".
3. Canonical buy/sell remains System A only.
4. No synthetic `Order` is created to emulate a player-share exit.
5. Product copy does not promise platform-funded liquidity.
6. Historical System B code is clearly treated as legacy and cannot silently become the live player-share venue.
