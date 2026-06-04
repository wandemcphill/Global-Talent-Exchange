# Thread 8 Canonicalization Guardrail Checklist

Scope: documentation-only checklist for GTEX canonicalization review. This file does not promote Unity, native 3D, or any payment provider as canonical product authority.

## Production Forbidden References

Mark every hit in production-facing code or docs before handoff:

- [ ] Prototype-only state is not used as authority: local balances, local match clocks, local event generators, hardcoded regen pools, auto-resolution, and demo success transitions must be mapped to backend-owned APIs before they appear in production flows.
- [ ] Mock/demo/fake/fallback wording is absent from production runtime claims unless it describes an explicitly gated local/dev/test path.
- [ ] Provider-specific payment labels are not described as canonical GTEX money authority. Canonical wording is wallet ledger, payment rail, treasury review, provider adapter, or backend payment lifecycle.
- [ ] Unity, native 3D, pseudo-3D, and original visual runtime wording is not described as canonical match authority. Canonical wording is GTEX match authority, backend/current-engine event authority, match-viewer payload, or visual/runtime adapter.
- [ ] Production copy does not claim native 3D availability unless the platform bridge is verified end to end.
- [ ] Frontend production clients do not silently import fixture/mock/demo data for canonical wallet, regen, match, notification, transfer, or competition state.
- [ ] Generated contract/docs hits are checked against their source. Do not hand-edit generated artifacts as the only fix.

## Unity And 3D Quarantine Allowance

Unity/3D references are allowed only when they stay inside one of these quarantine lanes:

| Lane | Allowed Examples | Guardrail |
| --- | --- | --- |
| Unity project/runtime | `Gtex_Test_Migration/**`, Unity build tools, scene names, live playback bootstrap, original visual runtime bridge | Allowed as engine/build integration. Never call Unity or 3D the canonical match authority. |
| P6/P6V evidence docs | `docs/GTEX_P6_*`, `GTEX_TASKS.md`, `GTEX_PHASED_PROMPTS.md`, release/runbook evidence | Allowed as current-engine hardening evidence. Keep the authority boundary explicit. |
| Match viewer disclosure | blocked native 3D screens/tests, Flutter 3D labels, pseudo-3D renderer docs | Allowed only when the UI truthfully labels live/partial/blocked state. |
| Prototype mapping docs | `docs/prototype_mapping/**`, prototype parity notes | Allowed as reference mapping. Must say prototype visuals are not runtime authority. |
| Ops tooling | Unity provisioning, hosted verification, soak, CI build checks | Allowed as operational support. Do not convert these routes into canonical product routes. |

Anything outside these lanes should be classified as `fixed` or assigned to the owning runtime thread.

## Payment Provider Quarantine Allowance

Provider references are allowed only when they stay inside one of these lanes:

| Lane | Allowed Examples | Guardrail |
| --- | --- | --- |
| Backend provider adapter | wallet/admin finance provider code, webhook verification, funding/verification service | Allowed as implementation detail behind canonical wallet ledger and rail lifecycle. |
| Tests and fixtures | backend wallet/admin finance tests, frontend wallet/admin tests, explicit mock checkout URLs | Allowed only when tests assert provider integration behavior or non-live blocking. |
| Generated contract docs | webhook paths in `FINAL_API_SCHEMA.json`, `ROUTE_MAP.json`, generated API bindings | Allowed when generated from backend routes. Regenerate from source if wrong. |
| Admin/ops documentation | reconciliation, fraud review, provider readiness, treasury controls | Allowed when provider is framed as a rail, not canonical money truth. |
| Prototype mapping docs | visual parity notes mentioning provider-labeled buttons | Allowed as mapping only. Production may use provider labels for button copy, not authority. |

Provider names in navigation, marketing, canonical feature names, or route authority language should be fixed or assigned to the wallet/payment owner.

## Local Guardrail Commands

Run from `C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE`. These are scans, not automatic fixes.

```powershell
rg -n -i --glob '!backend/generated_media/**' --glob '!backend/manual_phase1_checks/**' --glob '!backend/pytesttmp_phase1_admin/**' --glob '!**/node_modules/**' --glob '!**/Library/**' --glob '!**/Temp/**' --glob '!**/Build/**' '\b(paystack|korapay|stripe|flutterwave|payment provider|gateway provider)\b' backend frontend docs ops tools .github
```

```powershell
rg -n -i --glob '!backend/generated_media/**' --glob '!backend/manual_phase1_checks/**' --glob '!backend/pytesttmp_phase1_admin/**' --glob '!**/node_modules/**' --glob '!**/Library/**' --glob '!**/Temp/**' --glob '!**/Build/**' '\b(Unity|native 3D|3D match|3D viewer|pseudo-3D|Original Visual|OriginalFootballSimulator)\b' backend frontend docs ops tools .github Gtex_Test_Migration/Assets/Code Gtex_Test_Migration/ProjectSettings
```

```powershell
rg -n -i --glob '!backend/generated_media/**' --glob '!backend/manual_phase1_checks/**' --glob '!backend/pytesttmp_phase1_admin/**' --glob '!**/node_modules/**' --glob '!**/Library/**' --glob '!**/Temp/**' --glob '!**/Build/**' '\b(prototype|mock|demo|fallback|placeholder|fake|hardcoded)\b' backend frontend docs ops tools .github
```

Optional narrower production scan for suspicious user-facing language:

```powershell
rg -n -i '\b(native 3D session|Unity-powered|Paystack|Stripe|Flutterwave|fake|placeholder|mock\.korapay\.local|demo balance)\b' frontend/lib backend/app docs --glob '!docs/guardrails/**'
```

## Remaining Hit Classification

Use exactly one classification for each remaining hit:

| Classification | Meaning | Required Note |
| --- | --- | --- |
| `fixed` | The hit was removed, renamed, regenerated, or rewritten so it no longer violates production canon. | Include file path and the replacing canonical authority. |
| `quarantined` | The hit remains but is inside an allowed lane above. | Include lane name and why the wording cannot be removed without losing integration/test/evidence value. |
| `owned-by-thread` | The hit is real but outside this docs lane. | Include owner lane, expected thread, and why Thread 8 docs did not edit it. |

Current docs-lane classification for this pass:

| Hit Class | Classification | Owner / Quarantine Lane | Note |
| --- | --- | --- | --- |
| Provider references in backend wallet/admin finance code and tests | `owned-by-thread` | Wallet/payment provider integration | Legitimate integration strings, but payment owners must keep them behind canonical wallet ledger and rail lifecycle language. |
| Provider references in generated API contract/docs | `quarantined` | Generated contract docs | Webhook paths may include provider keys. Regenerate from backend route source if wrong. |
| Provider references in prototype mapping docs | `quarantined` | Prototype mapping docs | Mapping may mention source prototype labels. It must not promote provider labels as money authority. |
| Unity/current-engine references in `Gtex_Test_Migration/**` and Unity tools | `quarantined` | Unity project/runtime and ops tooling | Required for build/runtime integration. GTEX match authority remains outside Unity-specific wording. |
| Unity/3D references in P6/P6V docs | `quarantined` | P6/P6V evidence docs | Allowed as phase evidence under `GTEX_TASKS.md`; not canonical product authority. |
| Native 3D blocked/live/partial wording in frontend tests and route docs | `owned-by-thread` | Match viewer/native route owner | Keep truthful blocked/partial labels. Any product-copy change belongs to match viewer/native thread. |
| Mock/demo/fallback references in local ingestion/dev tooling | `owned-by-thread` | Backend ingestion/dev tooling | Local demo tooling can remain gated, but production preflight should keep rejecting mock ingestion providers. |
| Mock/demo/fallback references in production clients | `owned-by-thread` | Frontend/backend feature owners | Requires runtime review outside docs/guardrails ownership. Do not classify as fixed from this thread. |

## Handoff Checklist

- [ ] Every newly touched guardrail doc is under `docs/guardrails/**`.
- [ ] No Unity/3D or payment provider wording is introduced as canonical product authority.
- [ ] Any non-doc production hit discovered during review is assigned as `owned-by-thread`, not edited here.
- [ ] Access-denied or generated directories are called out in the handoff if they prevent a clean scan.
- [ ] Follow-up owners receive the exact command and hit class they need to review.
