# REALTIME CERTIFICATION (N35)

Date: 2026-06-12
Branch: `feature/original-visual-runtime` @ `5ca8db2d`
Verdict: **PASS (contract level) — staging soak recommended for reconnect/multi-device under load**

## Evidence

`pytest tests/realtime` — all 6 suites green inside the 77-passed shard (log: `.runtime/n35_realtime_transfer.log`):

| Suite | Coverage |
|---|---|
| `test_websocket_route_contracts.py` | Websocket route registration + canonical contract shape |
| `test_match_websocket_gateway.py` | Match gateway: authoritative score/clock payloads, authority flags |
| `test_wallet_websocket_gateway.py` | Wallet gateway: balance push contracts |
| `test_regen_creation_realtime.py` | Regen creation progress events |
| `test_competition_settlement_realtime.py` | Competition settlement events |
| `test_admin_export_realtime.py` | Admin export queue/readiness events |

Corroborating prior evidence (manifest, Stage 2A 2026-06-07): the same four websocket suites passed as a sidecar gate (13 passed), so this is a repeat-green, not a first-green.

Runtime wiring verified statically in `app/main.py`: `app.state.realtime.bind_loop()` on startup, graceful `realtime.shutdown()` on app shutdown.

## Directive checklist

| Requirement | Status |
|---|---|
| websocket registration | ✅ proven by route-contract tests |
| authoritative score/clock | ✅ match gateway tests |
| authored commentary / generated disabled | ✅ covered by `tests/ops/test_canonical_production_guards.py` (16 passed, core shard) + `live_matches/generated_stream_policy.py` |
| disconnect handling | ✅ gateway tests cover unregister paths |
| reconnect | ⚠️ contract-level only — no automated test simulates network drop/resume |
| stale session handling | ⚠️ not explicitly tested |
| multi-device behavior | ⚠️ not explicitly tested |
| event duplication prevention | ✅ outbox relay + commit-deferred publish (wallet event backbone tests) |

## Recommendation
The three ⚠️ rows are launch risks only under real client churn. Cover them in the staging soak (`tools/run_gtex_staging_soak.ps1`) with scripted disconnect/reconnect before public beta; closed beta can proceed.
