# GTEX P6-04 Release Path Audit

## Scope

This audit covers the first executable part of `P6-04`:
- ensure the shipped Windows validation lane uses the production build path
- ensure the startup diagnostics overlay cannot mount in production players
- record what is still missing before `P6-04` can be marked passed

Audit dates:
- `2026-04-17`
- `2026-04-18`
- `2026-04-22`

## Findings

### 1. The shipped Windows lane previously used the development command-line build entrypoint

Before this pass, the main Windows batch build references in the repo pointed to:
- `FStudio.GTEX.Editor.GtexBuildTools.BuildWindows64FromCommandLine`

That entrypoint resolves to development mode in batchmode, which is not appropriate for release validation.

Affected references before the fix:
- [AGENTS.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/AGENTS.md:21>)
- [ci-staging.yml](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/.github/workflows/ci-staging.yml:338>)
- [deploy-production.yml](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/.github/workflows/deploy-production.yml:163>)

### 2. The shipped Windows lane now uses the explicit production build entrypoint

The release-path references now point to:
- `FStudio.GTEX.Editor.GtexBuildTools.BuildWindows64ProductionFromCommandLine`

Updated references:
- [AGENTS.md](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/AGENTS.md:21>)
- [ci-staging.yml](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/.github/workflows/ci-staging.yml:338>)
- [deploy-production.yml](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/.github/workflows/deploy-production.yml:163>)

### 3. The runtime startup overlay is now explicitly disabled outside editor and GTEX development builds

`GtexLiveStartupOverlay` previously rendered when any of these were true:
- editor
- Unity debug build
- `GtexConfig.IsDev`

That has now been tightened to:
- editor
- `GtexConfig.IsDev`

Code reference:
- [GtexLiveStartupOverlay.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/GTEX/Core/GtexLiveStartupOverlay.cs:92>)

This means production players built with `GTEX_PROD` cannot mount the diagnostic startup overlay even if other Unity debug-style flags differ from the intended GTEX mode.

### 4. Production build evidence now shows the shipped lane entering GTEX production mode

The production batch build log shows:
- `Build mode: Production`
- `Scripting define symbols: GTEX_PROD`
- `Using GTEX Production build scenes`
- `Applied Production quality level: PC (1)`

Proof references:
- [gtex_test_migration_windows_production_build.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_test_migration_windows_production_build.log:1489>)
- [gtex_test_migration_windows_production_build.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_test_migration_windows_production_build.log:1504>)
- [gtex_test_migration_windows_production_build.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_test_migration_windows_production_build.log:1588>)
- [gtex_test_migration_windows_production_build.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_test_migration_windows_production_build.log:1718>)

### 5. Production player output is materializing under the production build folder

Current output path:
- [GTEXMatch.exe](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Builds/WindowsProduction/GTEXMatch.exe>)

This confirms the release-path build is packaging the production player into the intended `WindowsProduction` lane.

### 6. A deterministic local production-build wrapper now exists for long Windows Unity runs

Local desktop validation was previously being distorted by two issues:
- the desktop could suspend or lose foreground during long production runs
- the earlier shell launch path made it too easy to misread detached or interrupted Unity sessions as a build hang

To remove that ambiguity, a dedicated Windows helper was added:
- [run_gtex_windows_production_build.ps1](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_windows_production_build.ps1:1>)

This wrapper:
- keeps Windows awake for the duration of the Unity batch build
- launches the same production entrypoint with correctly quoted arguments
- waits for the Unity process to terminate and surfaces the real exit code

### 7. Clean local production batch termination is now proven

A local production batch build was rerun through the no-sleep wrapper and completed with a clean exit code of `0`.

Proof references:
- [run_gtex_windows_production_build.ps1](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_windows_production_build.ps1:1>)
- [gtex_test_migration_windows_production_build_20260418_082644.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_test_migration_windows_production_build_20260418_082644.log>)
- [gtex-build-StandaloneWindows64-20260418-083843.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/tmp/builds/gtex-build-StandaloneWindows64-20260418-083843.log>)

The successful run shows:
- `Build Finished, Result: Success`
- `Build result: Succeeded`
- `Total errors: 0`
- `Build completed successfully`
- `Batchmode quit successfully invoked`
- `Exiting batchmode successfully now!`

The companion trace records:
- `Build time: 00:23:37.6224288`
- `Build size: 195758858 bytes`
- `Trace session closed.`

This closes the earlier uncertainty about whether the local production lane could terminate cleanly. It can.

### 8. Release-player runtime evidence now shows the production player rendering without the startup diagnostics overlay

Two local production-player captures were recorded after the clean build:
- [gtex_windows_production_player_windowed_success_build.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_windows_production_player_windowed_success_build.png>)
- [gtex_windows_production_player_windowed_success_build_120s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_windows_production_player_windowed_success_build_120s.png>)

The stronger `120s` capture shows:
- a rendered stadium scene rather than a blank startup frame
- no visible dark red `GTEX Live Status` diagnostics panel in the top-left release window
- production runtime behavior rather than editor/dev-only overlay behavior

Supporting runtime log evidence:
- [gtex_prod_capture_120s.log](</C:/Users/ayomc/AppData/Local/Temp/gtex_prod_capture_120s.log>)

That runtime log shows:
- `[GTEX] Render mode applied: Production -> PC`
- `RuntimeMode -> LivePlayback`
- stadium load and imported stadium attachment
- `LiveScoreboardPanel` registration

It does not show any startup overlay mount log or visible overlay in the captured release window.

### 9. Full live-match release validation was previously blocked by missing runtime bootstrap inputs

The same local production-player log also shows:
- `matchId is required for live mode.`
- `Live playback auth bootstrap is missing.`
- `CanAutoStart -> False`
- no live access token or refresh token

So the remaining blocker for a full `P6-04` pass was no longer build reliability. The blocker at that stage was that local release validation was still running without a real live-match bootstrap, which prevented a true authenticated live-playback capture pack.

### 10. Authenticated live playback is now proven in the shipped player, with live-only input/UI leakage reduced

After the initial release-path audit, the live lane was tightened further:
- [MatchManager.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/MatchEngine/MatchManager.cs:327>) now skips general user-match input creation when GTEX live playback owns the match and `userTeam = None`
- [TeamTacticsUI.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/MatchEngine/UI/TeamTacticsUI.cs:36>) now hides whenever a `GtexMatchRuntime` instance is active, instead of waiting for `ExternalPlaybackEnabled` to flip later in bootstrap

Fresh shipped-player evidence now exists for authenticated live playback:
- [gtex_test_migration_windows_production_build_20260418_104516.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_test_migration_windows_production_build_20260418_104516.log>)
- [gtex_windows_production_player_live_bootstrap_post_input_cleanup_70s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_windows_production_player_live_bootstrap_post_input_cleanup_70s.png>)
- [gtex_prod_live_bootstrap_post_input_cleanup_70s.log](</C:/Users/ayomc/AppData/Local/Temp/gtex_prod_live_bootstrap_post_input_cleanup_70s.log>)

This run proves:
- the production player consumed a fresh live bootstrap for `match_fix_a6c7753b3b9f`
- the shipped lane rendered authenticated open play at `24:56`, `City 1-0 Royal`
- `TeamTacticsUI` no longer mounted during GTEX live playback in the shipped lane
- the old pause-panel leakage did not appear in the captured runtime log

### 11. A follow-up ball warning cleanup is in source but not yet revalidated in a fresh production export

The authenticated release runtime log still shows repeated Unity warnings:
- `Setting linear velocity of a kinematic body is not supported.`
- `Setting angular velocity of a kinematic body is not supported.`

That came from the external-playback ball path writing rigidbody velocities while the ball was kinematic. The source now avoids that by tracking external-playback velocity separately:
- [Ball.cs](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/Assets/Code/MatchEngine/Ball/Ball.cs:35>)

However, the immediate follow-up production export to validate that warning cleanup hung on the Bee player step, so that specific log cleanup remains unproven in a fresh shipped executable.

### 12. The release-path motion pack and ball-warning cleanup are now revalidated in a fresh shipped build

The earlier `P6-04` gap is now closed with a corrected full-session release harness and a fresh production export.

Release harness corrections:
- [capture_gtex_player_session.ps1](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/capture_gtex_player_session.ps1:1>) now supports leaving the player running after screenshots so the release proof can reach full time instead of terminating at the last capture offset
- [run_gtex_full_session_validation.ps1](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tools/run_gtex_full_session_validation.ps1:1>) now waits for full-time completion, refreshes the runtime trace after shutdown, and records kinematic-ball warning checks in the summary

Fresh production build proof:
- [gtex_test_migration_windows_build_p6_releasepath_20260422b.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_test_migration_windows_build_p6_releasepath_20260422b.log:10054>)
- [gtex-build-StandaloneWindows64-20260422-201953.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/Gtex_Test_Migration/tmp/builds/gtex-build-StandaloneWindows64-20260422-201953.log:1>)

The fresh release capture now proves all of the following in the shipped player:
- bootstrap completed
- moving players were visible
- moving ball was visible
- camera presets advanced through `broadcast`, `attack_push`, and `box_zoom`
- the session reached full time with monotonic clock and score
- the old kinematic rigidbody warnings were absent
- post-fulltime websocket churn dropped to a single websocket connection for the full session

Release capture proof:
- [gtex_full_session_summary.json](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_summary.json>)
- [gtex_full_session_validation.runtime.log](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation.runtime.log>)
- [gtex_full_session_validation.metadata.txt](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation.metadata.txt>)
- [gtex_full_session_validation_t0010s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation_t0010s.png>)
- [gtex_full_session_validation_t0018s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation_t0018s.png>)
- [gtex_full_session_validation_t0026s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation_t0026s.png>)
- [gtex_full_session_validation_t0034s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation_t0034s.png>)
- [gtex_full_session_validation_t0042s.png](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/gtex_full_session_capture/gtex_full_session_validation_t0042s.png>)

Key values from the summary:
- `bootstrap_seen: true`
- `motion_seen: true`
- `ball_motion_seen: true`
- `camera_stable: true`
- `linear_kinematic_warning_seen: false`
- `angular_kinematic_warning_seen: false`
- `server_summary.websocket_connections: 1`
- `server_summary.final_frame_sent: true`
- `passed: true`

## Verdict

Current status:
- release-path build references are corrected
- startup overlay gating is corrected for production players
- production-mode build evidence exists
- clean production batch termination is now proven locally
- a local release-player capture set now shows no visible startup diagnostics overlay
- authenticated live playback is now proven in the shipped player
- the stronger motion capture pack now exists in the shipped player
- the post-ball-cleanup release rerun is now proven in a fresh production export
- the shipped validation path reaches full time without post-fulltime websocket churn

`P6-04` is now `PASSED`.

## Remaining Work

- no remaining `P6-04` blockers
- preserve the corrected release harness for future regression checks
