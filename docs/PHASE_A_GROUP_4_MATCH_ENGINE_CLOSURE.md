# Phase A Group 4: Match Engine + Competition Economy Closure

## Release contract

The match engine remains layered: team strength incorporates form, morale, motivation, fatigue, chemistry, coaching, tactical quality and adaptability; event generation covers core football event families; simulation output remains deterministic from its seed.

Competition settlement is authoritative at `CompetitionMatchService.complete_match`. Completed matches may be replayed only with the same scoreline, terminal abandoned/cancelled matches cannot settle, and standings application is guarded by `stats_applied`.

Match economy flows through `MatchEconomyEngine` and the wallet ledger. User-hosted entry fees are collected through the economy service with idempotency support. GTEX-hosted prize funding is treasury-governed and sourced through the controlled promotional pool. Volume-triggered rewards use spending controls and `RewardSettlement` records.

## Release gates

- `audit_match_engine_competition_economy_release.py` is read-only and release-blocking.
- `test_match_economy_engine.py` covers entry fees, GTEX funding and volume rewards.
- `test_competition_match_settlement_guard.py` covers duplicate completion, worker-first settlement, score mutation rejection and terminal-match rejection.
- The Phase A economic workflow runs these regressions and the Group 4 static gate.

No alternate direct ledger mutation path is introduced by this closure pass.
