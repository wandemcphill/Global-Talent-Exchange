# GTEX Frontend RC Release Notes

Branch: `codex/treasury-mvp`  
Date: `2026-03-19`  
Status: frontend release candidate ready for controlled testing. Release build generation is the next step.

## Highlights

- Canonical club handling is tightened across the active shell and Home. The frontend now stays on the real session club context, removes remaining fallback-club behavior, and shows guided no-club onboarding when no canonical club is present.
- Wallet, compliance, and funding flows are hardened for restricted-capital states. Login and wallet surfaces now communicate active restrictions clearly, and the funding flow repaints correctly after compliance refresh instead of exposing premature manual funding actions.
- Notification and workspace routing is stabilized. Notification settings, wallet-adjacent inbox flows, read-state refresh after open, and withdrawal-notification routing into the withdrawal workspace were all tightened for RC use.
- Arena, Home, and shell-adjacent navigation are more stable. Arena overview and empty-state handling were hardened, wallet and community entry points were stabilized, and basic back/re-entry behavior around wallet and notification flows is covered.
- Branding is complete for the frontend RC surface. Canonical GTEX icon and logo assets are applied across app and web branding surfaces, including splash/header-adjacent presentation.

## Accepted Fix Areas In This Branch

- Wallet/compliance/funding hardening.
- Notification/workspace routing stabilization.
- Arena/home/shell stability improvements.
- Canonical GTEX branding completion.
- Frontend regression coverage for login, funding, home, arena, and withdrawal-notification re-entry paths.

## Known Limitations

- This RC does not claim native push lifecycle validation.
- Windows executable naming still has a cosmetic mismatch.
- Existing Kotlin warning during Android build remains non-blocking.
