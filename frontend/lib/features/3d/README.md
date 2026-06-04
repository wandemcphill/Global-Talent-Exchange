# Legacy 3D Quarantine

This folder is not a production GTEX surface. It contains deprecated legacy
match-rendering code preserved only for dependency analysis and possible
reuse of non-rendering orchestration ideas.

Canonical GTEX production match direction is the backend-authoritative 2D
broadcast match center under `frontend/lib/features/match_center`.

Rules for this folder:

- Do not import this folder from production modules outside `lib/features/3d`.
- Do not add production routes, navigation entries, CTAs, monetization, or
  deployment checks that point at this folder.
- Do not add new runtime dependencies for this legacy lane.
- Keep reusable domain/event ideas isolated from rendering before migrating
  them to canonical match-center infrastructure.
- Delete only after dependency analysis confirms no reusable value remains.
