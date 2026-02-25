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
- `DB_NAME` (default: `gomapping`)
- `DB_USER` (default: `demo`)
- `DB_PASSWORD`
- `DB_HOST` (default: `OCHAL25109748\SQLEXPRESS`)
- `ODBC_DRIVER` (default: `ODBC Driver 17 for SQL Server`)
- `DB_TRUST_CERT` (default: `yes`)
- `CORS_ALLOWED_ORIGINS` (default: `*`)
- `ZHIPUAI_API_KEY`
- `CACHE_TTL_SECONDS` (default: `3600`)

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
