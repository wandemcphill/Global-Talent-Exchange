# Withdrawal Controls + Admin Treasury/Competition Controls Report

Implemented and merged into the full project:

## Backend
- Added user withdrawal request API under `/api/wallets/withdrawals`
  - supports `trade` withdrawals
  - supports `competition` withdrawals
  - competition withdrawals are blocked unless admin enables them
- Added 10% default withdrawal fee policy (`1000 bps`)
- Withdrawal requests now reserve the **requested amount + fee** in escrow
- Admin completion settles escrow to platform treasury
- Admin rejection/failure releases escrow back to the user
- Added admin control endpoints:
  - `GET/PUT /api/admin/god-mode/withdrawal-controls`
  - `GET/PUT /api/admin/god-mode/competition-controls`
- Added admin bootstrap exposure for:
  - withdrawal controls
  - competition controls
- Added bank-transfer-first operational defaults in god-mode state

## Admin Controls
- Admin can now change:
  - withdrawal percentage / fee bps
  - minimum withdrawal fee
  - competition pool top-up percentage
  - processor mode: `automatic_gateway` or `manual_bank_transfer`
  - trade withdrawals enabled/disabled
  - e-game winnings withdrawals enabled/disabled
  - bank-transfer deposit/payout toggles

## Frontend Admin UI
- God Mode screen now exposes:
  - withdrawal controls section
  - competition pool control section
  - processor mode selector
  - bank transfer toggles
  - e-game cashout toggle
  - richer withdrawal cards showing source, fee, and total debit

## Tests
- Added wallet service tests for payout holds and competition-withdrawal restrictions
- Added wallet HTTP tests for trade withdrawal requests and competition withdrawal blocking

## Merge
- Merged the latest admin/creator patch archive into the full project base before applying these changes.
