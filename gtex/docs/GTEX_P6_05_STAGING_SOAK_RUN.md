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

## Decision Note

Decision date:
- `2026-04-22`

Decision:
- the technical lead accepted the deployed production-path soak evidence as the `P6-05` equivalent for this phase because the current GTEX deployment topology does not expose a separate staging API host

Reason:
- only the production Render API lane was available for external verification during this pass
- the production-path run exercised the highest-fidelity deployed environment actually reachable from this workspace
- the run preserved a 15-minute screenshot set plus runtime evidence on the shipped player

Follow-up staging probe:
- a staging candidate host was later supplied as `https://gtex-api-69rq.onrender.com`
- repeated staging verification probes on `2026-04-22` did not produce a healthy API surface
- saved probe summary: [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_staging_host_probe_20260422.json](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_staging_host_probe_20260422.json>)
- this confirms that the accepted production-path soak evidence remains the only successful deployed long-run proof available during the current gate window

## Current Status

Current status: `PASSED`

Repo-side completion:
- committed soak runner exists
- committed capture/provision helpers exist
- summary/log artifact format is now defined

Accepted executed evidence on the production lane:
- the same soak runner was exercised against `https://gtex-api.onrender.com` with a production profile
- the shipped Windows player remained alive through the full `900s` capture window and produced saved checkpoints at:
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\capture\gtex_production_soak_t0015s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/capture/gtex_production_soak_t0015s.png>)
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\capture\gtex_production_soak_t0300s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/capture/gtex_production_soak_t0300s.png>)
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\capture\gtex_production_soak_t0600s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/capture/gtex_production_soak_t0600s.png>)
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\capture\gtex_production_soak_t0900s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/capture/gtex_production_soak_t0900s.png>)
- the runtime trace for that production-path run is saved at [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\capture\gtex_production_soak.runtime.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/capture/gtex_production_soak.runtime.log>)
- a salvaged structured summary for that run is saved at [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\soak_summary.json](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/soak_summary.json>)
- this evidence is now accepted as the `P6-05` pass artifact for the current phase gate

What remains useful but is no longer required for `P6-05`:
- add a dedicated staging soak if a separate staging host is introduced later
- rerun the soak after major live transport/runtime changes
