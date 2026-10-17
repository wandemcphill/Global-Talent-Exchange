# GTEX Owner Console, Phase 2: inline decisions + Trust & Payouts desk

Phase 1 is already built: the native Flutter Owner Console is the home a signed-in owner sees, with Control Center, My Clubs, Market & Transfers, Manager & Squad and Academy / Regens.
Phase 2 lets owners settle Today's Decisions without leaving the console, and gives admins a review desk for trust and payouts.

## Who it's for
- **Club owners**: act on bids, contracts, sponsor offers, manager requests and invites straight from the home.
- **Admins and super-admins**: review withdrawals, integrity flags and held payouts in a new Admin Review section. Nobody else sees it, and the backend refuses anyone else.

## Core features and experience

### Inline actions on Today's Decisions
- Each decision row shows the buttons that decision offers, labelled exactly as the game writes them. For example:
  - **Transfer bid**: "Accept bid" / "Reject"
  - **Regen breakthrough** (contract renewal): "Offer improved academy contract (1,000)" / "Acknowledge"
  - **Player unrest**: "Promise first-team minutes" / "Transfer-list him" / "Ignore"
  - **Facility request**: "Approve spend (X)" / "Reject"
  - **Manager request**: "Approve budget & open market" / "Reject"
  - **Sponsor or endorsement offer**: "Sign sponsor" or "Approve endorsement" / "Decline"
  - **Competition invite**: "Enter competition" / "Not now"
  - **Manager meeting**: "Publicly back the manager" / "Decline meeting"
- Every decision type the backend supports works this way. The buttons come from the decision itself, so any new type the game adds later gets its buttons automatically.
- Actions that spend or move money (accept a bid, approve a spend, pay a contract, enter a paid competition) ask for a quick confirmation first: "Accept 12,400 GTX for Ade Bello?"
- While an action runs, the row shows a spinner and its buttons are disabled, so nothing is sent twice.
- On success the row shows the game's outcome line (for example "Ade Bello sold for 12,400 (5% platform fee). Funds added to club cash."). The Control Center then refreshes, so the decision count, club cash, health and inbox update.
- On failure (for example not enough club cash) the row stays and shows a clear error, and the owner can try again.
- Tapping the row itself (not a button) still opens the related screen, as in phase 1.

### Admin Review section (admin and super-admin only)
- A new "Admin Review" item in the left menu, shown only to admin roles, next to the existing admin-only "Seed default tournaments".
- **Trust & Payouts desk**, in three panels:
  - **Withdrawal queue**: pending and held withdrawals with owner, amount (GTX and ₦), bank details, and when they were requested. Actions: **Approve**, **Hold**, **Reject**, each with an optional note. Reject and Hold ask for confirmation.
  - **Risk flags**: open integrity flags with type, severity, club, detail and score impact. Actions: **Clear** or **Action**.
  - **Held payouts**: held ledger payouts with amount, club and reason. Action: **Release**, after a confirmation.
- Quiet states: "Queue clear", "No open flags", "Nothing held".
- After any action the item leaves its list, and the panel counts update.
- An owner who opens the section directly gets an "Admins only" message, and the backend returns 403.

## User flow
1. An owner signs in and lands on Control Center.
2. In Today's Decisions they tap "Accept bid", confirm, and see the outcome. Club cash and the decision count update in place.
3. An admin also sees "Admin Review" in the menu, opens the Trust & Payouts desk, approves a withdrawal with a note, and clears a risk flag.

## UI/UX feel
- Same GTEX Flutter look as phase 1: dark command-centre panels, gold for decisions, red for high priority and risk, cyan for payouts.
- Primary action as a filled pill, the others as ghost buttons. On phone widths the buttons wrap under the row.
- Each panel has its own loading, empty and "unavailable, retry" state.

## Implementation notes
- No new backend endpoints. Phase 2 uses the existing GTEX backend:
  - `POST /owner/inbox/{id}/decide` with `{action}`. The decision list already carries its actions and payload.
  - `GET /owner/admin/review-queue`
  - `POST /owner/admin/withdrawals/{id}/review` with `{decision: approve|reject|hold, note}`
  - `POST /owner/admin/flags/{id}/{clear|action}`
  - `POST /owner/admin/payouts/{id}/release`
- Admin endpoints are already guarded server-side (admin and super_admin roles only). The Flutter menu entry is hidden for other roles as well.
- Flutter changes:
  - `owner_console_api.dart`: carry actions, payload and outcome on decisions; add the decide call; add review-queue models and the admin calls.
  - `owner_console_sections.dart`: inline decision buttons with confirm, busy and outcome states; a new Admin Review section.
  - `owner_console_screen.dart`: an `admin` section in the enum and menu, for admins only.

## Testing
- Flutter widget tests with a fake reader. Decisions: buttons render from the actions, confirmation appears for money actions, the outcome shows, and the list refreshes. Admin: the menu is hidden for owners and shown for admins, the three panels render with their quiet states, and the actions call the right API.
- `flutter analyze`, the existing owner/regen/market suites, and a web build.
- A screenshot check, then the testing agent. Everything stays read-only on the live database: no decisions resolved and no withdrawals, flags or payouts changed on real records. Write paths are covered by the widget tests and the backend's existing role guard (403 for non-admins).

## Assumptions
- "Renew contract" maps to the game's existing contract decision, the regen breakthrough "improved academy contract (1,000)". No new contract system is added.
- Inline actions call the same backend logic the React preview used, so outcomes match the existing game rules exactly.
- Withdrawals stay manual bank transfers. Approving one only marks it approved, and the admin still sends the money by hand.
- The React preview stays unchanged in phase 2.

## Later phases (unchanged)
- **Phase 3**: owner alerts in the Owner Inbox, manager request and regen pressure depth, a parity check against the React preview, then the React frontend is retired.
- **Phase 4**: unified ledger and anti-collusion hardening.
- **Phase 5**: football-native gifting and sponsor inventory.
