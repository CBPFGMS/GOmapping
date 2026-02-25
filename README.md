# GOmapping

## Overview
GOmapping is a full-stack web application for managing mappings between **Global Organizations** and **Instance Organizations**.  
It provides:
- duplicate/similarity detection for global organizations
- merge/remap decision tracking and execution
- external data synchronization from UNOCHA CBPF APIs
- optional AI recommendation for master organization selection

---

## Tech Stack
- **Frontend**: React + Vite + React Router
- **Backend**: Django + Django REST Framework
- **Database**: Microsoft SQL Server (ODBC Driver 17)
- **AI (optional)**: ZhipuAI
- **External data source**: UNOCHA CBPF CSV APIs

---

## Repository Structure
- `GOmapping-frontend/` - frontend app
- `GOmapping-backend/` - backend app
  - `api/` - API endpoints and sync services
  - `orgnizations/` - data models
  - `scripts/` - data import/sync scripts
  - `main/` - Django project settings

---

## Prerequisites
- Node.js >= 18
- Python >= 3.12
- SQL Server
- ODBC Driver 17 for SQL Server

## Quick Start

### database
Before running the backend, configure database credentials via environment variables:

go to GOmapping\GOmapping-backend\main\settings.py, you need to configure here
DATABASES = {
    "default": {
        "ENGINE": "mssql",
        "NAME": "gomapping",
        "USER": "demo",
        "PASSWORD": '',
        "HOST":'',
        "OPTIONS": {
            "driver": "ODBC Driver 17 for SQL Server",
            "extra_params": "TrustServerCertificate=yes",  
        },
    }
}
### backend
1. cd GOmapping-backend
2. pip install -r requirements.txt
3. python manage.py migrate


### frontend
1. cd GOmapping-frontend
2. npm install
3. npm run dev

