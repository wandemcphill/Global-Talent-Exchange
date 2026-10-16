# Postgres Core Schema For The Live Football Economy

## Scope

This is a compact production-grade target schema for the football-economy core. It is intentionally narrower than the current backend ORM and should be treated as deployment DDL for a dedicated PostgreSQL cluster, not dropped directly into the existing cross-dialect Alembic path without a separate migration plan.

The companion DDL lives in `backend/docs/architecture/postgres_live_economy_schema.sql`.

## Design Rules

- Use `uuid` primary keys and `timestamptz` everywhere.
- Store money in minor units with `bigint`.
- Use `citext` for user identity fields that need case-insensitive uniqueness.
- Keep durable facts in PostgreSQL, but keep hot live state in Redis.
- Use `jsonb` for extensibility, not as a replacement for core foreign keys.
- Publish queue messages through a transactional outbox so writes and broker delivery stay atomic.
- Keep balances as projections. The ledger is the source of truth.

## Differences From The Draft

- Draft `wallets.gtex_balance`, `fan_coin_balance`, and `locked_balance` become `wallets`, `transactions`, `ledger_entries`, and `wallet_balance_projections`. This keeps balances queryable without sacrificing a full audit trail.
- `matches` adds `competition_id`, `match_type`, `host_user_id`, `entry_fee_minor`, and `prize_pool_minor`. Without them, user-hosted play and money flows cannot be joined cleanly.
- `match_participants` is explicit instead of burying squad ownership in match JSON. This is needed for user-hosted teams, payouts, and replay attribution.
- `player_orders` is normalized into `player_share_markets`, `player_share_holdings`, `player_orders`, and `player_order_fills`. Orders alone cannot reconstruct ownership.
- `club_shares` is normalized into `club_share_markets`, `club_share_holdings`, `club_share_distributions`, and `club_share_payouts` so shareholder revenue can be settled and audited.
- `user_progress` becomes `season_passes`, `season_pass_xp_grants`, and `season_pass_claims`. XP accrual and reward claiming are separate facts.
- `lottery_runs` links to `transactions` so every reward has a ledger reference.
- `player_rentals.tournament_id` references `competitions.id`. It is the same logical namespace.
- `transfer_listings.highest_bidder_club_id` is explicit. A plain `highest_bidder` field becomes ambiguous at scale.
- `follows` uses a composite primary key. It is a pure edge table and does not need a synthetic surrogate key.
- `match_events` uses a composite primary key `(match_id, id)`. PostgreSQL partitioned primary keys must include the partition key.

## Draft-To-Canonical Mapping

- `users` -> `users`
- `wallets` -> `wallets` plus `wallet_balance_projections`
- `transactions` -> `transactions` plus `ledger_entries`
- `matches` -> `matches` plus `match_participants`
- `match_events` -> `match_events`
- `players` -> `players` plus `player_share_markets`
- `player_orders` -> `player_orders` plus `player_order_fills`
- `clubs` -> `clubs`
- `club_shares` -> `club_share_markets`, `club_share_holdings`, `club_share_distributions`, and `club_share_payouts`
- `user_progress` -> `season_passes`, `season_pass_xp_grants`, and `season_pass_claims`
- `lottery_runs` -> `lottery_runs`

## Partitioning Strategy For `match_events`

- Partition by `HASH (match_id)` into 32 partitions.
- This is a better fit than time-range partitioning for live simulation because writes arrive in bursts per match and reads are almost always scoped to one `match_id`.
- The primary replay query path is `match_id -> ordered events`, so local partition pruning stays effective.
- Keep the authoritative append-only event log in PostgreSQL, but serve minute-by-minute spectator state from Redis.

## Relational Notes

- `users`, `wallets`, `transactions`, `ledger_entries`, `clubs`, `players`, `matches`, `match_participants`, `player_orders`, `club_share_payouts`, `transfer_listings`, and `club_listings` remain strongly relational.
- `player_meta`, `stories.entities`, `historical_records.data`, and `activity_feed.data` stay in `jsonb` because their shape evolves quickly.
- Contracts and rentals use exclusion constraints to prevent overlapping active ranges for the same player.
- Wallet balances, player ownership, club ownership, and lottery payouts are all reconstructible from immutable fact tables.

## Indexing Priorities

- Read-heavy lookups:
  `users(email)`, `users(username)`, `wallets(user_id, asset_code)`, `clubs(owner_id)`, `players(club_id, position, rating desc)`, `matches(status, scheduled_at)`, `season_passes(user_id, season_id)`, `activity_feed(user_id, created_at desc)`.
- Burst-write support:
  `match_events(match_id, minute, id)`, `ledger_entries(transaction_id, wallet_id)`, `player_orders(player_id, status, created_at desc)`, and `bids(listing_id, created_at desc)`.
- Market queries:
  partial indexes for open transfer listings, open player orders, and active club listings.
- Flexible search:
  `GIN` on `player_meta.attributes`, `stories.entities`, and `historical_records.data`.

## Redis Layout

- `match:{match_id}:state`
  Store hot score, clock, possession, and compact stats. Use a Redis hash unless RedisJSON is already standard in the stack.
- `match:{match_id}:events`
  Prefer a Redis Stream for fanout and replay cursors. If a list is used for simplicity, cap it aggressively with `LTRIM`.
- `listing:{listing_id}:bids`
  Sorted set keyed by bid amount or event sequence for fast leaderboard reads.
- `session:{user_id}`
  Session token and lightweight auth/session metadata with TTL.
- `home:{user_id}`, `player:{player_id}`, `club:{club_id}`
  Cache hydrated read models, not raw table rows.

## Queue Topology

- `match_simulation_queue`
  Partition key: `match_id`
  Consumers: simulation workers, replay archiver, live fanout workers
- `transfer_event_queue`
  Partition key: `listing_id`
  Consumers: bidding engine, market notifications, finance settlement
- `story_generation_queue`
  Partition key: `entity_scope`
  Consumers: narrative engine, recommendation and feed builders
- `notification_queue`
  Partition key: `user_id`
  Consumers: push, email, in-app delivery workers

## Broker Choice

- Kafka or Redpanda is the default recommendation for `match_simulation_queue` and other high-volume ordered streams.
- RabbitMQ fits well if the system is more command-driven than stream-driven.
- Redis Streams works for smaller single-cluster deployments, but it is the weakest option once replay, notifications, and market bursts all share the same infrastructure.

## Required Operational Table

Use a transactional `outbox_events` table in PostgreSQL.

- Application transaction writes domain rows and one outbox row.
- A publisher process reads pending outbox rows and publishes to Kafka, RabbitMQ, or Redis Streams.
- Consumers stay idempotent by event id and aggregate key.

Without this, match scheduling, transfer bidding, and story generation will eventually produce split-brain failures between the database commit and the broker publish step.
