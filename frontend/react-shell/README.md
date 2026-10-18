# GTEX React shell

This is a standalone React UI target imported from the Emergent design branch and isolated from the existing Flutter app. It uses the canonical API in `../../backend`; it does not include a duplicate backend or a nested copy of GTEX.

## Local development

1. Copy `.env.example` to `.env.local` and verify `REACT_APP_BACKEND_URL` points to the environment you intend to use.
2. Install dependencies with `npm install --legacy-peer-deps`.
3. Start with `npm start` or create a production bundle with `npm run build`.

The API base variable is the backend origin without a trailing slash or `/api`; requests are made under `/api`. Local and preview origins must be allowed by the backend CORS configuration.

## Deployment status

This integration intentionally does not change the current Render build, which still publishes the existing Flutter Web app. The React shell must pass its build and functional/API checks before a separate production cutover PR is approved.

Emergent-specific overlays, injected runtime scripts, remote analytics snippets, its hosted-backend test file, duplicate backend wrapper, and nested duplicate `gtex/` repository have been excluded.
