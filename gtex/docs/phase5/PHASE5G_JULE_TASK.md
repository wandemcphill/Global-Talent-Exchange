# Jules Task — Phase 5G

Implement `docs/phase5/PHASE5G_REALIZED_PL_ACCOUNTING_BRIEF.md` on a branch from the current `origin/main`.

Before coding, audit the real System A buy/sell settlement path and prove whether fees/cost basis semantics are already explicit. Do not infer or invent economic rules.

Deliver PR-only. No merge.

Acceptance is the full checklist in the brief, especially new-trade weighted-average cost basis, immutable sell accounting snapshot, correct realized P/L, honest historical unavailability, trading history from canonical System A events, Portfolio wording for price/value separation, and hard regression coverage.

Do not re-home System B admin buyback. Do not alter router/shell architecture. Do not use current mutable holding state to reconstruct historical realized P/L. No production writes.
