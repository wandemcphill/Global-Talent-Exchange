# GTEX Feature Depth Scorecard

Generated: 2026-06-04

Scoring scale: 0-100. Scores are evidence-weighted from source inspection, test coverage, and validation failures. They measure production readiness, not feature ambition.

| Area | Backend truth | UI depth | Realtime | Workflows | Ops readiness | Auditability | Failure handling | Overall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| WORLD | 60 | 60 | 40 | 60 | 60 | 60 | 80 | 60 |
| MARKET | 80 | 80 | 40 | 80 | 60 | 80 | 60 | 69 |
| CLUB | 80 | 80 | 40 | 80 | 60 | 80 | 80 | 71 |
| COMPETE | 70 | 80 | 60 | 65 | 55 | 60 | 75 | 66 |
| MATCH CENTER | 80 | 80 | 90 | 80 | 75 | 65 | 90 | 80 |
| CAPITAL | 85 | 80 | 60 | 80 | 75 | 90 | 70 | 77 |
| COMMUNITY | 60 | 60 | 40 | 60 | 40 | 60 | 60 | 54 |
| CREATOR | 75 | 60 | 40 | 70 | 55 | 75 | 60 | 62 |
| ADMIN | 85 | 80 | 40 | 75 | 65 | 90 | 75 | 73 |

## Area Notes

### WORLD

World has meaningful backend and UI surface, including world simulation routes and national-team/regen paths. Readiness is capped by partial realtime evidence and failing national regen parsing in frontend tests.

### MARKET

Market has strong transfer and wallet-reservation coverage, but targeted validation still found transfer-market auth message mismatches and transfer bid settlement failure. Realtime exists for transfer listings but is not uniformly proven across market workflows.

### CLUB

Club surface is deep and includes formation, squad readiness, identity, ownership, and club ops. Frontend quick-link routing failed in `club_identity_routing_test.dart`, and analyzer warnings show unreachable switch cases across club hub surfaces.

### COMPETE

Compete has the new bracket island and backend competition APIs. Readiness is reduced by frontend competition hub tests failing, missing `settlementReadiness` in runtime proof, backend competition API/auth/discovery errors, and route/mount contract failures.

### MATCH CENTER

Match Center is the strongest canonical feature island. It has backend-authoritative realtime posture, websocket truth guards, blocked/degraded states, and quarantined legacy 3D/native paths. Readiness is still capped by stale monetization tests and legacy route-wrapper expectations failing.

### CAPITAL

Capital/admin finance/wallet truth is comparatively strong. Wallet and transfer validation passed most tests but still failed reservation and access-message edge cases. Trader blocked-state UI failed because duplicate `Order book blocked` widgets were rendered.

### COMMUNITY

Community has route and UI presence, but production depth is thinner: less realtime evidence, less operational evidence, and historical overflow fixes noted in manifests rather than current full visual proof.

### CREATOR

Creator has backend and route scaffolding, plus creator access priming in shell. Several creator/creator-market/stadium/share surfaces remain blocked or duplicated, so launch depth depends on explicitly deciding which creator flows are in scope.

### ADMIN

Admin has strong backend/audit intent, finance controls, role guards, and command-center scaffolding. Readiness is capped by targeted competition/admin failures, export/artifact blockers, route duplication, and operational startup/migration churn.

## Overall Feature Readiness

Weighted current feature readiness: 68%.

This is not launch readiness. Feature code exists, but validation shows integration, route ownership, test, and dirty-tree blockers.

