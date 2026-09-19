# GTEX Task Gates

This file is the execution order for GTEX implementation work.

Rules:
- Only implement phases marked `READY`
- Do not start phases marked `BLOCKED`
- A blocked phase becomes ready only after its gate is satisfied
- Preserve build stability before expanding architecture

## Current Target

- `P5` is complete
- `P6` remains `READY` for current-engine production hardening
- `P6V` is `READY` for the controlled Original Visual Runtime Pivot
- `P6V` supersedes the old P6/P7/P8 current-engine-only restriction for this isolated visual-runtime pivot only
- The pivot is not a rewrite: GTEX remains the match authority and the original simulator owns football visuals in a separate scene
- Batchmode build stability and the current `Gtex_MainScene` path remain required acceptance gates
- `P7-FE` is `READY` for the independent Flutter frontend product-parity and design-system initiative
- `P7-FEV` is `BLOCKED` until the P7-FE verification gate can be satisfied
- P7-FE/P7-FEV do not change the Unity P6/P6V sequence, scope, or completion status

## Phases

### P0 Baseline
Status: `COMPLETE`

Scope:
- Confirm Unity project location and version
- Confirm existing engine ownership
- Add root project guidance

### P1 Build Hardening
Status: `COMPLETE`

Source prompt:
- `Prompt A` in `GTEX_PHASED_PROMPTS.md`

Scope:
- Harden `GtexBuildTools.cs`
- Improve scene validation and build logging
- Add companion build trace file
- Safely harden `GtexMatchRuntime.cs` startup for batchmode/headless contexts

Exit gate:
- Project compiles
- Windows batch build entrypoint provides actionable logs
- No new batchmode startup regressions are introduced
- Existing GTEX gameplay flow is unchanged

### P2 Windows Build Verification
Status: `COMPLETE`

Scope:
- Run the Windows batch build
- Use the improved logs to identify build failures
- Fix only concrete build blockers

Exit gate:
- Windows batch build completes successfully, or remaining failures are isolated to content-heavy late-stage packaging with clear logs

### P3 GTEX Simulation Core
Status: `COMPLETE`

Source prompt:
- `Prompt B` in `GTEX_PHASED_PROMPTS.md`

Scope:
- Add pure C# GTEX simulation core under `Assets/Code/GTEX/Simulation/`
- Add `GtexSimState`, `GtexSimClock`, `GtexSimEngine`, and `GtexSimEventSystem`

Exit gate:
- Simulation core compiles
- No changes to existing live playback flow

### P4 GTEX Simulation Adapters
Status: `COMPLETE`

Scope:
- Add `GtexSimRenderer`
- Add `GtexSimCrowdController`
- Keep them opt-in and logging-only

Exit gate:
- Adapters compile and react to simulation events
- No batchmode regressions

### P5 GTEX Bridge Work
Status: `COMPLETE`

Scope:
- Introduce a clean mode switch between live playback and local simulation
- Bridge simulation outputs into existing UI or GTEX systems carefully

Exit gate:
- Local sim mode is explicit, stable, and does not break live mode

### P6 GTEX Current-Engine Integration Hardening
Status: `READY`

Source prompt:
- `Prompt C` in `GTEX_PHASED_PROMPTS.md`

Execution addendum:
- `GTEX_P6_PRODUCTION_GAP_BACKLOG.md`

Scope:
- Keep `MatchManager`, `MatchEngineLoader`, and the current 3D engine as the default shipped runtime owners
- Use `Assets/Code/GTEX/Engine/` for additive seams, adapters, parity logging, and observability
- Route new GTEX integration work through GTEX-owned interfaces instead of adding fresh direct calls into legacy engine classes
- Keep legacy/current-engine bootstrap as the default path, with controller ownership remaining opt-in and reversible
- Stabilize live playback, local simulation, and Unity build behavior on top of the current engine
- Stabilize hosted live match generation and deployed Unity playback on the current engine path
- Remove debug overlays and complete render/content validation for desktop and mobile
- Add CI gating for Unity Windows batch builds and targeted backend live-motion tests
- Add soak testing, transport/auth monitoring, provisioning verification, and rollback-ready operator workflows

Exit gate:
- GTEX ships on top of the current engine without introducing ownership regressions
- New GTEX work plugs into GTEX-owned interfaces or adapters instead of adding fresh direct legacy coupling
- Legacy/current-engine bootstrap remains the default and is stable for live playback and local simulation
- Windows batch build remains stable
- Hosted live match generation is reliable and verified after deploy
- Unity live playback runs a full session with moving players, moving ball, stable camera, and no debug overlays
- `main` is gated by backend checks and Unity Windows batch build verification before deploy
- Staging passes a 15-minute soak run and production has actionable observability plus rollback-ready procedures

### P6V Original Visual Runtime Pivot
Status: `READY`

Source prompt:
- `Prompt C2` in `GTEX_PHASED_PROMPTS.md`

Supersedence:
- This phase explicitly supersedes the old P6/P7/P8 current-engine-only restriction for the controlled visual-runtime pivot.
- The supersedence is limited to a separate original-visual scene and bridge path.
- It does not authorize deleting current GTEX systems or rewriting the existing shipped scene.

Scope:
- Create branch `feature/original-visual-runtime`
- Preserve all existing GTEX work and scenes
- Create `Assets/Scenes/GTEX_OriginalVisualRuntime.unity`
- Store/reference the clean original simulator package under `Assets/ThirdParty/OriginalFootballSimulator/`
- Do not import duplicate active `FStudio.MatchEngine` code from the original simulator package
- Add a runtime mode `OriginalVisualRuntime`, separate from live playback, local simulation, and external transform playback
- Add `Assets/Code/GTEX/VisualBridge/` as the only integration point between GTEX match authority and original simulator visuals
- Route backend/local-sim events into high-level football commands, not per-frame transform playback
- Keep `MatchManager.SetExternalPlayback(false)` in the original-visual scene so original simulator movement, ball, keeper, and camera systems win
- Keep `GtexScoreAuthority` as the single score source

Exit gate:
- Original-visual scene runs original simulator camera, player movement, ball control, pass, shot, dribble, and keeper behavior without GTEX backend
- Scripted command replay can execute kickoff, possession, carry, pass, through pass, cross, shot saved, goal, and reset kickoff
- Local GTEX simulation events can drive the visual bridge to half-time and full-time
- Live/backend playback uses visual commands only on this path
- `DrivePlayers` and `DriveBall` transform playback are inactive in `OriginalVisualRuntime`
- Current GTEX scenes remain intact and build-stable
- Windows batch build remains stable

### P7-FE GTEX Frontend Product Parity & Design System
Status: `READY`

Independence:
- This is independent Flutter frontend work and may proceed without changing Unity P6/P6V status, scope, or sequencing.
- GTEX remains a Flutter product. Visual experimentation must use the real Flutter component system and a Flutter-compatible Design Lab; do not introduce a separate React or Next frontend solely for prototyping.

Source of truth:
- `docs/audits/gtex-product-parity-ux-baseline.md`
- Current frontend, backend API contracts, and verified product behavior take precedence over stale audits or assumptions.

Scope:
- Establish a GTEX Flutter Design Lab that reuses and extends canonical production tokens and components.
- Deliver frontend/backend product parity, route and surface completeness, navigation discoverability, state completeness, responsive quality, a coherent GTEX visual language, reusable design-system primitives, browser-driven visual validation, Playwright/e2e coverage, visual regression coverage, and premium product presentation.
- Prioritize verified issues from the canonical baseline: the Match Viewer indefinite verification/loading stall (P0), mobile lineup/substitute overflow (P1), notification deep-linking (P1), technical route-gate presentation (P2), and competition discoverability/parity where a complete backend workflow genuinely exists (P2).
- For Match Viewer, use an authoritative replay only when it exists; otherwise show a truthful, recoverable unavailable state with a useful next action. Never fabricate gameplay.

Rules:
- Do not create fake or demo production workflows, fabricated gameplay, financial results, user balances, or backend capabilities.
- Do not weaken authorization, perform destructive frontend rewrites, make unnecessary backend rewrites, create a duplicate design system, or copy external football-game products.
- Preserve real backend business rules and expose capabilities only through complete, authorized workflows.
- Every completed surface must handle relevant loading, empty, error, success, disabled, locked, permission, pending, expired, and unavailable states without raw technical messaging or indefinite loaders.

Exit gate:
- P7-FE has implemented and documented the selected vertical slices with real backend integration, canonical Flutter components/tokens, responsive behavior, and no fabricated production functionality.
- Critical completed-scope P0/P1 workflows are traceable end-to-end and have no known dead controls.

### P7-FEV GTEX Frontend Visual & Browser Verification
Status: `BLOCKED`

Gate:
- P7-FE exit gate is satisfied for the surfaces under verification.

Scope:
- Exercise important routes, actions, and API interactions in a real browser.
- Verify loading, empty, error, success, locked, and permission states at desktop and mobile breakpoints.
- Maintain Playwright/e2e coverage, captured visual screenshots, and reviewed visual regressions for critical flows.

Exit gate:
- Important completed-scope routes and actions have been browser-verified on desktop and mobile.
- Playwright coverage and visual evidence exist for critical flows.
- No known critical dead buttons, unintentionally hidden major backend capabilities, or fake/demo production functionality remain within completed scope.

### P7 Evidence For Engine Replacement
Status: `BLOCKED`

Gate:
- `P6` exit gate satisfied

Source prompt:
- `Prompt D` in `GTEX_PHASED_PROMPTS.md`

Scope:
- Gather objective evidence on whether replacing any part of the current engine is justified
- Measure parity, stability, live-motion correctness, reconnection behavior, build/runtime complexity, and operating cost on the current engine path
- Add instrumentation and comparison hooks for controller-boundary experiments without making them the shipped default
- Produce an evidence pack that identifies what should stay, what should be wrapped, and what specific subsystem might be worth replacing

Exit gate:
- There is measured evidence for or against replacement, not just architectural preference
- Any proposed replacement target is specific, bounded, and backed by runtime/build data
- A replacement decision can be made explicitly with rollback and success metrics defined

### P8 Selective Engine Replacement
Status: `BLOCKED`

Gate:
- `P7` exit gate satisfied

Source prompt:
- `Prompt E` in `GTEX_PHASED_PROMPTS.md`

Scope:
- Replace only the specific legacy subsystem(s) justified by the evidence pack
- Keep replacement targeted, reversible, and measured
- Preserve the shipped current-engine path until the replacement path proves materially better
- Define success metrics and rollback metrics before any ownership transfer

Exit gate:
- Replacement delivers measurable benefit against the current-engine baseline
- Rollback remains available until the replacement path is proven in staging and production-like verification
- No build, live-runtime, or deploy regressions are introduced by the targeted replacement
