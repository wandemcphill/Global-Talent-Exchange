# GTEX P6-01 Unity Windows CI Gate

## Scope

This note captures the verified repo-side implementation and local production batch-build proof for `P6-01`: making the Unity Windows production build and backend live-motion tests enforceable CI gates on `main` and release deployment paths.

## Repo-Side Verification

1. **Workflow Definitions (`.github/workflows/ci-staging.yml` & `.github/workflows/deploy-production.yml`)**
   - `backend-live-playback-tests` runs automatically on `ubuntu-latest` across pull requests, `main`, and production deploys, executing:
     - `backend/tests/live_matches/test_live_match_router.py`
     - `backend/tests/live_matches/test_live_match_hot_path_cache.py`
     - `backend/tests/live_matches/test_live_match_sampling.py`
     - `backend/tests/match_engine/test_live_match_experience_contract.py`
     - `backend/tests/test_match_timeline_service.py`
   - `unity-windows-build` is wired into both `.github/workflows/ci-staging.yml` and `.github/workflows/deploy-production.yml`:
     - Invokes the production command-line build entrypoint `FStudio.GTEX.Editor.GtexBuildTools.BuildWindows64ProductionFromCommandLine`.
     - Isolates runner profile directories (`LOCALAPPDATA`, `APPDATA`, `TEMP`, `TMP`) under `tmp/gtex-unity-runner-profile-${{ github.run_id }}-${{ github.run_attempt }}`.
     - Explicitly classifies Unity Editor licensing/entitlement failures (`No valid Unity Editor license found`, `Found 0 entitlement groups and 0 free entitlements matching requested entitlement ids`, `'com.unity.editor.headless' was not found`) with actionable runner-identity diagnostics.
     - Scans `tmp/gtex_test_migration_windows_build.log` for compile and build failure markers (`error CS`, `Compilation failed`, `Build completed with a result of 'Failed'`, `Aborting batchmode due to failure`).
     - Executes `FStudio.GTEX.Editor.GtexOriginalVisualRuntimeVerifier.VerifyFromCommandLine` on the staging CI lane after the player build.
     - Uploads `gtex-test-migration-windows-build-log` as a retained workflow artifact.

2. **Automated Readiness Audit Pinning**
   - `backend/scripts/audit_group6_production_readiness.py` and `backend/tests/production/test_group6_production_readiness.py` assert that `unity-windows-build:` and license-failure classification remain present in the production deploy workflow.

3. **Verified Local Production Batch Build Proof**
   - Deterministic no-sleep wrapper: `tools/run_gtex_windows_production_build.ps1`
   - Verified production build output: `Gtex_Test_Migration/Builds/WindowsProduction/GTEXMatch.exe`
   - Retained build logs:
     - `tmp/gtex_test_migration_windows_production_build_20260418_082644.log` (`Build result: Succeeded`, `Total errors: 0`, `Exiting batchmode successfully now!`)
     - `tmp/gtex_test_migration_windows_build_p6_releasepath_20260422b.log`
     - `Gtex_Test_Migration/tmp/builds/gtex-build-StandaloneWindows64-20260422-201953.log`

## Current Status

Current status: `PASSED`

Repo-side completion:
- `unity-windows-build` and `backend-live-playback-tests` are wired in `.github/workflows/ci-staging.yml` and `.github/workflows/deploy-production.yml`
- production batch build entrypoint (`BuildWindows64ProductionFromCommandLine`), profile isolation, license-failure classification, and build-log verification are committed and pinned by `backend/scripts/audit_group6_production_readiness.py`
- clean local Windows production batch builds (`GTEX_PROD`) are proven with zero compile/build errors

External operational follow-up (tracked in `docs/reports/GTEX_GROUP6_STATUS.md` runtime lane):
- keep the self-hosted Windows Unity runner online with an active Unity Editor license for the runner service account (`production Unity runner license`)
- enforce `unity-windows-build` as a required remote GitHub branch-protection check on `main` when the self-hosted runner is active
