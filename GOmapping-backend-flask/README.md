# GOmapping Backend (Flask)

Flask implementation of the GOmapping backend, migrated from the Django version.

## Quick Start

```bash
cd GOmapping-backend-flask
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Server starts at `http://localhost:8000`.

## Environment Variables

- `FLASK_DEBUG` (default: `true`)
- `DB_ENGINE` (default: `sqlite`, options: `sqlite` / `mssql`)
- `SQLITE_PATH` (default: `gomapping.db`)
- `AUTO_CREATE_TABLES` (default: `true`, SQLite only)
- `DATABASE_URL` (optional override, if set it takes highest priority)
- `DB_NAME` (used by MSSQL mode)
- `DB_USER` (used by MSSQL mode)
- `DB_PASSWORD` (used by MSSQL mode)
- `DB_HOST` (used by MSSQL mode)
- `ODBC_DRIVER` (used by MSSQL mode, default: `ODBC Driver 17 for SQL Server`)
- `DB_TRUST_CERT` (used by MSSQL mode, default: `yes`)
- `CORS_ALLOWED_ORIGINS` (default: `*`)
- `AZURE_OPENAI_ENDPOINT` (default: `https://pfbi-openai-test.openai.azure.com/`)
- `AZURE_OPENAI_LOCATION` (default: `westeurope`)
- `AZURE_OPENAI_API_VERSION` (default: `2025-01-01-preview`)
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT` (Azure model deployment name, default: `gpt-4o-mini`)
- `CACHE_TTL_SECONDS` (default: `3600`)

## SQLite Notes

- SQLite is now the default database for this Flask backend.
- No external database server is required.
- The app auto-creates tables on startup when using SQLite.
- The SQLite file is created at `GOmapping-backend-flask/gomapping.db` by default.

## API Endpoints

Both route styles are supported to keep frontend compatibility:
- `/go-summary/` and `/api/go-summary/`
- `/go-detail/<go_id>/` and `/api/go-detail/<go_id>/`
- `/org-mappings/<go_id>/` and `/api/org-mappings/<go_id>/`
- `/mapping-dashboard/` and `/api/mapping-dashboard/`
- `/ai-recommendation/` and `/api/ai-recommendation/`
- `/sync-status/` and `/api/sync-status/`
- `/sync-history/` and `/api/sync-history/`
- `/trigger-sync/` and `/api/trigger-sync/`
- `/check-for-updates/` and `/api/check-for-updates/`
- `/merge-decisions/` and `/api/merge-decisions/`
- `/merge-decisions/create/` and `/api/merge-decisions/create/`
- `/merge-decisions/<decision_id>/` and `/api/merge-decisions/<decision_id>/`
- `/merge-decisions/<decision_id>/status/` and `/api/merge-decisions/<decision_id>/status/`
