# GTEX P6-09 Render and Content Signoff

## Scope

This document captures the signoff checklist for `P6-09`:
- desktop render readiness
- mobile render readiness
- kits, materials, shaders, stadiums, and addressables
- current-engine live playback content stability

This is the content/readiness signoff, not the gameplay logic proof.

## Required Targets

Desktop:
- Windows production player

Mobile:
- Android runtime path used by GTEX validation

## Required Checks

### Visual correctness
- player kits render correctly
- stadium imports render correctly
- pitch materials render correctly
- no black strip / camera occluder appears in broadcast view
- scoreboard, clock, and overlays are readable
- no obviously broken shaders, pink materials, or missing meshes

### Runtime content stability
- addressables load successfully
- no content-driven exceptions in player logs
- camera presets remain usable
- crowd / atmosphere content does not regress the live lane

### Match playback readiness
- desktop live playback shows moving players and moving ball
- mobile live playback shows moving players and moving ball
- no critical kit / stadium / shader regression remains open

## Evidence To Attach

Desktop:
- at least one kickoff screenshot
- one mid-session screenshot
- one late-session or fulltime screenshot
- player log excerpt

Mobile:
- kickoff capture
- mid-session capture
- late-session or fulltime capture
- device/runtime log excerpt

## Useful Existing Inputs

Desktop full-session evidence:
- [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\docs\GTEX_P6_03_FULL_SESSION_PLAYBACK_VALIDATION.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/docs/GTEX_P6_03_FULL_SESSION_PLAYBACK_VALIDATION.md>)

Release-path evidence:
- [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\docs\GTEX_P6_04_RELEASE_PATH_AUDIT.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/docs/GTEX_P6_04_RELEASE_PATH_AUDIT.md>)

## Current Status

Current status: `IN PROGRESS`

Repo-side completion:
- desktop validation lanes already exist
- the black-strip occluder fix and release-path guardrails are in the repo

Desktop evidence now available:
- production-path kickoff-to-15-minute capture set:
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\capture\gtex_production_soak_t0015s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/capture/gtex_production_soak_t0015s.png>)
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\capture\gtex_production_soak_t0300s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/capture/gtex_production_soak_t0300s.png>)
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\capture\gtex_production_soak_t0600s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/capture/gtex_production_soak_t0600s.png>)
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\capture\gtex_production_soak_t0900s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/capture/gtex_production_soak_t0900s.png>)
- supporting runtime trace:
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\capture\gtex_production_soak.runtime.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/capture/gtex_production_soak.runtime.log>)
- supporting structured summary:
  - [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_production_soak\soak_summary.json](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_production_soak/soak_summary.json>)

What is still required to pass:
- collect the cross-device screenshot and log set
- explicitly review mobile runtime output
- record a signoff note once desktop and mobile both pass
