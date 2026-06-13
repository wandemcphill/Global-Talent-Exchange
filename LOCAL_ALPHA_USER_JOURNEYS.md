# LOCAL ALPHA USER JOURNEYS

Date: 2026-06-12
Verdict: **PASS with noted manual-browser follow-up**

## Journey 1: Player

Status: **PASS**

Evidence:

- Auth registration/login/session: 5 backend auth tests passed.
- Frontend session persistence/sync: 4 Flutter auth/session tests passed.
- Wallet and payout invariants: targeted wallet payout tests passed; N33 money lane has 100 passed.
- Build-a-Son frontend path: 7 Flutter tests passed across readiness, wallet block, realtime sync, and wizard flow.
- Build-a-Son backend orders + starter club regens: `backend/tests/regen/test_regen_creation_orders.py backend/tests/clubs/test_starter_regen_bootstrap.py` -> 27 passed after local schema fixture repair.
- Squad/formation backend: 6 passed.
- Squad/formation frontend: 11 passed.

Result:

- create account: PASS
- login: PASS
- wallet: PASS
- Build-a-Son: PASS
- squad: PASS

## Journey 2: Competition

Status: **PASS**

Evidence:

- `backend/tests/competitions/test_competition_lifecycle.py` -> 6 passed.
- Existing N34 report certifies creation, join, fixtures, standings, results, paid entry idempotency, and settlement path against canonical `/api/v2`.

Result:

- create: PASS
- join: PASS
- fixtures: PASS
- standings: PASS
- results: PASS

Residual:

- Sibling competition route-test files still need canonical v2 fixture lift before public beta, but the local alpha lifecycle path is green.

## Journey 3: Transfer Market

Status: **PASS**

Evidence:

- `backend/tests/players/test_transfer_market.py backend/tests/players/test_transfer_bid_wallet_reservations.py` -> 60 passed.
- N35 realtime/transfer shard: 77 passed.
- N33 money certification: bid reservation, withdraw release, checkout/settlement handoff.

Result:

- list player: PASS
- place bid: PASS
- reserve funds: PASS
- withdraw bid: PASS
- accept transfer: PASS

## Journey 4: Creator

Status: **PASS after local bug fix**

Evidence:

- `backend/tests/creator/test_creator_application_router.py backend/tests/creator/test_creator_module7_contracts.py` -> 10 passed.
- Creator frontend repository/module/access request tests -> 9 passed.
- Fix applied: creator withdrawal now passes gross debit to wallet payout so requested net amount, fee, and total debit are consistent.

Result:

- apply: PASS
- provision creator assets: PASS by Module 7 contract and frontend module tests
- create campaign: PASS by creator module contract/frontend repository tests
- settlement flow: PASS by creator withdrawal/settlement contract tests

## Manual Follow-Up Before Inviting Humans

Run one browser smoke with the final tunnel URLs:

1. Open the app URL.
2. Register a new player.
3. Login.
4. Close the browser.
5. Reopen the app URL.
6. Confirm session hydrates.
7. Exercise one wallet read, one Build-a-Son preview, one competition discovery/join, one transfer bid, and creator application.

