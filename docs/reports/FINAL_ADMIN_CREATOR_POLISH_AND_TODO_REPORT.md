# Final Admin / Creator Polish + TODO Pass

## What changed
- Upgraded creator leaderboard into a branded admin desk with better loading, retry, and empty states.
- Upgraded referral admin into a referral integrity desk with premium hero framing and calmer no-flag state.
- Upgraded manager admin loading and section hierarchy so the screen reads more like an operations desk than a raw admin tool.
- Added an explicit project TODO for withdrawal policy work:
  - e-game winnings and rewards withdrawable
  - 10% platform fee on every withdrawal
  - applies to trade and e-game reward withdrawals

## Files changed
- frontend/lib/screens/admin/creator_leaderboard_screen.dart
- frontend/lib/screens/admin/referral_admin_screen.dart
- frontend/lib/screens/admin/manager_admin_screen.dart
- NEXT_IMPLEMENTATION_TODO.md
- RELEASE_READINESS.md

## Notes
- Local Flutter analyze/test still needs to be run in a proper dev environment.
- This pass focused on premium copy, empty/error/loading states, and operational clarity.
