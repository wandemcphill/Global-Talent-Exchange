# GTEX OpenAI gateway

OpenAI is called only from the Python API through `app.ai_gateway`. React, Flutter, and browser JavaScript do not receive `OPENAI_API_KEY`.

The gateway uses the official OpenAI Python SDK and the Responses API (`client.responses.create`) plus the Moderations API. Game balances, ownership, transfers, match results, jackpots, and rewards stay in the existing deterministic services. AI output is a recommendation (`authoritative: false`).

## Required server environment

Set these on the API and on the workers that already run commentary or social LLM calls (`gtex-api`, `gtex-rq-worker`, `gtex-simulation-worker`, `gtex-worker`):

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_ENABLED=true
OPENAI_MAX_RETRIES=3
OPENAI_TIMEOUT_MS=60000
```

`OPENAI_API_KEY` is `sync: false` in `render.yaml`. Enter it in the Render dashboard. Do not commit it.

## Optional server environment

```env
OPENAI_ROUTE_LEGACY_CLIENTS=true
OPENAI_MODEL_COMPLEX=gpt-4o-mini
OPENAI_MAX_INPUT_TOKENS=2000
OPENAI_MAX_OUTPUT_TOKENS=800
OPENAI_USER_REQUESTS_PER_MINUTE=12
OPENAI_GLOBAL_REQUESTS_PER_MINUTE=300
OPENAI_DAILY_BUDGET_USD=25
OPENAI_MONTHLY_BUDGET_USD=400
OPENAI_INPUT_USD_PER_MILLION=0.15
OPENAI_OUTPUT_USD_PER_MILLION=0.60
```

`OPENAI_ROUTE_LEGACY_CLIENTS=true` sends commentary, captions, debates, and virality copy through the gateway when the endpoint host is `api.openai.com` and `OPENAI_API_KEY` is set. If the central key is missing, those features keep their existing HTTP clients.

Staff dialogue stays on the deterministic writer unless `GTEX_ENABLE_LIVE_LLM_COMMS=1` or an admin enables the `staff_dialogue` feature. The reply cannot change the Layer A decision.

`OPENAI_ENABLED=false` is a process-wide kill switch. The admin desk can also disable the provider or individual features. Both the environment flag and the admin switch must be on.

## What is connected

- Match reports, scouting briefs, competition summaries, youth-development notes, and club announcements for signed-in users.
- Community moderation review, operational summaries, market explanations, and fraud-signal explanations for admins.
- Existing staff wording, live commentary, pundit debates, captions, and virality analysis, behind the flags above.
- Optional polish of the local AI reporter, off until an admin enables `reporter_polish`.

There is no endpoint that executes a wallet adjustment, transfer, prize, or ownership change from model output.

## Admin desk

Platform admins open the AI tab on the admin desk. It shows the model, whether a key is configured, request counts, token totals, estimated spend, feature switches, budgets, per-user limits, and recent error codes. It does not show the key.

Club owners and ordinary users cannot call the admin AI routes.

## Database

Migration `20261118_0270_ai_gateway` adds `ai_provider_settings`, `ai_feature_settings`, `ai_request_limits`, and `ai_usage_logs`. It does not store the API key. API startup runs Alembic when `GTE_RUN_MIGRATION_CHECK` is on. This change was not applied to production from this workspace.

Usage logs store feature, status, token counts, estimated cost, and a hash. They do not store prompts.

## Manual steps

1. Merge the pull request.
2. In Render, set `OPENAI_API_KEY` on the API and the commentary workers. Leave the value out of git.
3. Confirm `OPENAI_ENABLED=true` and `OPENAI_MODEL=gpt-4o-mini` (or another current model id).
4. Deploy and let the API migration check reach `20261118_0270_ai_gateway`.
5. Sign in as a platform admin, open the AI tab, and confirm the status is `ready` without the key being visible.
6. Leave `staff_dialogue` off until you want paid staff wording. Layer A still decides.
