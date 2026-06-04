# GTEX Visual QA Report

Generated: 2026-06-04

## Requested Matrix

| Viewport | Screenshot status | Evidence |
|---|---|---|
| Desktop | Blocked for full-route screenshot | Flutter web app served at `http://127.0.0.1:5317`, but browser automation failed before navigation. |
| Tablet | Blocked for full-route screenshot | No stored tablet route screenshots found. Widget responsive test coverage exists. |
| Mobile | Blocked for full-route screenshot | No stored mobile route screenshot bundle found. Mobile golden exists only for viral feed. |

## Live App Attempt

Command:

`flutter run -d web-server --web-hostname 127.0.0.1 --web-port 5317 --no-pub`

Result:

- Web SDK download: 143.2s.
- Debug service wait: 1070.8s.
- Served `lib/main.dart` at `http://127.0.0.1:5317`.
- HTTP probe returned `200`.

Screenshot capture was blocked:

- In-app browser runtime failed before navigation with `failed to write kernel assets: The system cannot find the path specified.`
- Standard local browser executables (`msedge`, `chrome`, `chromium`) were not discoverable on PATH or common Edge install paths.

## Existing Visual Coverage

Existing responsive/golden evidence:

- `frontend/test/shell/gtex_shell_responsive_test.dart` covers desktop/tablet/mobile simulated viewport assertions.
- `frontend/test/match/broadcast_package_screen_golden_test.dart` defines desktop broadcast package golden coverage at `1440x1024`.
- `frontend/test/viral_feed/viral_feed_screen_test.dart` defines mobile viral feed golden coverage at `430x932`.
- Existing committed golden PNGs:
  - `frontend/test/goldens/broadcast_package_premium_surface.png`
  - `frontend/test/goldens/viral_feed_premium_surface.png`

No full-app screenshot bundle or `frontend/integration_test` directory was found.

## Visual Issues Observed From Runtime/Test Evidence

| Issue | Evidence | Risk |
|---|---|---|
| Offscreen tap target | `viral_feed_screen_test.dart:378` warning: `Share to WhatsApp` tap outside `800x600` root. | Desktop/tablet interaction clipping or scroll positioning issue. |
| Active shell nav labels missing | Full Flutter test failures expected `Funds`, `Home`, wallet actions, and withdrawal text but found none. | Primary navigation and route content may be hidden, renamed, or not mounted. |
| Competition arena content not reachable | `dragUntilVisible` raised `Bad state: No element`. | Competition layout/content may not render expected sections. |
| Trader blocked state duplicated | Expected one `Order book blocked`, found two. | Confusing blocked/degraded state UI. |
| Legacy route blocker copy drift | Tests expected `Coming soon`, found none. | Blocked legacy routes may not communicate state consistently. |
| Historical overflow fixes only documented | Manifest references community/creator overflow fixes, but no current full screenshot artifact confirms them. | Responsive regressions remain possible. |

## Loading, Degraded, and Blocked States

Positive evidence:

- Shared async state rendering tests exist for loading/empty/blocked/pending/syncing/reconnecting/degraded/confirmed/error/data states.
- Match-center truth-state evidence is strong in tests/manifests: closed websocket frames and missing backend score/xG truth render blocked/degraded states.

Remaining gap:

- These states are not captured in full-route desktop/tablet/mobile screenshots.

## Visual QA Verdict

Full visual QA is incomplete. The app can serve web HTML, and partial widget/golden coverage exists, but desktop/tablet/mobile screenshots were not produced because browser automation was unavailable in this environment. Current test evidence still shows real visual/interaction risks around offscreen controls, missing nav labels, duplicated blocked states, and competition content discovery.

