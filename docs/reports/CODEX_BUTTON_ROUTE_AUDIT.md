# CODEX Button and Route Audit

## Scope

This audit focused on the canonical live Flutter shell and the backend routes that support it. Because Flutter was not available in the environment, results below are based on source audit plus backend route inventory, not interactive runtime clicking.

## Canonical live entry points

- Backend boot: `backend/app/main.py`
- Frontend boot: `frontend/lib/main.dart`
- Canonical live shell: `frontend/lib/features/navigation/presentation/gte_navigation_shell_screen.dart`
- Named route registry: `frontend/lib/features/app_routes/gte_app_route_registry.dart`

## User-visible lanes audited

| Lane | Live entry point | Status | Notes |
| --- | --- | --- | --- |
| Auth and guest preview | `GteLoginScreen`, canonical shell sign-in CTA | Pass by source audit | Guest mode is supported and sign-in CTA is wired |
| Home dashboard | `HomeDashboardScreen` | Pass by source audit | Reachable from canonical bottom nav |
| Market | `GteMarketPlayersScreen` | Pass by source audit | Reachable from canonical bottom nav |
| Player detail | `GteExchangePlayerDetailScreen` | Pass by source audit | Reachable from market and holdings |
| Orders | `GteOrderDetailCard` flows via portfolio lane | Pass by source audit | Refresh and cancel actions wired |
| Wallet and portfolio | `GtePortfolioScreen` | Partial | Reachable, but no end-user withdrawal action |
| Competitions and live match center | `GteCompetitionsHubScreen` | Pass by source audit | Reachable from canonical bottom nav |
| Club hub and identity | `ClubHubScreen` plus named club identity routes | Pass after backend route fix | Canonical backend routes now align |
| Creator and referral | `ReferralHubScreen` | Fixed | Was unreachable from canonical shell; now exposed by app bar icon |
| Manager market | `ManagerMarketScreen` | Pass by source audit | Reachable from authenticated shell action |
| Admin controls | `GodModeAdminScreen` | Pass by source audit | Reachable for admin roles only |
| Replay and highlights | competitions and replays route registry | Pass by source audit | Graceful route fallback exists |

## Critical dead buttons

- None confirmed in the canonical live shell source.

## Broken routes found and fixed

- Canonical club reputation route
  - Backend canonical route `/api/clubs/{club_id}/reputation` is now directly owned and served by the canonical clubs module.

- Canonical club dynasty route
  - Backend canonical route `/api/clubs/{club_id}/dynasty` now returns a valid empty profile instead of `404` for clubs without dynasty history.

- Duplicate orders API aliases
  - Removed accidental `/api/api/orders*` routes caused by double prefixing in the wallet router.

- Canonical creator lane reachability
  - Added a creator/community app bar action to the canonical shell so `ReferralHubScreen` is no longer trapped behind the older shell.

## Misleading labels found and fixed

- `frontend/lib/screens/gte_portfolio_screen.dart`
  - Removed preview copy that implied a withdrawal user flow existed
  - Renamed `Refresh ledger` to `Refresh orders` to match actual behavior

## Safe improvements applied

- Added creator/community entry point to the live shell
- Removed duplicate backend orders aliases
- Cleaned wallet copy and CTA labeling

## Remaining issues needing manual product decision

- End-user withdrawal UI is still missing from the canonical wallet lane.
  - Backend request support exists, but there is no user CTA or form.

- Creator and referral screens are still not part of the canonical route registry.
  - The lane is now reachable from the live shell, but does not yet support canonical deep links.

- Legacy shell remains in repo.
  - `frontend/lib/screens/gte_exchange_shell_screen.dart` still contains route wiring for community surfaces and may confuse future work if not retired or clearly marked.

## CTA handler audit notes

- Search did not find obvious empty `onPressed: () {}` handlers in live frontend code paths.
- Route fallback panels exist for unavailable or unregistered route cases.
- Backend route inventory after hardening reports `301` unique paths.
