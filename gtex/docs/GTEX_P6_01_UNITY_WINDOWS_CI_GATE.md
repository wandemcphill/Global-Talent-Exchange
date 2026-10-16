# GTEX P6-01 Unity Windows CI Gate

## Scope

This note captures the repo-side portion of `P6-01`: making the Unity Windows build path a real default CI lane instead of a variable-gated optional job.

`P6-01` is only fully passed when both of these are true:
- the workflow always schedules the Windows Unity build on `main` and pull-request validation paths
- GitHub branch protection requires the `unity-windows-build` check before merge

## Repo-Side Change

The `unity-windows-build` job in [C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\.github\workflows\ci-staging.yml](</C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/.github/workflows/ci-staging.yml>) is no longer hidden behind `vars.GTEX_ENABLE_WINDOWS_UNITY_CI == 'true'`.

That means:
- the repository now treats the Windows Unity build as a first-class CI job
- missing runner/editor configuration now fails explicitly instead of silently skipping the lane
- the build log path and Windows runner profile isolation remain the same as before

## Remaining External Gate

Repo code alone cannot force branch protection on GitHub. The following still needs to be confirmed on the remote repository:
- the self-hosted Windows Unity runner is online and licensed
- `unity-windows-build` is configured as a required status check for `main`

Without that remote protection setting, `P6-01` should stay `IN PROGRESS` even though the repo-side workflow wiring is now correct.

## Expected Proof

The final `P6-01` evidence pack should contain:
- a successful GitHub Actions `unity-windows-build` run
- the uploaded Unity build log artifact
- a short runner configuration note
- the GitHub branch protection setting showing `unity-windows-build` is required on `main`

## Current Status

Current status: `IN PROGRESS`

What is complete:
- the workflow is always-on in the repo
- the build job no longer depends on a repository variable to exist at all

What still blocks a pass:
- remote branch protection verification
- runner availability and successful GitHub-hosted execution evidence
