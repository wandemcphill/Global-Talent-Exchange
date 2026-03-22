# GTEX Frontend RC Scenario And Account Matrix

Branch: `codex/treasury-mvp`  
Date: `2026-03-19`

## Required Account Types

- `club-linked account`
- `no-club account`
- `compliance-restricted account`

## Recommended Small-Group Split

| Tester | Account Type | What To Validate | Evidence To Capture |
| --- | --- | --- | --- |
| Tester A | Club-linked account | Launch APK, confirm GTEX branding, sign in, verify Home keeps the correct club context, enter Arena, enter Wallet | Screenshot of successful sign-in shell and Home with the correct club context |
| Tester A | Club-linked account | Open Notifications, confirm unread item opens correctly, return and confirm read-state refresh | Before/after screenshots of unread to read; recording if refresh fails |
| Tester A | Club-linked account | Open a withdrawal notification and confirm it lands in the withdrawal workspace; perform one back/re-entry check | Recording from notification tap through return/re-entry; screenshot if wrong workspace opens |
| Tester B | No-club account | Sign in and verify Home shows guided onboarding with `Create Club`, `Join Club`, and `Explore Arena` | Screenshot of the no-club Home state |
| Tester C | Compliance-restricted account | Sign in, open Wallet or funding, confirm funding stays blocked, confirm `Compliance action required` and `Open compliance center` appear | Screenshot of the blocked funding state; recording if deposit actions appear enabled |

## Minimum Scenario Coverage

| Scenario | Required Account Type | Pass Signal |
| --- | --- | --- |
| Splash, logo, header branding | Any assigned account | GTEX branding is consistent and no legacy branding appears |
| Sign-in | Any assigned account | Sign-in succeeds and lands in the main shell |
| Home canonical club context | Club-linked account | Correct club is shown and no fallback club appears |
| No-club onboarding | No-club account | `Create or join a club to unlock Home` appears with the expected actions |
| Arena entry | Club-linked account | Arena opens without route failure |
| Wallet entry | Club-linked account | Wallet opens and expected wallet actions are available |
| Blocked funding state | Compliance-restricted account | Funding remains locked and compliance guidance is shown |
| Notifications open/read refresh | Club-linked account | Opening an unread item marks it read after return |
| Withdrawal notification to workspace | Club-linked account | Withdrawal notification opens the withdrawal workspace |
| Back/re-entry sanity | Club-linked account | Returning and reopening stays stable with no route drift |
