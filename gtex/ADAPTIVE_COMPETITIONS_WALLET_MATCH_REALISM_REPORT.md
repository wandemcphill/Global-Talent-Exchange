# Adaptive competitions, wallet, and match realism pass

Implemented in this pass:
- adaptive competition runtime and orchestration with bracket sizing, byes, fallback fill, and region-aware logic
- adaptive wallet overview endpoint with withdrawal readiness and provider status
- richer manager recommendation payloads with squad strength and depth scoring
- manager trade history now exposes settlement references
- manager-aware tactical shaping in the synthetic team factory
- match summaries now include win/draw/loss probabilities, expected goals, key highlights, and manager-influence notes
- expanded manager seed catalog and bumped catalog version

Known boundary:
- manager assignment influence in the match factory depends on `team_id` matching the manager assignment owner id path already used in the app.
- full emulator-level validation still needs local runtime testing.
