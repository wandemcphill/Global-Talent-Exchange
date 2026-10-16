# Critical Issues

## HIGH - Shared Flutter repository still forces /api/v1

frontend/lib/data/gte_api_repository.dart rewrites most '/api/*' requests through gteVersionedApiPath(), keeping the primary app shell on legacy api_v1 contracts even when richer canonical routes exist.

Evidence:
- `frontend/lib/data/gte_api_repository.dart: gteVersionedApiPath`

## HIGH - Parallel routing and API access patterns still coexist

The premium shell now mounts through a central GoRouter, but feature screens and older API helpers still retain imperative or legacy access paths. This is the main reason updates do not feel uniformly reflected across web and mobile.

Evidence:
- `frontend/lib/router/app_router.dart`
- `frontend/lib/navigation/app_router.dart`
- `frontend/lib/features/app_routes/gte_navigation_helpers.dart`
