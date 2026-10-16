# Phase B Production Hardening

## Canonical production endpoints

- Web: `https://gtex-web-tw6c.onrender.com`
- API: `https://gtex-api-opea.onrender.com`
- KoraPay server-to-server webhook: `https://gtex-api-opea.onrender.com/integrations/payments/korapay/webhook`

The Render Blueprint keeps the browser API base URL and provider callback aligned with these production endpoints. This document is intentionally non-secret and exists as an operator-facing deployment contract.
