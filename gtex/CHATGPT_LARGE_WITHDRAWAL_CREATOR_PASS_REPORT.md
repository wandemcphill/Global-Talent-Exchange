# ChatGPT Large Withdrawal + Creator Finance Pass

This pass focused on two larger GTEX surfaces that were still thin in the full zip:

1. **Withdrawal quote / receipt / audit visibility**
2. **Creator finance summary surfaces**

## What was added

### Wallet / Treasury
- Added `POST /api/wallets/withdrawals/quote`
  - returns gross amount, platform fee, total debit, estimated fiat payout, processor mode, payout channel, and eligibility snapshot
  - supports `trade` and `competition` source scopes
- Added `GET /api/wallets/withdrawals/{withdrawal_id}/receipt`
  - returns a user-facing receipt with gross amount, fee amount, total debit, payout rail, and the nested withdrawal record
- Expanded withdrawal response payloads to include:
  - `source_scope`
  - `net_amount`
  - `processor_mode`
  - `payout_channel`
- Treasury withdrawal creation now accepts a source scope and persists it into payout metadata
- Wallet withdrawal creation now blocks requests when admin withdrawal controls disable the relevant source scope

### Creator finance
- Added `GET /api/creators/me/finance`
- Summary includes:
  - total gift income
  - total reward income
  - total withdrawn gross
  - total withdrawal fees
  - total withdrawn net
  - pending withdrawals
  - active competitions
  - attributed signups
  - qualified joins
  - short insight strings for dashboard usage

## Files touched
- `backend/app/treasury/schemas.py`
- `backend/app/treasury/service.py`
- `backend/app/wallets/router.py`
- `backend/app/schemas/creator_responses.py`
- `backend/app/segments/creators/segment_creators.py`
- `backend/tests/referrals/conftest.py`
- `backend/tests/referrals/test_api_creator_profiles.py`
- `backend/tests/wallets/test_wallet_http.py`

## Validation performed here
- Python compile check passed for all edited backend files and the added/updated tests.

## Validation blocked in this container
- Full pytest execution was blocked in this environment because the container runtime currently does not have `sqlalchemy` installed for test execution.
- That means the code is syntax-checked here, but runtime test execution still needs your local environment.
