# GTEX Flutter Web browser validation

This is a Playwright harness for the shipped Flutter Web app. It does not mock
application responses or generate screenshot-only data. Use a running GTEX API
and approved, seeded QA account instead.

## Install once

```powershell
cd qa/playwright
npm install
npm run install:browsers
```

## Run against a local API

Start the documented GTEX local backend and use one of its approved seeded
accounts. The config starts Flutter's web-server automatically.

```powershell
$env:GTEX_E2E_API_BASE_URL = 'http://127.0.0.1:8000'
$env:GTEX_E2E_EMAIL = 'seed.fan@gte.local'
$env:GTEX_E2E_PASSWORD = 'DemoPass123'
npm test
```

To connect to an already-hosted Flutter Web build, set `GTEX_E2E_BASE_URL`
instead of `GTEX_E2E_API_BASE_URL`.

The suite produces desktop, tablet, and mobile screenshots in Playwright's
test-result artifacts, and attaches console-error and failed-request logs to
each test. Optional notification variables point the suite at real seeded
notifications, never invented client-side content:

```powershell
$env:GTEX_E2E_NOTIFICATION_TEXT = 'Offer accepted'
$env:GTEX_E2E_NOTIFICATION_TARGET = '/app/market'
$env:GTEX_E2E_UNTARGETED_NOTIFICATION_TEXT = 'An informational alert'
```

Set `GTEX_E2E_LINEUP_ROUTE` or `GTEX_E2E_MATCH_VIEWER_ROUTE` only when the
approved account uses a different real route or authoritative match key.

Without a backend URL and credentials, the affected tests report as skipped;
this is intentional so CI never silently validates fabricated data.

## Design Lab screenshots

The isolated `/design-lab` route has its own clearly labelled local fixtures;
they are never inserted into production providers. It can therefore be
captured without an authenticated account, while still using the real Flutter
Web application and Chromium:

```powershell
$env:GTEX_E2E_API_BASE_URL = 'http://127.0.0.1:8000'
$env:GTEX_E2E_DESIGN_LAB = '1'
npm test -- --grep "design lab"
```

For a release-bundle visual check with a static local server, build the bundle,
serve `frontend/build/web` on port 7357, then run the same test with:

```powershell
$env:GTEX_E2E_BASE_URL = 'http://127.0.0.1:7357'
$env:GTEX_E2E_DESIGN_LAB = '1'
$env:GTEX_E2E_HASH_ROUTING = '1'
npm test -- --grep "design lab"
```

`GTEX_E2E_HASH_ROUTING` is only for a plain static server that does not
rewrite `/design-lab` to Flutter's `index.html`.
