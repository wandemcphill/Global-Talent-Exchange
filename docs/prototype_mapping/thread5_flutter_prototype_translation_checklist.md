# Thread 5 Flutter Prototype Translation Checklist

Verification date: 2026-05-29.

Scope: docs-only prototype mapping for Thread 5. No frontend, backend, shared
contract, router, match, shell, or Unity files were edited.

## Source Coverage

- `C:\Users\ayomc\Downloads\Gtex_prototype_v13 (5).html` is the canonical
  source for the requested named functions and states.
- `C:\Users\ayomc\Desktop\GTEX_FOOTBALL_OS_HIGH_FIDELITY_PROTOTYPE.html` was
  present and checked. It is an alternative high-fidelity/capital prototype:
  it has wallet/capital data and payment-review copy, but no direct
  `renderBuildASon`, `completeBuildSon`, `renderWallet`,
  `renderAdminPayments`, `renderRegenWorld`, `bracketTree`, or competition
  bracket equivalent by function name.

## V13 Function Proof Map

| Feature | V13 proof | Prototype lifecycle/state | Flutter target surface | Backend-truth guardrail |
| --- | --- | --- | --- | --- |
| Build-a-Son | `BUILD_SON_TRAITS_POOL` line 1888, `renderBuildASon()` lines 1890-2045, `completeBuildSon()` lines 2047-2091 | `buildSonStep` starts at `0`; steps are Choose Parent, Inherit Traits, Name & Position, Confirm. State is `buildSonParent`, `buildSonTraits`, `buildSonName`, `buildSonPos`, `buildSonNat`. Affordability uses `walletGTC - walletReserved >= 200`. Completion deducts local wallet state and pushes into `ACADEMY_PLAYERS`. | `frontend/lib/features/build_a_son/presentation/build_a_son_screen.dart`, `frontend/lib/features/regen_creation/presentation/build_a_son_wizard.dart`, `frontend/lib/features/build_a_son/data/build_a_son_creation_client.dart`, `frontend/lib/features/regen_creation/data/build_a_son_creation_client.dart`, `frontend/lib/data/regen_creation_api.dart` | Flutter must use backend preview/order/payment/generate-after-payment truth for generation, DNA, OVR, potential, price, wallet availability, and academy visibility. Do not port prototype random projection math or local academy mutation as authority. |
| Wallet | `showEmptyWallet` line 897, wallet balances lines 950-952, `renderWallet()` lines 2330-2365, empty/history helpers lines 2368-2403, payment modal entry `openPayModal(method)` lines 4016-4207 | Populated/empty wallet view, deposit history, transaction log, KoraPay funding, manual bank transfer, basket checkout, and withdrawal request states. | `frontend/lib/screens/wallet/gte_wallet_overview_screen.dart`, `gte_funding_flow_screen.dart`, `gte_deposit_history_screen.dart`, `gte_withdrawal_flow_screen.dart`, `gte_bank_details_screen.dart` | Balances, provider readiness, KoraPay session state, manual proof review, ledger rows, withdrawal eligibility, receipts, and status transitions must come from wallet APIs. Prototype success toasts are fixtures only. |
| Admin Payments | `adminPayTab` line 954, `adminPayQueue` lines 955-964, `renderAdminPayments()` lines 3006-3120, `adminApprovePayment()` line 3614, `adminRejectPayment()` line 3627, `adminReinstatePayment()` line 3637, `openProofModal()` line 4885 | Tabs are pending, approved, rejected, and bids. Pending includes Manual/KoraPay rows, proof action for Manual, approve/reject controls. Rejected rows can be reinstated. Bid tab reads pending transfer bids. Prototype approve mutates queue state and credits `walletGTC`. | `frontend/lib/screens/admin/admin_command_center_screen.dart`, `frontend/lib/data/admin_command_center_api.dart`, `frontend/lib/models/admin_finance_models.dart`, `frontend/lib/data/admin_finance_api.dart` | Admin review must use backend treasury/deposit/bid review endpoints and audit state. No local queue mutation or wallet crediting should be treated as settlement authority. Proof, dispute, KYC, and rail controls stay backend-owned. |
| Regen World | `regenGenFilter` and `regenDetailId` lines 899-900, `renderRegenWorld()` lines 4991-5059, `regenWorldCard()` lines 5061-5097, `regenDetailPanel()` line 5099 onward | Generation filter is `all`, `gen-1`, `gen-2`, `gen-3`. Detail panel toggles by selected card id. Cards show generation, nationality, origin, POT, DNA integrity, traits, value, and basket action. Detail shows DNA breakdown, all traits, inherited-from text, lineage/action panel. | `frontend/lib/features/regens/regens_screen.dart`, `frontend/lib/data/regen_universe_api.dart`, `frontend/lib/controllers/regen_universe_controller.dart`, `frontend/lib/shared/providers/regen_provider.dart` | Regen cards, lineage, DNA, values, tracking, bid/watch/basket eligibility, and empty states must hydrate from Regen Universe APIs. `REGEN_DATA` is fixture seed only. |
| Competition Bracket | `compTab = 'bracket'` line 920, `renderCompete()` lines 2458-2484, `compWizStep` line 2457, `BRACKET_DATA` lines 5924-5941, `bracketTree()` lines 5943-5965 | Competition hub has Bracket and Standings tabs. Bracket renders rounds from `BRACKET_DATA`: Quarter Finals, Semi Finals, Final. Match statuses are `done` and `upcoming`; final match has `final:true`; clicking a match navigates to `match`. | `frontend/lib/features/compete/data/competition_bracket_models.dart`, `frontend/lib/features/compete/presentation/competition_bracket_widgets.dart`, `frontend/lib/features/compete/compete_bracket.dart`, `frontend/lib/features/competitions_hub/presentation/gte_competitions_hub_screen.dart`, `frontend/lib/screens/competitions/competition_detail_screen.dart` | Bracket UI must render only backend `CompetitionBracketPayload`/lifecycle truth. Missing rounds should stay blocked/degraded, not generate a placeholder bracket. Active route mounting and legacy competition hub replacement remain outside this docs-only ownership. |

## Checklist

- [x] Proved the requested v13 prototype functions and backing states by line
  reference.
- [x] Checked the high-fidelity desktop prototype and documented that it is not
  a direct named-function equivalent for these Thread 5 surfaces.
- [x] Mapped Build-a-Son, Wallet, Admin Payments, Regen World, and Competition
  Bracket prototype behavior to current Flutter target surfaces.
- [x] Marked prototype local state and generated data as fixture/parity input,
  not production truth.
- [ ] Confirm final route mounting for compete bracket widgets in the active
  competition hub/detail flows. This is outside docs-only ownership.
- [ ] Prove staging/live backend flows for KoraPay funding, manual deposit
  review, withdrawal settlement, Build-a-Son generation, Regen marketplace
  actions, and bracket lifecycle payloads.
- [ ] Keep any future parity work scoped to backend-provided models and API
  states; do not reintroduce prototype-only random projection, local wallet
  crediting, or placeholder bracket generation.

## Open Gaps And Blockers

- High-fidelity prototype parity is informational only for this task because
  the desktop file does not expose the requested named functions.
- Admin payment parity has a direct prototype surface, but production settlement
  requires backend audit trails and treasury endpoints before UI approval/reject
  controls can be considered complete.
- Competition bracket rendering exists as backend-payload widgets, but active
  route integration and replacement of legacy hub summaries are blocked by
  ownership outside this Thread 5 docs pass.
