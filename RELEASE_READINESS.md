# GTEX Release Readiness

This pass focuses on production polish across the whole app, not just wallet surfaces.

## Included hardening

- Shared premium sync/status treatment across Home, Trade, Arena, Club, and Wallet surfaces.
- Page storage in the shell so major tabs preserve state more reliably during navigation.
- In-flight request dedupe for exchange bootstrap, portfolio loads, order loads, competition discovery, competition detail loading, and club dashboard loading.
- Sync timestamps stamped directly in controllers so the UI can explain freshness instead of feeling vague.
- Centralized session identity resolution to reduce route-shell duplication and drift.
- Material app restoration scope enabled for better recovery/readiness.
- Added tests covering session identity defaults, exchange hardening behavior, and sync status widget rendering.

## Remaining verification to run locally

Because Flutter SDK is not available in this environment, run these locally before packaging APK or release artifacts:

```bash
cd frontend
flutter pub get
flutter analyze
flutter test
```

## Suggested final release gate

1. Run analyzer and all widget/unit tests.
2. Smoke-test each primary tab while signed out and signed in.
3. Verify admin and manager market routes after sign-in.
4. Confirm wallet sync, order placement, and competition discovery against your intended backend mode.
5. Build release candidate only after local visual QA on desktop and mobile widths.


## Withdrawal fee policy to add
- Users should be able to withdraw e-game winnings and rewards.
- Platform fee on every withdrawal should be 10%, including trade withdrawals and e-game reward withdrawals.
- Wallet UI and ledger must show gross amount, fee deducted, and net payout.
