# GTEX Full User Journey Acceptance Pass

## Purpose

This acceptance journey provisions six authenticated test users and follows one cross-domain lifecycle through the canonical GTEX APIs.

## Test actors

| Actor | Purpose | Initial test balances |
|---|---|---|
| Journey Owner | Primary club owner, competition player, regen creator, Jackpot winner, gift sender | 5,000 Fan Coin + 10,000 GTEX Coin |
| Journey Trader | Coin Trader and real-player seller | 500 Fan Coin + 100,000 GTEX Coin |
| Journey Peer | Joins the owner-hosted competition | 5,000 Fan Coin + 5,000 GTEX Coin |
| Journey Recipient | Gift recipient and owner of the recipient club context | 2,500 Fan Coin + 2,500 GTEX Coin |
| Journey Buyer | Coin Trader buyer and later player buyer | 5,000 Fan Coin + 100,000 GTEX Coin |
| Journey Club Buyer | Regen buyer and club seller | 5,000 Fan Coin + 200,000 GTEX Coin |

The implementation uses the existing `auth_user_factory`, whose fixture calls the real `/auth/signup/user` endpoint and therefore exercises registration, user-id issuance, and the normal signup-created club profile.

## Journey sequence

1. Register all users and assert unique user IDs and owned clubs.
2. Coin Trader: apply, approve, publish NGN pricing, create buy order, accept, lock escrow, submit payment proof, confirm and release.
3. User-hosted competition: owner creates, publishes, peer joins with a club, competition launches, fixture is completed, standings are read.
4. GTEX-hosted competition: platform creates official competition and owner joins with the owner's club.
5. National-team competition: create platform competition, create Nigerian entry, load live rental pool, select a backend-eligible rental player, rent that player.
6. Real player: platform-seed one real imported player on the Trader's club, list it in the transfer market, negotiate a cash offer, accept and close.
7. Build-a-Son: discover eligible parent, request the son, pay from Coin wallet, generate successor regen and assert the regen belongs to the owner's club.
8. Regen transfer: list the generated regen, receive an offer, counter it, accept, close the listing, inspect negotiation and submit the player's contract offer.
9. Player contract lifecycle: create first contract, renew it, then exercise the canonical transfer path that terminates the selling contract while creating the replacement contract for the buyer.
10. Club infrastructure: upgrade training, medical and youth-recruitment capability.
11. Youth pipeline: generate academy prospects, offer first contracts, accept, and promote a signed prospect to senior football.
12. Staff: recruit a manager from the live manager catalogue. When a live club-growth staff candidate is available, offer, accept and terminate a coach/staff contract.
13. Club sale: value a club, list it, accept a buyer offer, execute the transfer, and assert the ownership transition.
14. Jackpot: lower the test threshold, contribute a deterministic amount, manually trigger settlement, assert the primary user is the winner and a payout exists.
15. Gifts: send one gift to a user, verify receipt, send one gift to that user's club context, and verify the club-context receipt appears in the same recipient's transaction history.

## Test-only provisioning

The test directly seeds only platform-owned prerequisites that have no appropriate end-user creation flow for an acceptance test, specifically a real imported player record and an open transfer window. Economic user balances are seeded through the repository's wallet service exactly as existing test fixtures do.

## Certification rule

This document and the test are a **journey definition**, not a claim of runtime certification. A green certification requires the repository test runner to execute `backend/tests/acceptance/test_gtex_full_user_journey.py` successfully. Prior runner-side GitHub Actions failures with zero executed steps are not application test evidence.
