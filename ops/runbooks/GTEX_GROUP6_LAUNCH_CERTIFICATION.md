# GTEX Group 6: Production Readiness & Launch Certification

Group 6 is a single production-readiness sweep. It does not introduce a new product phase. It closes the gap between a green repository and a defensible production launch.

## Release lanes

1. **Repository lane**: deterministic checks that can run in CI without real credentials.
2. **Staging lane**: authenticated end-to-end flows against real staging infrastructure.
3. **Production lane**: deployment, health, observability, rollback and controlled smoke verification.

A lane must not be marked complete from evidence belonging to another lane.

## Mandatory runtime inputs

- Canonical backend URL: `https://gtex-api.onrender.com` unless the deployment record explicitly supersedes it.
- Bootstrap admin secret stored in the deployment vault and injected into staging/production.
- Live KoraPay secret, webhook secret, redirect URL and public notification URL.
- Approved 5000+ real-player import cohort plus issuance rules and liquidity policy.
- Licensed Unity Windows runner identity.

Secrets never belong in this file or in CI logs.

## P0 certification matrix

### Live boot

- Every shipped release profile must require `GTE_API_BASE_URL`.
- Live mode remains the default.
- Missing base URL must fail before shipping rather than silently falling back to localhost/fixture transport.

### Wallet and payment rails

- Treasury mode is intentional and documented.
- KoraPay checkout, redirect, webhook signature verification and settlement are exercised in staging.
- Invalid webhook signatures fail closed.
- Payment events are idempotent under replay.

### Player trading

- Buy and sell routes require the trading-compliance dependency.
- Blocked users receive the expected authorization response.
- Verified users can buy and sell.
- Player discovery distinguishes searchable, pending and active markets.

### Player corpus

- Stage -> report -> repair -> publish pipeline succeeds.
- Searchable corpus exceeds 5000 real players.
- Approved issuance cohort is buyable and tradeable.
- Acquired players remain eligible for GTEX and hosted competitions.

### Competitions

- GTEX competition: create -> publish -> join -> launch.
- Hosted competition: create -> invite -> accept -> launch.
- Both families remain intentionally distinct in UI copy and routing.

### Admin control plane

- Admin role catalog and assignments are database-backed.
- Role updates survive restart and second-process reads.
- File-backed state is used only as a one-time legacy import/fallback when no database session factory exists.

### Realtime

- WebSocket connect, auth, heartbeat, disconnect and reconnect are exercised.
- A 15-minute staging soak records connection churn, error rate and message latency.
- Live match playback survives a reconnect without duplicating terminal events.

### Performance and concurrency

- PostgreSQL wallet/treasury operations are exercised concurrently.
- No duplicate settlement, negative invariant or lost update is observed.
- Market discovery remains paginated and bounded; large datasets must not require a full in-memory player table scan for every request.

### Deployment and rollback

- Production deploy is gated on backend, frontend and live-playback checks.
- Database backup is taken before schema-changing production deployment.
- Restore is rehearsed against an isolated target before launch.
- Rollback procedure identifies both application commit and migration state.

### Observability

- JSON logs are enabled.
- Health endpoint and dependency diagnostics are reachable.
- Payment, wallet, match and realtime failures have actionable log context.
- Alerts exist for elevated 5xx, webhook failures, queue backlog and realtime disconnect spikes.

## Launch decision

Group 6 is **GREEN** only when:

- repository gates are green;
- staging E2E evidence is captured for payments, trading and both competition families;
- 5000+ real-player evidence is captured;
- concurrency/realtime soak evidence is captured;
- backup/restore and rollback rehearsals are recorded;
- production configuration uses real values; and
- Unity Windows batch build is green on a licensed runner.

If a required runtime input is missing, mark the specific lane **BLOCKED**, not GREEN.
