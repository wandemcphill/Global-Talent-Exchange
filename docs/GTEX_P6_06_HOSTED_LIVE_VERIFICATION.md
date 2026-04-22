# GTEX P6-06 Hosted Live Verification

## Scope

This document defines the committed post-deploy verification lane for `P6-06`:
- match provisioning against a deployed backend
- Unity live access issuance
- refresh-token issuance
- live route hydration
- websocket bridge verification

This is the post-deploy truth check for the hosted GTEX live lane.

## Committed Verification Assets

Hosted verification wrapper:
- [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_hosted_live_verification.ps1](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_hosted_live_verification.ps1>)

Provisioning engine used by the wrapper:
- [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\provision_gtex_live_match.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/provision_gtex_live_match.py>)

## What The Wrapper Verifies

For the target deployed environment, the wrapper verifies:
- authentication or supplied bearer access works
- a target match can be selected or generated
- `/api/matches/{match_id}/unity-access` returns access and refresh tokens
- `/match/{match_id}/live` returns a Unity live payload for the same match
- `/api/v1/ws/match/{match_id}?format=unity` advances to a later payload frame unless websocket verification is explicitly skipped

The wrapper runs in `--dry-run` mode for Unity config/bootstrap writes, so it does not mutate the local shipped-player config during hosted verification.

## How To Run

### Staging

```powershell
& 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_hosted_live_verification.ps1' `
  -Profile staging `
  -BaseUrl 'https://<staging-api-host>' `
  -UserEmail '<viewer-email>' `
  -UserPassword '<viewer-password>' `
  -AllowMatchGeneration
```

### Production

```powershell
& 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_hosted_live_verification.ps1' `
  -Profile production `
  -BaseUrl 'https://<production-api-host>' `
  -UserEmail '<viewer-email>' `
  -UserPassword '<viewer-password>' `
  -AllowMatchGeneration
```

If you already have a backend bearer token, use `-UserAccessToken` instead of email/password.

## Artifacts

Default output summary:
- staging: `tmp\gtex_staging_hosted_live_verification_summary.json`
- production: `tmp\gtex_production_hosted_live_verification_summary.json`

Summary fields include:
- selected profile
- base URL
- match id
- Unity access issue summary
- live route frame summary
- websocket advancement summary

## Pass Criteria

This item passes only when a deployed environment shows:
- successful Unity access issuance
- successful refresh issuance
- successful live route hydration
- successful websocket frame advancement
- a saved summary artifact tied to the deployed environment and execution date

## Executed Evidence

Execution date:
- `2026-04-22`

Executed target:
- production API at `https://gtex-api.onrender.com`

Runner command:

```powershell
& 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_hosted_live_verification.ps1' `
  -Profile production `
  -BaseUrl 'https://gtex-api.onrender.com' `
  -UserEmail '<provided verification account>' `
  -UserPassword '<provided verification password>' `
  -AllowMatchGeneration
```

Observed result:
- hosted verification returned `verification_passed: true`
- a generated live match was provisioned successfully
- Unity live access and refresh tokens were issued
- `/match/{match_id}/live` returned a live payload for the same match
- `/api/v1/ws/match/{match_id}?format=unity` advanced from one frame to a later frame over websocket

Saved artifact:
- [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_hosted_live_verification_summary.json](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_hosted_live_verification_summary.json>)

Supporting runtime proof on the same deployed lane:
- the shipped Windows player stayed connected against the same production API long enough to capture 15-minute checkpoints at `15s`, `300s`, `600s`, and `900s` in [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\capture](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/capture>)

## Current Status

Current status: `PASSED`

Repo-side completion:
- committed hosted verification wrapper exists
- provisioning tool already verifies the required live route and websocket seams

What this closes:
- a deployed environment has now been exercised successfully
- Unity live access issuance, refresh issuance, live route hydration, and websocket advancement are all proven on the hosted lane

Still useful follow-up:
- repeat the same verification against staging when a staging endpoint is available
