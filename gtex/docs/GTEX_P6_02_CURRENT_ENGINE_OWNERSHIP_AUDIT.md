# GTEX P6-02 Current-Engine Ownership Audit

## Scope

This audit covers the `P6-02` gate:
- prove the current-engine path remains the default shipped runtime
- confirm controller-boundary ownership is opt-in only
- identify GTEX-owned files that still reach directly into legacy engine ownership classes

Audit date:
- `2026-04-17`

Audited areas:
- `Gtex_Test_Migration/Assets/Code/GTEX/Core/`
- `Gtex_Test_Migration/Assets/Code/GTEX/`
- `Gtex_Test_Migration/Assets/Code/GTEX/Engine/`

## Verdict

Current status:
- default ownership path remains `LegacyBootstrap`
- controller-boundary ownership remains opt-in only through `GTEX_ENGINE_OWNERSHIP_MODE`
- live GTEX bootstrap already routes through GTEX-owned adapters for `MatchEngineLoader`, `MatchManager`, and camera control
- `GtexStadiumAtmosphere` now listens through `GtexMatchController.EventStream` and `LiveStateObserved` instead of subscribing directly to legacy runtime events
- live-state fanout now goes through `GtexMatchController.PublishLiveState(...)`
- one direct legacy-owner reach-through in GTEX-owned code was removed during this pass

Overall recommendation:
- `P6-02` can be treated as passed at the code level
- remaining direct legacy access is now confined to intentional adapter internals, the centralized controller relay, and local-simulation UI bridging

## Findings

### 1. Default shipped ownership is still legacy bootstrap

`GtexMatchController` defines two ownership modes:
- `LegacyBootstrap`
- `GtexControllerBoundary`

Code references:
- [GtexMatchController.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexMatchController.cs:7>)
- [GtexMatchController.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexMatchController.cs:88>)

Key behavior:
- `ResolveOwnershipMode()` falls back to `LegacyBootstrap` by default when the environment variable is missing or unrecognized
- `TryAutoStart(...)` uses `LegacyTryAutoStart(...)` whenever the mode resolves to `LegacyBootstrap`

This means the shipped path is still the current engine unless an explicit environment override selects controller-boundary mode.

### 2. Runtime bootstrap still flows through GTEX-owned controller entrypoints

`GtexRuntimeBootstrap` does not start `MatchManager` or `MatchEngineLoader` directly. It delegates startup to `GtexMatchController`.

Code references:
- [GtexRuntimeBootstrap.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Core/GtexRuntimeBootstrap.cs:30>)
- [GtexRuntimeBootstrap.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Core/GtexRuntimeBootstrap.cs:31>)

This is consistent with the seam-layer intent for `P6`.

### 3. Live playback bootstrap is already seam-based at the critical handoff points

Inside `GtexMatchRuntime`, the runtime no longer starts the legacy loader and manager directly at the live bootstrap boundary. It goes through:
- `GtexMatchController.MatchEngineLoaderAdapter`
- `GtexMatchController.MatchManagerAdapter`
- `GtexMatchController.CameraAdapter`

Code references:
- [GtexMatchRuntime.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs:231>)
- [GtexMatchRuntime.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs:241>)
- [GtexMatchRuntime.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs:244>)
- [GtexMatchRuntime.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs:251>)
- [GtexMatchRuntime.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs:264>)

This is the strongest code-level evidence that the current-engine path remains the owner while GTEX integrates through seams.

### 4. One direct GTEX-to-legacy owner read was removed in this pass

Before this pass, `GtexStadiumAtmosphere` resolved field dimensions by reading `MatchManager.Current.fieldEndX` and `fieldEndY` directly.

That has now been changed to use:
- `GtexMatchController.MatchManagerAdapter.FieldSize`

Code reference:
- [GtexStadiumAtmosphere.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexStadiumAtmosphere.cs:928>)

This reduces fresh direct coupling in GTEX-owned runtime code.

### 5. Legacy whistle and final-match signals now cross the seam in one place

`GtexStadiumAtmosphere` no longer subscribes directly to `EventManager`. Legacy whistle events are now subscribed once inside `GtexMatchController.LegacyEngineEventRelay` and republished as `GtexMatchEvent` instances through the controller-owned event stream.

Code references:
- [GtexMatchController.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexMatchController.cs:62>)
- [GtexMatchController.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexMatchController.cs:470>)
- [GtexStadiumAtmosphere.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexStadiumAtmosphere.cs:75>)

Assessment:
- this keeps legacy event subscriptions centralized instead of scattering them across GTEX-owned runtime classes
- this is acceptable for `P6` because current-engine ownership remains intact and new GTEX runtime code consumes controller-owned signals

### 6. Live-state fanout now uses a GTEX-owned signal instead of a legacy event type

`GtexMatchRuntime` no longer triggers a direct `EventManager` event to broadcast live state. It now calls `GtexMatchController.PublishLiveState(...)`, and consumers subscribe through `GtexMatchController.LiveStateObserved`.

Code references:
- [GtexMatchRuntime.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs:865>)
- [GtexMatchController.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexMatchController.cs:110>)
- [GtexLiveStateSignal.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexLiveStateSignal.cs:1>)
- [GtexStadiumAtmosphere.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexStadiumAtmosphere.cs:76>)

Assessment:
- this removes another direct GTEX-owned dependency on a legacy event surface from the live runtime path
- the live path now crosses the seam through controller-owned contracts for both event replay and live-state observation

## Residual Risks

### Residual 1. Adapter internals still wrap the legacy owners directly by design

The seam layer is intentionally thin. The adapters still call the legacy owners directly internally.

Examples:
- [GtexLegacyMatchManagerAdapter.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexLegacyMatchManagerAdapter.cs:11>)
- [GtexLegacyMatchEngineLoaderAdapter.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexLegacyMatchEngineLoaderAdapter.cs:8>)

Assessment:
- this is acceptable for `P6`
- the point of `P6` is not replacing these owners
- the requirement is that new GTEX code talks through seams instead of adding fresh scattered direct calls

### Residual 2. `GtexSimUiBridge` still broadcasts legacy UI events for local simulation

The remaining non-adapter `EventManager` usage under `Assets/Code/GTEX/` is in `Simulation/GtexSimUiBridge.cs`, where local simulation optionally rebroadcasts legacy UI signals such as scoreboard, infoboard, and match-complete events.

Examples:
- [GtexSimUiBridge.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Simulation/GtexSimUiBridge.cs:103>)
- [GtexSimUiBridge.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Simulation/GtexSimUiBridge.cs:148>)

Assessment:
- this is outside the critical live current-engine path audited for `P6-02`
- it does not move shipped runtime ownership away from the current engine
- it should stay visible as future seam-cleanup work for the local-simulation UI lane

## Files Changed In This Audit Pass

- [GtexStadiumAtmosphere.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexStadiumAtmosphere.cs:1>)
- [GtexMatchController.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexMatchController.cs:1>)
- [GtexMatchRuntime.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs:1>)
- [GtexLiveStateSignal.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexLiveStateSignal.cs:1>)
- [ScoreboardPanel.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/UI/Panels/ScoreboardPanel.cs:1>)

Change made:
- replaced direct field-size reads from `MatchManager.Current` with `GtexMatchController.MatchManagerAdapter.FieldSize`
- moved stadium whistle/final and live-state observation onto controller-owned signals
- centralized legacy whistle relay inside `GtexMatchController`
- replaced the direct live-state event broadcast with `GtexMatchController.PublishLiveState(...)`
- updated the live scoreboard panel to consume `GtexMatchController.LiveStateObserved` after removing the old event type

## Verification

- `2026-04-17`: Unity Windows batch build succeeded after the seam and event-surface changes
- build log: `tmp/gtex_test_migration_windows_build_p602.log`
- output: `Gtex_Test_Migration/Builds/Windows/GTEXMatch.exe`

## Conclusion

`P6-02` is in good shape on the code path that matters most:
- default ownership is still legacy bootstrap
- controller-boundary mode is opt-in only
- the live runtime handoff points already use GTEX-owned seams
- `GtexStadiumAtmosphere` now consumes controller-owned signals instead of direct legacy runtime events
- one additional direct legacy-owner read was removed during this pass

Remaining caution:
- adapter internals still wrap legacy owners by design
- local-simulation UI bridging still has optional legacy event broadcasts outside the live current-engine path
