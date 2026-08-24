# Phase B deployment contract

## Current Render services

- API: `https://gtex-api-opea.onrender.com`
- Web: `https://gtex-web-tw6c.onrender.com`
- KoraPay server callback: `https://gtex-api-opea.onrender.com/integrations/payments/korapay/webhook`

The browser redirect URL is a separate client-side concern and must not be used as the server-to-server KoraPay notification endpoint.

`render.yaml` is the repository source of truth for the API base URL and KoraPay notification URL. Stale `gtex-api-cijn.onrender.com` references are prohibited.
