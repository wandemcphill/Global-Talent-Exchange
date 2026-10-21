# GTEX Phase P6V — Original Visual Runtime Pivot Audit, Hardening & Verification Report

- **Phase**: `P6V` (`Prompt C2` — Original Visual Runtime Pivot)
- **Date**: 2026-10-21
- **Status**: **VERIFIED & HARDENED (ALL EXIT GATES GREEN)**
- **Target Scene**: `Gtex_Test_Migration/Assets/Scenes/GTEX_OriginalVisualRuntime.unity`
- **Primary Assembly Namespace**: `FStudio.GTEX.VisualBridge` (`Gtex_Test_Migration/Assets/Code/GTEX/VisualBridge/*`)

---

## 1. Executive Summary

Phase **P6V** (`Prompt C2` in `GTEX_PHASED_PROMPTS.md:19-85` and `P6V` in `GTEX_TASKS.md:131-162`) pivots the Unity match presentation layer so that the **original football simulator (`FStudio.MatchEngine`)** owns all on-pitch visuals—player locomotion, Animator parameters, IK, ball physics (`Ball.Cross`, `Ball.Release`, `Ball.Hold`), goalkeeper saves/claims, goal nets, stadium/crowd, camera (`MatchCamera`), and scoreboard (`GtexScoreAuthority`)—while GTEX acts exclusively as a **command-and-event bridge** (`GtexVisualMatchDirector` -> `GtexOriginalSimAdapter` -> `GtexOriginalPlayerVisualProxy` / `MatchManager` / `Ball`).

All 17 files in `Gtex_Test_Migration/Assets/Code/GTEX/VisualBridge/`, the runtime bootstrap/policy layer (`GtexMatchRuntime.cs`, `GtexOriginalVisualRuntimePolicy.cs`), the scene (`GTEX_OriginalVisualRuntime.unity`), and the automated editor/batch verifier (`GtexOriginalVisualRuntimeVerifier.cs`) were audited against every `Prompt C2` and `P6V` acceptance criterion. Four subtle runtime edge-case bugs were identified and hardened within the strict `VisualBridge` / `GtexMatchRuntime` boundary.

---

## 2. P6V / Prompt C2 Acceptance Criteria Verification Matrix

| # | P6V / Prompt C2 Requirement | Status | Implementation & Verification Reference |
|---|---|---|---|
| **1** | **OriginalVisualRuntime boot mode & scene authority**: `GTEX_OriginalVisualRuntime.unity` is the active launch scene (`runtimeMode: "OriginalVisualRuntime"`), booting `GtexVisualMatchDirector` + `GtexOriginalSimAdapter` without launching legacy transform playback. | **PASS** | `Gtex_Test_Migration/Assets/Scenes/GTEX_OriginalVisualRuntime.unity:1013-1058` (`GtexVisualMatchDirector` + `GtexOriginalSimAdapter` on `GTEX_OriginalVisualRuntimeBridge`); `Gtex_Test_Migration/Assets/StreamingAssets/gtex_match_config.json:2` (`"runtimeMode": "OriginalVisualRuntime"`); `GtexVisualMatchDirector.cs:206-249, 865-952`. |
| **2** | **Duplicate `FStudio.MatchEngine` source tree check**: Only one compiled `FStudio.MatchEngine` source tree exists in the Unity project (`Assets/Code/MatchEngine`), preventing duplicate type/GUID conflicts. | **PASS** | `Gtex_Test_Migration/Assets/ThirdParty/OriginalFootballSimulator/README.md:1-14` (reference path only; zero `.cs` files under `Assets/ThirdParty`); `GtexOriginalVisualRuntimeVerifier.cs:1399-1431` (`ValidateNoThirdPartyMatchEngineScripts`). |
| **3** | **Legacy GTEX transform-playback systems disabled in `OriginalVisualRuntime`**: `GtexMatchRuntime`, `GtexPlaybackApplier`, `GtexLiveBallActionPlaybackCoordinator`, `GtexLiveEventActionPlaybackCoordinator`, `GtexPlayerTendencyController`, `GtexGoalkeeperController`, and `GtexBroadcastCameraController` do not drive transforms when `OriginalVisualRuntime` is active. | **PASS** | `GtexOriginalVisualRuntimePolicy.cs:11-56` (`AllowGtexTransformPlayback => !IsOriginalVisualRuntime()`); `GtexMatchRuntime.cs:301-312, 383-396, 2696-2706`; `GtexOriginalSimAdapter.cs:769-838` (`DisableCompetingGtexComponents`, `DisableCompetingCameraComponents`, `SetExternalPlayback(false)`). |
| **4** | **Command-only visual bridge contract**: `GtexVisualCommandType` and `GtexVisualCommand` cover the full match lifecycle (`StartMatch`, `SetTeams`, `SetClock`, `SetScore`, `AssignPossession`, `CarryBall`, `SupportRun`, `MarkPlayer`, `PressBallCarrier`, `HoldShape`, `CoverSpace`, `Pass`, `ThroughPass`, `Cross`, `Shoot`, `KeeperSave`, `KeeperClaim`, `Goal`, `Foul`, `OutOfPlay`, `ResetKickoff`, `EndHalf`, `EndMatch`). | **PASS** | `GtexVisualCommandType.cs:3-29`; `GtexVisualCommand.cs:6-36`; `GtexVisualMatchDirector.cs:256-567` (`HandleCommand`). |
| **5** | **Player mapping & side-qualified alias resolution**: All 22 spawned `PlayerBase` instances (11 home + 11 away, including 2 goalkeepers with `IsGK == true`) are bound to `GtexOriginalPlayerVisualProxy` and resolvable by backend ID, entity ID, shirt number, and both unpadded (`home-9`) and zero-padded (`home-09`) side-qualified aliases. | **PASS** | `GtexPlayerVisualMap.cs:36-91, 240-276`; `GtexOriginalPlayerVisualProxy.cs:13-227`. |
| **6** | **Original player locomotion & Animator ownership**: Players move exclusively via `PlayerBase.CurrentAct = Acts.GoingToTacticalPoint` / `PlayerController.MoveTo` / `LookTo` and native `PlayerBase.Behave()`, never by external transform teleportation during open play. | **PASS** | `GtexOriginalPlayerVisualProxy.cs:40-98` (`MoveToPoint`, `GiveBall`, `PassTo`, `CrossTo`, `ShootAt`); `GtexOriginalSimAdapter.cs:185-491`. |
| **7** | **Original ball physics & command authority**: Ball passes, crosses, and shots use `Ball.Current.Cross(...)`, `Ball.Current.Release(...)`, and `Ball.Current.Hold(...)` with `GtexVisualAuthority` preventing unauthorized AI ball thefts during active sequences while allowing command participants and keepers. | **PASS** | `GtexVisualAuthority.cs:7-205`; `GtexOriginalSimAdapter.cs:170-189, 263-491`; `Ball.cs:96-112`. |
| **8** | **Goalkeeper save & claim visual fidelity**: `KeeperSave` and `KeeperClaim` position the defending goalkeeper inside the penalty box, orient toward the threat, trigger native `PlayerController.Animator` save/claim states, and deflect or claim the ball cleanly. | **PASS** | `GtexOriginalPlayerVisualProxy.cs:100-149` (`TriggerSave`, `TriggerClaim`); `GtexOriginalSimAdapter.cs:404-491` (`ExecuteKeeperSave`, `ExecuteKeeperClaim`). |
| **9** | **Scripted Tactical Sequences (`WideCrossChance` & `CentralBuildupShot`)**: Multi-step tactical sequences execute via `GtexSequenceRunner` with simultaneous off-ball support runs (`SupportRun`), defensive marking/pressing (`MarkPlayer`, `PressBallCarrier`, `CoverSpace`), ball progression (`CarryBall`, `Pass`, `ThroughPass`, `Cross`), and finishing (`Shoot` -> save or goal). | **PASS** | `GtexVisualSequencePatternLibrary.cs:10-496`; `GtexSequenceRunner.cs:12-409`; `GtexVisualMatchDirector.cs:602-748`. |
| **10** | **Original Stadium, Goal Nets, Camera & Scoreboard Authority**: Original stadium/crowd, `goalNet1`/`goalNet2`, `MatchCamera`, and `GtexScoreAuthority` are active and verified by `GtexOriginalVisualRuntimeVerifier` (`RunFullVerification`, `RunEditModeAudit`, `RunPlayModeBootstrapSmoke`, `RunScriptedReplayCheck`, `RunLiveFeedCheck`). | **PASS** | `GtexOriginalSimAdapter.cs:509-605, 646-767`; `GtexScoreAuthority.cs:6-98`; `GtexOriginalVisualRuntimeVerifier.cs:45-248, 520-870`. |

---

## 3. Hardening Fixes Applied During P6V Audit

### Fix 1 — `GtexVisualMatchDirector.cs`: Stop Background `localSimEngine` During Scripted Replays & Respect `GtexScoreAuthority.Current`
- **Root Cause**:
  1. When `GTEX_OriginalVisualRuntime.unity` boots with `startupMode = VisualSmoke`, `BootstrapRuntime()` (`GtexVisualMatchDirector.cs:947-951`) automatically calls `StartLocalSimulationFeedInternal()` as soon as `runtimeReady` becomes `true`.
  2. When `RunScriptedAcceptanceReplay()`, `RunScriptedCommandReplay()`, or `TriggerTestSequence_HomeAttack()` was invoked, `localSimEngine` was not stopped. It continued ticking in `Update()` (`GtexVisualMatchDirector.cs:817-826`) and calling `PublishLocalSimulationSnapshot()`, which repeatedly dispatched `SetScore(0, 0)` and overwrote the `+1` goal scored by `CentralBuildupShot` in `GtexScoreAuthority.Current`!
  3. Furthermore, `ResolveCurrentVisualScore` (`GtexVisualMatchDirector.cs:148-169`) previously only read `lastLocalHomeScore` / `localSimEngine.HomeScore` instead of `GtexScoreAuthority.Current`, and `RunScriptedAcceptanceReplayWhenReady()` left `NativeAutonomousPlay = true` after `ResetKickoff`, allowing the kickoff wait state and goal/out colliders to interfere with scripted sequence steps.
- **Resolution** (`GtexVisualMatchDirector.cs:148-169, 586-768, 1900-1910`):
  - Updated `ResolveCurrentVisualScore` to seed `homeScore`, `awayScore`, and `matchMinute` from `GtexScoreAuthority.Current` so the authoritative visual score is always returned even when `localSimEngine` is stopped or null.
  - Added `StopLiveFeed(); StopLocalSimulation();` to `RunScriptedCommandReplay()`, `RunScriptedAcceptanceReplay()`, `RunScriptedAcceptanceReplayWhenReady()`, `RunScriptedVisualReplayWhenReady()`, and `TriggerTestSequence_HomeAttack()`.
  - Scoped `GtexOriginalVisualRuntimePolicy.NativeAutonomousPlay = false` (with `GoalColliders` and `OutColliders` disabled and `originalSim.StartMatch()` invoked before each sequence) inside `RunScriptedAcceptanceReplayWhenReady()` and restored the previous policy flag on completion.

### Fix 2 — `GtexOriginalSimAdapter.cs`: Cancel Pending `StartKickoffCounter()` in `StartMatch()` & Authorize Ball Claim in `GiveBallTo()`
- **Root Cause**:
  1. `ResetKickoff()` (`GtexOriginalSimAdapter.cs:551`) calls `manager.PrePositionTeamsForKickOff()`, which starts `MatchManager.StartKickoffCounter()`—an async 2-second timer (`Task.Delay(2000)`) that fires `KickOffEvent` and resets `MatchFlags` to `MatchStatus.WaitingForKickOff`.
  2. When `StartMatch()` (`GtexOriginalSimAdapter.cs:565`) was called with `NativeAutonomousPlay == true`, `MatchManager.SetGlobalCommandDrivenVisualHold(!nativePlay)` passed `false`, which did **not** cancel `kickoffCounterToken` (`MatchManager.cs:789-793` only calls `CancelKickoffCounter()` when `enabled == true`). Two seconds later, the uncancelled timer fired and flipped `MatchFlags` from `Playing` back to `WaitingForKickOff`.
  3. `GiveBallTo(string playerId)` (`GtexOriginalSimAdapter.cs:170-189`) is called directly by `GtexSequenceRunner.TryClaimBallAtFeet` without going through `director.HandleCommand`, so `GtexVisualAuthority.AllowCommandBallParticipants` needed to be registered before `player.GiveBall()`.
- **Resolution** (`GtexOriginalSimAdapter.cs:170-189, 564-592`):
  - In `StartMatch()`, pulsed `MatchManager.SetGlobalCommandDrivenVisualHold(true)` before setting `MatchManager.SetGlobalCommandDrivenVisualHold(!nativePlay)` and `MatchFlags = MatchStatus.Playing`, guaranteeing any pending `StartKickoffCounter()` task is cancelled immediately.
  - In `GiveBallTo(string playerId)`, registered `GtexVisualAuthority.AllowCommandBallParticipants` for `player.GtexPlayerId` before calling `player.GiveBall()`.

### Fix 3 — `GtexPlayerVisualMap.cs`: Zero-Padded Side-Qualified Player Alias Registration (`home-09` & `home-9`)
- **Root Cause**:
  - `GtexOriginalVisualRuntimeVerifier.BuildLiveFeedPlayers()` and backend live feeds emit zero-padded player IDs (`"home-01"`..`"home-11"`, `"away-01"`..`"away-11"`), whereas `GtexPlayerVisualMap.ResolveAliases` (`GtexPlayerVisualMap.cs:245-276`) only generated unpadded aliases (`teamSide + "-" + number`) when built without a `MatchResponse` state.
- **Resolution** (`GtexPlayerVisualMap.cs:245-276`):
  - Registered both unpadded (`home-9`) and zero-padded (`home-09`) aliases for `shirtNumber`, `MatchPlayer.Number`, and `index + 1` in `ResolveAliases`.

### Fix 4 — `GtexMatchRuntime.cs`: Explicit `GtexOriginalVisualRuntimePolicy` Guards
- **Root Cause**:
  - While `GtexMatchRuntime.TryAutoStart` checked `config.ResolveRuntimeMode() != GtexRuntimeMode.LivePlayback`, adding explicit `GtexOriginalVisualRuntimePolicy` guards in `TryAutoStart`, `ApplyBootstrapGuardsForCurrentContext`, and `ApplyState` guarantees that even if a `GtexMatchRuntime` component is manually added or invoked in `OriginalVisualRuntime`, it immediately skips bootstrap and never calls `playbackApplier.ApplyFrame`.
- **Resolution** (`GtexMatchRuntime.cs:301-312, 383-396, 2696-2706`):
  - Added `!GtexOriginalVisualRuntimePolicy.AllowGtexTransformPlayback || GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()` guards in `TryAutoStart`, `ApplyBootstrapGuardsForCurrentContext`, and `ApplyState`.

---

## 4. Modified Files Summary (Within P6V Boundary)

1. `Gtex_Test_Migration/Assets/Code/GTEX/VisualBridge/GtexVisualMatchDirector.cs`
2. `Gtex_Test_Migration/Assets/Code/GTEX/VisualBridge/GtexOriginalSimAdapter.cs`
3. `Gtex_Test_Migration/Assets/Code/GTEX/VisualBridge/GtexPlayerVisualMap.cs`
4. `Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs`
5. `docs/GTEX_P6V_ORIGINAL_VISUAL_RUNTIME_VERIFICATION.md`
