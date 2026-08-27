# Global Talent Exchange

See also:
- `Docs/README.md`
- `API_DOCUMENTATION.md`
- `DEPLOYMENT_GUIDE.md`
- `ADMIN_SETUP_GUIDE.md`

## Canonical production deployment

- Web: `https://gtex-web-tw6c.onrender.com`
- API: `https://gtex-api-opea.onrender.com`
- KoraPay webhook: `https://gtex-api-opea.onrender.com/integrations/payments/korapay/webhook`

The production frontend is configured for the canonical API above. Local/demo instructions remain explicitly local-only.

## Local setup

Commands below assume Python 3.14 and SQLite for local development.

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

## Frontend quick start

```powershell
cd frontend
flutter pub get
flutter analyze
flutter test
```

For the full local setup, smoke-test matrix, and deployment guidance, use the canonical docs in `Docs/`.
