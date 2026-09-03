# Crowd-Report Verification and Confidence Dashboard for Municipal Disaster Coordination

## Problem Overview
A municipality receives crowd-sourced complaints related to roads, street lighting, and waste. Decision-makers cannot verify these reports quickly enough. This project will eventually support citizen reports, evidence, corroboration, verification, confidence scoring, priority scoring, explainable decisions, and role-based views.

## Current Phase
Phase 1 — Project Foundation

## Technology Stack
- Frontend: React + Vite
- Backend: Python + FastAPI
- Future database: PostgreSQL
- Future map: Leaflet + OpenStreetMap

## Folder Structure
```
municipality-crowd-verification/
├── backend/
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── database/
│   ├── utils/
│   ├── scripts/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── utils/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── .env.example
│   └── package.json
├── dataset/
├── experiments/
├── tests/
├── docs/
├── .gitignore
└── README.md
```

## Prerequisites
- Node.js 18+ and npm
- Python 3.11+ or compatible Python 3.x
- Git

## Backend Installation
1. Open a terminal in `backend/`
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate the environment:
   - Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
   - Windows CMD: `.\.venv\Scripts\activate`
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Frontend Installation
1. Open a terminal in `frontend/`
2. Install Node dependencies:
   ```bash
   npm install
   ```

## How to start the project for demonstration
To quickly launch both the backend and frontend for local demonstration, simply double-click the **`start_project.bat`** file in the project root.

This launcher will:
- Check if ports 8000 and 5173 are free.
- Start the backend and frontend servers in independent windows.
- Wait for the backend health check to pass.
- Automatically open the frontend in your default browser.

Alternatively, you can manually start the services below.

## How to Start FastAPI (Manual)
From `backend/` run:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## How to Start React (Manual)
From `frontend/` run:
```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

## Development URLs
- Backend API: `http://localhost:8000/`
- Backend health: `http://localhost:8000/health`
- Frontend: `http://localhost:5173/`

## Notes
- This phase includes only the project foundation, backend health endpoints, and frontend status page.
- PostgreSQL, maps, authentication, dashboards, confidence scoring, and verification logic will be implemented in later phases.
