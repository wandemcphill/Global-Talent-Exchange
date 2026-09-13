# PR #178 Lifecycle Audit Notes

Current head: `1aa3d6369c91570e2ac7a907580e39cd547a8508`

## Certified by code/test evidence in the current branch

- Player-lifecycle mutation routes have an authentication boundary.
- Transfer authorization derives the seller from the player's active contract, validates the buyer's club access, rejects spoofed club ids, and rejects buying from the same club.
- Academy promotion has a canonical contract bridge with exactly-one active-contract and replay protection at the academy bridge boundary.
- Legacy ManagerMarket free recruitment is quarantined.
- Legacy API-v2 tournament rental mutation is quarantined.
- Competition finalization already has explicit idempotency coverage: repeated `finalize_competition(..., settle=True)` produces one reward row and one reward settlement.
- Player-card/settlement infrastructure uses the dedicated `PLAYER_CARD_PURCHASE` / `PLAYER_CARD_SALE` ledger source tags rather than transfer settlement tags.

## Confirmed blockers

### Transfer acceptance replay

`PlayerLifecycleService.accept_bid()` currently rejects a second acceptance because only `submitted` bids may be accepted. Existing regression coverage confirms that a repeated accept does not create a second contract, but the requested Phase 6 contract is stronger: a replayed settlement request should return the already-settled result. This must be implemented in the canonical lifecycle service, not by adding a parallel route.

### Academy wage-unit certification

The academy bridge preserves the accepted `wage_minor` numeric value into the canonical player-contract salary field. This is intentionally non-converting, but the authoritative Phase 6 economic contract still needs to certify whether that field is semantically Fan Coin units or merely an existing generic decimal amount.

### Regen transfer E2E

The canonical chain exists from free-agent quote through bid evaluation and acceptance, including hidden salary visibility, contract creation, club affiliation and squad synchronization. A complete repeat-signing and competing-offer settlement test still needs to be certified as one E2E invariant.

### National rental lifecycle

The canonical national rental routes and `RentalContract` model are present. The current audit has not yet certified the full lifecycle as one idempotent transaction: eligibility -> rental-only squad -> contract creation -> execution -> expiry/release -> settlement replay.

### Staff role effects

The canonical staff path uses `ClubStaffProfile`, `ClubStaffContract` and `ClubStaffAssignment`, and the route tests cover offer -> accept -> assignment. Role-effect propagation through the Phase 6D domain formulas still needs an explicit certification test.

### Award propagation

Winner persistence, duplicate-vote protection, and downstream hall/feed/profile propagation remain unverified in this audit pass.

## CI status

Fresh workflow runs for the exact current head have not been exposed by the repository connector. No green-CI claim is made.
