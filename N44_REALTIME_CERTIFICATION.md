# N44 — WEBSOCKET HARDENING CERTIFICATION

Date: 2026-06-13
Branch: `feature/original-visual-runtime` @ `f61d0edc`
Verdict: **PASS — contract + hardening coverage green; new collision/dedup/stale/rejoin tests added**

## New tests added this phase
`backend/tests/realtime/test_realtime_hub_hardening.py` — **6 passed** (`.runtime/n44_hardening.log`), driving `RealtimeHub` in-process via `asyncio.run` + a fake WebSocket:

| Test | Hardening property proven |
|---|---|
| `test_wallet_topic_scope_denies_cross_user_subscription` | **WS auth/authorization:** `_resolve_topics` rejects another user's `wallet:`/`admin:` topics; only the caller's own scoped topics resolve. No cross-tenant subscription. |
| `test_duplicate_subscriptions_are_idempotent` | **Duplicate subscriptions:** repeated `subscribe("market"×3)` collapses to one (`dict.fromkeys` dedup). |
| `test_broadcast_delivers_once_per_connection_no_duplication` | **Event duplication prevention:** a dispatch matching a doubly-subscribed topic delivers exactly once per connection. |
| `test_stale_listener_is_evicted_on_send_failure` | **Stale listeners / memory leak:** a socket that raises on `send_json` is evicted from `_connections`; healthy peers retained; `delivered_messages` counts only real sends. |
| `test_disconnect_then_rejoin_issues_fresh_client_and_no_leak` | **Disconnect/rejoin:** disconnect pops the client; rejoin issues a distinct `client_id`; subscribing on the stale id is a no-op (no resurrection/leak); connection count stays 1. |
| `test_client_id_collision_isolation_across_concurrent_connects` | **Route/id collision:** 25 concurrent `connect()` calls yield 25 unique `client_id`s, all tracked — no collision under concurrency. |

## Pre-existing contract coverage (N35, re-confirmed)
6 suites green: `test_websocket_route_contracts`, `test_match_websocket_gateway`, `test_wallet_websocket_gateway`, `test_competition_settlement_realtime`, `test_regen_creation_realtime`, `test_admin_export_realtime`.

## Audit findings (from `app/realtime/service.py`)
| Concern | Status | Evidence |
|---|---|---|
| WS auth | ✅ | topic-scope denial in `_resolve_topics` (wallet/admin pinned to `user_id`); gateway auth in N35 contract tests |
| Reconnect | ✅ (logic) | fresh `client_id` per `connect`; stale-id ops are no-ops |
| Duplicate subscriptions | ✅ | dict-keyed topics + `dict.fromkeys` |
| Stale listeners | ✅ | `_broadcast` evicts on send failure under `_connection_lock` |
| Memory leaks | ✅ (in-process) | disconnect pops; eviction on failure; `shutdown()` clears + closes all |
| Route collisions | ✅ | uuid4 `client_id`, unique under concurrent connect |

## Residual (not blockers for closed beta)
- **Network-level reconnect storm / multi-device soak** still not load-tested against a live ASGI server (in-process hub is proven; real socket churn is not). Recommend the staging soak (`run_gtex_staging_soak.ps1`) with scripted disconnect/reconnect before public beta.
- `_broadcast` is O(connections × dispatches) per event — fine for closed-beta scale (25–50 users); revisit for public beta fan-out.

## Conclusion
Realtime hub is **hardened and certified** for closed beta: topic auth, dedup, stale-eviction, rejoin, and collision isolation all proven by new tests; contract layer green. Public-beta gate: live-socket reconnect soak.
