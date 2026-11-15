# GTEX Coin Trader KYC — DIDit production setup

GTEX uses DIDit as the production identity-verification provider for Coin Trader accounts. The application creates a real DIDit verification session, stores its session ID and GTEX reference, and accepts an account decision only from a validly signed provider webhook.

## Required API environment

Set these variables on the GTEX API service (for example, in the Render service environment):

- \`GTE_DEFAULT_IDENTITY_PROVIDER=didit\`
- \`GTE_DIDIT_API_KEY\` — API key from the DIDit workspace
- \`GTE_DIDIT_WORKFLOW_ID\` — the workflow ID used for GTEX Coin Trader checks
- \`GTE_DIDIT_WEBHOOK_SECRET\` — the signing secret configured for the DIDit webhook

Do not commit credentials to the repository or put them in frontend build variables. The API responds with HTTP 503 when live credentials are missing; it never silently issues a fake production session.

## DIDit workflow

Configure the workflow in the DIDit dashboard to include the actual checks GTEX requires, such as supported government identity-document verification, selfie capture, liveness and face matching. The specific document types and country coverage are determined by the DIDit workflow and account plan, not by a frontend label.

Configure a webhook destination to the deployed GTEX API:

\`POST https://<GTEX-API-HOST>/api/kyc/webhooks/didit\`

Subscribe to the status-updated event. GTEX validates the provider signature and timestamp, correlates both the DIDit session ID and GTEX vendor reference, and only activates a Coin Trader after an approved final decision. In-review and retry states remain pending.

## Product scope

The connected hosted verification path is currently for Coin Trader onboarding. Ordinary User and Creator signup do not start a DIDit identity session. Creator signup has its own creator-account flow; it is not equivalent to identity-document KYC.

## Sandbox

The sandbox adapter is available only when the API startup profile is test/development or when an operator explicitly enables \`GTE_KYC_ALLOW_SANDBOX=true\` for a controlled non-production environment. Do not enable it in production. Smile ID is not advertised as a live option until its API and webhook integration is implemented.
