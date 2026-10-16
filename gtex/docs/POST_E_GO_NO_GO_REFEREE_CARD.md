# GTEX Post-E Go/No-Go Referee Card

Use this after the next narrow post-E fix pass. This is the final live-mode launch-candidate gate for the current phase.

## Go only if all of these are true

### Shell and startup

- [ ] `/app/home` loads without shell-level unavailable state.
- [ ] `/app/club` loads without shell-level unavailable state.
- [ ] Windows desktop app launches and stays responsive.
- [ ] Signed-in and signed-out shell behavior is correct.

### Route correctness

- [ ] Trade -> Club sale market opens the public club sale market or listing surface, not a wrong club-scoped detail route.
- [ ] Trade -> Creator shares either opens the correct canonical club-scoped market or shows an explicit club-selection-required state.
- [ ] Admin -> Creator shares opens the admin control surface, not the club-selection dead end.

### Club sale

- [ ] Public listings load.
- [ ] Listed club detail loads with valuation and asking price.
- [ ] Owner inbox is accessible only to the owner.
- [ ] Owner UI shows `Counteroffer`.
- [ ] Owner UI shows `Accept`.
- [ ] Owner UI shows `Reject`.
- [ ] Buyer actions are wired or clearly classified if still intentionally partial.
- [ ] Settlement visibility behaves correctly for executed sale price, platform fee, and seller net.
- [ ] There is no fake "no sale yet" messaging when history is merely restricted.

### Creator share, stadium, and fan prediction

- [ ] Creator share route uses the correct club scope.
- [ ] Creator stadium route uses the correct club and match scope.
- [ ] Fan prediction does not rely on placeholder featured IDs.
- [ ] Canonical guard states are explicit and correct.

### Admin surfaces

- [ ] League finance overview renders real data when the backend endpoint returns `200`.
- [ ] Settlements renders either data or an explicit empty state.
- [ ] Gift stabilizer renders correctly for admin only.
- [ ] Creator stadium admin renders correctly for admin only.
- [ ] Creator shares admin renders correctly for admin only.
- [ ] Guest and non-admin gating remain correct.

### Verification health

- [ ] Thread D reports `0` analyzer errors.
- [ ] Targeted route and widget tests pass.
- [ ] Live Thread E smoke shows no unresolved high-risk frontend route or render issues.
- [ ] Any remaining issues are only warning or info backlog, legitimate empty state, or known non-blocking desktop route-launch quirk.

## No-go if any of these remain

- [ ] `/app/home` still fails due to shell identity `404`.
- [ ] `/app/club` still fails due to shell identity `404`.
- [ ] Trade -> Club sale market still routes to the wrong place.
- [ ] Trade -> Creator shares still uses the wrong club scope.
- [ ] Admin -> Creator shares still lands on club selection instead of admin control.
- [ ] League finance still shows Not Found while the backend report endpoint returns `200`.
- [ ] Owner-only club sale UI cannot be meaningfully verified.
- [ ] Any high-risk live path is still failing because of frontend route or render wiring.
- [ ] A new backend change is required beyond a tiny compatibility fix.

## Acceptable leftovers for launch-candidate status

These are not launch-blocking for this phase if everything in the go section is green:

- Analyzer warnings or info backlog with no hard errors.
- Empty settlements because no rows exist yet.
- Empty fan-prediction leaderboard because the fixture is open or unsettled.
- Lack of full session persistence across app restart, if that remains accepted current behavior.
- Desktop `--route` launch unreliability, if normal in-app navigation works.

## Decision rule

### GO

Choose `GO` only if the post-E fix pass clears all of the following and nothing new high-risk appears:

- Home
- Club
- Market club sale
- Market creator shares
- Admin creator shares
- League finance

### NO-GO

Choose `NO-GO` if even one of the live-mode items above remains broken.

## Required structure for the next report

Use this exact section order:

```md
## Summary

## Exact files changed

## Root cause for each of the 5 live failures

## What was fixed

## Verification results for:
- /app/home
- /app/club
- Trade -> Club sale market
- Trade -> Creator shares
- Admin -> Creator shares
- Admin -> League finance

## Remaining blockers

## Final recommendation: GO or NO-GO
```
