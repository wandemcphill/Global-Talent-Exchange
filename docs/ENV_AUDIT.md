# Environment and Deployment Audit

## Backend / Web Deploy

- `render.yaml` configures `gtex-web` with `GTE_API_BASE_URL=https://gtex-api.onrender.com` and `GTE_BACKEND_MODE=live`.
- `render.yaml` configures `gtex-api` as the single backend origin for production traffic.

## Flutter Runtime Config

- `frontend/lib/app/gte_app_config.dart` uses `GTE_API_BASE_URL` and `GTE_BACKEND_MODE` as the canonical runtime inputs.
- Fixture mode is intentionally gated to tests; live is the default runtime path.

## Drift Risks

- Hardcoded localhost or alternate base-url defaults detected in frontend data files: **277**
- These should be consolidated behind the shared runtime config before any destructive backend route cleanup.

## Source Evidence

- `render.yaml` contains `GTE_API_BASE_URL`: True
- `gte_app_config.dart` contains `GTE_API_BASE_URL`: True
