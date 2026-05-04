# GTEX Production Stability Blockers

Date: May 4, 2026

## Scope

This handoff captures the production stability issues observed during live verification against [https://gtex-api.onrender.com](https://gtex-api.onrender.com), with emphasis on wallet read concurrency, host recovery after burst load, and live match/websocket readiness.

## Executive Summary

Production is in a better place than it was earlier in the day:

- wallet read endpoints now pass cleanly at `20` concurrent requests
- demo-backed `api/v1` shell payloads are no longer publicly visible
- protected diagnostics and metrics are no longer public

But the system is **not yet stable at `50` concurrent wallet reads**, and after the `50`-way burst the host degraded badly enough that even health and auth endpoints timed out. Live websocket verification is also still incomplete because production reported no active live matches and the provisioning path timed out under the degraded host state.

## Observed Production Behavior

### 1. Wallet read endpoints pass at 20 concurrency

Verified on production after the wallet-read limiter rollout:

- `/api/wallets/overview`
  - `5/5` ok
  - `10/10` ok
  - `20/20` ok
- `/api/wallets/adaptive-overview`
  - `5/5` ok
  - `10/10` ok
  - `20/20` ok
- `/api/wallets/withdrawals/eligibility`
  - `5/5` ok
  - `10/10` ok
  - `20/20` ok

Response headers confirmed the intended production limiter behavior:

- `X-RateLimit-Scope: wallet_read`
- `X-RateLimit-Limit: 120`

### 2. Wallet read endpoints fail at 50 concurrency

Production rerun at `50` concurrent requests:

- `/api/wallets/overview`
  - `1/50` ok
  - `49` read timeouts
  - avg `35.691s`
  - p95 `42.390s`
- `/api/wallets/adaptive-overview`
  - `0/50` ok
  - `50` read timeouts
  - avg `35.616s`
  - p95 `35.454s`
- `/api/wallets/withdrawals/eligibility`
  - `0/50` ok
  - `50` read timeouts
  - avg `35.508s`
  - p95 `35.373s`

Interpretation:

- the `20`-concurrency limiter problem is fixed
- the `50`-concurrency failure mode is now **host/service collapse**, not simple rate limiting

### 3. Host recovery after burst load is poor

After the `50`-way wallet read run, production stopped responding to basic checks within the timeout budget:

- `/health` -> read timeout
- `/ready` -> read timeout
- `/version` -> read timeout
- `/auth/login` -> read timeout

Interpretation:

- the issue is not isolated to a single wallet route
- a moderate burst can push the API into a degraded state with slow recovery

### 4. No active live matches available for websocket proof

The live-match discovery routes all returned empty active sets:

- `/api/matches/live/active` -> `{"total":0,"items":[]}`
- `/matches/live/active` -> `{"total":0,"items":[]}`
- `/match/live/active` -> `{"total":0,"items":[]}`
- `/api/match/live/active` -> `{"total":0,"items":[]}`

Interpretation:

- there was no genuine active live match available for spectator or Unity websocket verification

### 5. Live provisioning path did not complete reliably

The intended live verification path is already present in the repo:

- [tools/provision_gtex_live_match.py](C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\provision_gtex_live_match.py)

When run against production with live auth and match generation enabled, the script timed out:

- `[GTEX] The read operation timed out`

Interpretation:

- the production live provisioning flow is not yet reliable enough to use as a stable proof harness under current host conditions

## Likely Root-Cause Buckets

### 1. API worker saturation

Production Render config currently sets:

- `WEB_CONCURRENCY=2`

Given the observed collapse at `50` concurrent authenticated reads, this is a strong candidate. Two workers may simply be too thin for:

- authenticated wallet reads
- policy/treasury lookup chains
- background request pressure
- normal live app traffic

### 2. Shared dependency contention

Even after wallet read-path cleanup, these endpoints still depend on a shared stack that can become hot under concurrency:

- wallet summary reads
- treasury settings resolution
- policy resolution
- bank account checks
- DB session and query contention

Symptoms fit a shared dependency bottleneck:

- requests hang for tens of seconds
- health/auth endpoints degrade after burst load

### 3. Poor isolation between hot paths and health/auth surfaces

Once the service is pressured, even these lightweight endpoints become slow:

- `/health`
- `/ready`
- `/version`
- `/auth/login`

That suggests insufficient isolation between:

- user-facing read traffic
- core availability checks
- login/auth infrastructure

### 4. Lack of stable live runtime for websocket verification

The websocket routes can exist and still not be meaningfully verifiable if:

- no live matches are active
- the match generation path is slow or timing out
- the host is already degraded before provisioning completes

## Evidence Snapshot

### Production success case

Wallet read surfaces now use the correct limiter:

- scope: `wallet_read`
- limit: `120`

This confirms the wallet-read limiter rollout is deployed and functioning as intended.

### Production failure case

At `50` concurrency, wallet reads no longer fail with `429` responses. They fail with `ReadTimeout`, which is a more serious availability signal because it indicates the server is not returning timely responses rather than intentionally throttling.

## Recommended Immediate Actions

### 1. Increase API worker capacity

First production experiment:

- raise `WEB_CONCURRENCY` above `2`

Then rerun:

- wallet reads at `20`
- wallet reads at `50`

Why first:

- it is the fastest likely win
- it directly addresses the most obvious host-level choke point

### 2. Profile wallet read endpoints under load

Focus on:

- `/api/wallets/overview`
- `/api/wallets/adaptive-overview`
- `/api/wallets/withdrawals/eligibility`

Inspect:

- DB query count and latency
- connection pool wait time
- slow joins / repeated lookups
- per-request policy and treasury dependencies

### 3. Add a burst-recovery gate to release verification

After any load test, require:

- `/health` recovers within a short window
- `/ready` recovers within a short window
- `/auth/login` remains responsive

Without this gate, a load test can look survivable while the host is actually left in a degraded state.

### 4. Seed or schedule a known active live match for verification

To complete live websocket proof, production needs one of:

- a predictable active match kept available for verification
- a reliable provisioning path that can generate one on demand

Without that, websocket verification remains blocked by an empty runtime.

### 5. Re-run the live provisioning path after host tuning

Use:

- [tools/provision_gtex_live_match.py](C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\provision_gtex_live_match.py)

After capacity or performance fixes, rerun it against production and confirm:

- login succeeds
- match generation succeeds
- Unity access token issuance succeeds
- live HTTP bridge responds
- websocket verification completes

## Pass/Fail Release Gate

### Pass when

- wallet read endpoints remain healthy at `50` concurrency
- health and auth recover immediately after burst load
- at least one real live match can be provisioned or discovered
- websocket/live match verification completes end to end

### Fail when

- `50`-way wallet reads still time out
- health/auth endpoints time out after burst load
- live runtime remains empty
- provisioning continues to time out

## Current Release Call

Production is **not yet ready** for the next level of bursty live traffic.

Current status:

- wallet reads at `20`: pass
- wallet reads at `50`: fail
- host recovery after burst: fail
- live websocket proof: incomplete

The next highest-value move is to treat this as a stability incident, not just a feature verification gap.
