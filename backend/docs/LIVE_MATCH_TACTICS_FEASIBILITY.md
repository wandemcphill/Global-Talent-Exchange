# Live in-match tactics + halftime — feasibility & design

Status: **needs an architecture decision** before building. Date: 2026-06-29.

## The request
In a head-to-head live match: either user can change formation/tactics at **any time**,
the match **cannot be paused**, the change affects **only that user's team**, and the
opponent's view is **never disturbed**. At halftime, a **countdown timer** auto-returns to
the match; if **both** users press Done, they return early.

## The blocker (how matches actually run today)
- `match_simulation_service.build_replay_payload()` computes the **whole match up front** —
  full timeline, final score, penalty shootout, highlights.
- `execution_runtime` then **streams that pre-computed replay** out minute-by-minute
  (`time.sleep(stream_update_interval_seconds)`) so it *feels* live.
- `MatchRoomManager` is redis pub/sub fan-out to spectators; it takes **no tactical input**.

**Consequence:** the match result exists before the first minute is streamed. A tactical
change made "during" the match **cannot alter the outcome** — the engine is not a real-time
tick simulation that re-reads tactics as it plays.

## What this means for each part of the spec
| Part | Feasible now? | Notes |
| --- | --- | --- |
| Open tactics panel mid-match without pausing / disturbing opponent | ✅ (client-local) | The panel is on the user's own screen; the stream keeps playing; the opponent's stream is independent. Pure client UX. |
| That change **affects this match's play/result** | ❌ | Match is pre-computed. Would need a real-time tick engine. |
| Change affects **only that user's team** | ✅ at the *plan* level | We already persist per-club formation/XI (`ClubMatchPlan`); it shapes that club's **next** match build, not the running one. |
| No pause, ever | ✅ | Streaming never pauses for tactics (it's client-local). |
| Halftime countdown timer | ✅ (client) | Pause **stream playback** at the `half_time` checkpoint; count down; resume. |
| Both-Done early return | ⚠️ needs realtime | A 2-client "ready" exchange over the existing realtime channel. |

## Options
1. **Honest subset (no engine change).** Ship: (a) a non-disruptive in-match tactics panel
   that updates the user's saved `ClubMatchPlan` (affects their next match), with clear copy
   that changes apply next match; (b) the halftime countdown + both-Done as a live-viewer
   client feature with a realtime ready-signal. The current match keeps playing pre-computed.
2. **Real engine.** Re-architect the simulation from one-shot-precompute to **real-time
   tick-based**, reading each team's current tactics every N minutes, accepting live input
   per team. This makes mid-match changes truly affect play — but it's a large rewrite of
   `match_simulation_service` + `execution_runtime` + a live match session store, and changes
   determinism/replay/settlement guarantees.
3. **Two-pass hybrid.** Keep one-shot, but compute the match in **two halves**: stream first
   half (pre-computed), apply any halftime tactical changes, then compute + stream the second
   half. Mid-half changes still don't apply, but **halftime** changes genuinely affect the
   second half — matching "halftime adjustments" without a full real-time rewrite. Medium effort.

## Recommendation
**Option 3 (two-pass hybrid)** gives the most of the vision for the least risk: real halftime
tactical impact + the non-disruptive panel + the halftime timer, without a full real-time
rewrite. Option 1 ships fastest but mid-match changes are cosmetic-until-next-match. Option 2
is the "true" version but a major, settlement-sensitive rewrite.

All three need the live-match viewer UI + realtime ready-signal, which require device testing.

---

## Build status (decision: real-time engine rewrite)

**Increment 1 — real-time engine (DONE, functionally verified):** `app/live_match/` — a new,
additive, tick-based engine alongside the one-shot one. `LiveMatchEngine` advances a match one
minute at a time, **re-reads each team's current tactics every tick** (so mid-match changes
affect the rest of play for that side only), pauses at minute 45 for half time, and resumes
early when **both** sides mark ready (else on a 60s countdown). Endpoints: create / get / tick /
tactics / halftime-ready (registered via `live_match` module, `/api/live-match/...`). Verified
by a standalone run (ticks→HT→tactical change→both-ready resume→FT, goals + events recorded).

**Increment 3 — viewer UI (DONE, compile-clean, not device-tested):**
`lib/data/live_match_repository.dart` + `lib/features/match/gtex_live_match_viewer_screen.dart` —
scoreboard polling read-only state, a **non-disruptive tactics sheet** (formation + mentality,
applies to your side only — never pauses the match or touches the opponent), and a **halftime
overlay** (countdown + Done + "n/2 ready").

**Remaining increments (needed to run head-to-head in prod):**
- **Inc 2 — shared store + ticker:** the session store is in-process (per worker). Back it with
  Redis/DB and add a server-side ticker (a worker advancing active sessions every N seconds +
  broadcasting via `MatchRoomManager`) so clients only READ. Without this, multi-worker prod
  won't share sessions and matches won't auto-advance.
- **Inc 4 — matchmaking integration:** on a head-to-head pairing, create the session, assign each
  user their `side` (home/away), ownership-gate `tactics`/`halftime` to the controlling user,
  and route the viewer with `matchId` + `side`.
- **Inc 5 — replace/branch the one-shot path** for head-to-head live matches (competitions/
  settlement keep the one-shot engine).
