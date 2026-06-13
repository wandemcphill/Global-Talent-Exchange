# LOCAL ALPHA SEEDING PLAN

Date: 2026-06-12
Verdict: **Use isolated local SQLite database plus audited API/script seeding**

## Requirements Mapping

| Requirement | Plan |
| --- | --- |
| Reversible | Use a dedicated `.runtime/local_alpha.db`; stop services and replace/delete this file to reset |
| Auditable | Write every seeded account/action to `.runtime/local_alpha_seed_manifest.jsonl` |
| Non-production | Use local SQLite only; never point commands at staging/production `DATABASE_URL` |
| Isolated | Use `GTE_DATABASE_URL=sqlite+pysqlite:///.../.runtime/local_alpha.db` and Cloudflare Tunnel only to local loopback |

## Baseline Seed

```powershell
cd 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE'
$env:GTE_DATABASE_URL='sqlite+pysqlite:///C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/.runtime/local_alpha.db'
python backend/scripts/dev.py rebuild-demo-market --database-url $env:GTE_DATABASE_URL --seed 20260612
```

This seeds deterministic demo users, wallets, holdings, players, and liquidity.

Known local seed users from `Docs/RUNBOOK_LOCAL_DEV.md`:

- `seed.fan@gte.local`
- `seed.scout@gte.local`
- `seed.admin@gte.local`

## Account Types

Create alpha accounts through the same app/API paths testers use where possible:

- player accounts: `/api/v2/auth/signup/player`
- club accounts: player signup plus club creation flow
- creator accounts: creator application/provisioning flow
- admin accounts: bootstrap admin env or admin access endpoint from a bootstrap super-admin session

Do not seed payment rails beyond KoraPay/manual bank transfer.

## Suggested Manifest Row

```json
{"at":"2026-06-12T00:00:00Z","actor":"local-alpha-seed","kind":"player","email":"alpha.player01@gte.local","seed":"20260612","db":"local_alpha.db","reversible_by":"delete local_alpha.db or restore pre-seed copy"}
```

## Reset / Rollback

```powershell
Stop-Process -Name python -ErrorAction SilentlyContinue
Copy-Item .runtime\local_alpha.db .runtime\local_alpha.before-reset.db -Force
Remove-Item .runtime\local_alpha.db -Force
python backend/scripts/dev.py rebuild-demo-market --database-url $env:GTE_DATABASE_URL --seed 20260612
```

## Safety Rules

- Never use `gte_backend.db` for alpha testers unless it has been intentionally backed up.
- Never seed into production or staging.
- Never use Paystack labels, routes, or test rails.
- Keep alpha passwords temporary and rotate/delete after the test window.

