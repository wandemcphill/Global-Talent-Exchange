# LOCAL ALPHA MONITORING

Date: 2026-06-12
Verdict: **PASS for local alpha observability baseline**

## Evidence

`python -B -m pytest -p no:cacheprovider -q backend/tests/observability backend/tests/wallets/test_wallet_event_backbone.py backend/tests/realtime/test_admin_export_realtime.py`

Result: **13 passed**

Coverage:

- runtime probe metrics
- monitoring dashboard
- metrics endpoint behavior
- config snapshot security
- admin ops router
- wallet event backbone
- admin export realtime events

## Where Logs Appear

| Source | Location |
| --- | --- |
| Backend HTTP/app logs | terminal running `python backend/scripts/dev.py runserver ...` |
| Uvicorn access/errors | same backend terminal |
| Local alpha backend boot probe logs | `.runtime/local_alpha_backend.out.log`, `.runtime/local_alpha_backend.err.log` |
| Static frontend server logs | `.runtime/local_alpha_frontend.out.log`, `.runtime/local_alpha_frontend.err.log` |
| Admin audit JSONL | configured admin runtime path, including `admin_god_mode.audit.jsonl` under the app config/runtime directory |
| Wallet events | DB ledger tables, wallet event backbone, and outbox/domain event tests |
| Transfer events | transfer-market tests and wallet reservation ledger/event records |
| Websocket events | backend realtime gateway logs plus contract tests in `backend/tests/realtime` |

## Failure Investigation

1. Capture tester email, approximate time, URL, and action.
2. Check backend terminal for HTTP status and exception trace.
3. Query auth/session state if login/session failed.
4. Query wallet ledger entries and payout/payment events if money changed.
5. Query transfer bids/reservations if market action failed.
6. Check realtime gateway logs and browser console if live updates failed.
7. Reproduce using the same alpha DB before resetting data.

## Local Health Checks

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl http://127.0.0.1:8000/version
curl http://127.0.0.1:8000/diagnostics
```

The local boot probe confirmed `/health`, `/ready`, and `/version` respond after migrations. `/health` reports local degraded mode when Redis/Kafka are not configured; that is acceptable for this local alpha but should be visible to the operator.

