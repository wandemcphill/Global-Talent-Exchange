# GTEX Frontend RC Manual Smoke Checklist

Branch: `codex/treasury-mvp`  
Date: `2026-03-19`  
Use this only for the release-candidate build intended for controlled testing. Build and packaging are separate; if needed, use `Docs/LOCAL_BUILD_CHECKLIST.md` for operator build steps.

Stop and log a blocker on any crash, blank screen, dead-end route, wrong club context, or broken branding.

## Checklist

- [ ] Launch the RC build and confirm the splash, logo, and header branding are GTEX-canonical.
  Pass if the GTEX icon/logo appears cleanly, `Global Talent Exchange` is shown where expected, and no legacy or mismatched branding appears.

- [ ] Sign in with a club-linked test account.
  Pass if sign-in completes, the session lands in the main shell, and the app does not stall, loop, or return to guest gating.

- [ ] Verify Home with canonical club context.
  Pass if Home reflects the signed-in club context, the correct club name is shown, and no fallback club identity appears.

- [ ] Verify the no-club onboarding state with a no-club account.
  Pass if Home shows `Create or join a club to unlock Home` with `Create Club`, `Join Club`, and `Explore Arena`, and does not leak another club's context.

- [ ] Enter Arena from the active shell.
  Pass if Arena opens without a routing error and shows either the live/featured overview or the intended empty state.

- [ ] Enter Wallet from the active shell or portfolio wallet actions.
  Pass if Wallet opens successfully and exposes the expected wallet lane entry points such as overview, funding, withdrawal, and notifications.

- [ ] Verify the blocked funding state with a compliance-restricted account.
  Pass if funding stays locked, `Compliance action required` and `Open compliance center` are visible, and manual deposit request instructions do not appear while deposits are blocked.

- [ ] Verify notifications open/read refresh.
  Pass if opening an unread notification navigates into its target workspace, returning to the inbox refreshes the item to `Read`, and the unread badge/state clears.

- [ ] Verify withdrawal notification routing.
  Pass if opening a withdrawal notification lands in the withdrawal workspace and shows the withdrawal flow rather than deposit history or a generic wallet screen.

- [ ] Perform one back/re-entry sanity check.
  Pass if using back from Wallet, Notifications, or Withdrawal returns to the prior surface cleanly and reopening the same area works without duplicate stacks, stale state, or route drift.

## Operator Notes

- Prefer one club-linked account and one no-club account for this pass.
- Prefer one compliance-restricted wallet account or fixture state for blocked-funding validation.
- Capture screenshots immediately for any blocker before relaunching.
