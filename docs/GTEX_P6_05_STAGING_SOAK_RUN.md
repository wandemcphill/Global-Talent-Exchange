# GTEX P6-05 Staging Soak Run

## Scope

This document defines the committed soak lane for `P6-05`:
- 15-minute continuous runtime on the shipped Windows player
- deployed backend / hosted live lane
- retained screenshots, runtime trace, player log, and summary artifact

This is not a startup check. It is the long-run stability lane for the current-engine shipped path.

## Committed Soak Assets

Soak runner:
- [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_staging_soak.ps1](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_staging_soak.ps1>)

Supporting capture helper:
- [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\capture_gtex_player_session.ps1](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/capture_gtex_player_session.ps1>)

Provisioning engine:
- [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\provision_gtex_live_match.py](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/provision_gtex_live_match.py>)

## What The Soak Runner Does

The soak runner:
1. provisions a real hosted live session for the target environment
2. writes the runtime bootstrap for the shipped Windows player
3. launches the production player
4. captures screenshots across the run
5. leaves the player active for the target soak duration
6. preserves the player log, runtime trace, and a summary JSON artifact

## How To Run

### 15-minute staging soak

```powershell
& 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_staging_soak.ps1' `
  -Profile staging `
  -BaseUrl 'https://<staging-api-host>' `
  -UserEmail '<viewer-email>' `
  -UserPassword '<viewer-password>' `
  -AllowMatchGeneration `
  -DurationMinutes 15
```

If you already have a bearer token, use `-UserAccessToken` instead of email/password.

## Saved Artifacts

Default output root:
- `tmp\gtex_staging_soak`

Expected artifacts:
- `provision_summary.json`
- `soak_summary.json`
- screenshot capture folder
- player log
- runtime trace
- capture metadata

## Pass Criteria

The soak run passes only if all of the following are true:
- the player survives the full target duration
- movement remains visible in the runtime trace
- ball movement remains visible in the runtime trace
- no runtime error markers appear
- no player exceptions appear
- screenshot capture succeeds across the run

## Current Status

Current status: `IN PROGRESS`

Repo-side completion:
- committed soak runner exists
- committed capture/provision helpers exist
- summary/log artifact format is now defined

What is still required to pass:
- execute the soak against staging
- retain the produced summary/log/screenshot set
- review the output for unresolved high-severity defects
