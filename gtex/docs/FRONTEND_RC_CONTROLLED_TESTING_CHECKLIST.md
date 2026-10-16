# GTEX Frontend RC Tester Instructions

Branch: `codex/treasury-mvp`  
Date: `2026-03-19`  
Artifact: release APK for controlled testing

Use this pack for real-tester runs only. Keep testing concise, stay on assigned scenarios, and file one report per issue.

## Before You Start

- Install the assigned release APK.
- Use only the account type assigned to your scenario.
- Capture a screenshot for every issue.
- Start a screen recording before any routing, refresh, notification, or back/re-entry issue that may be hard to reproduce.

## Who Should Test What

- All testers: launch the APK, confirm GTEX splash/logo/header branding, and sign in successfully.
- Club-linked account tester: verify Home canonical club context, Arena entry, Wallet entry, notifications open/read refresh, withdrawal notification routing, and one back/re-entry sanity check.
- No-club account tester: verify the guided Home onboarding state with `Create Club`, `Join Club`, and `Explore Arena`.
- Compliance-restricted account tester: verify blocked funding behavior, `Compliance action required`, and entry into the compliance center.

If the group is small, one tester may rotate across all three account types. Keep reports separated by account type.

## Evidence To Capture

- Screenshot any visible error, wrong club context, incorrect branding, or blocked/unblocked state that looks wrong.
- Screen recording for crashes, blank screens, route failures, notification open/read refresh issues, withdrawal routing issues, and back/re-entry problems.
- Include the final visible screen after the failure, not only the step before it.

## When To Report Immediately

- Report immediately if the APK crashes, freezes, shows a blank screen, fails sign-in, opens the wrong workspace, loses the club context, or exposes funding actions that should stay blocked.
- Keep testing other scenarios only if the issue is not a blocker for the assigned account path.

## Severity Labels

- `Blocker`: testing cannot continue on the assigned path.
- `Major`: main flow is wrong or unreliable, but partial testing can continue.
- `Minor`: issue is real but does not break the main flow.
- `Cosmetic`: visual or copy issue only.
