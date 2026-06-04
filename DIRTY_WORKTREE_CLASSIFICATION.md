# GTEX Dirty Worktree Classification

Generated: 2026-06-04

Scope: `git status --porcelain=v1` at `C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE`.

No files were deleted, reverted, staged, or cleaned during this triage.

## Summary

Total dirty entries observed: 862

Status mix:

| Status | Count |
|---|---:|
| Modified | 512 |
| Deleted | 217 |
| Untracked | 133 |

Top dirty prefixes:

| Prefix | Count |
|---|---:|
| `frontend` | 519 |
| `backend` | 173 |
| `Gtex_Test_Migration` | 103 |
| `docs` / `Docs` | 27+ |
| `tools` | 12 |
| `ops` | 11 |
| `.github` | 3 |
| `desktop_salvage_20260421` | 2 |

Conflict-marker scan: no literal `<<<<<<<` or `>>>>>>>` merge conflict markers were found. Some markdown underline matches appeared, but no textual merge conflict blocks were identified.

## Classification

| Category | Count | Ownership | Risk | Delete candidate |
|---|---:|---|---|---|
| A. owned active changes | 34 | Active integration work: match center, compete, Build-a-Son, Unity GTEX runtime, backend auth/competition contracts | High | No |
| B. stale abandoned changes | 469 | Mixed/unknown historical edits across frontend, backend, Unity, workflows, secrets baseline | Critical | Review individually |
| C. generated artifacts | 106 | Tooling, Unity `.meta`, lockfiles, generated API maps, runtime/log artifacts | Medium | Yes, after provenance check |
| D. docs-only changes | 25 | Audit/manifests/route docs/reporting | Low | No, unless superseded |
| E. merge leftovers | 2 | `desktop_salvage_20260421` deletions | Medium | Yes, after confirming salvage is obsolete |
| F. conflicting implementations | 164 | Old match/competition systems versus new feature islands | Critical | Not yet |
| G. duplicate feature systems | 62 | Admin/capital/creator/club sale/share market duplicated surfaces | High | Not yet |

Counts are heuristic but exclusive. The worktree is too dirty to infer final intent from git status alone.

## Category Details

### A. Owned Active Changes

Representative files:

- `frontend/lib/features/match_center/**`
- `frontend/lib/features/compete/**`
- `frontend/lib/features/build_a_son/**`
- `frontend/lib/features/shell/**`
- `frontend/test/shared/auth_identity_store_test.dart`
- `backend/tests/auth/**`
- `backend/tests/competitions/**`
- `Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexEngineCommand.cs`
- `Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchController.cs`
- `Gtex_Test_Migration/Assets/Code/GTEX/VisualBridge/GtexCinemachineFootballCameraDirector.cs`

Assessment: likely intentional work from the canonicalization wave. Keep, reconcile, and make ownership explicit before staging.

### B. Stale Abandoned Changes

Representative areas:

- `.github` workflow edits
- `.gitignore`
- `.secrets.baseline`
- older backend auth/API/club route edits
- Unity runtime flags/config edits
- large groups of modified files without clear relationship to the active production-readiness mission

Assessment: largest risk bucket. These changes may be real, but the repo cannot be treated as production-ready until each is assigned to an owner or closed as abandoned.

### C. Generated Artifacts

Representative files:

- Unity `.meta` files
- `frontend/pubspec.lock`
- `package-lock.json`
- generated API contract maps under `frontend/lib/data/generated/**`
- runtime logs/zips under `tmp`, `ops`, and generated output folders

Assessment: do not delete blindly. Regenerate or compare with source commands first, then keep only deterministic generated output.

### D. Docs-Only Changes

Representative files:

- `docs/CODEX_*`
- `docs/DEPRECATION_MAP.json`
- `frontend/ROUTE_INTEGRITY_AUDIT.md`
- `Docs/*`

Assessment: useful evidence/history, but note casing split between `docs` and `Docs`.

### E. Merge Leftovers

Observed:

- `desktop_salvage_20260421/.gitignore`
- `desktop_salvage_20260421/README.md`

Assessment: likely salvage/merge residue. Delete only after confirming no thread still depends on the salvage directory.

### F. Conflicting Implementations

Representative files:

- deleted old `frontend/lib/features/match/**`
- backend `backend/app/live_matches/**`
- backend `backend/app/matches/**`
- backend `backend/app/match_engine/**`
- old competitions hub and match controllers/data/services/tests

Assessment: critical because production navigation and tests still reference old contracts in places while new `features/match_center` and `features/compete` exist.

### G. Duplicate Feature Systems

Representative areas:

- admin finance/trader/wallet providers
- old `club_sale`, `creator_share`, `creator_stadium`, `creator_league`, `fan_prediction` systems
- new `frontend/lib/features/capital/**`
- new `frontend/lib/features/market/**`
- new `frontend/lib/features/creator/**`

Assessment: keep quarantined until route ownership and replacement paths are written down. Do not mass delete.

## Immediate Risk

The current dirty tree is not launchable governance-wise. Even if tests passed, 862 dirty entries with 217 deletions and 133 untracked files means the production candidate cannot be reproduced, reviewed, or rolled back safely.

