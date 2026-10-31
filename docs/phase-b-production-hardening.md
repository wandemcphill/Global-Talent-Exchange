# Phase B Production Hardening

## Canonical production endpoints

- Web: `https://gtex-web-np2t.onrender.com`
- API: `https://gtex-api-2gtu.onrender.com`
- KoraPay server-to-server webhook: `https://gtex-api-2gtu.onrender.com/integrations/payments/korapay/webhook`

The Render Blueprint keeps the browser API base URL and provider callback aligned with these production endpoints. This document is intentionally non-secret and exists as an operator-facing deployment contract.
