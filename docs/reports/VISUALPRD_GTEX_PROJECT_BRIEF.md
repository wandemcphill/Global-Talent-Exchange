# GTEX Project Brief For VisualPRD

## Project Name
GTEX 3D Football Engine

## One-Line Summary
Build and harden a production-ready 3D football match runtime in Unity by shipping GTEX on top of the existing engine first, while keeping engine replacement explicitly deferred until evidence justifies it.

## Product Context
GTEX already exists inside a live codebase. This is not a greenfield game. The current Unity runtime, live playback path, and build pipeline must be preserved and stabilized before any architectural replacement work is considered.

The active Unity project is:
- `C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\Gtex_Test_Migration`

Current engine ownership already lives in:
- `Assets/Code/GTEX/GtexMatchRuntime.cs`
- `Assets/Code/MatchEngine/MatchEngineLoader.cs`
- `Assets/Code/MatchEngine/MatchManager.cs`
- `Assets/Code/Events/EventManager.cs`

GTEX seam/adaptor work belongs under:
- `Assets/Code/GTEX/Engine/`

## Current Delivery Target
Target the current implementation phase only:
- `P6` is `READY`
- `P7` and `P8` are blocked and must not be started

This means the project goal is:
- harden GTEX integration on top of the current engine
- keep the current engine as the default shipped runtime
- improve observability, reliability, and reversibility
- ship stable live playback and local simulation on the current path

Do not frame this as:
- a full engine rewrite
- replacing `MatchManager`
- replacing `MatchEngineLoader`
- replacing `EventManager`
- moving runtime ownership away from the legacy engine by default

## Core Product Goal
Ship a stable GTEX 3D football experience that can:
- run reliable Unity Windows builds in batchmode
- support a full 15-minute session validation / soak run
- play hosted live matches with moving players, moving ball, stable camera, and no debug overlays
- keep local simulation and live playback both working on top of the current engine
- provide enough seams and telemetry to reduce future coupling without destabilizing the shipped runtime

## Primary Users
1. Match viewers
- Watch live or generated football matches in a polished 3D runtime
- See stable camera behavior, score state, ball motion, and player motion

2. Operators / release owners
- Build Windows players reliably in CI and batchmode
- verify deploy health, live-motion correctness, provisioning, transport/auth health, and rollback readiness

3. Developers
- add GTEX features through GTEX-owned interfaces and adapters
- avoid new direct dependencies on legacy engine internals

## Core Experience Requirements
1. Live playback runtime
- GTEX live playback is bootstrapped by `GtexMatchRuntime`
- Live state arrives through HTTP polling and WebSocket updates
- Runtime binds live data to existing Unity match actors
- Camera focuses correctly and playback remains readable

2. Current-engine ownership remains intact
- `MatchEngineLoader` remains the scene/bootstrap owner
- `MatchManager` remains lifecycle and clock owner
- GTEX integration talks through adapters and interfaces where possible

3. Simulation compatibility
- local simulation mode remains opt-in and must not break live mode
- any new GTEX orchestration must be reversible

4. Production build reliability
- Windows batch builds must remain stable
- build logs must be actionable
- CI gating should protect `main`

5. Production operations
- hosted live match generation must be reliable
- staging must pass soak coverage
- production must have actionable observability and rollback-ready workflows

## Technical Stack
- Unity `6000.3.12f1`
- C# runtime
- existing Unity 3D football engine
- GTEX seam/adaptor layer in `Assets/Code/GTEX/Engine/`
- backend live match services feeding state to Unity
- WebSocket + polling fallback for live playback transport

## Existing Reality To Respect
- `GtexMatchRuntime` already handles live playback bootstrap, transport, and actor binding
- `MatchEngineLoader` already loads UI, stadium, match prefab, and ball, then starts the existing engine
- `MatchManager` already owns the core match lifecycle and supports an external playback mode
- seam files already exist under `Assets/Code/GTEX/Engine/`

VisualPRD should build from this reality, not replace it.

## Constraints
- Never break batchmode builds
- Prioritize performance over realism
- Keep systems modular
- Avoid heavy assets unless necessary
- Keep existing gameplay ownership intact
- Make changes additive and reversible
- Preserve editor play mode and Windows batch builds
- Do not start blocked phases early

## Non-Negotiable Rules
- Do not rewrite the whole engine
- Do not replace `MatchManager`, `MatchEngineLoader`, or `EventManager`
- Do not change player AI, referee logic, or animation systems in one sweep
- Do not move shipped runtime ownership away from the current engine in this phase
- Do not introduce fresh direct coupling from GTEX features into scattered legacy classes

## What VisualPRD Should Plan
Create a plan centered on P6: current-engine integration hardening.

Required workstreams:
1. Engine seam hardening
- define and use GTEX-owned contracts such as controller, state, phase, command, executor, clock source, and event stream
- keep legacy adapters thin and observable

2. Runtime integration cleanup
- route new GTEX logic through the seam layer
- keep legacy bootstrap as default
- make controller-boundary orchestration opt-in only

3. Live runtime reliability
- improve transport resilience
- handle stale transport, auth refresh, reconnects, and terminal match selection safely
- validate live motion, ball state, and camera behavior after deploy

4. Build and CI gating
- keep Unity Windows batch build green
- gate deploys on backend and live-motion checks
- preserve actionable logs and traces

5. Content and render validation
- remove debug-only overlays
- validate shaders, materials, kits, stadium imports, and addressables
- confirm desktop and mobile runtime behavior

6. Soak, monitoring, and ops
- add or strengthen soak coverage for a full session
- monitor websocket churn, stale state, auth refresh failures, and match-generation failures
- define provisioning, verification, incident, and rollback workflows

## Success Criteria
- GTEX ships on the current engine without ownership regressions
- Windows batch build is stable
- Unity live playback completes a full session with moving players, moving ball, stable camera, and no debug overlays
- hosted live match generation is reliable after deploy
- new GTEX work plugs into GTEX-owned interfaces/adapters instead of adding fresh legacy coupling
- staging passes a 15-minute soak run
- production has actionable observability and rollback-ready procedures

## Out Of Scope For This Brief
- full engine replacement
- speculative architecture rewrites
- replacing the current engine because a seam layer exists
- heavy realism upgrades or expensive new assets
- full commentary, VAR, or advanced broadcast systems
- broad native-runtime expansion outside the current-engine shipping path

## Important Files
- `Assets/Code/GTEX/GtexMatchRuntime.cs`
- `Assets/Code/Editor/GtexBuildTools.cs`
- `Assets/Code/MatchEngine/MatchEngineLoader.cs`
- `Assets/Code/MatchEngine/MatchManager.cs`
- `GTEX_TASKS.md`
- `GTEX_PHASED_PROMPTS.md`

## Build Command
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.3.12f1\Editor\Unity.exe' `
  -batchmode -quit -nographics `
  -buildTarget StandaloneWindows64 `
  -projectPath 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\Gtex_Test_Migration' `
  -executeMethod FStudio.GTEX.Editor.GtexBuildTools.BuildWindows64FromCommandLine `
  -logFile 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tmp\gtex_test_migration_windows_build.log'
```

## Instruction To VisualPRD
Generate a phased implementation plan and PRD for GTEX that assumes the current engine remains the default shipping path. Focus on integration hardening, live runtime reliability, build stability, seam-based architecture, observability, and production readiness. Do not propose engine replacement unless it is explicitly framed as a later, blocked evidence phase.
