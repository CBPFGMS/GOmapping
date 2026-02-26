# GOmapping

GOmapping is a full-stack app for managing mappings between **Global Organizations** and **Instance Organizations**.

## Features
- Duplicate/similarity detection for Global Organizations
- Merge decision recording and execution
- Data sync from UNOCHA CBPF APIs
- Optional AI recommendation for KEEP/MERGE decisions

## Tech Stack
- Frontend: React + Vite + React Router
- Backend: Flask + SQLAlchemy
- Database: SQLite (default)
- AI: Azure OpenAI (optional)

## Repository Structure
- `GOmapping-frontend/` - frontend app
- `GOmapping-backend-flask/` - Flask backend
- `GOmapping-backend/` - legacy Django backend (reference only)

## Prerequisitess
- Node.js >= 18
- Python >= 3.12

## Quick Start

### 1) Start backend (Flask)
```
cd GOmapping-backend-flask
pip install -r requirements.txt
python app.py
```

Backend runs at `http://localhost:8000`.

### 2) Start frontend
```bash
cd GOmapping-frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

## Database

SQLite:
- File path: `GOmapping-backend-flask/gomapping.db`
- Tables are auto-created on startup (`AUTO_CREATE_TABLES=true` by default)

Important:
- Do **not** commit `gomapping.db` to GitHub.
- Keep the database file on persistent storage in production.


