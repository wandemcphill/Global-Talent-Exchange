# Player Share Release Certification

This document defines the local certification sequence for the player-share economy. It is intentionally independent of GitHub Actions so the economic surface can still be audited while CI quota is unavailable.

## Gate 0: composite release gate

Run from the repository root:

```bash
python backend/scripts/audit_player_share_release_gate.py --strict
```

This is a read-only composite gate. It combines the lifecycle and trade-boundary checks and returns non-zero when either gate fails.

## Gate 1: lifecycle integrity

Run:

```bash
python backend/scripts/audit_player_share_lifecycle.py --database-url "$DATABASE_URL" --strict
```

The command is read-only. A non-zero result blocks release.

The audit checks explicit issuance provenance, eligibility of active markets, liquidity-account metadata, and legacy automatic initialization.

## Gate 2: inventory integrity

Run:

```bash
python backend/scripts/audit_player_share_integrity.py --database-url "$DATABASE_URL" --strict
```

The audit checks active-market eligibility, zero/negative supply, and circulating supply against total supply.

## Gate 3: event reconciliation

Run:

```bash
python backend/scripts/audit_player_share_reconciliation.py --database-url "$DATABASE_URL"
```

The command is read-only and fails when persisted market or holding share counts disagree with recorded share deltas, or when a holding is negative.

## Gate 4: trade boundary

Run:

```bash
python backend/scripts/audit_player_share_trade_boundary.py --strict
```

This is a source-level guard against accidentally restoring implicit market issuance inside the trade service.

## Required invariants

1. Discovery does not issue markets.
2. Issuance is explicit and eligibility-gated.
3. Trading cannot create a market as a side effect.
4. Market and holding share counts remain non-negative.
5. Share events are durable and reconcilable.
6. Economic settlement remains ledger-authoritative.
7. Repeated requests must not create duplicate economic effects.
8. A failed economic precondition must fail closed without provisioning a market.
9. The composite release gate must remain read-only.

## CI limitation

GitHub Actions is currently unavailable because the repository account has exhausted its Actions quota. These commands are therefore the local release-certificate path until the quota resets.

## Interpretation

A green unit-test suite alone is insufficient. Production certification requires the read-only database audits to return healthy results against the actual deployment database, plus source-level confirmation that the trade boundary has not regressed.
