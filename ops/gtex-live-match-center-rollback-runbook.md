# GTEX 2D Match Center Rollback Runbook

## Purpose

This runbook gives operators a concrete rollback path for GTEX live 2D match center incidents.

It covers:

- verifying hosted 2D match center route health
- checking live match websocket readiness
- triaging the failing layer
- named rollback trigger conditions
- manual rollback steps
- post-rollback verification

## Scope

Use this runbook for staging or production incidents where any of these regress:

- hosted 2D match center or realtime routes
- live match provisioning
- websocket frame advancement
- broadcast match center rendering
- match center overlays, scorebug, commentary, or tactical pitch state

## Required Inputs

Before changing anything, capture:

- environment: `staging` or `production`
- backend base URL
- health URL
- current git SHA
- last known good git SHA
- failing `match_id`, if one exists
- verification account or access token used for protected match center checks, if required

## Canonical Verification Commands

### 1. Hosted route contract

```powershell
python ops/render/verify_match_center_routes.py --url "<health-or-api-url>"
```

This must pass before the environment is considered safe for canonical 2D match center traffic.

### 2. Hosted live match and websocket contract

```powershell
python tools/provision_gtex_live_match.py `
  --profile staging `
  --base-url "<api-base-url>" `
  --user-email "<viewer-email>" `
  --user-password "<viewer-password>" `
  --match-id "<backend-authored-live-match-id>" `
  --dry-run
```

For production, switch `--profile production`.
Do not use generated or local-only matches for staging or production verification.

This command is the primary post-deploy truth check for:

- match center access readiness
- payload hydration
- websocket frame advancement

### 3. Quarantined runtime validation

```powershell
powershell -File tools/run_gtex_windows_production_build.ps1
```

Optional session capture:

```powershell
powershell -File tools/capture_gtex_player_session.ps1 `
  -ExePath "C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\Gtex_Test_Migration\Builds\WindowsProduction\GTEXMatch.exe" `
  -OutputDir "C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\p6_rollback_validation"
```

Use the capture step only when an explicitly quarantined runtime is under investigation. It is not a production match center gate.

## Rollback Trigger Conditions

Rollback is required when any named trigger below is confirmed.

### Trigger R1: Health gate regression

- `/health` does not return `status=ok`
- required checks (`api`, `database`, `redis`) do not return `ok`

### Trigger R2: Match center route contract regression

- `verify_match_center_routes.py` fails
- canonical 2D match center or realtime gateway endpoints are missing or malformed

### Trigger R3: Live provisioning regression

- `tools/provision_gtex_live_match.py` fails to provision or refresh live access
- websocket verification does not advance to a new frame

### Trigger R4: Match center rendering regression

- scorebug, timeline, or tactical pitch fails to hydrate from backend state
- commentary or event feed stops reconciling over websocket
- overlay modes show unavailable data without a blocked/degraded state
- mobile/tablet layouts block core match actions

### Trigger R5: Auth or reconnect regression

- token refresh breaks the live lane
- reconnect repeatedly degrades or drops playback
- terminal-match handling leaves the player stuck in a bad session state

## Incident Triage Sequence

1. Freeze further deploys for the affected environment.
2. Record the current git SHA and the last known good SHA.
3. Run hosted route verification.
4. Run hosted provisioning verification.
5. If both hosted checks pass, move to the shipped-player validation lane.
6. Preserve evidence before rollback:
   - failing command output
   - health payload
   - match id
   - backend log excerpt
   - player log excerpt
   - screenshots or capture folder if player behavior regressed

## Layer Diagnosis

### Backend contract failure

Symptoms:

- health gate fails
- match viewer route verification fails
- gateway provisioning never issues access

Action:

- rollback backend services first

### Live runtime data failure

Symptoms:

- gateway access issues succeed
- websocket bridge fails
- provisioning returns stale or incomplete payloads

Action:

- rollback backend services first
- keep the current player build only if local player validation remains healthy against the restored backend

### Shipped-player-only failure

Symptoms:

- hosted route verification passes
- hosted provisioning passes
- local or distributed player still shows motion, camera, or overlay regressions

Action:

- rollback the shipped player bundle to the last known good release package
- keep backend rollback separate unless backend checks also fail

## Manual Rollback Procedure

### Preferred path: Render service rollback

Use this when Render exposes the previous healthy deploy for each affected service.

1. Identify the affected service set in this order:
   - API
   - OUTBOX
   - SIMULATION
   - PROJECTIONS
   - WEB
2. In Render, select the last healthy deploy for each affected service.
3. Roll back services in dependency order:
   - API first if the route contract is broken
   - worker services next if projection or simulation failures caused the regression
   - WEB last if the issue includes frontend shell regressions
4. Wait for the rolled-back services to become healthy.

### Fallback path: Repository-driven rollback

Use this when Render rollback is unavailable or cannot restore the known good state.

1. Revert `main` to the last known good SHA.
2. Re-dispatch the production deploy workflow from the reverted `main`.
3. Confirm the deploy uses the restored revision before reopening traffic.

### Player bundle rollback

Use this when the hosted API is healthy but the shipped player is not.

1. Restore the last known good GTEX production player package.
2. Re-run the local capture flow against the restored player.
3. Keep the restored player active until a new candidate passes the full session validation lane.

## Post-Rollback Verification

A rollback is not complete until all of these pass:

1. `verify_match_center_routes.py` passes.
2. `tools/provision_gtex_live_match.py --dry-run` passes for the affected environment.
3. `/health` is healthy again.
4. If match center rendering was involved, the restored build:
   - shows backend-derived score, clock, and event state
   - renders the 2D pitch without local simulation
   - marks missing overlays as blocked or degraded
   - keeps commentary and websocket status visible
5. Incident notes include:
   - restored SHA or Render deploy id
   - verification timestamp
   - operator name
   - remaining follow-up items

## Operator Handoff Checklist

- failing SHA recorded
- restored SHA or deploy id recorded
- match center route verification attached
- provisioning verification attached
- player capture attached if runtime rollback was needed
- follow-up owner assigned for the root-cause fix

## Notes

- `ops/render/deploy.py` currently logs that automatic rollback is not available in hook-only mode and is not otherwise configured in the workflow, so operators must treat rollback as a manual runbook step.
- Do not mark the incident resolved only because health recovered. Match center route verification and live provisioning must both pass again.
