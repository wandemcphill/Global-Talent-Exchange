# GTEX P6-10 Runtime Resilience Verification

## Scope

This document captures the committed verification lane for `P6-10`:
- stale transport
- reconnect
- token refresh
- terminal-match selection

`P6-10` is not passed by source inspection alone. It needs explicit exercised scenarios plus saved logs and a repeatable invocation path.

## What Already Exists In Source

The shipped runtime already contains the intended failure-handling branches:
- stale transport detection in [GtexMatchRuntime.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs:1697>)
- websocket disconnect and reconnect scheduling in [GtexMatchRuntime.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs:1733>)
- live access token refresh in [GtexMatchRuntime.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs:1775>)
- terminal-match detection in [GtexMatchRuntime.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs:1113>)

The backend already contains the route-level auth and refresh seams:
- Unity access refresh endpoint in [backend/app/live_matches/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/live_matches/router.py:1092>)
- Unity websocket pre-accept rejection in [backend/app/api_v1/router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/app/api_v1/router.py:488>)

## Committed Verification Assets

The repo now includes a dedicated resilience harness:
- mock backend server: [tools/gtex_live_resilience_mock_server.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/gtex_live_resilience_mock_server.py>)
- Windows player runner: [tools/run_gtex_live_resilience_smoke.ps1](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_live_resilience_smoke.ps1>)

The harness covers two concrete scenarios:

### 1. Resilience Scenario

Match id:
- `live-resilience-test`

Injected behavior:
- initial websocket connects successfully
- server closes the first websocket with `4401 unauthorized`
- runtime is expected to refresh the live token
- refreshed websocket reconnects successfully
- server then stalls the websocket long enough to trigger stale-transport handling
- runtime is expected to detect stale transport, disconnect, and reconnect again

Passing evidence:
- bootstrap finished
- refresh request hit the backend
- runtime logged successful token refresh
- runtime trace logged stale transport
- server observed a third websocket connect after the stale event
- runtime trace returned to active websocket ticks after reconnect

### 2. Terminal Scenario

Match id:
- `live-terminal-test`

Injected behavior:
- live bridge returns a completed/fulltime payload immediately
- terminal websocket sends a final frame and closes

Passing evidence:
- bootstrap finished
- runtime logged the terminal-match warning
- server observed the terminal websocket final-frame path

## Backend Assertions Added

The backend test suite now makes auth-failure expectations explicit:
- invalid Unity refresh tokens return `401` in [backend/tests/live_matches/test_live_match_router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/tests/live_matches/test_live_match_router.py:177>)
- invalid Unity websocket access tokens reject pre-accept with `4401` in [backend/tests/api_v1/test_router.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/backend/tests/api_v1/test_router.py:297>)

These do not replace runtime verification, but they keep the auth-failure contract pinned while the player harness covers recovery behavior.

## How To Run

PowerShell:

```powershell
& 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_live_resilience_smoke.ps1' -Scenario all
```

Artifacts written by the runner:
- summary: [tmp/gtex_live_resilience_summary.json](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_live_resilience_summary.json>)
- server logs:
  - [tmp/gtex_live_resilience_server.out.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_live_resilience_server.out.log>)
  - [tmp/gtex_live_resilience_server.err.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_live_resilience_server.err.log>)
- player log: [tmp/gtex_live_resilience_player.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_live_resilience_player.log>)
- runtime trace: [Gtex_Test_Migration/Builds/WindowsProduction/tmp/gtex_live_runtime_trace.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Builds/WindowsProduction/tmp/gtex_live_runtime_trace.log>)

## Current Status

Current status: `IN PROGRESS`

What this closes:
- a committed, repeatable resilience harness now exists
- auth failure expectations are now explicit in backend tests
- runtime recovery proof has a standard log/summary artifact path

What still remains before `P6-10` can be marked `PASSED`:
- run the harness and save a clean evidence pack from the current shipped player
- attach the resulting summary/logs to the `P6` evidence pack
- confirm the same scenarios against a real deployed backend path where appropriate, not only the controlled mock lane
