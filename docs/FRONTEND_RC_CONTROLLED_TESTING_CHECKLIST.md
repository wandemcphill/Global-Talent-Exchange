# GTEX Frontend RC Controlled Testing Checklist

Branch: `codex/treasury-mvp`  
Date: `2026-03-19`  
Baseline: GTEX frontend is release-candidate ready for controlled testing. Release build generation is the next operator step.

## What This RC Validates

- Sign-in and authenticated shell entry.
- GTEX splash, logo, and header branding consistency.
- Home stability with canonical club context.
- Guided no-club onboarding instead of fallback club leakage.
- Arena entry and overview or empty-state rendering.
- Wallet entry, funding, withdrawal, and notifications access.
- Compliance-gated funding behavior when deposits are blocked.
- Notifications opening the correct workspace and refreshing read state after return.
- Withdrawal notification routing into the withdrawal workspace.
- One-step back/re-entry sanity on shell-adjacent frontend flows.

## What Is Not Yet Fully Validated

- Native push lifecycle behavior across install, background, foreground, and OS-delivered notification paths.
- Full real-world payment, bank transfer, or settlement operations beyond frontend gating and routing behavior.
- Long-session endurance, low-connectivity recovery, and broad device-matrix coverage.
- Final packaging polish beyond the controlled release-candidate build itself.

## Known Non-Blockers

- Windows executable naming still has a cosmetic mismatch.
- Existing Kotlin warning during Android build is non-blocking for this RC.
- This RC does not claim native push lifecycle validation.

## What Testers Should Report

- Any crash, blank screen, frozen loader, or route that does not resolve.
- Any wrong club name, fallback club identity, or missing no-club onboarding state.
- Any GTEX branding mismatch on splash, login, header, or shell surfaces.
- Any wallet/compliance issue where blocked funding appears enabled or incorrect instructions are shown.
- Any notification that fails to open, fails to mark read after return, or opens the wrong workspace.
- Any withdrawal notification that does not land in the withdrawal workspace.

## Reporting Format

- Include device, OS, build timestamp or artifact name, and account type used.
- Include exact step-by-step reproduction.
- Include expected result and actual result.
- Include at least one screenshot; add screen recording if the issue involves routing or refresh behavior.
