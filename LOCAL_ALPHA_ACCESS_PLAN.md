# LOCAL ALPHA ACCESS PLAN

Date: 2026-06-12
Verdict: **Recommend Cloudflare Tunnel, named tunnel mode**

## Comparison

| Option | Setup | Safety | Maintenance | WebSockets | Flutter web |
| --- | --- | --- | --- | --- | --- |
| Cloudflare Tunnel | Medium for named tunnel; quick tunnel is easiest | Best if paired with Cloudflare Access / DNS ownership | Best once named hostnames are set | Compatible with HTTP/WebSocket tunneling | Good; compile app with HTTPS API URL so WebSocket URLs become WSS |
| Tailscale Funnel | Medium; requires Tailscale identity and Funnel enabled | Strong if testers are controlled, but public Funnel is still internet-facing | Good for tailnet-native teams | Likely workable for HTTP/WebSocket, but needs validation against GTEX realtime | Good, but tester onboarding is heavier |
| Ngrok | Easiest single command | Acceptable for very small tests; public random URLs unless reserved domain | Low for one-off, weaker for repeated testing unless paid/reserved domain | Good WebSocket support | Good; random URL changes force rebuild unless using reserved domain |

References:

- Cloudflare Tunnel docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Cloudflare WebSockets docs: https://developers.cloudflare.com/network/websockets/
- Tailscale Funnel docs: https://tailscale.com/kb/1223/funnel
- Tailscale Serve docs: https://tailscale.com/kb/1312/serve
- ngrok WebSockets docs: https://ngrok.com/docs/using-ngrok-with/websockets/

## Recommended Architecture

Use two public HTTPS hostnames:

- App: `https://alpha.gtex.example.com`
- API: `https://alpha-api.gtex.example.com`

Run both services only on loopback locally:

- Backend: `http://127.0.0.1:8000`
- Built Flutter web: `http://127.0.0.1:8790`

The Flutter app must be built with the public API URL because live mode requires `GTE_API_BASE_URL` at compile time.

## Exact Commands

Replace `gtex.example.com` with the Cloudflare-managed domain.

```powershell
cd 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE'

cloudflared tunnel login
cloudflared tunnel create gtex-local-alpha
cloudflared tunnel route dns gtex-local-alpha alpha.gtex.example.com
cloudflared tunnel route dns gtex-local-alpha alpha-api.gtex.example.com
```

Create `%USERPROFILE%\.cloudflared\gtex-local-alpha.yml`:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: C:\Users\ayomc\.cloudflared\<TUNNEL_UUID>.json

ingress:
  - hostname: alpha.gtex.example.com
    service: http://127.0.0.1:8790
  - hostname: alpha-api.gtex.example.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

Prepare the local alpha database:

```powershell
cd 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE'
$env:GTE_DATABASE_URL='sqlite+pysqlite:///C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/.runtime/local_alpha.db'
$env:GTE_DATABASE_READ_URL=$env:GTE_DATABASE_URL
$env:GTE_AUTH_SECRET='<local-alpha-secret>'
$env:GTE_MEDIA_SIGNING_SECRET='<local-alpha-media-secret>'
$env:GTE_CORS_ALLOW_ORIGINS='https://alpha.gtex.example.com'
$env:GTE_CORS_ALLOW_ORIGIN_REGEX=''
$env:GTE_BOOTSTRAP_ADMIN_ENABLED='1'

python backend/scripts/dev.py rebuild-demo-market --database-url $env:GTE_DATABASE_URL --seed 20260612
```

Start backend:

```powershell
python backend/scripts/dev.py runserver --database-url $env:GTE_DATABASE_URL --host 127.0.0.1 --port 8000 --demo-simulation --seed 20260612
```

Build and serve Flutter web:

```powershell
cd 'C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\frontend'
C:\flutter\bin\flutter.bat build web --no-pub --dart-define=GTE_API_BASE_URL=https://alpha-api.gtex.example.com --dart-define=GTE_BACKEND_MODE=live
cd build\web
python -m http.server 8790
```

Start tunnel:

```powershell
cloudflared tunnel --config $env:USERPROFILE\.cloudflared\gtex-local-alpha.yml run gtex-local-alpha
```

Expected URLs:

- Tester app URL: `https://alpha.gtex.example.com`
- Backend API URL compiled into app: `https://alpha-api.gtex.example.com`
- WebSocket URLs derive as `wss://alpha-api.gtex.example.com/...`

## Quick Tunnel Fallback

Only use this for a same-day smoke test, because URLs rotate:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
cloudflared tunnel --url http://127.0.0.1:8790
```

Expected URLs:

- `https://<random-api>.trycloudflare.com`
- `https://<random-app>.trycloudflare.com`

For quick tunnel mode, set backend CORS broadly enough before backend start:

```powershell
$env:GTE_CORS_ALLOW_ORIGIN_REGEX='https://.*\.trycloudflare\.com$'
```

Then rebuild Flutter using the generated API tunnel URL.

