# GTEX PHASE 4E — MATCHDAY → FORM → VALUE CONTRACT

**Status:** IMPLEMENTED, PENDING ARCHITECTURAL REVIEW
**Scope:** the chain `match → performance → form → valuation → market → ownership`

This document is the contract for the only mechanism in GTEX by which football
performance is permitted to move money. It is deliberately explicit, because the
mechanism touches user funds.

---

## 1. WHAT WAS ACTUALLY BROKEN

Direct inspection of the tree before this change, not handover text:

| Link | State before | Evidence |
|---|---|---|
| match → performance | **BROKEN.** Ratings computed per request and discarded. | `match_engine/services/match_simulation_service.py` builds `rating_views` at `_build_summary` and attaches them to the response. The service contains **zero** `session.add` calls. Nothing was persisted, ever. |
| performance → form | **Real-world only.** | `value_engine/service.py:587` reads `recent_form_rating` from `PlayerSeasonStat.average_rating` / `PlayerEventWindow`. Both are written **only** by `ingestion/` (provider feeds). The match engine wrote to neither. |
| form → value | **Working.** | `value_engine/scoring.py:505` — `recent_form_factor = clamp((form - 6.5) * 0.12, -0.10, 0.22)`, plus `performance_adjustment_pct`, emitting `strong_recent_form`. Genuine, tested machinery — fed real-world data only. |
| value → market | **Working when the job runs.** | `PlayerSummaryProjector.project` (`players/service.py:48`) writes `current_value_credits` from `snapshot.target_credits`. Admin edits (`admin_players/service.py:119`) are a second writer. |
| market → owner | **Working.** | `portfolio/service.py:257` `_resolve_current_price`: summary → snapshot → market signal. |

**Conclusion:** the chain was severed at exactly one place — nothing persisted match
performance. Everything downstream already existed and worked.

The join key was, however, already available: `team_factory.py:741` sets
`player_id=player.id` (canonical `ingestion_players.id`) whenever squads are built
from a database session.

---

## 2. WHAT THIS CHANGE ADDS

### 2.1 `player_match_performances` (new table)

`backend/app/models/player_match_performance.py`, migration
`20260902_0117_player_match_performance`.

One row per (player, completed competition match). Written by
`players/performance_recorder.py`, called from
`services/competition_auto_runner.py::_store_match_performances` **after** settlement,
so the row carries the real completion timestamp.

`player_id` intentionally carries **no** foreign key. It is validated against
`ingestion_players` before insert. This gives the same integrity guarantee without
letting one unrecognised id abort settlement of an otherwise valid match.

### 2.2 Eligibility policy — what may reach the economy

Decided **once, at write time**, and stored on the row (`eligible_for_valuation`,
`ineligibility_reason`) so that it is auditable after the fact rather than re-derived
against a moving policy.

| Rule | Effect |
|---|---|
| Competition matches only | Friendlies, fast matches, private and ad-hoc simulations never reach this code path at all. |
| Canonical player ids only | Synthetic squad ids (`"{team_id}-p{shirt}"`) are dropped, not stored. |
| Minutes ≥ 15 | Recorded, but `eligible_for_valuation = false` (`insufficient_minutes`). Stops repeated late cameos from being farmed. |
| Early red card | Recorded, flagged distinctly (`sent_off_early`). |
| Idempotent | Re-settling a fixture cannot double-count form. |

### 2.3 Form window — `players/form_service.py`

Rolling window over the **last 6 eligible performances**, newest first, with
deterministic tie-breaking.

**Anti-farming guard:** at most **3** performances from any single competition may
occupy the window (`MAX_PERFORMANCES_PER_COMPETITION`). An owner who can influence one
competition cannot fill a held player's form window from it. The count of excluded
performances is returned and **shown in the UI**, not hidden.

Trajectory is the recent half of the window against the older half, with a 0.15
epsilon. Below four matches it reports `steady` rather than inventing a direction.

### 2.4 The valuation signal — `value_engine/matchday_signal.py`

Pure, database-free, exhaustively tested.

```
per_match_i  = clamp((rating_i − 6.5) × 0.012, ±0.02)
mean         = Σ per_match_i / n
trend_nudge  = ±0.004  (rising / falling only)
confidence   = clamp(n / 6, 0, 1)
adjustment   = clamp((mean + trend_nudge) × confidence, ±0.05)
```

| Property | Guarantee |
|---|---|
| **Gradual** | The signal is a *mean* of per-match contributions that are each capped *before* averaging. One spectacular match cannot carry it. |
| **Bounded** | `MAX_TOTAL_ADJUSTMENT_PCT = 0.05` is a backstop that **does not bind**. Because the mean of values each capped at `PER_MATCH_CAP_PCT` cannot exceed that cap, the true effective bound is `PER_MATCH_CAP_PCT + TREND_NUDGE_PCT` = **±2.4%**, exposed as `EFFECTIVE_MAX_ADJUSTMENT_PCT` and asserted by tests. The 5% constant is retained as defence in depth so a future change to the per-match maths cannot silently unbound the economy. |
| **Gated** | Below `MINIMUM_MATCHES_FOR_SIGNAL = 3` counted matches the signal is not applied at all. |
| **Deterministic** | Same window in, same number out. No randomness, no clock. |
| **Auditable** | `as_audit_payload()` carries every intermediate quantity and is persisted. |

### 2.5 Application — an overlay, never a replacement

`ValueSnapshotJob` gained an **optional** `matchday_signal_provider`. When absent,
behaviour is byte-identical to before; the overlay is strictly additive to the existing
pipeline.

`apply_matchday_overlay` adjusts `target_credits` and recomputes `movement_pct`, and
leaves **every component value untouched** — `football_truth_value_credits`,
`market_signal_value_credits`, `scouting_signal_value_credits` and the whole
`breakdown` are unchanged. The base valuation stays the primary source of truth and the
two contributions stay separable forever.

`ValueEngine` itself — the golden-tested core — was **not modified**.

The audit payload is persisted to `breakdown_json["matchday_signal"]` and the reason
code appended to `reason_codes_json`, so "why did his value move?" is answerable from
stored data.

### 2.6 Reaching the owner

`snapshot.target_credits` → `PlayerSummaryProjector` → `PlayerSummaryReadModel.current_value_credits`
→ `PortfolioService._resolve_current_price` → the holder's position.

Covered end to end by `tests/performance_economy/test_chain_end_to_end.py`.

---

## 3. WHAT THIS CHANGE DELIBERATELY DOES **NOT** DO

- **It does not move `PlayerShareMarket.share_price_coin`.** The tradable share price
  is still moved only by trades and by the existing admin-only
  `POST /players/{id}/shares/performance`. Wiring matchday form directly into the
  tradable price is a separate economic decision and is **not** in this change.
- It does not modify the router, the canonical player card, the wallet, or market
  architecture.
- It does not compute any form number in Dart. Form and causality remain backend-owned,
  per §9.2 of the Phase 4 contract.

---

## 4. UI HONESTY RULES (enforced by test)

`test/player_detail/matchday_form_card_test.dart` defends these, because a card that
implies a causal link the backend has not made is worse than no card:

1. No eligible competition football → says so explicitly. Never draws flat form, which
   would read as "he played and was average".
2. Form present but not applied → says so, and says how many matches are still needed.
3. Signal applied → shows the **real bounded adjustment**, not a restatement of the
   rating, and discloses the ±2.4% cap.
4. The anti-farming exclusion count is disclosed.
5. Ineligible performances are shown dimmed, not hidden.
6. The form→position sentence appears **only** when form is genuinely driving value.
7. No position → "no position". Never a fabricated zero holding.

---

## 5. API

| Endpoint | Purpose |
|---|---|
| `GET /api/players/{id}/form` | Form window, bounded signal, recent performances. Read-only. Reports `has_sample=false` rather than inventing a neutral window. |

---

## 6. TEST COVERAGE

| Suite | Count | Covers |
|---|---|---|
| `tests/performance_economy/test_performance_recorder.py` | 7 | canonical-id filtering, idempotency, eligibility, timestamps |
| `tests/performance_economy/test_form_service.py` | 10 | windowing, competition cap, trajectory, determinism |
| `tests/performance_economy/test_matchday_signal.py` | 16 | bounds, gradualism, gating, determinism, audit |
| `tests/performance_economy/test_matchday_overlay.py` | 10 | overlay maths, component isolation, job seam, backwards compatibility |
| `tests/performance_economy/test_chain_end_to_end.py` | 10 | every link, plus farming and single-match cases |
| `test/player_detail/matchday_form_card_test.dart` | 12 | the honesty rules above |
| **Total** | **65** | |

---

## 7. OPEN QUESTIONS FOR REVIEW

1. **Owner-hosted competitions.** The per-competition cap blunts farming structurally
   without needing an ownership lookup. A stricter tier — excluding performances in
   competitions hosted by the player's own holder — was considered and **not**
   implemented, because it requires an ownership join at write time. Flagged rather
   than faked.
2. **Snapshot cadence.** No scheduler currently runs `ValueSnapshotJob`; the only
   trigger is `POST /api/value/snapshots/rebuild`. Matchday form therefore reaches
   valuations only when that job runs. That predates this change, but it now has
   product consequences and should be decided.
3. **Tradable share price.** See §3. Whether matchday form should ever reach
   `share_price_coin` is an economics decision, not an engineering one.
