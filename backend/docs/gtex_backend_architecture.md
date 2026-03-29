# GTEX Backend Architecture

## Folder Structure

- `backend/app/gtex/config.py`
  GTEX tuning knobs for jackpot, market, AI, and worker polling.
- `backend/app/gtex/redis_keys.py`
  Central Redis keyspace and stream naming.
- `backend/app/gtex/store.py`
  Redis-backed realtime state, queue, sorted-set, and distributed-lock adapter with in-memory fallback for tests.
- `backend/app/gtex/service.py`
  Jackpot engine, creator market, AI leagues, and unified economy settlement logic.
- `backend/app/gtex/runtime.py`
  Runtime assembly and FastAPI startup/shutdown binding.
- `backend/app/gtex/router.py`
  Public API surface for jackpot, creator market, and AI leagues.
- `backend/app/gtex/worker_runtime.py`
  Long-running worker loops for jackpot evaluation, valuations, matchmaking, and AI simulation.
- `backend/app/models/gtex_economy.py`
  PostgreSQL source-of-truth tables for GTEX state.
- `backend/migrations/versions/20260329_0064_gtex_unified_economy.py`
  Schema migration for all GTEX tables.
- `backend/workers/jackpot_worker.py`
  Dedicated jackpot trigger worker entrypoint.
- `backend/workers/valuation_worker.py`
  Dedicated creator valuation worker entrypoint.
- `backend/workers/ai_matchmaker.py`
  Dedicated matchmaking worker entrypoint.
- `backend/workers/ai_brain.py`
  Dedicated AI simulation worker entrypoint.
- `backend/scripts/gtex_load_test.py`
  Sample load harness for match, jackpot, and market spikes.
- `backend/tests/gtex/test_gtex_system.py`
  Integration coverage for the unified loop.

## Redis Key Design

- `jackpot:global_balance`
  Current open-round jackpot balance cache.
- `jackpot:global:trigger_state`
  Trigger metadata for the current round.
- `jackpot:global:last_winner`
  Last settled winner payload.
- `jackpot:{round_id}:participants:set`
  Eligible participant IDs for the round.
- `player:{id}:price`
  Real-time creator share price cache.
- `player:{id}:demand_score`
  Real-time creator demand cache.
- `market:trending_players`
  Sorted set used for trending market reads.
- `ai:{id}:state`
  Serialized AI profile state for realtime reads.
- `ai:{id}:elo`
  Cached AI ELO score.
- `leaderboard:league:{league_id}`
  Sorted set for fast league ranking reads.
- `match:queue`
  Waiting matchmaking queue index.
- `gtex.stream.matchmaking`
  Queue entries for the matchmaking worker.
- `gtex.stream.ai_brain`
  Match IDs awaiting simulation.
- `gtex.stream.valuation`
  Player IDs awaiting valuation recalculation.
- `gtex.stream.jackpot`
  Jackpot balance-change notifications for the trigger worker.

## Event System

- `MATCH_COMPLETED`
  Emitted after AI/human match settlement, leaderboard updates, jackpot contributions, and creator stat updates.
- `JACKPOT_TRIGGERED`
  Emitted when the jackpot worker settles the current round and opens the next one.
- `PLAYER_VALUE_UPDATED`
  Emitted when creator share valuation changes and caches are refreshed.
- `TRADE_EXECUTED`
  Emitted after creator share buys or sells commit.
- `JACKPOT_CONTRIBUTION_RECORDED`
  Emitted whenever eligible platform activity increments the jackpot pool.
- `MATCH_CREATED`
  Emitted when the matchmaker pairs humans or spawns an AI opponent.

All GTEX domain events are staged through the existing outbox/event-publisher path so they remain durable and horizontally fan out through Redis/Kafka-backed infrastructure already present in the backend.

## Worker Responsibilities

- `jackpot_worker.py`
  Monitors jackpot balance, evaluates threshold/probability/failsafe triggers, takes a Redis lock, and settles payouts exactly once.
- `valuation_worker.py`
  Consumes valuation jobs, recalculates creator prices, refreshes caches, and emits `PLAYER_VALUE_UPDATED`.
- `ai_matchmaker.py`
  Consumes queue entries, pairs human players when possible, otherwise spawns AI, then enqueues simulation work.
- `ai_brain.py`
  Simulates matches asynchronously, persists match events/results, settles wallets, updates leaderboards, pushes jackpot contributions, and emits `MATCH_COMPLETED`.
